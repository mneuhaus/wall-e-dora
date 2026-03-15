"""Main module for the Audio Node.

Handles audio playback using Pygame mixer, manages sound files,
and responds to Dora events for playing sounds and setting volume.
"""

import os
import time
from pathlib import Path

import pygame
import pyarrow as pa
from dora import Node


EMERGENCY_STOP_SOUND = "stopp.mp3"


def _build_audio_init_attempts() -> list[tuple[str | None, str | None, str]]:
    """Return ordered mixer initialization attempts.

    The robot sometimes boots without a usable default ALSA route because the
    system default points at HDMI. Try the environment/default first, then
    prefer the Pi headphone output explicitly, and finally fall back to a dummy
    sink so the rest of the robot can still start.
    """
    attempts: list[tuple[str | None, str | None, str]] = []
    seen: set[tuple[str | None, str | None]] = set()

    def add(driver: str | None, device: str | None, label: str):
        key = (driver, device)
        if key in seen:
            return
        seen.add(key)
        attempts.append((driver, device, label))

    env_driver = os.environ.get("SDL_AUDIODRIVER") or None
    env_device = os.environ.get("AUDIODEV") or None
    if env_driver or env_device:
        add(env_driver, env_device, "environment")

    add(None, None, "automatic")

    for device in (
        "plughw:CARD=Headphones,DEV=0",
        "hw:CARD=Headphones,DEV=0",
        "plughw:2,0",
        "hw:2,0",
    ):
        add("alsa", device, f"alsa:{device}")

    add("pulse", None, "pulse")
    add("dummy", None, "dummy")
    return attempts


def _init_mixer_with_fallback() -> tuple[bool, str]:
    """Initialize the mixer with robust fallbacks.

    Returns:
        Tuple of ``(audio_enabled, selected_backend)``.
    """
    errors: list[str] = []

    for driver, device, label in _build_audio_init_attempts():
        pygame.mixer.quit()

        if driver is None:
            os.environ.pop("SDL_AUDIODRIVER", None)
        else:
            os.environ["SDL_AUDIODRIVER"] = driver

        if device is None:
            os.environ.pop("AUDIODEV", None)
        else:
            os.environ["AUDIODEV"] = device

        try:
            pygame.mixer.init()
            print(f"Audio mixer initialized via {label}")
            return driver != "dummy", label
        except pygame.error as error:
            errors.append(f"{label}: {error}")

    print("Audio mixer fallback exhausted:")
    for error in errors:
        print(f"  - {error}")
    raise RuntimeError("Could not initialize any audio backend")


def setup_hardware() -> str:
    """Initialize Pygame mixer and return the path to the sounds directory."""
    audio_enabled, backend = _init_mixer_with_fallback()
    pygame.mixer.music.set_volume(1.0)
    for i in range(pygame.mixer.get_num_channels()):
        pygame.mixer.Channel(i).set_volume(1.0)
    if not audio_enabled:
        print(f"Audio running in silent fallback mode via {backend}")
    # Assume 'sounds' directory is located at nodes/audio/sounds/ relative to this file.
    sounds_dir = Path(__file__).resolve().parent.parent / "sounds"
    return str(sounds_dir)


def play_startup_sound(sounds_dir: str):
    """Play the startup sound if it exists."""
    startup_sound = os.path.join(sounds_dir, "startup.mp3")
    if not os.path.exists(startup_sound):
        print(f"Startup sound not found at {startup_sound}")
        return
    try:
        sound = pygame.mixer.Sound(startup_sound)
        channel = pygame.mixer.find_channel()
        if not channel:
            print("No available audio channels")
            return
        # Save current volume
        current_vol = channel.get_volume()
        # Set fixed startup volume at 5%
        channel.set_volume(0.05)
        channel.play(sound)
        print("Playing startup sound at 5% volume")
        time.sleep(2)
        # Restore original volume
        channel.set_volume(current_vol)
    except pygame.error as e:
        print(f"Error playing startup sound: {e}")

