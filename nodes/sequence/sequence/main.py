"""Simple sequence executor node.

Listens for a trigger from the web UI and performs small multi-step
actions by emitting outputs to other nodes (audio, servo).
"""

from dora import Node
import pyarrow as pa
import time


def main():
    node = Node()
    print("Sequence node started")

    for event in node:
        if event["type"] != "INPUT":
            continue

        if event["id"] == "trigger":
            # Expect first element of array to be the sequence id string
            try:
                seq_id = None
                if hasattr(event["value"], "to_pylist"):
                    values = event["value"].to_pylist()
                    seq_id = values[0] if values else None
                else:
                    seq_id = event["value"]
            except Exception:
                seq_id = None

            if not seq_id:
                print("Sequence: received empty trigger")
                continue

            print(f"Sequence: trigger -> {seq_id}")
            if seq_id == "hands-up":
                run_hands_up(node)
            elif seq_id == "candy":
                run_candy(node)
            elif seq_id == "party":
                run_party(node)
            else:
                print(f"Sequence: unknown sequence '{seq_id}'")


def run_hands_up(node: Node):
    # Eyes: energetic
    node.send_output("play_gif_sequence", pa.array(["lets-go.gif"]))
    # Sound: joyful
    node.send_output("play_sound_sequence", pa.array(["freudiges-jubeln.mp3"]))

    # Arms up (left=#2, right=#13), then back down
    node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": 820 }]))
    node.send_output("move_servo_sequence", pa.array([{ "id": 13, "position": 940 }]))
    time.sleep(1.2)
    node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": 520 }]))
    node.send_output("move_servo_sequence", pa.array([{ "id": 13, "position": 720 }]))
    print("Sequence: hands-up complete")


def run_candy(node: Node):
    # Eyes: candy motif
    node.send_output("play_gif_sequence", pa.array(["ghibli-candy.gif"]))
    # Sound: curious
    node.send_output("play_sound_sequence", pa.array(["fragendes-seufzen.mp3"]))
    # Head tilt one side only (left head=#6)
    node.send_output("move_servo_sequence", pa.array([{ "id": 6, "position": 560 }]))
    time.sleep(0.5)
    node.send_output("move_servo_sequence", pa.array([{ "id": 6, "position": 460 }]))
    # Small left arm wiggle (#2)
    time.sleep(0.2)
    node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": 560 }]))
    time.sleep(0.3)
    node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": 520 }]))
    print("Sequence: candy complete")


def run_party(node: Node):
    # Eyes: dance animation
    node.send_output("play_gif_sequence", pa.array(["lets-dance.gif"]))
    # Music
    node.send_output("play_sound_sequence", pa.array(["träumerisches-summen.mp3"]))
    # Alternate arms and head sides (never raise both head sides simultaneously)
    for _ in range(3):
        # Arms bump
        node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": 560 }]))
        node.send_output("move_servo_sequence", pa.array([{ "id": 13, "position": 800 }]))
        # Head left up (#6), then back
        node.send_output("move_servo_sequence", pa.array([{ "id": 6, "position": 560 }]))
        time.sleep(0.18)
        node.send_output("move_servo_sequence", pa.array([{ "id": 6, "position": 460 }]))
        time.sleep(0.12)
        # Arms back
        node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": 520 }]))
        node.send_output("move_servo_sequence", pa.array([{ "id": 13, "position": 720 }]))
        # Head right up (#4), then back
        node.send_output("move_servo_sequence", pa.array([{ "id": 4, "position": 560 }]))
        time.sleep(0.18)
        node.send_output("move_servo_sequence", pa.array([{ "id": 4, "position": 460 }]))
        time.sleep(0.12)
    print("Sequence: party complete")


if __name__ == "__main__":
    main()
