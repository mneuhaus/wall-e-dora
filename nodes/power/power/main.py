"""Main module for the Power Node.

Monitors battery voltage, current, and power consumption using an INA226 sensor
via I2C. Calculates State of Charge (SoC), estimates remaining runtime, and
broadcasts power metrics through Dora. Includes safety shutdown logic.
"""

import math
import time
from collections import deque
from datetime import datetime

import pyarrow as pa
import smbus2
from dora import Node

LIPO_3S_CAPACITY_AH = 2.2
LIPO_3S_NOMINAL_VOLTAGE = 11.1
LIPO_3S_MAX_VOLTAGE = 12.6
LIPO_3S_MIN_VOLTAGE = 9.9
LIPO_3S_INTERNAL_RESISTANCE_OHM = 0.075
LIPO_3S_MAX_COMPENSATED_SAG = 0.30
LIPO_3S_CAPACITY_BOUNDS_AH = (1.6, 2.8)
LIPO_3S_SOC_CURVE = (
    (12.60, 100.0),
    (12.45, 95.0),
    (12.33, 90.0),
    (12.24, 85.0),
    (12.15, 80.0),
    (12.06, 75.0),
    (11.97, 70.0),
    (11.88, 60.0),
    (11.79, 50.0),
    (11.70, 40.0),
    (11.61, 30.0),
    (11.49, 20.0),
    (11.31, 10.0),
    (10.95, 5.0),
    (9.90, 0.0),
)


