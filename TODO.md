# WALL-E-DORA Technical Debt and Improvement Plan

This document outlines the technical debt accumulated during the prototyping phase and proposes structured approaches to address each issue. The goal is to transform the codebase from a prototype to a production-quality system with consistent patterns, robust error handling, and improved maintainability.

## Immediate Action Items

### Replace Eyes Widget HTTP Proxy with Native Dora Events

**Priority:** Medium  
**Estimated Effort:** 3-4 hours

Currently, the WALL-E Eyes Widget uses an HTTP proxy endpoint to communicate with the eye displays. This is a temporary solution that should be replaced with a proper Dora event flow.

#### Required Changes:

1. Create a new `play_gif` output event in the web node
   ```yaml
   outputs:
     - play_gif
   ```

2. Add corresponding `play_gif` input event to the eyes node
   ```yaml
   inputs:
     play_gif: web/play_gif
   ```

3. Implement input handler in the eyes node:
   - Create `/eyes/eyes/inputs/play_gif.py` 
   - Implement a handler that communicates with both eye displays
   - Use direct HTTP requests from the Python code (no CORS issues there)

4. Update the frontend widget:
   - Replace proxy endpoint calls with a WebSocket emission
   - Send the `play_gif` event with the filename as data

5. Update dataflow.yml:
   - Connect the events between web and eyes nodes

This approach will:
- Maintain a cleaner architecture by respecting the dataflow design
- Remove the need for the proxy endpoint
- Make the system more maintainable
- Allow for future enhancements like queueing images or synchronizing eye displays

## 1. ✅ Inconsistent Naming Conventions

### Issue (RESOLVED)

The component naming conventions have been standardized across the codebase following the plan below.

### Solution Implemented

#### Frontend Naming Convention

**Core Pattern**:
We implemented a consistent suffix-based naming scheme:
- `*Widget.jsx` - Grid-based widget components (draggable components in dashboard)
- `*Status.jsx` - Status indicators in header/menu bar
- `*View.jsx` - Full page/screen components
- `*Control.jsx` - User input components (sliders, joysticks, etc.)

**Directory Structure**:
We reorganized components into a logical directory structure:
```
/scripts
  /components
    /widgets      # All grid-based widget components
    /status       # Status bar components
    /controls     # User input control components
    /common       # Shared utility components
      /inputs     # Reusable input components
  /contexts       # React context providers
  /constants      # Shared constants and enums
  /utils          # Utility functions
  /views          # Full page views
  App.jsx         # Root application component
  Node.js         # WebSocket communication
```

#### Component Registry and Type Constants

1. Created type constants in `/constants/widgetTypes.js`
2. Implemented widget registry in `/components/widgets/index.js`
3. Updated WidgetContainer to use the registry pattern
4. Created migration utility in `/utils/widgetMigration.js` to handle backward compatibility

#### Actual Component Renames & Moves

| Original File | New File |
|--------------|----------|
| `ServoControl.jsx` | `widgets/ServoWidget.jsx` |
| `SoundsWidget.jsx` | `widgets/SoundWidget.jsx` |
| `JoystickControl.jsx` | `widgets/JoystickWidget.jsx` |
| `TestWidget.jsx` | `widgets/TestWidget.jsx` |
| `Power.jsx` | `widgets/PowerWidget.jsx` |
| `ConnectionStatus.jsx` | `status/ConnectionStatus.jsx` |
| `ServoStatus.jsx` | `status/ServoStatus.jsx` |
| `Gamepad.jsx` | `status/GamepadStatus.jsx` |
| `GridLock.jsx` | `controls/GridLockControl.jsx` |
| `ServoSelector.jsx` | `common/inputs/ServoSelector.jsx` |
| `Volume.jsx` | `controls/VolumeControl.jsx` |
| `AddWidget.jsx` | `controls/AddWidgetControl.jsx` |
| `Dashboard.jsx` | `views/DashboardView.jsx` |
| `Gamepad.jsx` (view) | `views/GamepadView.jsx` |
| `ServoDebug.jsx` | `views/ServoDebugView.jsx` |

Additional indexes were created for each directory to provide convenient imports, and appropriate documentation was added to the web node README.md file.

## 2. Settings Persistence

### Issues

- **Multiple Persistence Mechanisms**:
  - Audio node uses `volume.cfg` file
  - Web node uses `grid_state.json`
  - Waveshare servo uses `servo_settings.json`
  - Multiple serialization/deserialization operations for the same data
  - Redundant persistence logic duplicated across nodes

### Solution

