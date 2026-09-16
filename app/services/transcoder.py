from dataclasses import dataclass
from pathlib import Path

from app.services import converter, downloader
from app.services.profiles import Ps2Profile


@dataclass
class TranscodeResult:
    title: str
    filename: str
    duration: float | None


def produce(
    url: str,
    temp_dir: Path,
    output_path: Path,
    profile: Ps2Profile,
    max_height: int = 480,
    on_download=None,
    on_convert=None,
) -> TranscodeResult:
    """Descarga y convierte un video, dejandolo listo para SMS."""
    temp_dir = Path(temp_dir)
    output_path = Path(output_path)
    temp_dir.mkdir(parents=True, exist_ok=True)

    video = downloader.download(url, temp_dir, max_height, on_progress=on_download)

    if on_convert is not None:
        on_convert(0.0)
    converter.convert(
        video.path,
        output_path,
        profile,
        duration=video.duration,
        on_progress=on_convert,
    )

    return TranscodeResult(video.title, output_path.name, video.duration)
