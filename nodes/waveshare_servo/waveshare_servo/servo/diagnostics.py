"""Diagnostic read helpers for Waveshare SC-series servos."""

from __future__ import annotations

from typing import Optional

from .models import ServoConfig, ServoModel, ServoStatus
from .registers import (
    ADDR_EEPROM_LOCK,
    ADDR_GOAL_POSITION,
    ADDR_GOAL_SPEED,
    ADDR_GOAL_TIME,
    BAUD_RATE_VALUES,
    EEPROM_LENGTH,
    EEPROM_START,
    SRAM_LENGTH,
    SRAM_START,
    STATUS_LENGTH,
    STATUS_START,
)
from .sdk import COMM_SUCCESS, SCS_MAKEWORD, SCS_TOHOST


def _prepare_port(port_handler) -> None:
    """Reset SDK port state before issuing a new command."""
    port_handler.is_using = False
    try:
        if port_handler.ser and port_handler.ser.is_open:
            port_handler.ser.reset_input_buffer()
    except Exception:
        pass


def _read_bytes(packet_handler, port_handler, servo_id: int, address: int, length: int) -> Optional[list[int]]:
    """Read a byte range from the servo and return a list of ints."""
    _prepare_port(port_handler)
    data, result, error = packet_handler.readTxRx(port_handler, servo_id, address, length)
    if result != COMM_SUCCESS:
        return None
    return list(data)


def _read_word(data: list[int], offset: int) -> int:
    """Read a 16-bit value from a byte buffer using SDK byte-order helpers."""
    return SCS_MAKEWORD(data[offset], data[offset + 1])


def read_status(packet_handler, port_handler, servo_id: int) -> Optional[ServoStatus]:
    """Read live status registers from the servo."""
    data = _read_bytes(packet_handler, port_handler, servo_id, STATUS_START, STATUS_LENGTH)
    if not data or len(data) < 8:
        return None

    position = _read_word(data, 0) & 0x0FFF
    raw_speed = _read_word(data, 2) & 0x07FF
    raw_load = _read_word(data, 4) & 0x07FF

    return ServoStatus(
        position=position,
        speed=int(SCS_TOHOST(raw_speed, 10)),
        load=int(SCS_TOHOST(raw_load, 10)),
        voltage=(data[6] / 10.0),
        temperature=int(data[7]),
        moving=bool(data[10]) if len(data) > 10 else False,
    )


def read_model(packet_handler, port_handler, servo_id: int) -> Optional[ServoModel]:
    """Read the model number and map it to a known servo model."""
    data = _read_bytes(packet_handler, port_handler, servo_id, EEPROM_START, 2)
    if not data or len(data) < 2:
        return None
    return ServoModel.from_model_number(SCS_MAKEWORD(data[0], data[1]))


def read_config(packet_handler, port_handler, servo_id: int) -> Optional[ServoConfig]:
    """Read EEPROM and writable SRAM configuration registers."""
    eeprom = _read_bytes(packet_handler, port_handler, servo_id, EEPROM_START, EEPROM_LENGTH)
    if not eeprom or len(eeprom) < EEPROM_LENGTH:
        return None

    sram = _read_bytes(packet_handler, port_handler, servo_id, SRAM_START, SRAM_LENGTH)
    if not sram or len(sram) < SRAM_LENGTH:
        return None

    model = ServoModel.from_model_number(_read_word(eeprom, 0))
    mode = int(eeprom[30])

    return ServoConfig(
        id=int(eeprom[2]),
        model_number=model.model_number,
        model_name=model.name,
        baud_rate=int(eeprom[3]),
        baud_rate_bps=BAUD_RATE_VALUES.get(int(eeprom[3]), 1_000_000),
        return_delay=int(eeprom[4]),
        response_status_level=int(eeprom[5]),
        min_angle=_read_word(eeprom, 6),
        max_angle=_read_word(eeprom, 8),
        max_temperature=int(eeprom[10]),
        max_voltage=int(eeprom[11]),
        min_voltage=int(eeprom[12]),
        max_torque=_read_word(eeprom, 13),
        phase=int(eeprom[15]),
        unload_condition=int(eeprom[16]),
        led_alarm=int(eeprom[17]),
        p_coefficient=int(eeprom[18]),
        d_coefficient=int(eeprom[19]),
        i_coefficient=int(eeprom[20]),
        min_startup_force=_read_word(eeprom, 21),
        cw_dead_zone=int(eeprom[23]),
        ccw_dead_zone=int(eeprom[24]),
        protection_current=_read_word(eeprom, 25),
        position_offset=int(SCS_TOHOST(_read_word(eeprom, 28), 15)),
        mode=mode,
        mode_name={0: "Servo", 1: "Motor", 2: "Step", 3: "PWM"}.get(mode, "Unknown"),
        torque_enabled=bool(sram[0]),
        acceleration=int(sram[1]),
        goal_position=_read_word(sram, ADDR_GOAL_POSITION - SRAM_START),
        goal_time=_read_word(sram, ADDR_GOAL_TIME - SRAM_START),
        goal_speed=int(SCS_TOHOST(_read_word(sram, ADDR_GOAL_SPEED - SRAM_START) & 0x07FF, 10)),
        lock_state=bool(sram[ADDR_EEPROM_LOCK - SRAM_START]),
        raw_eeprom=list(eeprom),
        raw_sram=list(sram),
    )
