#!/usr/bin/env bash
set -euo pipefail

RULES_PATH="/etc/udev/rules.d/51-kinect.rules"
FALLBACK_KNOWN=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --fallback-known) FALLBACK_KNOWN=true; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

if ! command -v lsusb >/dev/null 2>&1; then
  echo "lsusb is required to detect Kinect USB IDs." >&2
  exit 1
fi

declare -a product_ids=()
while IFS= read -r line; do
  if [[ "$line" =~ ID[[:space:]]045e:([0-9a-fA-F]{4}).*[Kk]inect ]]; then
    product_ids+=("${BASH_REMATCH[1],,}")
  fi
done < <(lsusb)

if [[ ${#product_ids[@]} -eq 0 ]]; then
  if $FALLBACK_KNOWN; then
    product_ids=("02ae" "02ad" "02b0" "02c2" "02be" "02bf")
    echo "No Kinect devices detected; using known Kinect v1 IDs." >&2
  else
    echo "No Kinect devices detected. Plug it in and rerun, or use --fallback-known." >&2
    exit 1
  fi
fi

{
  echo "# Kinect v1 udev rules (auto-generated)"
  for pid in "${product_ids[@]}"; do
    echo "SUBSYSTEM==\"usb\", ATTR{idVendor}==\"045e\", ATTR{idProduct}==\"$pid\", MODE=\"0666\", GROUP=\"plugdev\""
  done
} | sudo tee "$RULES_PATH" >/dev/null

sudo udevadm control --reload-rules
sudo udevadm trigger

echo "Installed $RULES_PATH"
echo "Unplug/replug the Kinect (or reboot) to apply permissions."
