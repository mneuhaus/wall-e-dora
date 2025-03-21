/**
 * Status Components Registry
 * 
 * Centralizes all status indicator components for consistent imports.
 */

// Import all status components
import ConnectionStatus from './ConnectionStatus';
import ServoStatus from './ServoStatus';
import GamepadStatus from './GamepadStatus';

// Export components individually
export { ConnectionStatus, ServoStatus, GamepadStatus };

// Default export for importing all at once
export default {
  ConnectionStatus,
  ServoStatus,
  GamepadStatus
};