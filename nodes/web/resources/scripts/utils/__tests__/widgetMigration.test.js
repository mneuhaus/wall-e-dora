import { migrateWidgetType, migrateLayout } from '../widgetMigration';
import { WIDGET_TYPES } from '../../constants/widgetTypes';

describe('widgetMigration', () => {
  describe('migrateWidgetType', () => {
    test('migrates servo-control to servo-widget', () => {
      expect(migrateWidgetType('servo-control')).toBe(WIDGET_TYPES.SERVO);
    });

    test('migrates sounds-widget to sound-widget', () => {
      expect(migrateWidgetType('sounds-widget')).toBe(WIDGET_TYPES.SOUND);
    });

    test('migrates joystick-control to joystick-widget', () => {
      expect(migrateWidgetType('joystick-control')).toBe(WIDGET_TYPES.JOYSTICK);
    });

    test('returns the same value for already migrated types', () => {
      expect(migrateWidgetType(WIDGET_TYPES.SERVO)).toBe(WIDGET_TYPES.SERVO);
      expect(migrateWidgetType(WIDGET_TYPES.SOUND)).toBe(WIDGET_TYPES.SOUND);
    });

    test('returns the original value for unknown types', () => {
      expect(migrateWidgetType('unknown-widget')).toBe('unknown-widget');
    });
  });

  describe('migrateLayout', () => {
    test('migrates all widget types in a layout', () => {
      const layout = [
        { i: 'widget1', type: 'servo-control', x: 0, y: 0, w: 2, h: 2, servoId: 1 },
        { i: 'widget2', type: 'sounds-widget', x: 2, y: 0, w: 4, h: 3 },
        { i: 'widget3', type: 'joystick-control', x: 6, y: 0, w: 2, h: 2 }
      ];

      const migratedLayout = migrateLayout(layout);
      
      expect(migratedLayout).toEqual([
        { i: 'widget1', type: WIDGET_TYPES.SERVO, x: 0, y: 0, w: 2, h: 2, servoId: 1 },
        { i: 'widget2', type: WIDGET_TYPES.SOUND, x: 2, y: 0, w: 4, h: 3 },
        { i: 'widget3', type: WIDGET_TYPES.JOYSTICK, x: 6, y: 0, w: 2, h: 2 }
      ]);
    });

    test('handles empty layout', () => {
      expect(migrateLayout([])).toEqual([]);
    });

    test('handles null/undefined layout', () => {
      expect(migrateLayout(null)).toBeNull();
      expect(migrateLayout(undefined)).toBeUndefined();
    });

    test('handles layout items without type property', () => {
      const layout = [
        { i: 'widget1', x: 0, y: 0, w: 2, h: 2 } // no type property
      ];
      
      const migratedLayout = migrateLayout(layout);
      
      expect(migratedLayout).toEqual([
        { i: 'widget1', x: 0, y: 0, w: 2, h: 2 } // should remain unchanged
      ]);
    });
  });
});