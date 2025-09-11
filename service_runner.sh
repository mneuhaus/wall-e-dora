#!/bin/bash
set -e

cd /home/mneuhaus/wall-e-dora

# Function to handle shutdown signals
shutdown() {
    echo "Shutting down wall-e-dora services..."
    if [[ -n $DORA_PID ]]; then
        echo "Stopping dora process (PID: $DORA_PID)"
        kill -TERM $DORA_PID 2>/dev/null || true
        wait $DORA_PID 2>/dev/null || true
    fi
    exit 0
}

# Trap shutdown signals
trap shutdown SIGTERM SIGINT

echo "Starting wall-e-dora services..."

# Start dora dataflow (includes web server node)
echo "Starting dora dataflow with web server..."
/home/mneuhaus/.dora/bin/dora run dataflow.yml --uv &
DORA_PID=$!

echo "Services started - dora PID: $DORA_PID (includes web server on port 8443)"

# Wait for process to exit
wait
