import struct

import pytest

import size_analysis


def _sof(channels: bytes = b"") -> bytes:
    # SOI + SOF0 (uzunluk 17, 8 bit, 16x16) + kanal sayısı
    return b"\xff\xd8\xff\xc0\x00\x11\x08\x00\x10\x00\x10" + channels


def _png_ihdr(bit_depth: int, color_type: int = 2) -> bytes:
    body = struct.pack(">II", 16, 16) + bytes([bit_depth, color_type, 0, 0, 0])
    return b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + body + b"\x00" * 4


def test_jpeg_sof_truncated_before_channel_byte_raises_value_error():
    with pytest.raises(ValueError):
        size_analysis.read_jpeg_dimensions(_sof())


def test_jpeg_zero_channels_raises_value_error():
    with pytest.raises(ValueError):
        size_analysis.read_jpeg_dimensions(_sof(b"\x00"))


def test_jpeg_valid_sof_is_read():
    assert size_analysis.read_jpeg_dimensions(_sof(b"\x03")) == {"width": 16, "height": 16, "channels": 3}


@pytest.mark.parametrize("bit_depth", [0, 3, 32])
def test_png_invalid_bit_depth_raises_value_error(bit_depth):
    with pytest.raises(ValueError):
        size_analysis.read_png_dimensions(_png_ihdr(bit_depth))


def test_png_valid_header_is_read():
    dims = size_analysis.read_png_dimensions(_png_ihdr(8))
    assert dims == {"width": 16, "height": 16, "bit_depth": 8, "channels": 3}
