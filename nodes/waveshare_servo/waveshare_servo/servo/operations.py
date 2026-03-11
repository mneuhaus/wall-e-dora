"""Operational helpers for Waveshare SC-series servos."""

from __future__ import annotations

import time
from typing import Optional

from .diagnostics import read_status
from .registers import (
    ADDR_BAUD_RATE,
    ADDR_CCW_DEAD_ZONE,
    ADDR_CW_DEAD_ZONE,
    ADDR_EEPROM_LOCK,
    ADDR_GOAL_POSITION,
    ADDR_GOAL_SPEED,
    ADDR_ID,
    ADDR_LED_ALARM,
    ADDR_MAX_ANGLE,
    ADDR_MAX_TEMPERATURE,
    ADDR_MAX_TORQUE,
    ADDR_MAX_VOLTAGE,
    ADDR_MIN_ANGLE,
    ADDR_MIN_STARTUP_FORCE,
    ADDR_MIN_VOLTAGE,
    ADDR_MODE,
    ADDR_P_COEFFICIENT,
    ADDR_D_COEFFICIENT,
    ADDR_I_COEFFICIENT,
    ADDR_PHASE,
    ADDR_POSITION_OFFSET,
    ADDR_PROTECTION_CURRENT,
    ADDR_RESPONSE_STATUS_LEVEL,
    ADDR_RETURN_DELAY,
    ADDR_TORQUE_ENABLE,
    ADDR_UNLOAD_CONDITION,
    DEFAULT_FACTORY_BAUD,
    DEFAULT_FACTORY_DEAD_ZONE,
    DEFAULT_FACTORY_ID,
    DEFAULT_FACTORY_MAX_ANGLE,
    DEFAULT_FACTORY_MIN_ANGLE,
    DEFAULT_FACTORY_MODE,
    DEFAULT_FACTORY_OFFSET,
    EEPROM_LENGTH,
    EEPROM_LOCKED,
    EEPROM_START,
    EEPROM_UNLOCKED,
    TORQUE_DISABLED,
    TORQUE_ENABLED,
)
from .sdk import COMM_SUCCESS


def _prepare_port(port_handler) -> None:
    """Reset SDK port state before issuing a new command."""
    port_handler.is_using = False
    try:
        if port_handler.ser and port_handler.ser.is_open:
            port_handler.ser.reset_input_buffer()
    except Exception:
        pass


def _write1(packet_handler, port_handler, servo_id: int, address: int, value: int) -> bool:
    _prepare_port(port_handler)
    result, error = packet_handler.write1ByteTxRx(port_handler, servo_id, address, value)
    return result == COMM_SUCCESS and error == 0


def _write2(packet_handler, port_handler, servo_id: int, address: int, value: int) -> bool:
    _prepare_port(port_handler)
    result, error = packet_handler.write2ByteTxRx(port_handler, servo_id, address, value)
    return result == COMM_SUCCESS and error == 0


def clone_settings(packet_handler, port_handler, source_id: int, target_id: int) -> tuple[bool, list[str]]:
    """Clone EEPROM settings from one servo to another, skipping the ID."""
    skipped: list[str] = []

    _prepare_port(port_handler)
    eeprom, result, error = packet_handler.readTxRx(port_handler, source_id, EEPROM_START, EEPROM_LENGTH)
    if result != COMM_SUCCESS or len(eeprom) < EEPROM_LENGTH:
        return False, ["read source EEPROM"]

    _write1(packet_handler, port_handler, target_id, ADDR_TORQUE_ENABLE, TORQUE_DISABLED)
    if not _write1(packet_handler, port_handler, target_id, ADDR_EEPROM_LOCK, EEPROM_UNLOCKED):
        return False, ["unlock EEPROM"]

    time.sleep(0.02)

    writes = [
        ("baud rate", _write1, ADDR_BAUD_RATE, int(eeprom[3])),
        ("return delay", _write1, ADDR_RETURN_DELAY, int(eeprom[4])),
        ("response status", _write1, ADDR_RESPONSE_STATUS_LEVEL, int(eeprom[5])),
        ("min angle", _write2, ADDR_MIN_ANGLE, int(eeprom[6]) | (int(eeprom[7]) << 8)),
        ("max angle", _write2, ADDR_MAX_ANGLE, int(eeprom[8]) | (int(eeprom[9]) << 8)),
        ("max temperature", _write1, ADDR_MAX_TEMPERATURE, int(eeprom[10])),
        ("max voltage", _write1, ADDR_MAX_VOLTAGE, int(eeprom[11])),
        ("min voltage", _write1, ADDR_MIN_VOLTAGE, int(eeprom[12])),
        ("max torque", _write2, ADDR_MAX_TORQUE, int(eeprom[13]) | (int(eeprom[14]) << 8)),
        ("phase", _write1, ADDR_PHASE, int(eeprom[15])),
        ("unload condition", _write1, ADDR_UNLOAD_CONDITION, int(eeprom[16])),
        ("LED alarm", _write1, ADDR_LED_ALARM, int(eeprom[17])),
        ("P coefficient", _write1, ADDR_P_COEFFICIENT, int(eeprom[18])),
        ("D coefficient", _write1, ADDR_D_COEFFICIENT, int(eeprom[19])),
        ("I coefficient", _write1, ADDR_I_COEFFICIENT, int(eeprom[20])),
        ("startup force", _write2, ADDR_MIN_STARTUP_FORCE, int(eeprom[21]) | (int(eeprom[22]) << 8)),
        ("CW dead zone", _write1, ADDR_CW_DEAD_ZONE, int(eeprom[23])),
        ("CCW dead zone", _write1, ADDR_CCW_DEAD_ZONE, int(eeprom[24])),
        ("protection current", _write2, ADDR_PROTECTION_CURRENT, int(eeprom[25]) | (int(eeprom[26]) << 8)),
        ("position offset", _write2, ADDR_POSITION_OFFSET, int(eeprom[28]) | (int(eeprom[29]) << 8)),
        ("mode", _write1, ADDR_MODE, int(eeprom[30])),
    ]

    for label, writer, address, value in writes:
        if not writer(packet_handler, port_handler, target_id, address, value):
            skipped.append(label)
        time.sleep(0.01)

    if not _write1(packet_handler, port_handler, target_id, ADDR_EEPROM_LOCK, EEPROM_LOCKED):
        skipped.append("lock EEPROM")

    return True, skipped


