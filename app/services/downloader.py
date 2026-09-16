from dataclasses import dataclass
from pathlib import Path

from app.services.errors import DownloadError


@dataclass
class DownloadedVideo:
    title: str
    path: Path
    duration: float | None


def _format_selector(max_height: int) -> str:
    return (
        f"bestvideo[height<={max_height}]+bestaudio/"
        f"best[height<={max_height}]"
    )


def _resolve_path(ydl, info: dict) -> Path:
    for entry in info.get("requested_downloads") or []:
        filepath = entry.get("filepath")
        if filepath:
            return Path(filepath)
    return Path(ydl.prepare_filename(info))


def download(
    url: str,
    dest_dir: Path,
    max_height: int = 480,
    on_progress=None,
) -> DownloadedVideo:
    """Descarga un video de YouTube y devuelve titulo, ruta y duracion."""
    try:
        import yt_dlp
    except ImportError as exc:
        raise DownloadError("yt-dlp no esta instalado.") from exc

    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)

    def hook(payload: dict) -> None:
        if on_progress is None or payload.get("status") != "downloading":
            return
        total = payload.get("total_bytes") or payload.get("total_bytes_estimate")
        if total:
            on_progress(min(payload.get("downloaded_bytes", 0) / total, 1.0))

    ydl_opts = {
        "format": _format_selector(max_height),
        "format_sort": [f"res:{max_height}"],
        "outtmpl": str(dest_dir / "download.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
        "progress_hooks": [hook],
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if info.get("entries"):
                info = next(iter(info["entries"]))
            title = info.get("title") or "video"
            path = _resolve_path(ydl, info)
    except DownloadError:
        raise
    except Exception as exc:
        raise DownloadError(f"No se pudo descargar el video: {exc}") from exc

    if not path.is_file():
        raise DownloadError(f"No se encontro el archivo descargado: {path}")

    duration = info.get("duration")
    return DownloadedVideo(title, path, float(duration) if duration else None)