class BatteryTracker:
    """Tracks battery state, estimates capacity, and predicts runtime."""

    def __init__(self):
        """Initialize the BatteryTracker with battery-specific parameters."""
        # Battery specifications (3S LiPo pack, 2200mAh)
        self.nominal_capacity_ah = LIPO_3S_CAPACITY_AH
        self.capacity_ah = LIPO_3S_CAPACITY_AH
        self.min_capacity_ah, self.max_capacity_ah = LIPO_3S_CAPACITY_BOUNDS_AH
        self.threshold_soc = 20.0  # Runtime estimate reserve threshold
        self.nominal_voltage = LIPO_3S_NOMINAL_VOLTAGE
        self.min_voltage = LIPO_3S_MIN_VOLTAGE
        self.max_voltage = LIPO_3S_MAX_VOLTAGE
        self.soc_voltage_curve = LIPO_3S_SOC_CURVE
        self.internal_resistance_ohm = LIPO_3S_INTERNAL_RESISTANCE_OHM
        self.max_compensated_sag = LIPO_3S_MAX_COMPENSATED_SAG

        # Smoothing parameters for exponential moving averages
        self.alpha_current = 0.2
        self.alpha_power = 0.1
        self.alpha_discharge_rate = 0.1
        self.alpha_runtime = 0.2
        self.alpha_capacity = 0.05

        # State tracking
        self.soc = 100.0
        self.ema_current = None
        self.ema_power = None
        self.ema_discharge_rate = None
        self.ema_runtime_estimate = None
        self.ema_capacity = None
        self.last_timestamp = None
        self.last_soc = None
        self.last_voltage = None
        self.startup_readings = 0
        self.min_readings_before_estimate = 3
        self.accumulated_ah = 0.0

        # Store recent current values to smooth runtime calculations.
        self.current_history = deque(maxlen=10)

        # Capacity estimation tracking
        self.capacity_tracking_enabled = False
        self.capacity_tracking_start_time = None
        self.capacity_tracking_start_voltage = None
        self.capacity_tracking_start_soc = None
        self.capacity_tracking_ah_used = 0.0
        self.capacity_estimation_count = 0

    def add_reading(self, voltage: float, current: float, power: float):
        """Add a new voltage, current, and power reading to the tracker."""
        now = datetime.now()
        self.current_history.append(abs(current))

        if self.ema_current is None:
            self.ema_current = current
            self.ema_power = power
            self.last_timestamp = now
            self.last_soc = self._voltage_to_rough_soc(voltage, current)
            self.soc = self.last_soc
            self.last_voltage = voltage
            self.startup_readings += 1

            if voltage > (self.max_voltage - 0.2):
                self.start_capacity_tracking(voltage, now)
            return

        time_diff = (now - self.last_timestamp).total_seconds() / 3600
        if time_diff <= 0:
            return

        self.ema_current = (self.alpha_current * current) + ((1 - self.alpha_current) * self.ema_current)
        self.ema_power = (self.alpha_power * power) + ((1 - self.alpha_power) * self.ema_power)

        current_soc = self._voltage_to_rough_soc(voltage, current)
        self.soc = current_soc

        if self.last_soc is not None and current > 0.01:
            soc_change = self.last_soc - current_soc
            current_based_rate = (abs(current) / max(self.capacity_ah, 0.1)) * 100.0
            voltage_based_rate = 0.0
            if soc_change > 0:
                voltage_based_rate = min(100.0, soc_change / time_diff)

            if voltage_based_rate > 0:
                discharge_rate = (0.65 * current_based_rate) + (0.35 * voltage_based_rate)
            else:
                discharge_rate = current_based_rate

            if self.ema_discharge_rate is None:
                self.ema_discharge_rate = max(0.01, discharge_rate)
            else:
                alpha = self.alpha_discharge_rate
                if current > 1.0:
                    alpha = min(0.3, alpha * 2)
                self.ema_discharge_rate = (alpha * discharge_rate) + ((1 - alpha) * self.ema_discharge_rate)
                self.ema_discharge_rate = max(0.01, self.ema_discharge_rate)

        if self.capacity_tracking_enabled and current > 0:
            self.update_capacity_tracking(voltage, current, time_diff, now)

        if not self.capacity_tracking_enabled:
            if voltage > (self.max_voltage - 0.2):
                self.start_capacity_tracking(voltage, now)
            elif self.startup_readings > 60 and self.capacity_estimation_count == 0:
                self.start_capacity_tracking(voltage, now)

        self.startup_readings += 1
        self.last_timestamp = now
        self.last_soc = current_soc
        self.last_voltage = voltage

    def start_capacity_tracking(self, voltage: float, timestamp: datetime):
        """Start a capacity estimation tracking cycle."""
        try:
            self.capacity_tracking_enabled = True
            self.capacity_tracking_start_time = timestamp
            self.capacity_tracking_start_voltage = voltage
            self.capacity_tracking_start_soc = self._voltage_to_rough_soc(voltage, self.ema_current)
            self.capacity_tracking_ah_used = 0.0
            print(
                f"Starting capacity tracking at {voltage:.4f}V "
                f"({self.capacity_tracking_start_soc:.1f}%)"
            )
        except Exception as error:
            print(f"Error starting capacity tracking: {error}")
            self.capacity_tracking_enabled = False

    def update_capacity_tracking(
        self,
        voltage: float,
        current: float,
        time_diff: float,
        timestamp: datetime,
    ):
        """Update the ongoing capacity estimation cycle."""
        try:
            if self.capacity_tracking_start_time is None or self.capacity_tracking_start_soc is None:
                print("Capacity tracking not properly initialized - resetting")
                self.capacity_tracking_enabled = False
                return

            self.capacity_tracking_ah_used += current * time_diff
            current_soc = self._voltage_to_rough_soc(voltage, current)
            soc_drop = self.capacity_tracking_start_soc - current_soc
            tracking_duration_hours = (
                timestamp - self.capacity_tracking_start_time
            ).total_seconds() / 3600

            if current_soc > self.capacity_tracking_start_soc + 1.0:
                print("Voltage increased during capacity tracking - resetting")
                self.capacity_tracking_enabled = False
                return

            if tracking_duration_hours > 1.0 and soc_drop < 1.0:
                print(
                    "Capacity tracking reset - insufficient change "
                    f"({soc_drop:.1f}%) after {tracking_duration_hours:.1f}h"
                )
                self.capacity_tracking_enabled = False
                return

            if soc_drop > 2.0 or tracking_duration_hours > 0.33:
                if soc_drop > 0.5:
                    ah_per_percent = self.capacity_tracking_ah_used / soc_drop
                    estimated_capacity = ah_per_percent * 100.0

                    if self.min_capacity_ah <= estimated_capacity <= self.max_capacity_ah:
                        confidence_factor = min(
                            0.3,
                            (soc_drop / 20.0) + (tracking_duration_hours / 4.0),
                        )
                        alpha = max(0.05, min(0.2, confidence_factor))

                        if self.ema_capacity is None:
                            self.ema_capacity = estimated_capacity
                        else:
                            self.ema_capacity = (
                                alpha * estimated_capacity
                                + (1 - alpha) * self.ema_capacity
                            )

                        self.capacity_ah = max(
                            self.min_capacity_ah,
                            min(
                                self.max_capacity_ah,
                                min(self.ema_capacity, estimated_capacity),
                            ),
                        )

                        self.capacity_estimation_count += 1
                        print(
                            f"New capacity estimate: {estimated_capacity:.2f}Ah "
                            f"(EMA: {self.ema_capacity:.2f}Ah) based on "
                            f"{self.capacity_tracking_ah_used:.4f}Ah used for "
                            f"{soc_drop:.1f}% drop over {tracking_duration_hours:.2f}h"
                        )
                    else:
                        print(
                            "Capacity estimate outside reasonable range: "
                            f"{estimated_capacity:.2f}Ah - ignoring"
                        )

                self.capacity_tracking_enabled = False
        except Exception as error:
            print(f"Error in capacity tracking: {error}")
            self.capacity_tracking_enabled = False

    def get_average_power(self) -> float:
        """Return the smoothed average power consumption (EMA)."""
        return self.ema_power if self.ema_power is not None else 0.0

    def _estimate_resting_voltage(self, voltage: float, current: float | None = None) -> float:
        """Estimate resting voltage by compensating a little for discharge sag."""
        discharge_current = current if current is not None else (self.ema_current or 0.0)
        if discharge_current <= 0:
            return max(self.min_voltage, min(self.max_voltage, voltage))

        sag = min(self.max_compensated_sag, discharge_current * self.internal_resistance_ohm)
        resting_voltage = voltage + sag
        return max(self.min_voltage, min(self.max_voltage, resting_voltage))

    def _voltage_to_rough_soc(self, voltage: float, current: float | None = None) -> float:
        """Estimate SoC using a 3S LiPo voltage curve instead of a linear model."""
        resting_voltage = self._estimate_resting_voltage(voltage, current)
        if resting_voltage >= self.max_voltage:
            return 100.0
        if resting_voltage <= self.min_voltage:
            return 0.0

        for index in range(len(self.soc_voltage_curve) - 1):
            upper_voltage, upper_soc = self.soc_voltage_curve[index]
            lower_voltage, lower_soc = self.soc_voltage_curve[index + 1]
            if upper_voltage >= resting_voltage >= lower_voltage:
                span = upper_voltage - lower_voltage
                if span <= 0:
                    return lower_soc
                progress = (resting_voltage - lower_voltage) / span
                return lower_soc + progress * (upper_soc - lower_soc)

        return 0.0

    def estimate_remaining_time(self, current_voltage: float) -> float:
        """Estimate remaining runtime in seconds until SoC reaches the reserve threshold."""
        if self.startup_readings < self.min_readings_before_estimate:
            return float("inf")

        avg_current = 0.0
        if self.current_history:
            avg_current = sum(self.current_history) / len(self.current_history)

        if avg_current < 0.05:
            if self.ema_runtime_estimate is not None:
                return self.ema_runtime_estimate * 1.05
            return float("inf")

        current_soc = self._voltage_to_rough_soc(current_voltage, avg_current)
        remaining_percent = current_soc - self.threshold_soc
        if remaining_percent <= 0:
            return 0.0

        remaining_capacity_ah = (remaining_percent / 100.0) * self.capacity_ah
        hours_remaining = (remaining_capacity_ah / avg_current) * 0.85

        if hours_remaining < 0:
            return 0.0
        if hours_remaining > 48:
            hours_remaining = 48.0

        seconds_remaining = hours_remaining * 3600
        if self.ema_runtime_estimate is None:
            self.ema_runtime_estimate = seconds_remaining
        else:
            self.ema_runtime_estimate = (
                self.alpha_runtime * seconds_remaining
                + (1 - self.alpha_runtime) * self.ema_runtime_estimate
            )

        return max(0, self.ema_runtime_estimate)


