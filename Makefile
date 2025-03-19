.PHONY: tracks/build tracks/flash tracks/update

run:
	dora run dataflow.yml --uv

web/build:
	cd nodes/web/resources && ./node_modules/.bin/encore dev

web/build-watch:
	cd nodes/web/resources && ./node_modules/.bin/encore dev --watch

tracks/build:
	@echo "Building tracks firmware..."
	cd nodes/tracks/firmware && mkdir -p build && cd build && cmake .. && make

tracks/flash:
	@echo "Flashing tracks firmware..."
	python3 nodes/tracks/scripts/flash_firmware.py /dev/serial/by-id/usb-Raspberry_Pi_Pico_E6612483CB1A9621-if00

tracks/update: tracks/build tracks/flash
	@echo "Tracks firmware updated (build and flash complete)."
