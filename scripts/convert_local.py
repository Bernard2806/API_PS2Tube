"""Descarga un video de YouTube y lo convierte a un MPEG-PS reproducible en PS2.

El formato de salida apunta a Simple Media System (SMS): video MPEG-1/2 en un
program stream (`.mpg`), audio MP2 y dimensiones multiplas de 16.

Uso:
    python scripts/convert_local.py --url "https://youtu.be/XXXXXXXXXXX"
    python scripts/convert_local.py --profile mpeg1 --url "..."
    python scripts/convert_local.py            # modo interactivo
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import yt_dlp

CACHE_DIR = Path("cache")
TEMP_DIR = Path("temp")


class ConversionError(RuntimeError):
    """Error controlado durante la descarga o la conversion."""


@dataclass(frozen=True)
class Ps2Profile:
    """Perfil de codificacion compatible con SMS.

    Las dimensiones deben ser multiplos de 16: SMS rechaza (o reproduce mal)
    videos con lados que no cumplen esa condicion.
    """

    name: str
    codec: str
    width: int
    height: int
    video_kbps: int
    audio_kbps: int
    fps: str = "30000/1001"
    gop: int = 15

    def validate(self) -> None:
        for axis, value in (("width", self.width), ("height", self.height)):
            if value % 16 != 0:
                raise ConversionError(
                    f"{axis}={value} no es multiplo de 16 en el perfil '{self.name}'."
                )


PROFILES: dict[str, Ps2Profile] = {
    "mpeg1": Ps2Profile("mpeg1", "mpeg1video", 352, 240, 1150, 192),
    "mpeg2": Ps2Profile("mpeg2", "mpeg2video", 640, 480, 2500, 192),
    "mpeg2-hq": Ps2Profile("mpeg2-hq", "mpeg2video", 720, 480, 4000, 224),
}


def sanitize_filename(title: str, max_length: int = 80) -> str:
    """Convierte un titulo en un nombre de archivo seguro y portable.

    Quita acentos, restringe a ASCII, reemplaza caracteres invalidos y limita
    la longitud para no generar rutas problemáticas en FAT/exFAT.
    """
    normalized = (
        unicodedata.normalize("NFKD", title)
        .encode("ascii", "ignore")
        .decode("ascii")
    )
    cleaned = "".join(c if c.isalnum() or c in " _-" else "_" for c in normalized)
    cleaned = "_".join(cleaned.split())
    return cleaned[:max_length].strip("._-") or "video"


def require_tool(name: str) -> None:
    """Verifica que un binario externo exista antes de usarlo."""
    if shutil.which(name) is None:
        raise ConversionError(
            f"'{name}' no está instalado o no está en el PATH. "
            f"Instalalo antes de continuar."
        )


def _downloaded_path(ydl: yt_dlp.YoutubeDL, info: dict) -> Path:
    """Resuelve la ruta real del archivo descargado (evita asumir la extensión)."""
    for entry in info.get("requested_downloads") or []:
        filepath = entry.get("filepath")
        if filepath:
            return Path(filepath)
    return Path(ydl.prepare_filename(info))


def download_video(url: str, max_height: int = 480) -> tuple[str, Path]:
    """Descarga un video de YouTube (<= max_height) y devuelve (titulo, ruta)."""
    ydl_opts = {
        # Prefiere pistas <= max_height; el mejor plan B tambien queda acotado.
        "format": (
            f"bestvideo[height<={max_height}]+bestaudio/"
            f"best[height<={max_height}]"
        ),
        "format_sort": [f"res:{max_height}"],
        "outtmpl": str(TEMP_DIR / "download.%(ext)s"),
        "merge_output_format": "mp4",
        "noplaylist": True,
        "quiet": True,
        "no_warnings": True,
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print("⬇️  Descargando video...")
        info = ydl.extract_info(url, download=True)
        if info.get("entries"):
            info = next(iter(info["entries"]))
        title = info.get("title") or "video"
        path = _downloaded_path(ydl, info)

    if not path.is_file():
        raise ConversionError(f"No se encontró el archivo descargado: {path}")
    return title, path


def build_ffmpeg_command(
    input_path: Path, output_path: Path, profile: Ps2Profile
) -> list[str]:
    """Construye el comando FFmpeg para un MPEG-PS compatible con SMS."""
    profile.validate()
    # Escala respetando aspecto, rellena con negro y fuerza fps estándar.
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
        "-stats",
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
        "-f", "mpeg",           # Program stream (.mpg), obligatorio para SMS.
        str(output_path),
    ]


def convert_to_ps2(input_path: Path, output_path: Path, profile: Ps2Profile) -> None:
    """Ejecuta FFmpeg para convertir el video al perfil PS2 indicado."""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = build_ffmpeg_command(input_path, output_path, profile)
    print(f"🎥 Convirtiendo a PS2 (perfil '{profile.name}')...")
    try:
        subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError as exc:
        raise ConversionError(
            f"FFmpeg falló con código {exc.returncode}."
        ) from exc

    if not output_path.is_file() or output_path.stat().st_size == 0:
        raise ConversionError("FFmpeg no generó un archivo de salida válido.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-u", "--url", help="URL del video de YouTube")
    parser.add_argument(
        "-p", "--profile", choices=sorted(PROFILES), default="mpeg2",
        help="Perfil de calidad/códec (default: mpeg2)",
    )
    parser.add_argument(
        "-o", "--output-dir", type=Path, default=CACHE_DIR,
        help="Carpeta donde guardar el resultado (default: cache)",
    )
    parser.add_argument(
        "--max-height", type=int, default=480,
        help="Altura máxima a descargar antes de convertir (default: 480)",
    )
    parser.add_argument(
        "--keep-temp", action="store_true",
        help="No borrar la carpeta temporal (útil para depurar)",
    )
    return parser.parse_args(argv)


def run(args: argparse.Namespace) -> Path:
    profile = PROFILES[args.profile]
    require_tool("ffmpeg")

    url = (args.url or input("📺 Ingresá la URL de YouTube: ")).strip()
    if not url:
        raise ConversionError("No ingresaste ninguna URL.")

    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    args.output_dir.mkdir(parents=True, exist_ok=True)

    title, downloaded = download_video(url, args.max_height)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_title = sanitize_filename(title)
    output_folder = args.output_dir / f"{safe_title}_{timestamp}"
    output_path = output_folder / f"{safe_title}.mpg"

    convert_to_ps2(downloaded, output_path, profile)
    return output_path


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        output_path = run(args)
    except (ConversionError, yt_dlp.utils.DownloadError) as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\n⚠️  Cancelado por el usuario.", file=sys.stderr)
        return 130
    finally:
        if not getattr(args, "keep_temp", False):
            shutil.rmtree(TEMP_DIR, ignore_errors=True)

    print(f"✅ Video listo para PS2: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
