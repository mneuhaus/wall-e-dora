import pytest

def process_command(command: str):
    parts = command.strip().split()
    if len(parts) != 2:
        print("Invalid command")
        return
    direction, speed = parts
    if direction.lower() not in ["left", "right"]:
        print("Unknown direction")
        return
    try:
        speed_val = int(speed)
    except ValueError:
        print("Invalid speed")
        return
    print(f"Setting {direction} track to {speed_val}% speed")

def test_valid_left_command(capfd):
    process_command("left 30")
    out, _ = capfd.readouterr()
    assert out.strip() == "Setting left track to 30% speed"

def test_valid_right_command(capfd):
    process_command("right 100")
    out, _ = capfd.readouterr()
    assert out.strip() == "Setting right track to 100% speed"

def test_invalid_command(capfd):
    process_command("forward 50")
    out, _ = capfd.readouterr()
    assert out.strip() == "Unknown direction"

def test_invalid_format(capfd):
    process_command("left")
    out, _ = capfd.readouterr()
    assert out.strip() == "Invalid command"
