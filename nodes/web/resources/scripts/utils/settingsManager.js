/**
 * Settings Manager Utility
 * 
 * A centralized utility for managing widget and application settings.
 * Provides a consistent API for reading, writing, and syncing settings
 * across the application, with both backend persistence and localStorage fallback.
 */

import node from '../Node';

/**
 * Default settings by widget type
 */
export const DEFAULT_SETTINGS = {
  'servo-widget': {
    servoId: null,
    speed: 100
  },
  'joystick-widget': {
    xServoId: null,
    yServoId: null,
    speed: 100,
    invertX: false,
    invertY: false
  },
  'sound-widget': {
    volume: 70,
    autoplay: false
  },
  'power-widget': {
    showBatteryPercent: true
  }
};

/**
 * Gets default settings for a widget type
 * @param {string} widgetType - Type of widget
 * @returns {Object} Default settings for that widget type
 */
export const getDefaultSettings = (widgetType) => {
  return DEFAULT_SETTINGS[widgetType] || {};
};

/**
 * Updates widget settings in the grid context
 * @param {string} widgetId - ID of the widget to update
 * @param {Object} newSettings - New settings to apply
 * @param {Function} updateWidgetProps - GridContext's updateWidgetProps function
 * @param {boolean} backendSync - Whether to explicitly sync with backend
 */
export const updateWidgetSettings = (widgetId, newSettings, updateWidgetProps, backendSync = false) => {
  if (!widgetId) {
    console.error("Cannot update settings: widgetId is required");
    return;
  }
  
  console.log(`Updating settings for widget ${widgetId}:`, newSettings);
  
  // Update the widget through GridContext
  updateWidgetProps(widgetId, newSettings);
  
  // If explicit backend sync is requested (for critical settings)
  if (backendSync) {
    syncSettingsWithBackend(widgetId, newSettings);
  }
};

/**
 * Explicitly sync specific settings with backend
 * @param {string} widgetId - ID of the widget
 * @param {Object} settings - Settings to sync
 */
export const syncSettingsWithBackend = (widgetId, settings) => {
  // Determine if this is a joystick widget with servo settings
  if (settings.hasOwnProperty('xServoId') || settings.hasOwnProperty('yServoId')) {
    if (settings.hasOwnProperty('xServoId')) {
      node.emit('save_joystick_servo', {
        data: {
          id: widgetId,
          axis: 'x',
          servoId: settings.xServoId === null ? null : parseInt(settings.xServoId)
        }
      });
    }
    
    if (settings.hasOwnProperty('yServoId')) {
      node.emit('save_joystick_servo', {
        data: {
          id: widgetId,
          axis: 'y',
          servoId: settings.yServoId === null ? null : parseInt(settings.yServoId)
        }
      });
    }
  }
};

/**
 * Loads settings with defaults merged
 * @param {Object} widgetData - Current widget data
 * @returns {Object} Widget data with defaults applied
 */
export const loadSettingsWithDefaults = (widgetData) => {
  if (!widgetData || !widgetData.type) {
    return widgetData;
  }
  
  const defaults = getDefaultSettings(widgetData.type);
  return {
    ...defaults,
    ...widgetData
  };
};

// For testing purposes only
export const _testing = {
  node,
};

export default {
  getDefaultSettings,
  updateWidgetSettings,
  syncSettingsWithBackend,
  loadSettingsWithDefaults,
  DEFAULT_SETTINGS
};