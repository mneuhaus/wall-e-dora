# WALL-E-DORA Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Joystick control widget using rc-joystick library
  - Allows linking X and Y axes to separate servos
  - Configurable servo assignments via settings modal
  - Adjustable servo speed control
  - Real-time position feedback display

### Changed
- Improved widget drag functionality
  - Added dedicated drag handle to widget headers
  - Prevents accidental widget movement when interacting with controls
- Enhanced widget configuration UX
  - Added settings button to widget headers
  - Moved configuration options to modal dialogs
  - Settings can now be accessed in both edit and view modes
- Added updateWidgetProps method to GridContext for persisting widget configuration changes

### Fixed
- Fixed issue with grid editing mode where whole widget was draggable, preventing interaction with controls