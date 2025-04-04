# WALL-E Eye - Coding Guidelines

## Build/Run Commands
- Build: `arduino-cli compile --fqbn esp32:esp32:XIAO_ESP32S3 --libraries ./libraries wall-e_eye.ino`
- Flash: `arduino-cli upload -p /dev/cu.usbmodem31101 --fqbn esp32:esp32:XIAO_ESP32S3 wall-e_eye.ino`
- Image optimization: `python3 optimize_gif.py input_directory output_directory [--rotate degrees]`

## Code Style Guidelines
- Indentation: 2 spaces
- Line endings: LF (Unix-style)
- Variable naming: camelCase for variables, PascalCase for classes
- Format strings with proper type specifiers (e.g., %d for integers)
- Limit GIF playback to optimize performance (see constant declarations)
- Web responses should return meaningful status codes and messages
- Check SD card operations for success/failure
- Use consistent error handling and logging
- Support both animated GIFs and static JPG image formats

## Error Handling
- Check SD card operations for success
- Validate user input from web API
- Use proper HTTP status codes for error responses
- Limit file upload sizes appropriately (max 10MB)
- Implement timeout mechanisms for network operations
- Handle image format-specific errors separately for each format
- Call server.handleClient() during long operations to maintain responsiveness