def factory_reset(packet_handler, port_handler, servo_id: int) -> tuple[bool, list[str]]:
    """Reset a servo back to factory defaults."""
    skipped: list[str] = []

    if not _write1(packet_handler, port_handler, servo_id, ADDR_EEPROM_LOCK, EEPROM_UNLOCKED):
        return False, ["unlock EEPROM"]

    time.sleep(0.02)

    if not _write1(packet_handler, port_handler, servo_id, ADDR_ID, DEFAULT_FACTORY_ID):
        _write1(packet_handler, port_handler, servo_id, ADDR_EEPROM_LOCK, EEPROM_LOCKED)
        return False, ["write ID"]

    time.sleep(0.05)
    new_id = DEFAULT_FACTORY_ID

    optional_writes = [
        ("baud rate", _write1, ADDR_BAUD_RATE, DEFAULT_FACTORY_BAUD),
        ("min angle", _write2, ADDR_MIN_ANGLE, DEFAULT_FACTORY_MIN_ANGLE),
        ("max angle", _write2, ADDR_MAX_ANGLE, DEFAULT_FACTORY_MAX_ANGLE),
        ("CW dead zone", _write1, ADDR_CW_DEAD_ZONE, DEFAULT_FACTORY_DEAD_ZONE),
        ("CCW dead zone", _write1, ADDR_CCW_DEAD_ZONE, DEFAULT_FACTORY_DEAD_ZONE),
        ("mode", _write1, ADDR_MODE, DEFAULT_FACTORY_MODE),
        ("position offset", _write2, ADDR_POSITION_OFFSET, DEFAULT_FACTORY_OFFSET),
    ]

    for label, writer, address, value in optional_writes:
        if not writer(packet_handler, port_handler, new_id, address, value):
            skipped.append(label)
        time.sleep(0.01)

    if not _write1(packet_handler, port_handler, new_id, ADDR_EEPROM_LOCK, EEPROM_LOCKED):
        skipped.append("lock EEPROM")

    if not _write1(packet_handler, port_handler, new_id, ADDR_TORQUE_ENABLE, TORQUE_DISABLED):
        skipped.append("disable torque")

    return True, skipped


def auto_calibrate(
    packet_handler,
    port_handler,
    servo_id: int,
    step_size: int = 30,
    load_threshold: int = 300,
) -> Optional[tuple[int, int]]:
    """Discover safe software limits by stepping into each physical end stop."""
    step_size = max(5, step_size)
    move_speed = 400

    if not _write1(packet_handler, port_handler, servo_id, ADDR_TORQUE_ENABLE, TORQUE_ENABLED):
        return None
    _write2(packet_handler, port_handler, servo_id, ADDR_GOAL_SPEED, move_speed)

    initial_status = read_status(packet_handler, port_handler, servo_id)
    if initial_status is None:
        return None

    def find_limit(start_position: int, direction: int) -> Optional[int]:
        best_position = start_position
        target = start_position

        while True:
            next_target = max(0, min(1023, target + (direction * step_size)))
            if next_target == target:
                return best_position

            if not _write2(packet_handler, port_handler, servo_id, ADDR_GOAL_POSITION, next_target):
                return best_position

            time.sleep(0.45)

            last_position = None
            stall_count = 0
            load_count = 0
            reached_target = False

            for _ in range(5):
                status = read_status(packet_handler, port_handler, servo_id)
                if status is None:
                    return None

                current_position = status.position
                current_load = abs(status.load)

                if direction < 0:
                    if current_position < best_position:
                        best_position = current_position
                else:
                    if current_position > best_position:
                        best_position = current_position

                if abs(current_position - next_target) <= max(10, step_size // 2):
                    reached_target = True
                    target = next_target
                    break

                if last_position is not None and abs(current_position - last_position) < 2:
                    stall_count += 1
                else:
                    stall_count = 0

                if current_load > load_threshold:
                    load_count += 1
                else:
                    load_count = 0

                if stall_count >= 2 or load_count >= 3:
                    return best_position

                last_position = current_position
                time.sleep(0.12)

            if not reached_target:
                return best_position

    min_limit = find_limit(initial_status.position, -1)
    if min_limit is None:
        return None

    max_limit = find_limit(min_limit, 1)
    if max_limit is None:
        return None

    safe_min = min_limit + 25
    safe_max = max_limit - 25
    if safe_max <= safe_min:
        return None

    return safe_min, safe_max
