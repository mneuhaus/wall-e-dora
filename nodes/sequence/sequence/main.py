"""Simple sequence executor node.

Listens for a trigger from the web UI and performs small multi-step
actions by emitting outputs to other nodes (audio, servo).
"""

from dora import Node
import pyarrow as pa
import time

# Neutral/default positions (tune as needed)
# Arms (position values provided by user)
ARM_LEFT_NEUTRAL = 0      # servo #2 (down)
ARM_LEFT_UP = 350         # servo #2 (up)
ARM_RIGHT_NEUTRAL = 940   # servo #13 (down)
ARM_RIGHT_UP = 640        # servo #13 (up)
# Head sides (provided by user)
HEAD_LEFT_NEUTRAL = 120   # servo #6 (down)
HEAD_LEFT_UP = 230        # servo #6 (up)
HEAD_RIGHT_NEUTRAL = 300  # servo #4 (down)
HEAD_RIGHT_UP = 120       # servo #4 (up)
# Head pivot (provided by user)
HEAD_PIVOT_LEFT = 125     # servo #14 (left)
HEAD_PIVOT_RIGHT = 175    # servo #14 (right)
HEAD_PIVOT_CENTER = 150   # servo #14 (center)
DOOR_CLOSED = 700         # servo #5 (matches UI toggle expectations)
DOOR_OPEN = 1023          # servo #5 (fully open)
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
            elif seq_id == "neutral":
                # Explicit neutral request: reset everything and close door
                neutral_pose(node, close_door=True, keep_eyes=False)
                print("Sequence: neutral complete")
            else:
                print(f"Sequence: unknown sequence '{seq_id}'")


def run_hands_up(node: Node):
    # Ensure door is closed if left open by previous actions
    node.send_output("move_servo_sequence", pa.array([{ "id": 5, "position": DOOR_CLOSED }]))
    # Ensure pivot is centered before motion
    node.send_output("move_servo_sequence", pa.array([{ "id": 14, "position": HEAD_PIVOT_CENTER }]))
    # Eyes: energetic
    node.send_output("play_gif_sequence", pa.array(["lets-go.gif"]))
    # Sound: joyful
    node.send_output("play_sound_sequence", pa.array(["freudiges-jubeln.mp3"]))

    # Arms up (left=#2, right=#13), then back down (staggered to avoid overlap issues)
    node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": ARM_LEFT_UP }]))
    time.sleep(0.15)
    node.send_output("move_servo_sequence", pa.array([{ "id": 13, "position": ARM_RIGHT_UP }]))
    time.sleep(1.2)
    node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": ARM_LEFT_NEUTRAL }]))
    time.sleep(0.15)
    node.send_output("move_servo_sequence", pa.array([{ "id": 13, "position": ARM_RIGHT_NEUTRAL }]))
    # Return to neutral
    neutral_pose(node)
    print("Sequence: hands-up complete")


def run_candy(node: Node):
    # Eyes: candy motif
    node.send_output("play_gif_sequence", pa.array(["ghibli-candy.gif"]))
    # Sound: curious
    node.send_output("play_sound_sequence", pa.array(["fragendes-seufzen.mp3"]))
    # Keep pivot centered for peek
    node.send_output("move_servo_sequence", pa.array([{ "id": 14, "position": HEAD_PIVOT_CENTER }]))
    # Open front door (#5) fully and give enough time for motion
    node.send_output("move_servo_sequence", pa.array([{ "id": 5, "position": DOOR_OPEN }]))
    time.sleep(1.2)
    # Head tilt one side only (left head=#6), peek, then return
    node.send_output("move_servo_sequence", pa.array([{ "id": 6, "position": HEAD_LEFT_UP }]))
    time.sleep(1.0)
    node.send_output("move_servo_sequence", pa.array([{ "id": 6, "position": HEAD_LEFT_NEUTRAL }]))
    # Left arm wiggle (#2) with larger amplitude (relative to new range)
    time.sleep(0.4)
    node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": 220 }]))
    time.sleep(0.5)
    node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": ARM_LEFT_NEUTRAL }]))
    time.sleep(0.4)
    node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": 120 }]))
    time.sleep(0.5)
    node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": ARM_LEFT_NEUTRAL }]))
    # Leave door open for treats and keep candy eyes visible
    neutral_pose(node, close_door=False, keep_eyes=True)
    print("Sequence: candy complete")


