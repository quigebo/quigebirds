#!/usr/bin/env bash
# Fetch Waveshare's 13.3" e-Paper HAT+ (E) driver into vendor/waveshare, where
# the frame looks for it (src/fugleramme/waveshare.py). Its presence is what
# switches the frame from probing for an Inky to driving the Waveshare panel;
# delete the folder to switch back. Also installs wiringPi, which the driver's
# DEV_Config .so links against, and restarts the frame if it is installed.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="$REPO_ROOT/vendor/waveshare"
BASE="https://raw.githubusercontent.com/waveshareteam/e-Paper/master/E-paper_Separate_Program/13.3inch_e-Paper_E/RaspberryPi/python/lib"

echo "==> waveshare driver -> $DEST"
mkdir -p "$DEST"
# _w is the wiringPi build epdconfig picks on a Pi 5, _b the bcm2835 one for older Pis.
for f in epd13in3E.py epdconfig.py DEV_Config_64_w.so DEV_Config_64_b.so; do
  curl -fsSL "$BASE/$f" -o "$DEST/$f"
done

echo "==> wiringPi"
if /sbin/ldconfig -p | grep -q libwiringPi.so; then
  echo "   already installed"
else
  url="$(curl -fsSL https://api.github.com/repos/WiringPi/WiringPi/releases/latest \
    | grep -o 'https://[^"]*arm64\.deb' | head -1)"
  tmp="$(mktemp --suffix=.deb)"
  curl -fsSL "$url" -o "$tmp"
  sudo apt-get install -y "$tmp"
  rm -f "$tmp"
fi

if systemctl list-unit-files fugleramme-frame.service >/dev/null 2>&1; then
  echo "==> restarting fugleramme-frame"
  sudo systemctl restart fugleramme-frame
fi
echo "==> done"
