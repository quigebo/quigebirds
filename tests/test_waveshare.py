"""Waveshare adapter invariants. The vendor driver is Pi-only, so a fake EPD
records what the adapter hands it: the controller's portrait buffer, packed two
pixels a byte in its own colour codes."""

from __future__ import annotations

import numpy
import pytest
from PIL import Image

from fugleramme import waveshare
from fugleramme.panel import Panel, init_panel
from fugleramme.render.dither import PALETTE_6, dither


class FakeEPD:
    def __init__(self):
        self.calls: list[str] = []
        self.buffer = None

    def Init(self):  # the vendor's name
        self.calls.append("Init")

    def display(self, buffer):
        self.calls.append("display")
        self.buffer = buffer

    def sleep(self):
        self.calls.append("sleep")


def _unpack(buffer: bytes) -> numpy.ndarray:
    packed = numpy.frombuffer(buffer, dtype=numpy.uint8).reshape(1600, 600)
    return numpy.stack([packed >> 4, packed & 0xF], axis=-1).reshape(1600, 1200)


def _solid(index: int) -> Image.Image:
    return dither(Image.new("RGB", (1600, 1200), PALETTE_6[index]))


def test_buffer_is_the_controllers_portrait_size():
    assert len(waveshare.pack(_solid(1))) == 1200 * 1600 // 2


@pytest.mark.parametrize("index,code", [(0, 0), (1, 1), (2, 2), (3, 3), (4, 5), (5, 6)])
def test_each_ink_maps_to_its_controller_code(index, code):
    assert set(numpy.unique(_unpack(waveshare.pack(_solid(index))))) == {code}


def test_landscape_turns_counter_clockwise_like_the_vendor_getbuffer():
    source = Image.new("RGB", (1600, 1200), PALETTE_6[1])
    source.putpixel((1599, 0), PALETTE_6[3])  # top-right -> top-left when rotated CCW
    assert _unpack(waveshare.pack(dither(source)))[0, 0] == 3


def test_full_colour_input_is_dithered_first():
    codes = _unpack(waveshare.pack(Image.new("RGB", (1600, 1200), (200, 30, 30))))
    assert set(numpy.unique(codes)) <= {0, 1, 2, 3, 5, 6}


def test_panel_push_wakes_draws_and_sleeps():
    epd = FakeEPD()
    panel = Panel(waveshare.Waveshare13in3E(epd))
    assert panel.resolution == (1600, 1200)
    panel.push(Image.new("RGB", (1200, 1600)), 90)
    assert epd.calls == ["Init", "display", "sleep"]
    assert len(epd.buffer) == 1200 * 1600 // 2


def test_wrong_size_never_reaches_the_glass():
    epd = FakeEPD()
    with pytest.raises(ValueError):
        waveshare.Waveshare13in3E(epd).set_image(Image.new("P", (800, 480)))
    assert epd.calls == []


def test_fetched_driver_is_chosen_over_inky(tmp_path, monkeypatch):
    (tmp_path / "epd13in3E.py").write_text("")
    monkeypatch.setenv("FUGLERAMME_WAVESHARE_LIB", str(tmp_path))
    monkeypatch.setattr(waveshare, "load", lambda: waveshare.Waveshare13in3E(FakeEPD()))
    panel = init_panel()
    assert panel is not None
    assert "waveshare" in panel.driver


def test_unloadable_driver_degrades_to_web_only(tmp_path, monkeypatch):
    (tmp_path / "epd13in3E.py").write_text("raise ImportError('no wiringPi')")
    monkeypatch.setenv("FUGLERAMME_WAVESHARE_LIB", str(tmp_path))
    assert init_panel() is None
