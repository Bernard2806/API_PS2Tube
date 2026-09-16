from dataclasses import dataclass

from app.services.errors import ConversionError


@dataclass(frozen=True)
class Ps2Profile:
    """Perfil de codificacion compatible con Simple Media System (SMS).

    SMS exige dimensiones multiplas de 16 y fps estandar. El contenedor de
    salida es un program stream MPEG (`.mpg`) con audio MP2.
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
                    f"{axis}={value} no es multiplo de 16 en el perfil "
                    f"'{self.name}'."
                )


PROFILES: dict[str, Ps2Profile] = {
    "mpeg1": Ps2Profile("mpeg1", "mpeg1video", 352, 240, 1150, 192),
    "mpeg2": Ps2Profile("mpeg2", "mpeg2video", 640, 480, 2500, 192),
    "mpeg2-hq": Ps2Profile("mpeg2-hq", "mpeg2video", 720, 480, 4000, 224),
}


def get_profile(name: str) -> Ps2Profile:
    try:
        return PROFILES[name]
    except KeyError as exc:
        raise ConversionError(f"Perfil desconocido: '{name}'") from exc
