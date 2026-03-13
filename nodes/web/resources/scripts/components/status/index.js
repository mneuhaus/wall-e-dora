/**
 * Status Components Registry
 * 
 * Centralizes all status indicator components for consistent imports.
 */

import ConnectionStatus from './ConnectionStatus';
import ServoStatus from './ServoStatus';
import GamepadStatus from './GamepadStatus';
import PowerStatus from './PowerStatus';
import DoorStatus from './DoorStatus';
import CameraStatus from './CameraStatus';

export { ConnectionStatus, ServoStatus, GamepadStatus, PowerStatus, DoorStatus, CameraStatus };

export default {
  ConnectionStatus,
  ServoStatus,
  GamepadStatus,
  PowerStatus,
  DoorStatus,
  CameraStatus,
};
