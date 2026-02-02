#!/usr/bin/env bash
set -euo pipefail

RULES_PATH="/etc/udev/rules.d/51-kinect.rules"

cat <<'EOF' | sudo tee "$RULES_PATH" >/dev/null
# Kinect for Xbox 360 (Kinect v1) udev rules
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02ae", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02ad", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTR{idVendor}=="045e", ATTR{idProduct}=="02b0", MODE="0666", GROUP="plugdev"
EOF

sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Installed $RULES_PATH"
echo "Unplug/replug the Kinect (or reboot) to apply permissions."
