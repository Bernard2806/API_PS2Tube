import os
import subprocess
import yt_dlp
from datetime import datetime
import shutil

# Carpeta donde se guardan los resultados y los archivos temporales
CACHE_DIR = "cache"
TEMP_DIR = "temp"

def sanitize_filename(title: str) -> str:
    """
    Limpia un texto para que pueda usarse como nombre de archivo.
    Solo deja letras, números, espacio, guion y guion bajo.
    """
    return "".join(c if c.isalnum() or c in " _-" else "_" for c in title)

def download_video(url: str):
    """
    Descarga un video de YouTube con yt-dlp en resolución baja (máximo 480p).
    Devuelve el título del video y la ruta del archivo descargado.
    """
    ydl_opts = {
        # Elige la mejor versión con resolución <= 480p (para que no pese demasiado)
        'format': 'best[ext=mp4][height<=480]/best[height<=480]/best',
        # Ruta de salida dentro de la carpeta temporal
        'outtmpl': os.path.join(TEMP_DIR, 'download.%(ext)s'),
        'merge_output_format': 'mp4',  # Fuerza a mp4 si descarga audio+video separados
        'quiet': True,                 # Oculta logs innecesarios
        'no_warnings': True,           # Evita mostrar advertencias
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        print("⬇️ Descargando video...")
        info = ydl.extract_info(url, download=True)
        # Devuelve el título y la ruta al archivo mp4 final
        return info['title'], os.path.join(TEMP_DIR, 'download.mp4')

def convert_to_ps2(input_path: str, output_path: str):
    """
    Convierte el video descargado a formato compatible con PS2.
    Usa MPEG-2 con resolución reducida y bitrate bajo (para pruebas rápidas).
    """
    cmd = [
        'ffmpeg',
        '-y',                      # Sobrescribe si ya existe el archivo destino
        '-i', input_path,          # Archivo de entrada
        '-vf', 'scale=480:360,setsar=1',   # Escala a 480x360 y corrige proporción
        '-c:v', 'mpeg2video',      # Codec de video: MPEG-2 (lo soporta PS2)
        '-b:v', '800k',            # Bitrate bajo para videos de prueba
        '-c:a', 'mp2',             # Codec de audio: MP2 (simple y compatible)
        '-b:a', '128k',            # Bitrate de audio bajo
        '-ar', '44100',            # Frecuencia de muestreo de audio
        '-target', 'ntsc-dvd',     # Perfil NTSC DVD (compatible con PS2 NTSC)
        output_path
    ]

    print("🎥 Convirtiendo (modo rápido/pruebas)...")
    # Ejecuta FFmpeg y lanza excepción si falla
    subprocess.run(cmd, check=True)

def main():
    try:
        # Pedir al usuario la URL del video
        url = input("📺 Ingresá la URL de YouTube: ").strip()
        if not url:
            print("⚠️ No ingresaste ninguna URL.")
            return

        # Descargar video
        title, input_path = download_video(url)

        # Crear nombre de carpeta de salida con título y timestamp
        safe_title = sanitize_filename(title)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_folder = os.path.join(CACHE_DIR, f"{safe_title}_{timestamp}")
        os.makedirs(output_folder, exist_ok=True)

        # Definir ruta de salida del archivo convertido
        output_path = os.path.join(output_folder, "ps2_ready.mpg")

        # Convertir a formato PS2
        convert_to_ps2(input_path, output_path)

        print(f"✅ Video convertido (pruebas): {output_path}")

    finally:
        # Borrar carpeta temporal después de usarla (limpieza automática)
        if os.path.exists(TEMP_DIR):
            shutil.rmtree(TEMP_DIR, ignore_errors=True)

if __name__ == "__main__":
    # Crear carpetas necesarias si no existen
    os.makedirs(TEMP_DIR, exist_ok=True)
    os.makedirs(CACHE_DIR, exist_ok=True)
    main()
