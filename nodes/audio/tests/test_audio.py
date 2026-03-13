"""Basic tests for the audio node."""

import os
import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_import_main():
    """Test that the main function can be imported and called."""
    from audio.main import main

    # Check that everything is working, and catch dora Runtime Exception as we're not running in a dora dataflow.
    with pytest.raises(RuntimeError):
        main()


def test_setup_hardware_falls_back_to_explicit_headphones(monkeypatch):
    """The mixer should try explicit headphone devices if defaults fail."""
    from audio import main as audio_main

    attempts = []

    def fake_init(**kwargs):
        attempts.append(
            (
                os.environ.get("SDL_AUDIODRIVER"),
                os.environ.get("AUDIODEV"),
                kwargs.get("devicename"),
            )
        )
        if os.environ.get("AUDIODEV") != "plughw:CARD=Headphones,DEV=0":
            raise audio_main.pygame.error("no device")

    monkeypatch.delenv("SDL_AUDIODRIVER", raising=False)
    monkeypatch.delenv("AUDIODEV", raising=False)
    monkeypatch.setattr(audio_main.pygame.mixer, "quit", lambda: None)
    monkeypatch.setattr(audio_main.pygame.mixer, "init", fake_init)
    monkeypatch.setattr(audio_main.pygame.mixer.music, "set_volume", lambda vol: None)
    monkeypatch.setattr(audio_main.pygame.mixer, "get_num_channels", lambda: 0)

    sounds_dir = audio_main.setup_hardware()

    assert attempts[0] == (None, None, None)
    assert ("alsa", "plughw:CARD=Headphones,DEV=0", None) in attempts
    assert sounds_dir.endswith("/nodes/audio/sounds")


def test_setup_hardware_can_fall_back_to_dummy(monkeypatch):
    """The robot should keep booting even if real audio is unavailable."""
    from audio import main as audio_main

    attempts = []

    def fake_init(**kwargs):
        attempts.append(
            (
                os.environ.get("SDL_AUDIODRIVER"),
                os.environ.get("AUDIODEV"),
                kwargs.get("devicename"),
            )
        )
        if os.environ.get("SDL_AUDIODRIVER") != "dummy":
            raise audio_main.pygame.error("still unavailable")

    monkeypatch.delenv("SDL_AUDIODRIVER", raising=False)
    monkeypatch.delenv("AUDIODEV", raising=False)
    monkeypatch.setattr(audio_main.pygame.mixer, "quit", lambda: None)
    monkeypatch.setattr(audio_main.pygame.mixer, "init", fake_init)
    monkeypatch.setattr(audio_main.pygame.mixer.music, "set_volume", lambda vol: None)
    monkeypatch.setattr(audio_main.pygame.mixer, "get_num_channels", lambda: 0)

    audio_main.setup_hardware()

    assert attempts[-1] == ("dummy", None, None)
