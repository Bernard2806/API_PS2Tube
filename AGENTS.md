# AGENTS.md

Guía obligatoria para cualquier agente (IA o humano) que trabaje en este repositorio.

## Qué es este repositorio

`API_PS2Tube` es **únicamente el backend** del proyecto PS2Tube. No contiene código
de la consola PS2 ni de los reproductores (SMS, OPL, etc.). Su responsabilidad es:

1. Crear **sesiones** emparejables mediante un QR que se muestra en la PS2.
2. Permitir que un celular **gestione una cola** de enlaces de YouTube.
3. **Descargar y convertir** cada video a MPEG-PS reproducible en PS2.
4. Exponer los archivos convertidos para que la PS2 los lea (por SMB, o por HTTP
   como fallback).

## Ecosistema PS2Tube (repos separados)

Este proyecto vive en varios repositorios independientes. **No mezclar código de
otro componente acá.**

| Repositorio | Responsabilidad |
|---|---|
| `API_PS2Tube` (este) | Backend FastAPI: sesiones, cola, conversión y entrega de archivos. |
| Cliente PS2 (separado, pendiente) | App para PS2 (C / ps2sdk) que pide el QR, lo dibuja y lanza SMS con el video que le indica el backend. |
| Reproductor PS2 | SMS (Simple Media System) u otro. Por ahora **no se modifica**: se usa SMB. |

Si una tarea necesita tocar la PS2, SMS o el firmware, **no corresponde a este repo**.

## Flujo completo

```
PS2 (cliente) ── pide QR ──► Backend ── GET /api/v1/sessions/{id}/qr.png
      │                                    ▲
      │ escanea con el celular              │ el celular agrega links a la cola
      ▼                                    │
  Celular ── POST /queue ──────────────────┘
      ▲
      │ el worker descarga + convierte (prefetch secuencial)
      ▼
  Backend guarda .mpg en data/media/<session>/<item>.mpg
      │
      │ PS2 hace poll de GET /api/v1/sessions/{id}/next
      ▼
  PS2 reproduces el .mpg desde SMB (smb_prefix) o por HTTP (/media/...)
```

Modo de reproducción: **cola secuencial con pre-conversión**. El worker convierte
el siguiente item mientras suena el actual (`prefetch_ahead`). No hay streaming
byte a byte.

## Arquitectura del backend

- **Framework**: FastAPI + Uvicorn (async).
- **Persistencia**: SQLite vía `sqlite3` de la stdlib. Sin ORM.
- **Worker**: tarea asyncio (`QueueWorker`) que corre dentro del proceso de la API.
  Ejecuta trabajo bloqueante (yt-dlp, ffmpeg) con `asyncio.to_thread`.
- **Conversión**: `ffmpeg` externo, perfil MPEG-PS + MP2 (`app/services/profiles.py`).
- **QR**: librería `segno` (PNG puro Python).
- **Web móvil**: HTML/JS/CSS estáticos (sin build) en `app/web/static/`.

### Estructura

```
app/
  main.py                 # App FastAPI, lifespan, montaje de estáticos
  config.py               # Settings (pydantic-settings, prefijo PS2TUBE_)
  schemas.py              # Modelos Pydantic de entrada/salida
  api/
    deps.py               # Dependencias (db, settings)
    serializers.py        # DB dict -> respuesta de API (urls, rutas SMB)
    routes/
      health.py           # GET /health (reporta ffmpeg y yt-dlp disponibles)
      sessions.py         # CRUD de sesiones y cola, /next, /qr.png
      media.py            # GET /media/<session>/<file>
  core/
    database.py           # SQLite: sesiones e items
    ids.py                # IDs y códigos de emparejamiento
  services/
    profiles.py           # Perfiles PS2 (dimensiones multiplas de 16)
    downloader.py         # yt-dlp (import perezoso)
    converter.py          # ffmpeg -> MPEG-PS
    transcoder.py         # orquesta descarga + conversión
    worker.py             # prefetch secuencial
  web/static/             # UI móvil
scripts/
  convert_local.py        # CLI histórico para convertir un video suelto
tests/                    # pytest
```

## Entorno de desarrollo (¡importante!)

Esta máquina corre **WSL**, pero Python está instalado en **Windows**:

- No existe `python`/`python3` en el PATH de WSL.
- Usar el intérprete de Windows: `/mnt/c/Python314/python.exe`.
- `ffmpeg` y `yt-dlp` **no están instalados** actualmente. La API arranca igual
  (el import de `yt_dlp` es perezoso), pero la conversión real fallará hasta
  instalarlos. `/health` lo reporta.

