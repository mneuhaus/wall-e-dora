/**
 * Widget Registry
 * 
 * Centralizes all widget components to provide a single import point and 
 * a mapping between widget types and their components.
 */
import { WIDGET_TYPES } from '../../constants/widgetTypes';

// Import all widget components
import ServoWidget from './ServoWidget';
import SoundWidget from './SoundWidget';
import JoystickWidget from './JoystickWidget';
import TestWidget from './TestWidget';
import EyesWidget from './EyesWidget';

/**
 * Registry of all available widgets mapped by their type constants
 */
export const WIDGET_REGISTRY = {
  [WIDGET_TYPES.SERVO]: ServoWidget,
  [WIDGET_TYPES.SOUND]: SoundWidget,
  [WIDGET_TYPES.JOYSTICK]: JoystickWidget,
  [WIDGET_TYPES.TEST]: TestWidget,
  [WIDGET_TYPES.EYES]: EyesWidget,
  [WIDGET_TYPES.SEPARATOR]: 'div',
};

/**
 * Returns the widget component for the given type
 * @param {string} type - Widget type identifier
 * @returns {React.Component|string} Component or HTML tag to render
 */
export const getWidgetComponent = (type) => {
  return WIDGET_REGISTRY[type] || 'div';
};

/**
 * Returns true if the widget type has settings available
 * @param {string} type - Widget type identifier
 * @returns {boolean} Whether the widget has settings
 */
export const hasWidgetSettings = (type) => {
  return [WIDGET_TYPES.JOYSTICK].includes(type);
};

export default {
  WIDGET_REGISTRY,
  getWidgetComponent,
  hasWidgetSettings
};