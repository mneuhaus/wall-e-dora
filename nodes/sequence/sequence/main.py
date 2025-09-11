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
    # Play a short celebratory clip
    node.send_output("play_sound_sequence", pa.array(["freudiges-jubeln.mp3"]))

    # Raise both arms (IDs may need adjustment per rig)
    node.send_output("move_servo_sequence", pa.array([{ "id": 12, "position": 1023 }]))
    node.send_output("move_servo_sequence", pa.array([{ "id": 13, "position": 940 }]))
    time.sleep(1.5)
    # Return to neutral
    node.send_output("move_servo_sequence", pa.array([{ "id": 12, "position": 413 }]))
    node.send_output("move_servo_sequence", pa.array([{ "id": 13, "position": 720 }]))
    print("Sequence: hands-up complete")


def run_candy(node: Node):
    # Curious tone
    node.send_output("play_sound_sequence", pa.array(["fragendes-seufzen.mp3"]))
    # Small arm wiggle
    node.send_output("move_servo_sequence", pa.array([{ "id": 12, "position": 500 }]))
    time.sleep(0.4)
    node.send_output("move_servo_sequence", pa.array([{ "id": 12, "position": 420 }]))
    time.sleep(0.3)
    node.send_output("move_servo_sequence", pa.array([{ "id": 12, "position": 460 }]))
    print("Sequence: candy complete")


def run_party(node: Node):
    # Play dancing music clip (träumerisches-summen)
    node.send_output("play_sound_sequence", pa.array(["träumerisches-summen.mp3"]))
    # Quick alternating arm bumps
    for _ in range(3):
        node.send_output("move_servo_sequence", pa.array([{ "id": 12, "position": 560 }]))
        node.send_output("move_servo_sequence", pa.array([{ "id": 13, "position": 800 }]))
        time.sleep(0.25)
        node.send_output("move_servo_sequence", pa.array([{ "id": 12, "position": 460 }]))
        node.send_output("move_servo_sequence", pa.array([{ "id": 13, "position": 720 }]))
        time.sleep(0.25)
    print("Sequence: party complete")


if __name__ == "__main__":
    main()
