# Tracks Node

## Purpose

The tracks node turns high-level movement intent into low-level serial commands
for the RP2040 drive controller. It is responsible for manual browser/gamepad
driving, heartbeat traffic to the motor controller, and short sequence-driven
movement overrides used by scenes and dance actions.

## What It Currently Does

- Reads left-stick X/Y movement input from the web node
- Converts joystick input into differential drive commands
- Applies smoothing / easing before sending commands
- Sends regular heartbeat traffic to the RP2040
- Accepts temporary `move_tracks_sequence` overrides from the sequence node
- Keeps the actual motor driver details hidden behind the RP2040 firmware

## Hardware Context

The current robot drive stack is built around:

- a Raspberry Pi as the high-level controller
- an RP2040-based drive controller board with a XIAO RP2040-style pinout
- Cytron MD13S motor driver hardware
- differential tracked movement

## Dora Integration

### Inputs

| Input ID | Source | Description |
| --- | --- | --- |
| `tick` | `dora/timer/millis/33` | Main control update tick |
| `heartbeat` | `dora/timer/secs/1` | Keepalive for the RP2040 link |
| `GAMEPAD_LEFT_ANALOG_STICK_X` | `web/GAMEPAD_LEFT_ANALOG_STICK_X` | Turn input |
| `GAMEPAD_LEFT_ANALOG_STICK_Y` | `web/GAMEPAD_LEFT_ANALOG_STICK_Y` | Forward / reverse input |
| `move_tracks_sequence` | `sequence/move_tracks_sequence` | Timed sequence override payload |
| `setting_updated` | `config/setting_updated` | Future-facing config change hook |

### Sequence Override Payload

The sequence node can temporarily take over track motion with a structured
payload:

```json
{
  "linear": 30,
  "angular": -70,
  "duration": 0.8
}
```

This is what powers on-the-spot turns, spins, and short dance beats.

## Serial Protocol

The RP2040 firmware currently understands simple line-based commands such as:

```text
move 100 50
heartbeat
stop
```

That keeps the Python side easy to reason about and makes firmware debugging
fairly straightforward.

## Firmware Responsibilities

The firmware under `nodes/tracks/firmware` is responsible for:

- PWM motor output
- direction control
- command parsing
- safety timeout handling
- translating `move <linear> <angular>` into actual motor behavior

## Development Notes

### Build / Flash

```bash
make tracks/build
make tracks/flash
make tracks/update
```

### Tests / Validation

```bash
pytest nodes/tracks/tests -q
python3 -m compileall nodes/tracks/tracks
```

## Documentation Expectations

- Keep this README aligned with the actual serial protocol and hardware pinout
- Document any changes to joystick mapping or sequence movement semantics
- Use English in docs, Issues, and Discussions
