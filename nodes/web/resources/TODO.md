# WALL-E-DORA Technical Debt and Improvement Plan

This document outlines the technical debt accumulated during the prototyping phase and proposes structured approaches to address each issue. The goal is to transform the codebase from a prototype to a production-quality system with consistent patterns, robust error handling, and improved maintainability.

## Architecture & Consistency

-   **[High] Standardize Configuration:**
    -   Refactor `audio` node to use `config` node instead of `volume.cfg`.
    -   Refactor `waveshare_servo` node (`config/handler.py`) to use `config` node instead of `servo.json`.
    -   Refactor `tracks` node to get `SERIAL_PORT` and joystick settings from `config` node.
    -   Refactor `eyes` node to get fixed IPs from `config` node.
    -   Review `config` node's `update_setting` for robustness with nested structures/lists.
    -   Ensure `grid_state.json` handling is moved entirely to `config` node or managed consistently.
    -   Decide on single source of truth for `gamepad_profiles` (currently saved in two locations).
-   **[Medium] Standardize Event Handling:**
    -   Use `extract_event_data` utility consistently across all Python input handlers (e.g., `audio/main.py`, `web/handlers/gamepad_profiles.py`).
    -   Define and use constants for event names (both Python and JS).
    -   Review `dataflow.yml`: Consolidate `GAMEPAD_*` events into a single `gamepad_state` event if feasible. Check `TICK` vs `tick` consistency. Review `settings` broadcast frequency/necessity.
-   **[Medium] Improve Node Structure Adherence:**
    -   Review all Python nodes against `Dora Node Architecture` in `CLAUDE.md`.
    -   Ensure `main.py` files are purely for orchestration.
    -   Refactor large files (>200 lines) into smaller modules (e.g., `Gamepad.js`, `ServoDebugView.jsx`, `gamepad_profiles.py`, `tick.py`).
    -   Fix `sys.path.insert` usage by ensuring correct package structure and editable installs.
-   **[Low] Cleanup Global Variables:** Refactor `web/main.py` to avoid global variables (`global_web_inputs`, `ws_clients`, `web_loop`).

## Python Nodes

-   **[High] `waveshare_servo` Refactoring:**
    -   Remove direct file I/O in `config/handler.py`.
    -   Cleanup unused code paths in `servo/controller.py` (non-SDK methods).
    -   Refactor `servo/discovery.py` to use SDK `ping` instead of manual byte commands.
    -   Move `wiggle` and `calibrate` logic into `Servo` class methods or ensure they use `Servo` methods consistently.
    -   Simplify `inputs/gamepad_event.py` logic for input ranges and ensure `move_servo` is called correctly via context/node.
    -   Review and simplify `inputs/tick.py` ID assignment logic. Ensure `next_available_id` initialization is correct.
    -   Cleanup `main.py` by removing references to unused setting handlers.
-   **[Medium] `tracks` Refactoring:**
    -   Make `SERIAL_PORT`, joystick settings configurable.
    -   Encapsulate easing logic.
-   **[Medium] `eyes` Refactoring:**
    -   Make fixed IPs configurable.
    -   Consolidate file syncing logic between `inputs/tick.py` and `firmware/sync_images.py`. Choose one primary mechanism.
    -   Consider using mDNS or a more robust discovery method than IP scanning if fixed IPs aren't sufficient.
-   **[Low] `audio` Refactoring:**
    -   Use `config` node for volume.
    -   Simplify event value handling using `extract_event_data`.
-   **[Low] General Python Cleanup:**
    -   Improve error handling and logging consistency across all nodes.
    -   Ensure imports follow standard order.

## Web Frontend

-   **[High] Refactor Direct DOM Manipulation:**
    -   Rewrite `ServoSelector.jsx` using React `createPortal` and standard event handling. Remove manual listener management.
-   **[Medium] Improve WebSocket Client (`Node.js`):**
    -   Refine reconnection logic (e.g., notify user after max attempts).
    -   Add logging for WebSocket errors, especially JSON parsing failures.
-   **[Medium] Simplify Complex Components:**
    -   Refactor `Gamepad.js`: Simplify state updates, mapping logic, and analog/digital handling. Reduce polling frequency if possible or make it adaptive.
    -   Refactor `ServoDebugView.jsx`: Simplify state management, reduce `useEffect` complexity, manage timeouts carefully. Ensure gamepad listener doesn't conflict with `Gamepads.js`.
    -   Refactor `GridContext.jsx`: Simplify initialization logic. Consider debouncing layout saves (`onLayoutChange`). Clarify backend vs. localStorage sync strategy.
    -   Refactor `JoystickWidget.jsx`: Simplify `useEffect` logic.
-   **[Low] Performance Optimization:**
    -   Apply `React.memo`, `useCallback`, `useMemo` where appropriate to prevent unnecessary re-renders.
    -   Review state updates in contexts (`AppContext`, `GridContext`) to minimize cascading renders.
-   **[Low] Review PWA Logic:** Evaluate if PWA behavior in `template.html` can be moved into the React app. Update `service-worker.js` caching strategy if needed.
-   **[Low] Build Configuration:** Ensure `web/build` Makefile target uses `encore production`.

## Firmware

-   **[Medium] Remove Hardcoded Values:** Make ports (`Makefile`) and potentially other constants configurable if necessary.
-   **[Medium] `eyes/firmware/wall-e_eye.ino`:** Replace `delay()` with non-blocking alternatives or `yield()`/`server.handleClient()` calls during long operations. Improve SD/WiFi error handling.
-   **[Low] `tracks/firmware/main.cpp`:** Review mixing logic for clarity. Ensure safety mechanisms (like heartbeat timeout) are robust.
-   **[Low] Script Cleanup:** Clarify purpose of `png_to_gif.py`. Document dependencies for `optimize_gif.py`. Ensure `flash_firmware.py` handles permissions issues gracefully or provides clearer instructions.

## Documentation & Testing

-   **[High] Expand Test Coverage:**
    -   Write comprehensive unit tests for Python node logic (input handlers, domain logic, utilities).
    -   Write component and integration tests for the React frontend, covering widget interactions, settings, and context behavior.
    -   Add basic tests for firmware logic if possible.
-   **[Medium] Update Documentation:**
    -   Review and update all node `README.md` files to match current functionality, inputs, outputs, and architecture.
    -   Add JSDoc comments to all React components and major functions.
    -   Add docstrings to Python modules, classes, and functions following conventions.
    -   Ensure `CLAUDE.md` guidelines are reflected in the codebase or update the guidelines.
    -   Document dependencies for firmware tools (`gifsicle`, `ffmpeg`, etc.).
-   **[Low] Review `.gitignore`:** Ensure all generated/temporary files are ignored. Clarify intention regarding `config/` files.

## Completed Items (from previous TODO)

-   [x] Vue to React Migration (Core infrastructure, components, styling, routing)
-   [x] Basic grid layout persistence (Backend + localStorage fallback)
-   [x] Standardized component naming and structure (Widgets, Status, Views, Controls)
-   [x] Widget registry and type constants
-   [x] Basic settings persistence framework (`settingsManager.js`)
