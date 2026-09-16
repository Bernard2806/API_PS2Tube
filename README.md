# PS2Tube — Backend

Backend de PS2Tube: convierte enlaces de YouTube a MPEG-PS reproducible en una
PS2 con [Simple Media System (SMS)](https://github.com/NathanNeurotic/Simple-Media-System)
y gestiona la cola desde el celular mediante un QR.

> Este repositorio es **solo el backend**. El cliente de PS2 y SMS viven en
> repositorios aparte. Ver [AGENTS.md](AGENTS.md) para las reglas y el contexto.

## Cómo funciona

1. La PS2 pide una sesión y muestra un **QR** con `http://<host>/s/<codigo>`.
2. Escaneás el QR con el celular y pegás los enlaces de YouTube.
3. Un worker descarga y convierte cada video a **MPEG-2 + MP2 en un program
   stream `.mpg`** (perfil compatible con SMS).
4. La PS2 reproduce desde SMB; mientras suena un video, el siguiente ya está
   convertido (prefetch secuencial).

## Requisitos

- Python 3.11+
- `ffmpeg` en el PATH (para convertir)
- `yt-dlp` (se instala con `requirements.txt`)

## Instalación y uso

```bash
python -m pip install -r requirements.txt
cp .env.example .env          # ajustá PUBLIC_BASE_URL y SMB_PREFIX
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

- Documentación interactiva: `http://localhost:8000/docs`
- Salud y disponibilidad de herramientas: `GET /health`
- Web móvil: `http://localhost:8000/s/<codigo>`

### SMB para la PS2

Compartí `data/media` por Samba y apuntá `PS2TUBE_SMB_PREFIX` a esa ruta. El
backend devuelve en cada item `stream_path` (ruta SMB para SMS) y `http_url`
(fallback por HTTP).

## API (resumen)

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/v1/sessions` | Crea una sesión y devuelve `code`, `pair_url`, `qr_url`. |
| `GET` | `/api/v1/sessions/{id}` | Estado de la sesión. |
| `GET` | `/api/v1/sessions/code/{code}` | Resuelve un código a su sesión. |
| `GET` | `/api/v1/sessions/{id}/qr.png` | PNG del QR de emparejamiento. |
| `GET` | `/api/v1/sessions/{id}/queue` | Lista la cola. |
| `POST` | `/api/v1/sessions/{id}/queue` | Agrega uno o varios enlaces. |
| `POST` | `/api/v1/sessions/{id}/queue/reorder` | Reordena la cola. |
| `DELETE` | `/api/v1/sessions/{id}/queue/{item}` | Borra un item. |
| `POST` | `/api/v1/sessions/{id}/queue/{item}/play` | Reproduce ese item ahora. |
| `GET` | `/api/v1/sessions/{id}/next` | La PS2 consulta el próximo video listo (204 si no hay). |
| `POST` | `/api/v1/sessions/{id}/complete` | La PS2 avisa que terminó el actual. |
| `GET` | `/media/{session}/{file}` | Entrega del `.mpg` por HTTP. |

## Perfiles de conversión

| Perfil | Códec | Resolución | Video | Audio |
|---|---|---|---|---|
| `mpeg1` | MPEG-1 | 352x240 | 1150k | 192k MP2 |
| `mpeg2` (default) | MPEG-2 | 640x480 | 2500k | 192k MP2 |
| `mpeg2-hq` | MPEG-2 | 720x480 | 4000k | 224k MP2 |

Todas las dimensiones son múltiplas de 16, requisito de SMS.

## Desarrollo

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
python -m ruff check .
```

## Aviso legal

Descargar contenido de YouTube puede infringir sus términos de servicio y
derechos de autor. Usá este proyecto para contenido propio o con permiso.

## Licencia

MIT. Ver [LICENSE](LICENSE).
