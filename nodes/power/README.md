# Power Node

## Purpose

The power node monitors the robot battery and turns raw INA226 readings into
useful operational telemetry: voltage, current, power draw, state of charge,
runtime estimates, and a low-battery shutdown signal.

## What It Currently Does

- Reads voltage, current, and power through an INA226 sensor on I2C
- Tracks a `3S LiPo` battery pack with a LiPo-aware SoC curve
- Estimates runtime from smoothed discharge behavior
- Publishes battery telemetry to the web node
- Emits a shutdown signal when the pack reaches the critical threshold

## Hardware Assumptions

The current reference build is based on:

- INA226 current / voltage monitor
- I2C bus `1`
- `0.002 Ohm` shunt resistor
- `3S LiPo` battery pack
- current reference battery family: `HOOVO 2200 mAh 11.1V 50C`

## Current Battery Model

The implementation is no longer just a naive linear voltage percentage:

- nominal pack voltage: `11.1V`
- full pack voltage: `12.6V`
- practical empty floor: `9.9V`
- capacity reference: `2.2Ah`
- shutdown threshold: `10%`

The node combines:

- LiPo-curve-based SoC estimation
- light load compensation
- exponential smoothing
- adaptive runtime estimation that ignores misleading idle periods

## Dora Integration

### Inputs

| Input ID | Source | Description |
| --- | --- | --- |
| `tick` | `dora/timer/secs/10` | Periodic power update trigger |

### Outputs

| Output ID | Destination | Description |
| --- | --- | --- |
| `voltage` | `web` | Battery voltage |
| `current` | `web` | Battery current |
| `power` | `web` | Battery power draw |
| `soc` | `web` | State of charge |
| `runtime` | `web` | Estimated remaining runtime |
| `capacity` | `web` | Estimated battery capacity |
| `discharge_rate` | `web` | Estimated discharge rate |
| `shutdown` | `web` | Critical low-battery shutdown signal |

## Example Log Line

```text
Power: 11.7740V (94.4%) 0.4570A 5.3808W | Avg: 5.381W | Runtime: >24h | Est.Cap: 2.50Ah | Discharge: 12.0%/hr | (>24h)
```

This line intentionally compresses the most relevant information into one place:

- current voltage
- state of charge
- current and power draw
- smoothed average power
- runtime estimate
- estimated effective capacity
- discharge rate

## Development Notes

### Tests

```bash
pytest nodes/power/tests -q
python3 -m compileall nodes/power/power
```

### Keep In Sync

When the reference battery changes, update all three of these together:

- code in `nodes/power/power/main.py`
- this README
- the root project BOM / Pages site

## Documentation Expectations

- Use English in docs and Discussions
- Keep the battery assumptions explicit
- Treat this node as safety-relevant documentation, not just implementation detail
