.PHONY: tracks/build tracks/flash tracks/update

tracks/build:
	@echo "Building tracks firmware..."
	cd tracks/firmware && mkdir -p build && cd build && cmake .. && make

tracks/flash:
	@echo "Flashing tracks firmware..."
	python3 tracks/scripts/flash_firmware.py /dev/serial/by-id/usb-Raspberry_Pi_Pico_E6612483CB1A9621-if00

tracks/update: tracks/build tracks/flash
	@echo "Tracks firmware updated (build and flash complete)."
