import asyncio
import logging
import shutil

from app.config import Settings
from app.core.database import Database
from app.services.errors import Ps2TubeError
from app.services.profiles import get_profile
from app.services.transcoder import produce

logger = logging.getLogger(__name__)


class QueueWorker:
    """Prefetch secuencial: mantiene convertidos los proximos `prefetch_ahead`.

    La PS2 reproduce de a uno; este worker convierte el siguiente mientras
    suena el actual, de modo que el salto sea instantaneo.
    """

    def __init__(self, db: Database, settings: Settings):
        self.db = db
        self.settings = settings
        self._task: asyncio.Task | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._run(), name="queue-worker")

    async def stop(self) -> None:
        if self._task is None:
            return
        self._task.cancel()
        try:
            await self._task
        except asyncio.CancelledError:
            pass
        self._task = None

    async def _run(self) -> None:
        while True:
            try:
                await self.tick()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Fallo el ciclo del worker")
            await asyncio.sleep(self.settings.worker_interval)

    async def tick(self) -> None:
        sessions = await asyncio.to_thread(self.db.list_sessions)
        for session in sessions:
            items = await asyncio.to_thread(self.db.get_items, session["id"])
            target = self._pick(session, items)
            if target is not None:
                await self._process(session, target)
                return

    def _pick(self, session: dict, items: list[dict]) -> dict | None:
        if not items:
            return None

        current = next(
            (i for i in items if i["id"] == session["current_item_id"]), None
        )
        if current is None:
            candidates = items
        else:
            if current["status"] == "queued":
                return current
            candidates = [i for i in items if i["position"] > current["position"]]

        ready = [i for i in candidates if i["status"] == "ready"]
        if len(ready) >= self.settings.prefetch_ahead:
            return None

        queued = [i for i in candidates if i["status"] == "queued"]
        return queued[0] if queued else None

    async def _process(self, session: dict, item: dict) -> None:
        item_id = item["id"]
        session_id = session["id"]
        profile = get_profile(self.settings.default_profile)
        output_path = self.settings.media_dir / session_id / f"{item_id}.mpg"
        temp_dir = self.settings.temp_dir / item_id

        await asyncio.to_thread(
            self.db.update_item,
            item_id,
            status="converting",
            progress=0.01,
            error=None,
        )

        try:
            result = await asyncio.to_thread(
                produce,
                item["url"],
                temp_dir,
                output_path,
                profile,
                self.settings.max_height,
                lambda value: self.db.update_item(
                    item_id, progress=round(value * 0.4, 3)
                ),
                lambda value: self.db.update_item(
                    item_id, progress=round(0.4 + value * 0.6, 3)
                ),
            )
            await asyncio.to_thread(
                self.db.update_item,
                item_id,
                status="ready",
                progress=1.0,
                filename=result.filename,
                title=result.title,
                duration=result.duration,
            )
        except Ps2TubeError as exc:
            await asyncio.to_thread(
                self.db.update_item, item_id, status="failed", error=str(exc)
            )
        except Exception as exc:
            logger.exception("Error inesperado procesando %s", item_id)
            await asyncio.to_thread(
                self.db.update_item, item_id, status="failed", error=str(exc)
            )
        finally:
            if not self.settings.keep_temp:
                shutil.rmtree(temp_dir, ignore_errors=True)
