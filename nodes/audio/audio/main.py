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
        sound.set_volume(1.0)
        channel = pygame.mixer.find_channel()
        if not channel:
            print("No available audio channels")
            return
        channel.set_volume(1.0)
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
        sound.set_volume(1.0)
        channel = pygame.mixer.find_channel()
        if channel:
            channel.set_volume(1.0)
            channel.play(sound)
            print(f"Playing sound: {filename}")
    except pygame.error as e:
        print(f"Error playing sound {filename}: {e}")

def main():
    sounds_dir = setup_hardware()
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

if __name__ == "__main__":
    main()
