import os
import time
import random
import pygame
import pyarrow as pa
from dora import Node

def setup_hardware():
    pygame.mixer.init()
    pygame.mixer.music.set_volume(1.0)
    for i in range(pygame.mixer.get_num_channels()):
        pygame.mixer.Channel(i).set_volume(1.0)
    # Assume 'sounds' directory is located at nodes/audio/sounds/ relative to this file.
    sounds_dir = os.path.join(os.path.dirname(__file__), "..", "sounds")
    return sounds_dir

def play_startup_sound(sounds_dir):
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
        channel.play(sound)
        print("Playing startup sound")
        time.sleep(2)
    except pygame.error as e:
        print(f"Error playing startup sound: {e}")

def play_sound(sounds_dir, filename):
    sound_file = os.path.join(sounds_dir, filename)
    if not os.path.exists(sound_file):
        print(f"Sound file not found: {sound_file}")
        return
    try:
        sound = pygame.mixer.Sound(sound_file)
        channel = pygame.mixer.find_channel()
        if channel:
            channel.play(sound)
            print(f"Playing sound: {filename}")
    except pygame.error as e:
        print(f"Error playing sound {filename}: {e}")

def load_volume():
    vol_file = os.path.join(os.path.dirname(__file__), "volume.cfg")
    try:
        with open(vol_file, "r") as f:
            vol = float(f.read().strip())
            return vol
    except Exception:
        return 1.0

def save_volume(vol):
    vol_file = os.path.join(os.path.dirname(__file__), "volume.cfg")
    try:
        with open(vol_file, "w") as f:
            f.write(str(vol))
    except Exception as e:
        print("Could not save volume:", e)

def main():
    sounds_dir = setup_hardware()
    vol = load_volume()
    pygame.mixer.music.set_volume(vol)
    for i in range(pygame.mixer.get_num_channels()):
        pygame.mixer.Channel(i).set_volume(vol)
    play_startup_sound(sounds_dir)
    node = Node()
    print("Audio node started")
    for event in node:
        if event["type"] == "INPUT":
            if event["id"] == "play_sound":
                # Assume event["value"] is a pyarrow array with the sound filename as the first element.
                try:
                    if hasattr(event["value"], "to_pylist"):
                        filename_list = event["value"].to_pylist()
                        filename = filename_list[0] if filename_list else ""
                    else:
                        filename = event["value"]
                except Exception:
                    filename = event["value"]
                play_sound(sounds_dir, filename)

            if event["id"] == "scan_sounds":
                available = [f for f in os.listdir(sounds_dir) if f.endswith('.mp3')]
                node.send_output("available_sounds", pa.array(available), metadata={})
            elif event["id"] == "stop":
                print("Stopping all sounds")
                pygame.mixer.stop()
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
