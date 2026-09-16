from pathlib import Path

import pytest

from app.services.converter import build_command
from app.services.errors import ConversionError
from app.services.profiles import PROFILES, Ps2Profile, get_profile


def test_all_profiles_use_mod16_dimensions():
    for profile in PROFILES.values():
        profile.validate()
        assert profile.width % 16 == 0
        assert profile.height % 16 == 0


def test_invalid_profile_dimensions_are_rejected():
    bad = Ps2Profile("bad", "mpeg2video", 480, 360, 1000, 128)
    with pytest.raises(ConversionError):
        bad.validate()


def test_unknown_profile_raises():
    with pytest.raises(ConversionError):
        get_profile("nope")


def test_build_command_targets_mpeg_program_stream():
    command = build_command(
        Path("in.mp4"), Path("out.mpg"), PROFILES["mpeg2"]
    )
    assert "-target" not in command
    assert command[command.index("-f") + 1] == "mpeg"
    assert command[command.index("-c:a") + 1] == "mp2"
    assert command[command.index("-ar") + 1] == "48000"
    assert command[-1] == "out.mpg"
    video_filter = command[command.index("-vf") + 1]
    assert "scale=640:480" in video_filter
    assert "fps=30000/1001" in video_filter