def run_party(node: Node):
    # Ensure door is closed if left open by previous actions
    node.send_output("move_servo_sequence", pa.array([{ "id": 5, "position": DOOR_CLOSED }]))
    # Start from pivot center
    node.send_output("move_servo_sequence", pa.array([{ "id": 14, "position": HEAD_PIVOT_CENTER }]))
    # Eyes: dance animation
    node.send_output("play_gif_sequence", pa.array(["lets-dance.gif"]))
    # Music
    node.send_output("play_sound_sequence", pa.array(["träumerisches-summen.mp3"]))
    # Alternate arms and head sides (never raise both head sides simultaneously)
    for _ in range(3):
        # Arms bump (use user-provided ranges midpoints)
        node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": 220 }]))
        time.sleep(0.15)
        node.send_output("move_servo_sequence", pa.array([{ "id": 13, "position": 780 }]))
        # Head left up (#6), then back (sequential)
        node.send_output("move_servo_sequence", pa.array([{ "id": 6, "position": HEAD_LEFT_UP }]))
        time.sleep(0.18)
        node.send_output("move_servo_sequence", pa.array([{ "id": 6, "position": HEAD_LEFT_NEUTRAL }]))
        time.sleep(0.12)
        # Arms back
        node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": ARM_LEFT_NEUTRAL }]))
        time.sleep(0.15)
        node.send_output("move_servo_sequence", pa.array([{ "id": 13, "position": ARM_RIGHT_NEUTRAL }]))
        # Head right up (#4), then back (sequential)
        node.send_output("move_servo_sequence", pa.array([{ "id": 4, "position": HEAD_RIGHT_UP }]))
        time.sleep(0.18)
        node.send_output("move_servo_sequence", pa.array([{ "id": 4, "position": HEAD_RIGHT_NEUTRAL }]))
        time.sleep(0.12)
        # Gentle pivot sway left-center-right-center
        node.send_output("move_servo_sequence", pa.array([{ "id": 14, "position": HEAD_PIVOT_LEFT }]))
        time.sleep(0.12)
        node.send_output("move_servo_sequence", pa.array([{ "id": 14, "position": HEAD_PIVOT_CENTER }]))
        time.sleep(0.12)
        node.send_output("move_servo_sequence", pa.array([{ "id": 14, "position": HEAD_PIVOT_RIGHT }]))
        time.sleep(0.12)
        node.send_output("move_servo_sequence", pa.array([{ "id": 14, "position": HEAD_PIVOT_CENTER }]))
    # Return to neutral
    neutral_pose(node)
    print("Sequence: party complete")


def neutral_pose(node: Node, close_door: bool = True, keep_eyes: bool = False):
    """Return the robot to a safe, neutral pose.

    - Arms lowered to neutral (2,13)
    - Head sides lowered (6 then 4) and pivot centered (14)
    - Door closed (5)
    - Eyes set to default
    """
    # Eyes back to default unless caller requests to keep current image
    if not keep_eyes:
        node.send_output("play_gif_sequence", pa.array([DEFAULT_EYES]))
    # Door closed (optional)
    if close_door:
        node.send_output("move_servo_sequence", pa.array([{ "id": 5, "position": DOOR_CLOSED }]))
    # Arms to neutral (staggered)
    node.send_output("move_servo_sequence", pa.array([{ "id": 2, "position": ARM_LEFT_NEUTRAL }]))
    time.sleep(0.15)
    node.send_output("move_servo_sequence", pa.array([{ "id": 13, "position": ARM_RIGHT_NEUTRAL }]))
    # Head sides to neutral one at a time (avoid collision)
    node.send_output("move_servo_sequence", pa.array([{ "id": 6, "position": HEAD_LEFT_NEUTRAL }]))
    time.sleep(0.2)
    node.send_output("move_servo_sequence", pa.array([{ "id": 4, "position": HEAD_RIGHT_NEUTRAL }]))
    # Head pivot centered
    node.send_output("move_servo_sequence", pa.array([{ "id": 14, "position": HEAD_PIVOT_CENTER }]))
    time.sleep(0.2)


if __name__ == "__main__":
    main()
