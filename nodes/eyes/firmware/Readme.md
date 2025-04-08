# Wall-E Eyes Firmware

## Description
The Wall-E Eyes firmware is an Arduino sketch that displays and controls animated GIFs and JPEG images on a 240×240 TFT display. It provides a comprehensive web API for remote control, allowing users to upload images, change display settings, and trigger various eye animations. Designed specifically for the Wall-E robot project, it enables expressive eye animations that bring character and personality to the robot.

## Features
- Plays animated GIFs and displays JPEG images on a 240×240 TFT display
- Web interface and API for remote control and file management
- Supports various eye animations (open, close, blink, colorful)
- SD card storage for image files
- WiFi connectivity for remote access
- Rotation control for display orientation
- Image upload and management via web interface
- Optimized GIF playback for smooth animations
- Python tools for GIF optimization and conversion

## Files

- wall-e_eye.ino: Main Arduino sketch for the eyes firmware
- optimize_gif.py: Python script for optimizing GIFs
- png_to_gif.py: Python script for converting PNG files to GIFs
- sync_images.py: Script for syncing images to the SD card
- CONVENTIONS.md: Coding conventions
- Readme.md: This file

## Web API Documentation

The firmware provides a comprehensive web API for controlling the display:

| Endpoint | Method | Description | Parameters |
|----------|--------|-------------|------------|
| `/` | GET | Web interface for eye control | None |
| `/gifs` | GET | Returns a JSON array of all GIF files | None |
| `/playgif` | GET | Displays a specific GIF or JPEG | `name`: Filename to display |
| `/open` | GET | Animates the eye opening | None |
| `/close` | GET | Animates the eye closing | None |
| `/blink` | GET | Animates the eye blinking | None |
| `/colorful` | GET | Displays a colorful animation | None |
| `/upload` | POST | Uploads a new image file | Form data with `file` field |
| `/delete` | GET | Deletes a file | `name`: Filename to delete |
| `/rotate` | GET | Rotates the display | `value`: Rotation value (0-3) |

### Example Usage:

```
# Display a specific GIF
GET http://<esp32-ip>/playgif?name=emotion-love.gif

# Trigger a blink animation
GET http://<esp32-ip>/blink

# Rotate the display 90 degrees
GET http://<esp32-ip>/rotate?value=1
```

## Installation & Flashing

1. Install the Arduino IDE (or PlatformIO) and configure it for your ESP32 board.
2. Install the required libraries (TFT_eSPI, AnimatedGIF, SPI, SD, WiFi, WebServer, Preferences, JPEGDecoder).
3. Connect your board via USB and select the proper COM port and board type in the IDE.
4. Open wall-e_eye.ino, compile, and flash the firmware.
5. On startup, the device initializes the SD card and WiFi. Monitor Serial output to confirm successful connection.
6. Once running, access the web interface by navigating to the device's IP address in your browser.

## GIF Optimization Tool

The provided optimize_gif.py script optimizes GIF files (or converts MP4s) for the device.

### Requirements
- Python 3 with the Pillow package (install via 'pip3 install Pillow')
- gifsicle, ffmpeg, and ImageMagick must be installed and available in your system PATH.

### Installation for the CLI Tool
For instance, on Ubuntu/Debian you can install the dependencies with:
  ```
  sudo apt-get install gifsicle ffmpeg imagemagick
  ```
Then install Pillow:
  ```
  pip3 install Pillow
  ```

### Usage Examples
- Basic GIF Optimization:
  ```
  python3 optimize_gif.py path/to/input_gifs path/to/output_gifs
  ```
- Optimize with additional rotation (e.g., 90°):
  ```
  python3 optimize_gif.py path/to/input_gifs path/to/output_gifs --rotate 90
  ```
- Advanced example (converting MP4s, optimizing, and rotating 180°):
  ```
  python3 optimize_gif.py ./originals ./optimized --rotate 180
  ```

The script processes files with .gif and .mp4 extensions in the specified input directory, generating:
  - Files with the '_o' suffix: optimized for playback.
  - Files with the '_preview' suffix: a preview image from the first GIF frame.
  - If rotation is specified, additional rotated files ('_left+<angle>' and '_right-<angle>') are also created.