/**
 * Control Components Registry
 * 
 * Centralizes all control components for consistent imports.
 */

// Import all control components
import { ServoSelector } from '../common/inputs';
import GridLockControl from './GridLockControl';
import AddWidgetControl from './AddWidgetControl';
import VolumeControl from './VolumeControl';
import RandomSoundControl from './RandomSoundControl';

// Export components individually
export { ServoSelector, GridLockControl, AddWidgetControl, VolumeControl, RandomSoundControl };

// Default export for importing all at once
export default {
  ServoSelector,
  GridLockControl,
  AddWidgetControl,
  VolumeControl,
  RandomSoundControl
};