"""Simple sequence executor node.

Listens for a trigger from the web UI and performs small multi-step
actions by emitting outputs to other nodes (audio, servo).
"""

from dora import Node
import pyarrow as pa
import time

# Neutral/default positions (tune as needed)
ARM_LEFT_NEUTRAL = 520    # servo #2
ARM_RIGHT_NEUTRAL = 720   # servo #13
HEAD_LEFT_NEUTRAL = 460   # servo #6
HEAD_RIGHT_NEUTRAL = 460  # servo #4
HEAD_PIVOT_CENTER = 512   # servo #14
DOOR_CLOSED = 500         # servo #5
DOOR_OPEN = 600           # servo #5
DEFAULT_EYES = "realistic-orange.gif"


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
    # Return to neutral
    neutral_pose(node)
    print("Sequence: hands-up complete")


def run_candy(node: Node):
    # Eyes: candy motif
    node.send_output("play_gif_sequence", pa.array(["ghibli-candy.gif"]))
    # Sound: curious
    node.send_output("play_sound_sequence", pa.array(["fragendes-seufzen.mp3"]))
    # Open front door (#5). Conservative positions; adjust via config if needed.
    node.send_output("move_servo_sequence", pa.array([{ "id": 5, "position": 600 }]))  # open
    time.sleep(0.5)
    # Head tilt one side only (left head=#6), peek
    node.send_output("move_servo_sequence", pa.array([{ "id": 6, "position": 560 }]))
    time.sleep(0.5)
    node.send_output("move_servo_sequence", pa.array([{ "id": 6, "position": 460 }]))
    # Small left arm wiggle (#2)
    time.sleep(0.2)
    node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": 560 }]))
    time.sleep(0.3)
    node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": 520 }]))
    # Close door
    time.sleep(0.2)
    node.send_output("move_servo_sequence", pa.array([{ "id": 5, "position": DOOR_CLOSED }]))  # close
    # Return to neutral
    neutral_pose(node)
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
    # Return to neutral
    neutral_pose(node)
    print("Sequence: party complete")


def neutral_pose(node: Node):
    """Return the robot to a safe, neutral pose.

    - Arms lowered to neutral (2,13)
    - Head sides lowered (6 then 4) and pivot centered (14)
    - Door closed (5)
    - Eyes set to default
    """
    # Eyes back to default
    node.send_output("play_gif_sequence", pa.array([DEFAULT_EYES]))
    # Door closed
    node.send_output("move_servo_sequence", pa.array([{ "id": 5, "position": DOOR_CLOSED }]))
    # Arms to neutral
    node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": ARM_LEFT_NEUTRAL }]))
    node.send_output("move_servo_sequence", pa.array([{ "id": 13, "position": ARM_RIGHT_NEUTRAL }]))
    # Head sides to neutral one at a time (avoid collision)
    node.send_output("move_servo_sequence", pa.array([{ "id": 6, "position": HEAD_LEFT_NEUTRAL }]))
    time.sleep(0.12)
    node.send_output("move_servo_sequence", pa.array([{ "id": 4, "position": HEAD_RIGHT_NEUTRAL }]))
    # Head pivot centered
    node.send_output("move_servo_sequence", pa.array([{ "id": 14, "position": HEAD_PIVOT_CENTER }]))


if __name__ == "__main__":
    main()
