# Makefile to compile and flash wall-e_eye.ino to an ESP32S3 board using Arduino CLI

# Fully Qualified Board Name (FQBN) for your Seeed XIAO ESP32S3 board
FQBN = esp32:esp32:XIAO_ESP32S3

# Source Arduino sketch
SRC = wall-e_eye.ino

# Serial port for the USB attached ESP32S3 (adjust as needed)
PORT = /dev/cu.usbmodem3131201

# Default target: compile and flash the sketch
all: flash

# Build target: compile the sketch
build:
	@echo "Compiling $(SRC) for board $(FQBN)..."
	arduino-cli compile --fqbn $(FQBN) --libraries ./libraries $(SRC)

# Flash target: compile then upload the sketch to the board
flash: build
	@echo "Uploading $(SRC) to $(PORT)..."
	arduino-cli upload -p $(PORT) --fqbn $(FQBN) $(SRC)

# Clean build artifacts
clean:
	@echo "Cleaning build files..."
	rm -rf ./build

.PHONY: all build flash clean
