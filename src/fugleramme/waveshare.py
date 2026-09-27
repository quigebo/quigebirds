"""Waveshare 13.3" e-Paper HAT+ (E), shaped like an Inky.

Same Spectra 6 glass as the Impression 13.3", but Waveshare drives it with its
own vendor code (epd13in3E.py plus a DEV_Config .so over wiringPi) rather than
anything pip-installable, and the HAT has no EEPROM for inky.auto() to find.
This wraps that driver in the two calls Panel makes - set_image and show - and
a landscape `resolution`, so the rest of the frame can't tell the boards apart.

The vendor files are fetched onto the Pi by vendor/fetch-waveshare.sh, and
their presence is the opt-in: the driver can't probe for the panel, and with
nothing wired up it would wait on BUSY forever.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import numpy
from PIL import Image

from .render.dither import PALETTE_6, dither

DEFAULT_LIB = Path(__file__).resolve().parents[2] / "vendor" / "waveshare"

# Our dither's indices (inky's order: black, white, yellow, red, blue, green) to
# the controller's colour codes, which skip 4. Anything past 5 is palette padding,
# which dither.py fills with black.
_CODES = numpy.zeros(256, dtype=numpy.uint8)
_CODES[: len(PALETTE_6)] = [0x0, 0x1, 0x2, 0x3, 0x5, 0x6]


def lib_dir() -> Path:
    return Path(os.environ.get("FUGLERAMME_WAVESHARE_LIB", DEFAULT_LIB))


def available() -> bool:
    return (lib_dir() / "epd13in3E.py").exists()


def pack(image: Image.Image) -> bytes:
    """A landscape frame -> the controller's portrait, two-pixels-a-byte buffer."""
    if image.mode != "P" or image.palette is None or len(image.palette.colors) != len(PALETTE_6):
        image = dither(image)
    # The glass is portrait-native; turn it the way the vendor's getbuffer does.
    codes = _CODES[numpy.asarray(image.transpose(Image.Transpose.ROTATE_90))]
    return ((codes[:, 0::2] << 4) | codes[:, 1::2]).tobytes()


class Waveshare13in3E:
    resolution = (1600, 1200)

    def __init__(self, epd):
        self._epd = epd
        self._buffer: bytes | None = None

    def set_image(self, image: Image.Image) -> None:
        if image.size != self.resolution:
            raise ValueError(f"image is {image.size}, panel is {self.resolution}")
        self._buffer = pack(image)

    def show(self) -> None:
        if self._buffer is None:
            return
        # Woken per refresh and slept after, as the vendor demo does: the panel
        # sits idle for minutes between pushes and holds its image unpowered.
        self._epd.Init()
        self._epd.display(self._buffer)
        self._epd.sleep()


def load() -> Waveshare13in3E:
    """Import the vendor driver from lib_dir(). Raises if it can't be loaded."""
    sys.path.insert(0, str(lib_dir()))
    import epd13in3E  # type: ignore[import-not-found]
    import epdconfig  # type: ignore[import-not-found]

    # epdconfig builds, but never raises, its "Cannot find DEV_Config.so".
    if epdconfig.spi is None:
        raise RuntimeError(f"no DEV_Config .so in {lib_dir()}")
    return Waveshare13in3E(epd13in3E.EPD())