def play_sound(sounds_dir: str, filename: str, node=None):
    """Play the specified sound file."""
    sound_file = os.path.join(sounds_dir, filename)
    if not os.path.exists(sound_file):
        print(f"Sound file not found: {sound_file}")
        return False
    try:
        pygame.mixer.stop()
        sound = pygame.mixer.Sound(sound_file)
        channel = pygame.mixer.find_channel()
        if channel:
            channel.play(sound)
            print(f"Playing sound: {filename}")
            
            # Broadcast the currently playing sound if node is provided
            if node:
                node.send_output("current_sound", pa.array([filename]), metadata={})
            return True
        return False
    except pygame.error as e:
        print(f"Error playing sound {filename}: {e}")
        return False


def play_emergency_stop_sound(sounds_dir: str, node=None) -> bool:
    """Interrupt current playback and play the dedicated emergency stop clip."""
    print("Emergency stop: interrupting current audio and playing stop clip")
    return play_sound(sounds_dir, EMERGENCY_STOP_SOUND, node=node)


def load_volume() -> float:
    """Load the volume setting from the configuration file."""
    # TODO: Refactor to use the config node instead of volume.cfg
    vol_file = os.path.join(os.path.dirname(__file__), "volume.cfg")
    try:
        with open(vol_file, "r") as f:
            vol = float(f.read().strip())
            return vol
    except Exception:
        return 1.0


def save_volume(vol: float):
    """Save the volume setting to the configuration file."""
    # TODO: Refactor to use the config node instead of volume.cfg
    vol_file = os.path.join(os.path.dirname(__file__), "volume.cfg")
    try:
        with open(vol_file, "w") as f:
            f.write(str(vol))
    except Exception as e:
        print("Could not save volume:", e)


def main():
    """Main function for the Audio Node.

    Initializes hardware, loads settings, and enters the Dora event loop
    to handle audio playback and volume control commands.
    """
    sounds_dir = setup_hardware()
    vol = load_volume()
    pygame.mixer.music.set_volume(vol)
    for i in range(pygame.mixer.get_num_channels()):
        pygame.mixer.Channel(i).set_volume(vol)
    play_startup_sound(sounds_dir)
    node = Node()
    # Immediately broadcast current volume so UI reflects persisted value
    try:
        node.send_output("volume", pa.array([vol]), metadata={})
    except Exception:
        pass
    # Track current playing sound
    current_sound = None
    print("Audio node started")
    for event in node:
        if event["type"] == "INPUT":
            if event["id"] in ("play_sound", "play_sound_sequence"):
                # Assume event["value"] is a pyarrow array with the sound filename as the first element.
                try:
                    if hasattr(event["value"], "to_pylist"):
                        filename_list = event["value"].to_pylist()
                        filename = filename_list[0] if filename_list else ""
                    else:
                        filename = event["value"]
                except Exception:
                    filename = event["value"]
                
                success = play_sound(sounds_dir, filename, node)
                if success:
                    current_sound = filename

            if event["id"] == "scan_sounds":
                available = [f for f in os.listdir(sounds_dir) if f.endswith('.mp3')]
                node.send_output("available_sounds", pa.array(available), metadata={})
                # If a sound is playing, send it again to ensure the frontend knows about it
                if current_sound:
                    node.send_output("current_sound", pa.array([current_sound]), metadata={})
            elif event["id"] == "emergency_stop":
                success = play_emergency_stop_sound(sounds_dir, node)
                if success:
                    current_sound = EMERGENCY_STOP_SOUND
            elif event["id"] in ("stop", "stop_sequence"):
                print("Stopping all sounds")
                pygame.mixer.stop()
                current_sound = None
                node.send_output("current_sound", pa.array([""]), metadata={})
            elif event["id"] == "set_volume":
                print('set_volume: ', event['value'])
                try:
                    if hasattr(event["value"], "to_pylist"):
                        vol = float(event["value"].to_pylist()[0])
                    else:
                        vol = float(event["value"])
                    vol = max(0.0, min(1.0, vol))
                    pygame.mixer.music.set_volume(vol)
                    for i in range(pygame.mixer.get_num_channels()):
                        pygame.mixer.Channel(i).set_volume(vol)
                    node.send_output("volume", pa.array([vol]), metadata={})
                    save_volume(vol)
                except Exception as e:
                    print("Error setting volume:", e)
            elif event["id"] == "volume_tick":
                vol = pygame.mixer.music.get_volume()
                node.send_output("volume", pa.array([vol]), metadata={})

if __name__ == "__main__":
    main()
