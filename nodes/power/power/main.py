import time
import math
import smbus2
from collections import deque
from datetime import datetime

import pyarrow as pa
from dora import Node


class BatteryTracker:
    def __init__(self):
        # Battery specifications (3S Li-ion pack)
        self.capacity_ah = 2.5  # Initial estimate of capacity in Amp-hours
        self.threshold_soc = 20.0  # Threshold percentage  
        self.nominal_voltage = 11.1  # 3S nominal voltage
        self.min_voltage = 8.0  # Empty battery threshold
        self.max_voltage = 12.2  # Full battery threshold

        # Smoothing parameters for exponential moving averages
        self.alpha_current = 0.2  # EMA factor for current (more responsive)
        self.alpha_power = 0.1  # EMA factor for power (more responsive)
        self.alpha_discharge_rate = 0.1  # EMA for discharge rate (more responsive)
        self.alpha_runtime = 0.2  # EMA factor for runtime predictions (more responsive)
        self.alpha_capacity = 0.05  # EMA for capacity estimation (very smooth)

        # State tracking
        self.soc = 100.0  # Initial state of charge
        self.ema_current = None
        self.ema_power = None
        self.ema_discharge_rate = None  # % of battery per hour
        self.ema_runtime_estimate = None  # Smoothed runtime estimate
        self.ema_capacity = None  # Estimated capacity based on usage patterns
        self.last_timestamp = None
        self.last_soc = None
        self.last_voltage = None
        self.startup_readings = 0  # Count readings during startup period
        self.min_readings_before_estimate = 3  # Reduced minimum readings before estimating
        self.accumulated_ah = 0.0  # Coulomb counting
        
        # Create deque for storing recent current values to detect rest state
        self.current_history = deque(maxlen=10)  # Store last 10 readings
        
        # Capacity estimation tracking
        self.capacity_tracking_enabled = False
        self.capacity_tracking_start_time = None
        self.capacity_tracking_start_voltage = None
        self.capacity_tracking_start_soc = None
        self.capacity_tracking_ah_used = 0.0
        self.capacity_estimation_count = 0

    def add_reading(self, voltage, current, power):
        now = datetime.now()
        
        # Store current value in history
        self.current_history.append(abs(current))
        
        # On first reading, initialize values
        if self.ema_current is None:
            self.ema_current = current
            self.ema_power = power
            self.last_timestamp = now
            self.last_soc = self._voltage_to_rough_soc(voltage)
            self.last_voltage = voltage
            self.startup_readings += 1
            
            # Start capacity tracking if we're at a high voltage
            if voltage > (self.max_voltage - 0.2):  # Near full charge
                self.start_capacity_tracking(voltage, now)
            
            return

        # Calculate time difference in hours
        time_diff = (now - self.last_timestamp).total_seconds() / 3600
        if time_diff <= 0:
            return  # Skip if no time has passed

        # Update EMAs for measurements
        self.ema_current = (self.alpha_current * current +
                           (1 - self.alpha_current) * self.ema_current)
        self.ema_power = (self.alpha_power * power +
                         (1 - self.alpha_power) * self.ema_power)

        # Get current SOC
        current_soc = self._voltage_to_rough_soc(voltage)
        self.soc = current_soc  # Use voltage-based SOC directly

        # Calculate discharge rate (% per hour) if we have previous readings
        if self.last_soc is not None and time_diff > 0:
            # Update discharge rate if we're consuming current (not charging)
            if current > 0.01:  # Only need minimal current to count as discharging
                soc_change = self.last_soc - current_soc
                
                # Even if voltage fluctuates slightly upward, we can estimate based on current draw
                if soc_change <= 0 and current > 0.1:
                    # Use a much more conservative estimate based on capacity
                    # Full battery (2.5-7.5Ah) should last 2-3 hours at idle (0.4A)
                    # So discharge rate should be around 4-5% per hour at idle
                    discharge_rate = current * 10.0  # % per hour (conservative)
                else:
                    # Limit the max discharge rate to something reasonable
                    discharge_rate = min(30.0, soc_change / time_diff)  # % per hour
                
                # Only update the EMA if we have a reasonable discharge rate
                # Allow very small positive values or use current-based estimate
                if discharge_rate > 0 or (discharge_rate <= 0 and current > 0.2):
                    # If no valid rate but significant current, use current-based estimate
                    if discharge_rate <= 0 and current > 0.2:
                        # More conservative estimate: 1A draw ~ 10-15% discharge per hour at idle
                        discharge_rate = current * 12.0  # % per hour
                    
                    if self.ema_discharge_rate is None:
                        self.ema_discharge_rate = max(0.01, discharge_rate)  # Ensure positive value
                    else:
                        # More weight to current measurement if it's high current
                        alpha = self.alpha_discharge_rate
                        if current > 1.0:  # High current gets more weight
                            alpha = min(0.3, alpha * 2)
                        
                        self.ema_discharge_rate = (alpha * discharge_rate +
                                                 (1 - alpha) * self.ema_discharge_rate)
                        
                        # Ensure we always have a positive discharge rate
                        self.ema_discharge_rate = max(0.01, self.ema_discharge_rate)

        # Update capacity tracking if active
        if self.capacity_tracking_enabled and current > 0:
            self.update_capacity_tracking(voltage, current, time_diff, now)
            
        # Start capacity tracking if conditions are right
        # Either we're near full charge, or we've been running a while with no tracking
        if not self.capacity_tracking_enabled:
            if voltage > (self.max_voltage - 0.2):  # Near full charge
                self.start_capacity_tracking(voltage, now)
            elif self.startup_readings > 60 and self.capacity_estimation_count == 0:
                # After 10 minutes, start tracking anyway if we haven't before
                self.start_capacity_tracking(voltage, now)

        # Increment startup readings counter
        self.startup_readings += 1
        
        # Save current state for next calculation
        self.last_timestamp = now
        self.last_soc = current_soc
        self.last_voltage = voltage
    
    def start_capacity_tracking(self, voltage, timestamp):
        """Start tracking for capacity estimation"""
        try:
            self.capacity_tracking_enabled = True
            self.capacity_tracking_start_time = timestamp
            self.capacity_tracking_start_voltage = voltage
            self.capacity_tracking_start_soc = self._voltage_to_rough_soc(voltage)
            self.capacity_tracking_ah_used = 0.0
            print(f"Starting capacity tracking at {voltage:.4f}V ({self.capacity_tracking_start_soc:.1f}%)")
        except Exception as e:
            print(f"Error starting capacity tracking: {str(e)}")
            self.capacity_tracking_enabled = False
    
    def update_capacity_tracking(self, voltage, current, time_diff, timestamp):
        """Update capacity tracking with new measurements"""
        try:
            # Safety check
            if self.capacity_tracking_start_time is None or self.capacity_tracking_start_soc is None:
                print("Capacity tracking not properly initialized - resetting")
                self.capacity_tracking_enabled = False
                return
                
            # Accumulate amp-hours used
            self.capacity_tracking_ah_used += current * time_diff
            
            # Calculate SOC drop
            current_soc = self._voltage_to_rough_soc(voltage)
            soc_drop = self.capacity_tracking_start_soc - current_soc
            
            # Only estimate if we have enough data (>2% SOC drop or >20 minutes)
            tracking_duration_hours = (timestamp - self.capacity_tracking_start_time).total_seconds() / 3600
            
            # If voltage increased, something is wrong - reset tracking
            if current_soc > self.capacity_tracking_start_soc + 1.0:
                print(f"Voltage increased during capacity tracking - resetting")
                self.capacity_tracking_enabled = False
                return
                
            # If tracking for too long without significant change, reset
            if tracking_duration_hours > 1.0 and soc_drop < 1.0:
                print(f"Capacity tracking reset - insufficient change ({soc_drop:.1f}%) after {tracking_duration_hours:.1f}h")
                self.capacity_tracking_enabled = False
                return
                
            # If we have enough data to make an estimate
            if soc_drop > 2.0 or tracking_duration_hours > 0.33:  # 2% drop or 20 minutes
                # Calculate the estimated capacity: 
                # If X Ah caused Y% drop, then 100% = (X / Y) * 100 Ah
                if soc_drop > 0.5:  # Only calculate if we have a meaningful drop
                    # Calculate what 1% SOC represents in Ah
                    ah_per_percent = self.capacity_tracking_ah_used / soc_drop
                    # Total capacity is 100 times that
                    estimated_capacity = ah_per_percent * 100.0
                    
                    # Apply bounds to the estimate - lithium batteries roughly 2.5-7.5Ah
                    # for a 3S pack (assuming 3S 18650 pack)
                    nominal_capacity = 2.5  # Starting point
                    # Tighter bounds based on expected capacity range
                    if 2.0 <= estimated_capacity <= 7.5:  # Reasonable range for 3S Li-ion
                        # Adjust weight based on tracking duration and SOC drop
                        # More confidence with longer tracking and larger drops
                        confidence_factor = min(0.3, (soc_drop / 20.0) + (tracking_duration_hours / 4.0))
                        alpha = max(0.05, min(0.2, confidence_factor))
                        
                        # Initialize EMA if needed
                        if self.ema_capacity is None:
                            self.ema_capacity = estimated_capacity
                        else:
                            self.ema_capacity = (alpha * estimated_capacity + 
                                               (1 - alpha) * self.ema_capacity)
                        
                        # Update our working capacity value - conservatively
                        # Bias toward the lower capacity (safer for runtime estimates)
                        self.capacity_ah = min(self.ema_capacity, estimated_capacity)
                        
                        self.capacity_estimation_count += 1
                        print(f"New capacity estimate: {estimated_capacity:.2f}Ah (EMA: {self.ema_capacity:.2f}Ah) based on " +
                              f"{self.capacity_tracking_ah_used:.4f}Ah used for {soc_drop:.1f}% drop over {tracking_duration_hours:.2f}h")
                    else:
                        print(f"Capacity estimate outside reasonable range: {estimated_capacity:.2f}Ah - ignoring")
                
                # Reset tracking to start fresh
                self.capacity_tracking_enabled = False
        except Exception as e:
            print(f"Error in capacity tracking: {str(e)}")
            self.capacity_tracking_enabled = False

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
        # Return infinity during startup period
        if self.startup_readings < self.min_readings_before_estimate:
            return float('inf')
        
        # Get current average current draw
        avg_current = 0.0
        if len(self.current_history) > 0:
            avg_current = sum(self.current_history) / len(self.current_history)
        
        # For idle operation (typically 0.35-0.45A on this system)
        # Calculate based on our current capacity estimate
        if 0.2 < avg_current < 0.5:
            # Current-based estimate for idle condition
            current_soc = self._voltage_to_rough_soc(current_voltage)
            remaining_percent = current_soc - self.threshold_soc
            
            if remaining_percent <= 0:
                return 0.0
                
            # Calculate remaining capacity
            remaining_capacity_ah = (remaining_percent / 100.0) * self.capacity_ah
            
            # Divide by current draw to get hours remaining
            hours_remaining = remaining_capacity_ah / avg_current
            
            # Add a small safety margin (10%)
            hours_remaining = hours_remaining * 0.9
            
            # Apply EMA if we have an existing estimate
            seconds_remaining = hours_remaining * 3600
            if self.ema_runtime_estimate is None:
                self.ema_runtime_estimate = seconds_remaining
            else:
                self.ema_runtime_estimate = (self.alpha_runtime * seconds_remaining +
                                          (1 - self.alpha_runtime) * self.ema_runtime_estimate)
            
            return max(0, self.ema_runtime_estimate)
        
        # Set a minimal discharge rate if we don't have one yet but have current draw
        if (self.ema_discharge_rate is None or self.ema_discharge_rate <= 0.01) and avg_current > 0.1:
            # Fallback estimation based on current
            # Much more conservative estimate: 1A draw ~ 12% discharge per hour for idle system
            self.ema_discharge_rate = max(1.0, avg_current * 12.0)  # Minimum 1% per hour if drawing current
            
        # If battery is charging or very low current draw
        if avg_current < 0.05:  # Very low current
            # Special case: if we have a prior estimate, keep it but increase uncertainty
            if self.ema_runtime_estimate is not None:
                # Gradually increase the estimate (battery lasts longer at low draw)
                return self.ema_runtime_estimate * 1.05  # 5% increase
            return float('inf')
        
        # If we still don't have discharge rate data
        if self.ema_discharge_rate is None or self.ema_discharge_rate <= 0:
            return float('inf')
            
        # Calculate remaining percentage until threshold
        current_soc = self._voltage_to_rough_soc(current_voltage)
        remaining_percent = current_soc - self.threshold_soc
        
        if remaining_percent <= 0:
            return 0.0  # Already at or below threshold
            
        # Adjust discharge rate based on current draw
        # Lower current means slower discharge
        adjusted_rate = self.ema_discharge_rate
        if avg_current < 0.5:  # Low current gets a reduced discharge rate
            adjusted_rate = self.ema_discharge_rate * (0.5 + avg_current) # Scale factor between 0.5-1.0
            
        # Calculate hours remaining based on discharge rate
        hours_remaining = remaining_percent / adjusted_rate
        
        # Apply more permissive sanity checks
        if hours_remaining < 0:
            return 0.0  # Can't have negative time
        elif hours_remaining > 48:  # 2 days maximum
            hours_remaining = 48.0
            
        # Convert to seconds
        seconds_remaining = hours_remaining * 3600
        
        # Apply EMA smoothing to runtime estimate
        if self.ema_runtime_estimate is None:
            self.ema_runtime_estimate = seconds_remaining
        else:
            self.ema_runtime_estimate = (self.alpha_runtime * seconds_remaining +
                                       (1 - self.alpha_runtime) * self.ema_runtime_estimate)
        
        return max(0, self.ema_runtime_estimate)


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

                # Calculate battery percentage (linear approximation: 8.0V empty to 12.2V full)
                percentage = max(0.0, min(100.0, (voltage - 8.0) * 100.0 / (12.2 - 8.0)))

                battery_tracker.add_reading(voltage, current, power)
                avg_power = battery_tracker.get_average_power()
                remaining_seconds = battery_tracker.estimate_remaining_time(voltage)
                
                # Log debug info to diagnose runtime estimation issues
                debug_info = ""
                if battery_tracker.startup_readings < battery_tracker.min_readings_before_estimate:
                    debug_info = f"(startup: {battery_tracker.startup_readings}/{battery_tracker.min_readings_before_estimate})"
                elif len(battery_tracker.current_history) > 0 and sum(battery_tracker.current_history) / len(battery_tracker.current_history) < 0.1:
                    debug_info = "(low current)"
                elif battery_tracker.ema_discharge_rate is None or battery_tracker.ema_discharge_rate <= 0:
                    debug_info = "(no discharge data)"
                elif remaining_seconds > 86400:
                    debug_info = "(>24h)"
                
                # Format runtime display
                if remaining_seconds == float('inf') or remaining_seconds != remaining_seconds or remaining_seconds <= 0:
                    time_str = "--:--"
                else:
                    # Format runtime nicely for display
                    if remaining_seconds > 86400:  # More than 24 hours
                        time_str = ">24h"
                    else:
                        hours = int(remaining_seconds // 3600)
                        minutes = int((remaining_seconds % 3600) // 60)
                        time_str = f"{hours:02d}:{minutes:02d}"

                # Condense all info into a single log row
                try:
                    # Calculate average current
                    avg_current = sum(battery_tracker.current_history)/max(1, len(battery_tracker.current_history))
                    
                    # Format discharge rate
                    discharge_rate = battery_tracker.ema_discharge_rate
                    if discharge_rate is None:
                        discharge_rate = 0.0
                    
                    # Estimate time to empty
                    estimated_empty_time = "N/A"
                    if remaining_seconds != float('inf'):
                        hours_to_empty = remaining_seconds / 3600
                        if hours_to_empty < 24:
                            estimated_empty_time = f"{hours_to_empty:.1f}h"
                        else:
                            estimated_empty_time = f"{hours_to_empty/24:.1f}d"
                    
                    # Consolidated output in a single line
                    print(f'Power: {voltage:.4f}V ({percentage:.1f}%) {current:.4f}A {power:.4f}W | '
                          f'Avg: {avg_power:.4f}W | Runtime: {time_str} | '
                          f'Est.Cap: {battery_tracker.capacity_ah:.2f}Ah | Discharge: {discharge_rate:.1f}%/hr | '
                          f'Time to 20%: {estimated_empty_time} | Avg current: {avg_current:.2f}A {debug_info}')
                except Exception as e:
                    # Fallback to basic info if there's an error
                    print(f'Power: {voltage:.4f}V ({percentage:.1f}%) {current:.4f}A {power:.4f}W | '
                          f'Avg: {avg_power:.4f}W | Runtime: {time_str} {debug_info}')
                    print(f"Error displaying detailed battery info: {str(e)}")
                # Add capacity and discharge rate to outputs
                capacity_value = battery_tracker.capacity_ah
                discharge_rate_value = 0.0
                if battery_tracker.ema_discharge_rate is not None:
                    discharge_rate_value = battery_tracker.ema_discharge_rate
                
                node.send_output(output_id="voltage", data=pa.array([voltage]), metadata={})
                node.send_output(output_id="current", data=pa.array([current]), metadata={})
                node.send_output(output_id="power", data=pa.array([power]), metadata={})
                node.send_output(output_id="soc", data=pa.array([percentage]), metadata={})
                # Ensure remaining_seconds is a valid number, not inf or nan
                runtime_value = float(remaining_seconds)
                if math.isinf(runtime_value) or math.isnan(runtime_value) or runtime_value < 0:
                    runtime_value = 0.0

                node.send_output(output_id="runtime", data=pa.array([runtime_value]), metadata={})
                node.send_output(output_id="capacity", data=pa.array([capacity_value]), metadata={})
                node.send_output(output_id="discharge_rate", data=pa.array([discharge_rate_value]), metadata={})

                if percentage < 10.0:
                    print("CRITICAL: Battery below 10%! Initiating shutdown...")
                    node.send_output(output_id="shutdown", data=pa.array([]), metadata={})
            except Exception as e:
                print(f"Error reading power data: {str(e)}")


if __name__ == "__main__":
    main()
