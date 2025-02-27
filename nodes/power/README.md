# Power Monitoring Package

## Overview
The power package provides battery monitoring and power management for the Wall-E robot using an INA226 current/voltage sensor. It tracks battery state, estimates remaining runtime, and implements safety shutdown at low battery levels.

## Hardware Requirements
- INA226 current/voltage sensor
- I2C connection to Raspberry Pi (bus 1)
- 12V LiPo battery system (3S configuration)
- Shunt resistor: 0.002Ω

## Configuration

### INA226 Settings
| Register | Value    | Description                    |
|----------|----------|--------------------------------|
| Config   | 0x4127   | 128 samples avg, 8.244ms conv  |
| Cal      | 0x15E7   | Calibrated for 15A max        |
| Mask/En  | 0x4527   | Continuous measurements        |

### Battery Specifications
| Parameter          | Value | Description              |
|-------------------|-------|--------------------------|
| Nominal Voltage   | 11.1V | 3S Li-ion configuration |
| Maximum Voltage   | 12.6V | 4.2V per cell           |
| Minimum Voltage   | 9.0V  | 3.0V per cell           |
| Capacity         | 2.5Ah | Per cell capacity        |
| Shutdown Threshold| 10%   | Auto shutdown trigger    |

## DORA Node Information

The power package includes a dora node that monitors battery status using an INA226 sensor. It publishes the following outputs:
- voltage: Battery voltage measurement in volts.
- current: Battery current measurement in amperes.
- power: Instantaneous power consumption in watts.
- soc: Battery state of charge as a percentage.
- runtime: Estimated available runtime in seconds until a critical battery level is reached.
- shutdown: A signal output triggered when battery charge falls below the critical threshold (10%), indicating that a shutdown should be initiated.

The node is integrated into the Dora dataflow framework and communicates with other nodes via Apache Arrow arrays.

## Example Dataflow Configuration

Below is an example dataflow configuration integrating the power node, web node, and listener node:

```yaml
nodes:
  - id: listener_1
    path: listener-1/listener_1/main.py
    inputs:
      speech-2: web/my_output_id

  - id: power
    path: power/power/main.py
    inputs:
      tick: dora/timer/secs/10
    outputs:
      - voltage
      - current
      - power
      - soc
      - runtime
      - shutdown

  - id: web
    path: web/web/main.py
    inputs:
      tick: dora/timer/millis/100
      voltage: power/voltage
      current: power/current
      power: power/power
      soc: power/soc
      runtime: power/runtime
      shutdown: power/shutdown
    outputs:
      - my_output_id
      - slider_input
```

You can run this configuration with:

```bash
dora run dataflow.yml --name my_power_flow
```
