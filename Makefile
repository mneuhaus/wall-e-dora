.PHONY: tracks/build tracks/flash tracks/update service/install service/uninstall

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

service/install:
	@echo "Creating systemd service to start wall-e-dora on boot..."
	@echo "[Unit]\nDescription=WALL-E-DORA Robot Control System\nAfter=network.target\n\n[Service]\nType=simple\nUser=$(shell whoami)\nWorkingDirectory=$(shell pwd)\nExecStart=$(shell pwd)/service_runner.sh\nRestart=on-failure\nStandardOutput=journal\nStandardError=journal\nEnvironment=\"PATH=/home/$(shell whoami)/.dora/bin:$(PATH)\"\n\n[Install]\nWantedBy=multi-user.target" > wall-e-dora.service
	@echo "#!/bin/bash\ncd $(shell pwd) && /home/$(shell whoami)/.dora/bin/dora run dataflow.yml --uv" > service_runner.sh
	@chmod +x service_runner.sh
	@sudo mv wall-e-dora.service /etc/systemd/system/
	@sudo systemctl daemon-reload
	@sudo systemctl enable wall-e-dora.service
	@echo "Service installed. Start with: sudo systemctl start wall-e-dora"
	@echo "View logs with: sudo journalctl -u wall-e-dora.service -f"

service/uninstall:
	@echo "Removing wall-e-dora systemd service..."
	@sudo systemctl disable wall-e-dora.service || true
	@sudo rm -f /etc/systemd/system/wall-e-dora.service
	@rm -f service_runner.sh
	@sudo systemctl daemon-reload
	@echo "Service removed."

service/logs:
	@sudo journalctl -u wall-e-dora.service -f
