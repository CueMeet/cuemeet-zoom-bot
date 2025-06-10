#!/bin/bash
set -e

# Start Xvfb
Xvfb :99 -screen 0 1920x1080x24 -ac +extension GLX +render -noreset &
export DISPLAY=:99

# Start PulseAudio server in the background
pulseaudio --start --log-target=syslog --system=false --disallow-exit

# Create a virtual audio sink
pacmd load-module module-null-sink sink_name=virtual-sink sink_properties=device.description="Virtual_Sink"

# Wait for services to initialize
sleep 2

# Execute the passed command
exec "$@"