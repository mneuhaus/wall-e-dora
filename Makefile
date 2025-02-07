.PHONY: tracks/build tracks/flash tracks/update

tracks/build:
	@echo "Building tracks firmware..."
	cd tracks/firmware && mkdir -p build && cd build && cmake .. && make

tracks/flash:
	@echo "Flashing tracks firmware..."
	picotool load tracks/firmware/build/tracks_firmware.uf2

tracks/update: tracks/build tracks/flash
	@echo "Tracks firmware updated (build and flash complete)."
