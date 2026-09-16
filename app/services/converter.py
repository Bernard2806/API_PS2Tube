import shutil
import subprocess
from pathlib import Path

from app.services.errors import ConversionError
from app.services.profiles import Ps2Profile


def ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


def build_command(
    input_path: Path, output_path: Path, profile: Ps2Profile
) -> list[str]:
    """Construye el comando FFmpeg para un MPEG-PS compatible con SMS."""
    profile.validate()
    video_filter = (
        f"scale={profile.width}:{profile.height}:force_original_aspect_ratio=decrease,"
        f"pad={profile.width}:{profile.height}:(ow-iw)/2:(oh-ih)/2:color=black,"
        f"setsar=1,fps={profile.fps}"
    )
    return [
        "ffmpeg",
        "-y",
        "-hide_banner",
        "-loglevel", "error",
        "-nostats",
        "-progress", "pipe:1",
        "-i", str(input_path),
        "-vf", video_filter,
        "-c:v", profile.codec,
        "-b:v", f"{profile.video_kbps}k",
        "-maxrate", f"{profile.video_kbps}k",
        "-bufsize", f"{profile.video_kbps * 2}k",
        "-g", str(profile.gop),
        "-pix_fmt", "yuv420p",
        "-c:a", "mp2",
        "-b:a", f"{profile.audio_kbps}k",
        "-ar", "48000",
        "-ac", "2",
        "-f", "mpeg",
        str(output_path),
    ]


def _parse_time(line: str) -> float | None:
    if line.startswith("out_time_us="):
        raw = line.split("=", 1)[1].strip()
        try:
            return int(raw) / 1_000_000
        except ValueError:
            return None
    return None


def convert(
    input_path: Path,
    output_path: Path,
    profile: Ps2Profile,
    duration: float | None = None,
    on_progress=None,
) -> None:
    """Ejecuta FFmpeg y reporta progreso (0.0-1.0) si hay duracion conocida."""
    if not ffmpeg_available():
        raise ConversionError("ffmpeg no esta instalado o no esta en el PATH.")

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_command(input_path, output_path, profile)

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
        )
    except OSError as exc:
        raise ConversionError(f"No se pudo iniciar FFmpeg: {exc}") from exc

    assert proc.stdout is not None
    for line in proc.stdout:
        if on_progress and duration:
            seconds = _parse_time(line.strip())
            if seconds is not None:
                on_progress(min(seconds / duration, 1.0))

    code = proc.wait()
    if code != 0:
        raise ConversionError(f"FFmpeg fallo con codigo {code}.")

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise ConversionError("FFmpeg no genero un archivo de salida valido.")
