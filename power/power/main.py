import time
import smbus2
from collections import deque
from datetime import datetime

import pyarrow as pa
from dora import Node


class BatteryTracker:
    def __init__(self):
        # Battery specifications (3S Li-ion pack)
        self.capacity_ah = 2.5  # Actual capacity in Amp-hours (single cell capacity)
        self.threshold_soc = 20.0  # Threshold percentage  
        self.nominal_voltage = 11.1  # 3S nominal voltage
        self.min_voltage = 9.0  # 3.0V per cell
        self.max_voltage = 12.6  # 4.2V per cell

        # Smoothing parameters (tuned for stability)
        self.alpha_current = 0.1  # Reduced for more stable current
        self.alpha_power = 0.01   # Reduced for more stable power display
        self.window_size = 60     # 1 minute window for rolling average

        # State tracking
        self.soc = 100.0  # Initial state of charge
        self.ema_current = None
        self.ema_power = None
        self.last_timestamp = None
        self.current_window = deque(maxlen=self.window_size)
        self.accumulated_ah = 0.0  # Coulomb counting

    def add_reading(self, voltage, current, power):
        now = datetime.now()
        if self.ema_current is None:
            self.ema_current = current
            self.ema_power = power
            self.last_timestamp = now
            self.current_window.append(current)
            return

        # Calculate time difference in hours
        time_diff = (now - self.last_timestamp).total_seconds() / 3600

        # Update EMAs
        self.ema_current = (self.alpha_current * current +
                            (1 - self.alpha_current) * self.ema_current)
        self.ema_power = (self.alpha_power * power +
                          (1 - self.alpha_power) * self.ema_power)

        # Update rolling window
        self.current_window.append(current)
        avg_current = sum(self.current_window) / len(self.current_window)

        # Coulomb counting for SoC
        self.accumulated_ah += (avg_current * time_diff)
        self.soc = max(min(100.0 * (1.0 - self.accumulated_ah / self.capacity_ah), 100.0), 0.0)

        # Validate SoC against voltage
        voltage_soc = self._voltage_to_rough_soc(voltage)
        if abs(voltage_soc - self.soc) > 20.0:
            self.accumulated_ah = self.capacity_ah * (1.0 - voltage_soc / 100.0)
            self.soc = voltage_soc

        self.last_timestamp = now

    def get_average_power(self):
        return self.ema_power if self.ema_power is not None else 0.0

    def _voltage_to_rough_soc(self, voltage):
        if voltage >= self.max_voltage:
            return 100.0
        elif voltage <= self.min_voltage:
            return 0.0
        voltage_range = self.max_voltage - self.min_voltage
        voltage_offset = voltage - self.min_voltage
        return (voltage_offset / voltage_range) * 100.0

    def estimate_remaining_time(self, current_voltage):
        if len(self.current_window) < self.window_size:
            return float('inf')
        avg_current = sum(self.current_window) / len(self.current_window)
        if avg_current <= 0.01:
            return float('inf')
        remaining_capacity = (self.soc / 100) * self.capacity_ah
        target_capacity = (self.threshold_soc / 100) * self.capacity_ah
        capacity_difference = remaining_capacity - target_capacity
        hours_remaining = capacity_difference / avg_current
        seconds_remaining = hours_remaining * 3600
        return max(0, seconds_remaining)


def write_register(bus, address, register, value):
    bytes_val = value.to_bytes(2, byteorder='big')
    bus.write_i2c_block_data(address, register, list(bytes_val))


def read_register(bus, address, register):
    result = bus.read_i2c_block_data(address, register, 2)
    return int.from_bytes(bytes(result), byteorder='big')


def main():
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
    except Exception as e:
        print(f"Error configuring INA226: {str(e)}")
    time.sleep(0.1)

    for event in node:
        if event["type"] == "INPUT" and event["id"] == "tick":
            try:
                voltage_raw = read_register(bus, address, 0x02)
                # Bus voltage LSB is 1.25mV
                voltage = voltage_raw * 1.25 / 1000.0  # in volts

                current_raw = read_register(bus, address, 0x04)
                if current_raw > 32767:
                    current_raw -= 65536
                # Current LSB is 0.457mA (15A/32767)
                current = current_raw * 0.457 / 1000.0  # in amps

                power_raw = read_register(bus, address, 0x03)
                # Power LSB is 25 times the current LSB
                power = power_raw * (0.457 * 25.0 / 1000.0)  # in watts

                # Calculate battery percentage (linear approximation: 9.0V empty to 12.6V full)
                percentage = max(0.0, min(100.0, (voltage - 9.0) * 100.0 / (12.6 - 9.0)))

                battery_tracker.add_reading(voltage, current, power)
                avg_power = battery_tracker.get_average_power()
                remaining_seconds = battery_tracker.estimate_remaining_time(voltage)
                if remaining_seconds == float('inf') or remaining_seconds != remaining_seconds:
                    time_str = "--:--"
                else:
                    hours = int(remaining_seconds // 3600)
                    minutes = int((remaining_seconds % 3600) // 60)
                    time_str = f"{hours:02d}:{minutes:02d}"

                print(f'Power: {voltage:.4f}V ({percentage:.1f}%) {current:.4f}A {power:.4f}W | '
                      f'Avg: {avg_power:.4f}W | Runtime: {time_str}')
                node.send_output(output_id="voltage", data=pa.array([voltage]), metadata={})
                node.send_output(output_id="current", data=pa.array([current]), metadata={})
                node.send_output(output_id="power", data=pa.array([power]), metadata={})
                node.send_output(output_id="soc", data=pa.array([percentage]), metadata={})
                node.send_output(output_id="runtime", data=pa.array([remaining_seconds]), metadata={})

                if percentage < 10.0:
                    print("CRITICAL: Battery below 10%! Initiating shutdown...")
                    node.send_output(output_id="shutdown", data=pa.array([]), metadata={})
            except Exception as e:
                print(f"Error reading power data: {str(e)}")


if __name__ == "__main__":
    main()
