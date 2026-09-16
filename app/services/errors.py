class Ps2TubeError(RuntimeError):
    """Error base controlado del backend."""


class DownloadError(Ps2TubeError):
    """Fallo al descargar el video de origen."""


class ConversionError(Ps2TubeError):
    """Fallo al convertir el video a formato PS2."""
