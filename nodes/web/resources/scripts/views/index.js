/**
 * Views Registry
 *
 * Centralizes all view components for consistent imports.
 * Each view represents a full page in the application.
 */

// Import view components
import DashboardView from './DashboardView';
import GamepadView from './GamepadView';
import ServoDebugView from './ServoDebugView';
import ServoDiagnosticsOverviewView from './ServoDiagnosticsOverviewView';
import ShowtimeView from './ShowtimeView';

// Export components individually
export {
  DashboardView,
  GamepadView,
  ServoDebugView,
  ServoDiagnosticsOverviewView,
  ShowtimeView,
};

// Default export for importing all at once
export default {
  DashboardView,
  GamepadView,
  ServoDebugView,
  ServoDiagnosticsOverviewView,
  ShowtimeView,
};