1. **Create Settings Service**:
   - Implement a common settings service for both Python and JavaScript
   ```python
   # settings_service.py
   class SettingsService:
       def __init__(self, file_path, defaults=None):
           self.file_path = file_path
           self.defaults = defaults or {}
           self.settings = self._load()
           
       def _load(self):
           try:
               with open(self.file_path, 'r') as f:
                   return json.load(f)
           except (FileNotFoundError, json.JSONDecodeError):
               return self.defaults.copy()
               
       def save(self):
           with open(self.file_path, 'w') as f:
               json.dump(self.settings, f)
               
       def get(self, key, default=None):
           return self.settings.get(key, default)
           
       def set(self, key, value):
           self.settings[key] = value
           self.save()
   ```

2. **Standardize Configuration Formats**:
   - Convert all config files to JSON format
   - Use consistent naming for configuration files (`<node_name>_config.json`)
   - Create migration helpers for existing configuration files

3. **Decouple UI State from Settings**:
   - Separate transient UI state from persistent settings
   - Implement clear boundaries between state types

## 3. Event Handling

### Issues

- **Inconsistent Event Registration**:
  - Some components use direct `node.on/emit`, others use Context API
  - Missing event cleanup in some `useEffect` hooks
  - Some event handlers missing error boundaries
  - Mix of camelCase and snake_case in event names

### Solution

1. **Create Event Service**:
   ```javascript
   // EventService.js
   class EventService {
     constructor(node) {
       this.node = node;
       this.subscriptions = new Map();
     }
     
     subscribe(eventName, callback) {
       const unsubscribe = this.node.on(eventName, callback);
       this.subscriptions.set(callback, { eventName, unsubscribe });
       return () => this.unsubscribe(callback);
     }
     
     unsubscribe(callback) {
       const subscription = this.subscriptions.get(callback);
       if (subscription) {
         subscription.unsubscribe();
         this.subscriptions.delete(callback);
       }
     }
     
     emit(eventName, data) {
       this.node.emit(eventName, data);
     }
     
     useEvent(eventName, callback, deps = []) {
       useEffect(() => {
         const unsubscribe = this.subscribe(eventName, callback);
         return unsubscribe;
       }, [eventName, callback, ...deps]);
     }
   }
   ```

2. **Standardize Event Naming**:
   - Use consistent camelCase for all event names
   - Create an event name registry with constants:
   ```javascript
   // events.js
   export const EVENTS = {
     SERVO_STATUS: 'servoStatus',
     PLAY_SOUND: 'playSound',
     SET_VOLUME: 'setVolume',
     // etc.
   };
   ```

3. **Implement React Error Boundaries**:
   - Add error boundaries around all component renders
   - Implement fallback UI for component failures

## 4. Error Handling

### Issues

- **Inconsistent Error Recovery**:
  - Waveshare node has comprehensive error handling
  - Other nodes have minimal error recovery
  - Missing error boundaries in React components
  - Inconsistent error logging and reporting

### Solution

1. **Create Error Handling Strategy**:
   - Define error severity levels (fatal, warning, recoverable)
   - Implement consistent error logging pattern
   ```python
   # error_handling.py
   def handle_error(error, context=None, severity="warning"):
       """
       Standard error handler for consistent logging and recovery.
       """
       context_str = f" in {context}" if context else ""
       logger.log(get_level(severity), f"{error.__class__.__name__}{context_str}: {str(error)}")
       
       if severity == "fatal":
           # Take fatal error actions
           raise error
       
       # Return appropriate fallback or None
       return get_fallback(context)
   ```

2. **Implement React Error Boundaries**:
   ```jsx
   // ErrorBoundary.jsx
   class ErrorBoundary extends React.Component {
     constructor(props) {
       super(props);
       this.state = { hasError: false };
     }
     
     static getDerivedStateFromError(error) {
       return { hasError: true };
     }
     
     componentDidCatch(error, errorInfo) {
       console.error("Component error:", error, errorInfo);
     }
     
     render() {
       if (this.state.hasError) {
         return this.props.fallback || <div>Something went wrong.</div>;
       }
       
       return this.props.children;
     }
   }
   ```

3. **Add Fallback Behaviors**:
   - Implement fallback behaviors for all critical systems
   - Add retry mechanisms for transient failures
   - Create a central error reporting system

## 5. Code Duplication

### Issues

- **Repeated Patterns**:
  - Type conversion logic duplicated
  - Similar component initialization patterns
  - Repeated settings management code
  - Multiple implementations of the same utility functions

### Solution

1. **Create Utility Libraries**:
   ```javascript
   // utils/conversion.js
   export function parseServoId(id) {
     return typeof id === 'string' ? parseInt(id, 10) : id;
   }
   
   export function ensureNumeric(value, defaultValue = 0) {
     const num = Number(value);
     return isNaN(num) ? defaultValue : num;
   }
   ```