def write_register(bus: smbus2.SMBus, address: int, register: int, value: int):
    """Write a 16-bit value to an I2C register."""
    bytes_val = value.to_bytes(2, byteorder="big")
    bus.write_i2c_block_data(address, register, list(bytes_val))


def read_register(bus: smbus2.SMBus, address: int, register: int) -> int:
    """Read a 16-bit value from an I2C register."""
    result = bus.read_i2c_block_data(address, register, 2)
    return int.from_bytes(bytes(result), byteorder="big")


def main():
    """Main function for the Power Node."""
    node = Node()
    battery_tracker = BatteryTracker()
    bus = smbus2.SMBus(1)
    address = 0x40

    try:
        write_register(bus, address, 0x00, 0x4127)
        print("Set config register")
        write_register(bus, address, 0x05, 0x15E7)
        print("Set calibration register")
        write_register(bus, address, 0x06, 0x4527)
        print("Enabled continuous measurements")
        config = read_register(bus, address, 0x00)
        cal = read_register(bus, address, 0x05)
        print(f"Config: 0x{config:04x}, Cal: 0x{cal:04x}")
        if config != 0x4127:
            print(f"INA226 config failed! Got: 0x{config:04x}")
        if cal != 0x15E7:
            print(f"INA226 calibration failed! Got: 0x{cal:04x}")
    except Exception as error:
        print(f"Error configuring INA226: {error}")
    time.sleep(0.1)

    for event in node:
        if event["type"] == "INPUT" and event["id"] == "tick":
            try:
                voltage_raw = read_register(bus, address, 0x02)
                voltage = voltage_raw * 1.25 / 1000.0

                current_raw = read_register(bus, address, 0x04)
                if current_raw > 32767:
                    current_raw -= 65536
                current = current_raw * 0.457 / 1000.0

                power_raw = read_register(bus, address, 0x03)
                power = power_raw * (0.457 * 25.0 / 1000.0)

                battery_tracker.add_reading(voltage, current, power)
                percentage = battery_tracker.soc
                avg_power = battery_tracker.get_average_power()
                remaining_seconds = battery_tracker.estimate_remaining_time(voltage)

                debug_info = ""
                if battery_tracker.startup_readings < battery_tracker.min_readings_before_estimate:
                    debug_info = (
                        f"(startup: {battery_tracker.startup_readings}/"
                        f"{battery_tracker.min_readings_before_estimate})"
                    )
                elif (
                    battery_tracker.current_history
                    and sum(battery_tracker.current_history) / len(battery_tracker.current_history) < 0.1
                ):
                    debug_info = "(low current)"
                elif (
                    battery_tracker.ema_discharge_rate is None
                    or battery_tracker.ema_discharge_rate <= 0
                ):
                    debug_info = "(no discharge data)"
                elif remaining_seconds > 86400:
                    debug_info = "(>24h)"

                if (
                    remaining_seconds == float("inf")
                    or remaining_seconds != remaining_seconds
                    or remaining_seconds <= 0
                ):
                    time_str = "--:--"
                elif remaining_seconds > 86400:
                    time_str = ">24h"
                else:
                    hours = int(remaining_seconds // 3600)
                    minutes = int((remaining_seconds % 3600) // 60)
                    time_str = f"{hours:02d}:{minutes:02d}"

                try:
                    discharge_rate = battery_tracker.ema_discharge_rate
                    if discharge_rate is None:
                        discharge_rate = 0.0

                    print(
                        f"Power: {voltage:.4f}V ({percentage:.1f}%) {current:.4f}A {power:.4f}W | "
                        f"Avg: {avg_power:.4f}W | Runtime: {time_str} | "
                        f"Est.Cap: {battery_tracker.capacity_ah:.2f}Ah | "
                        f"Discharge: {discharge_rate:.1f}%/hr | {debug_info}"
                    )
                except Exception as error:
                    print(
                        f"Power: {voltage:.4f}V ({percentage:.1f}%) {current:.4f}A {power:.4f}W | "
                        f"Avg: {avg_power:.4f}W | Runtime: {time_str} {debug_info}"
                    )
                    print(f"Error displaying detailed battery info: {error}")

                capacity_value = battery_tracker.capacity_ah
                discharge_rate_value = 0.0
                if battery_tracker.ema_discharge_rate is not None:
                    discharge_rate_value = battery_tracker.ema_discharge_rate

                node.send_output(output_id="voltage", data=pa.array([voltage]), metadata={})
                node.send_output(output_id="current", data=pa.array([current]), metadata={})
                node.send_output(output_id="power", data=pa.array([power]), metadata={})
                node.send_output(output_id="soc", data=pa.array([percentage]), metadata={})

                runtime_value = float(remaining_seconds)
                if math.isinf(runtime_value) or math.isnan(runtime_value) or runtime_value < 0:
                    runtime_value = 0.0

                node.send_output(output_id="runtime", data=pa.array([runtime_value]), metadata={})
                node.send_output(output_id="capacity", data=pa.array([capacity_value]), metadata={})
                node.send_output(output_id="discharge_rate", data=pa.array([discharge_rate_value]), metadata={})

                if percentage < 10.0:
                    print("CRITICAL: Battery below 10%! Initiating shutdown...")
                    node.send_output(output_id="shutdown", data=pa.array([]), metadata={})
            except Exception as error:
                print(f"Error reading power data: {error}")


if __name__ == "__main__":
    main()
