/**
 * Widget Migration Utility
 * 
 * Provides functions to migrate existing grid layout data to use the new widget type constants.
 * This allows for backward compatibility with layouts created before the refactoring.
 */

import { WIDGET_TYPES } from '../constants/widgetTypes';

// Maps old widget type names to new constants
const TYPE_MIGRATION_MAP = {
  'servo-control': WIDGET_TYPES.SERVO,
  'sounds-widget': WIDGET_TYPES.SOUND,
  'joystick-control': WIDGET_TYPES.JOYSTICK,
  'test-widget': WIDGET_TYPES.TEST,
  'separator': WIDGET_TYPES.SEPARATOR,
  'power': WIDGET_TYPES.POWER
};

/**
 * Migrates a widget's type from old naming format to new constant-based format
 * @param {string} oldType - The original widget type
 * @returns {string} The new widget type or the original if no migration needed
 */
export const migrateWidgetType = (oldType) => {
  return TYPE_MIGRATION_MAP[oldType] || oldType;
};

/**
 * Migrates an entire grid layout by updating each widget's type
 * @param {Array} layout - The layout configuration array
 * @returns {Array} The updated layout with migrated widget types
 */
export const migrateLayout = (layout) => {
  if (!layout || !Array.isArray(layout)) {
    return layout;
  }
  
  return layout.map(item => {
    if (item && item.type) {
      return {
        ...item,
        type: migrateWidgetType(item.type)
      };
    }
    return item;
  });
};

export default {
  migrateWidgetType,
  migrateLayout
};