2. **Implement Shared Hooks**:
   ```javascript
   // hooks/usePersistedState.js
   export function usePersistedState(key, initialValue) {
     const [state, setState] = useState(() => {
       try {
         const item = localStorage.getItem(key);
         return item ? JSON.parse(item) : initialValue;
       } catch (error) {
         console.error('Error loading persisted state:', error);
         return initialValue;
       }
     });
     
     useEffect(() => {
       try {
         localStorage.setItem(key, JSON.stringify(state));
       } catch (error) {
         console.error('Error saving persisted state:', error);
       }
     }, [key, state]);
     
     return [state, setState];
   }
   ```

3. **Create Common Settings Service**:
   - Extract settings management into a shared service
   - Use dependency injection for configuration

## 6. Performance Issues

### Issues

- **Inefficient React Rendering**:
  - Missing memoization causing unnecessary re-renders
  - Inefficient hooks dependencies
  - Excessive state updates
  - Multiple file I/O operations
  - Inefficient background thread usage

### Solution

1. **Add Component Memoization**:
   ```javascript
   // Memoized components
   const ServoControl = React.memo(function ServoControl(props) {
     // Component implementation
   });
   
   // Memoized event handlers
   const handleServoChange = useCallback((value) => {
     // Handler implementation
   }, [dependencies]);
   ```

2. **Optimize File Operations**:
   - Batch file operations
   - Implement caching layer
   - Add debounced saving:
   ```javascript
   const debouncedSave = useMemo(() => 
     debounce((data) => {
       // Save operation
     }, 500)
   , []);
   ```

3. **Improve Thread Management**:
   - Use proper thread pools
   - Implement event-driven communication instead of polling
   - Use cooperative multitasking patterns

## 7. Architectural Improvements

### Issues

- **Missing Abstraction Layers**:
  - Direct dependencies between components
  - Tight coupling between UI and backend
  - No clear separation of concerns

### Solution

1. **Implement Service Layer**:
   ```javascript
   // services/ServoService.js
   class ServoService {
     getServos() { /* implementation */ }
     controlServo(id, position) { /* implementation */ }
     calibrateServo(id) { /* implementation */ }
   }
   
   export const servoService = new ServoService();
   ```

2. **Adopt Model-View-ViewModel Pattern**:
   - Extract business logic from components
   - Create view models to manage component state
   - Implement data transformation layer

3. **Create Domain Models**:
   ```javascript
   // models/Servo.js
   class Servo {
     constructor(data) {
       this.id = data.id;
       this.position = data.position;
       this.minPos = data.min_pos;
       this.maxPos = data.max_pos;
       this.alias = data.alias || `Servo ${this.id}`;
     }
     
     get displayName() {
       return this.alias || `Servo ${this.id}`;
     }
     
     isInRange(position) {
       return position >= this.minPos && position <= this.maxPos;
     }
   }
   ```

## 8. Documentation Improvements

### Issues

- **Inconsistent Documentation**:
  - Missing component documentation
  - Outdated comments
  - No clear architecture documentation

### Solution

1. **Add JSDoc to All Components**:
   ```javascript
   /**
    * ServoControl - Controls a single servo motor
    * 
    * @component
    * @param {Object} props - Component props
    * @param {number} props.servoId - ID of the servo to control
    * @param {string} [props.alias] - Optional display name for the servo
    * @param {function} [props.onChange] - Optional callback for position changes
    */
   function ServoControl(props) {
     // Implementation
   }
   ```

2. **Create Architecture Documents**:
   - Add system architecture diagrams
   - Document node communication patterns
   - Create component relationship diagrams

3. **Enhance README Files**:
   - Update node README files with current implementation details
   - Add troubleshooting sections
   - Include development workflow documentation

## Implementation Plan

### Phase 1: Foundation (2 weeks)

1. **Create Utility Libraries**
   - Build common utilities for both frontend and backend
   - Extract repeated code into shared functions
   - Implement settings service

2. **Standardize Naming Conventions**
   - Rename components for consistency
   - Create type constants and registries
   - Update references throughout the codebase

### Phase 2: Core Improvements (3 weeks)

1. **Enhance Error Handling**
   - Implement error boundaries
   - Add fallback behaviors
   - Create consistent error logging

2. **Optimize State Management**
   - Implement service layer
   - Extract view models
   - Create domain models

3. **Performance Optimizations**
   - Add component memoization
   - Optimize file operations
   - Improve thread management

### Phase 3: Documentation and Testing (2 weeks)

1. **Enhance Documentation**
   - Add JSDoc to all components
   - Create architecture diagrams
   - Update README files

2. **Improve Testing**
   - Add unit tests for utility functions
   - Implement component tests
   - Create integration tests for node communication

## Conclusion

Addressing this technical debt will transform the WALL-E-DORA project from a prototype to a production-ready system with improved maintainability, performance, and robustness. The phased approach allows for incremental improvements while maintaining system functionality throughout the refactoring process.

The most critical areas to address first are the inconsistent naming conventions and the settings persistence mechanisms, as these improvements will provide the foundation for further enhancements.