## Comandos

```bash
# Dependencias (desde la raíz del repo)
/mnt/c/Python314/python.exe -m pip install -r requirements-dev.txt

# Levantar la API
/mnt/c/Python314/python.exe -m uvicorn app.main:app --host 0.0.0.0 --port 8000

# Tests
/mnt/c/Python314/python.exe -m pytest -q

# Lint
/mnt/c/Python314/python.exe -m ruff check .

# Verificar compilación (lo mismo que hace el CI)
/mnt/c/Python314/python.exe -m compileall -q app
/mnt/c/Python314/python.exe -c "import app.main"
```

## Reglas obligatorias

### 1. Commits convencionales en español

Todas las contribuciones usan [Conventional Commits](https://www.conventionalcommits.org/).
El **tipo y el scope** son los estándar (en inglés); la **descripción va en español**,
en modo imperativo, en minúscula y **sin punto final**.

Tipos permitidos: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`,
`build`, `ci`, `chore`, `revert`.

Formato:

```
<tipo>(<scope opcional>): <descripción en español>

[cuerpo opcional en español]

[footer opcional]
```

Ejemplos válidos:

```
feat(sessions): agregar endpoint para reproducir un item ahora
fix(worker): evitar convertir dos items a la vez
fix: corregir bucle infinito en /next
docs: documentar variables de entorno
test(profiles): cubrir validacion de dimensiones multiplas de 16
ci: validar compilacion y tests en cada push
chore: actualizar dependencias
refactor(converter): extraer construccion del comando ffmpeg
```

Ejemplos **inválidos**:

```
Fix bug                  # sin tipo ni formato
feat: Add QR endpoint    # descripcion en ingles
feat: agregar QR.        # punto final
update                   # ambiguo
```

### 2. Límites del repositorio

- No agregar código de PS2, SMS, firmware ni scripts de consola.
- No cambiar el transporte (SMB + SMS) sin decisión explícita del dueño.
- No romper el contrato de la API (`/api/v1/...`) sin actualizar `README.md` y tests.

### 3. Estilo de código

- Python 3.11+ (target de Ruff). Código y nombres en inglés; **docstrings y
  mensajes de usuario en español**.
- No agregar comentarios obvios. Docstrings sí.
- Formato de línea: 88 columnas.
- Mantener la separación por capas: `routes` no toca `sqlite3` directo; usa
  `Database`. La lógica de conversión vive en `services/`.

### 4. Pruebas y verificación

- Todo cambio de comportamiento debe venir con tests en `tests/`.
- Los tests **no** deben depender de `ffmpeg` ni de `yt-dlp` (el worker se
  desactiva con `PS2TUBE_WORKER_ENABLED=false` en `tests/conftest.py`).
- Antes de terminar: `ruff check .`, `python -m compileall -q app` y `pytest -q`.

## Variables de entorno

Prefijo `PS2TUBE_` (ver `.env.example`):

| Variable | Default | Descripción |
|---|---|---|
| `PS2TUBE_PUBLIC_BASE_URL` | derivada del request | URL pública usada en el QR y los enlaces. |
| `PS2TUBE_SMB_PREFIX` | vacío | Ruta SMB que ve la PS2, ej. `//192.168.1.50/ps2tube`. |
| `PS2TUBE_DATA_DIR` | `data` | Base de datos, media y temporales. |
| `PS2TUBE_DEFAULT_PROFILE` | `mpeg2` | Perfil PS2: `mpeg1`, `mpeg2`, `mpeg2-hq`. |
| `PS2TUBE_MAX_HEIGHT` | `480` | Altura máxima de descarga. |
| `PS2TUBE_PREFETCH_AHEAD` | `1` | Items preconvertidos por delante del playhead. |
| `PS2TUBE_WORKER_ENABLED` | `true` | Desactivar el worker (tests). |
| `PS2TUBE_KEEP_TEMP` | `false` | Conservar temporales para depurar. |

## Estado actual y pendientes

Implementado: sesiones + QR, cola (agregar/listar/borrar/reordenar/play-now),
`/next` + `/complete`, worker de pre-conversión, entrega por `/media` y SMB,
UI móvil, tests, CI.

Pendiente / ideas:
- Autenticación real del emparejamiento (hoy el código de 6 caracteres es el secreto).
- Perfil de conversión por item.
- Cola de trabajos robusta (hoy es una tarea en el proceso; no sobrevive a reinicios
  a mitad de conversión).
- Cliente PS2 que muestre el QR y lance SMS.
