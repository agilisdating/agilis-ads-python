from __future__ import annotations

import struct
import zlib

from .images import EVENT_IMAGE_SIZE, gradient_png, png_size


def test_event_image_meets_the_minimum_size() -> None:
    data = gradient_png()
    width, height = png_size(data)
    assert (width, height) == EVENT_IMAGE_SIZE
    assert width >= 1280
    assert height >= 720
    assert len(data) < 5 * 1024 * 1024  # well under the upload limit


def test_generated_png_is_well_formed() -> None:
    data = gradient_png(4, 3)
    assert png_size(data) == (4, 3)
    offset = 8
    kinds = []
    while offset < len(data):
        (length,) = struct.unpack(">I", data[offset : offset + 4])
        kind = data[offset + 4 : offset + 8]
        body = data[offset + 8 : offset + 8 + length]
        (crc,) = struct.unpack(">I", data[offset + 8 + length : offset + 12 + length])
        assert crc == zlib.crc32(kind + body) & 0xFFFFFFFF
        kinds.append(kind)
        if kind == b"IDAT":
            assert len(zlib.decompress(body)) == 3 * (1 + 4 * 3)
        offset += 12 + length
    assert kinds == [b"IHDR", b"IDAT", b"IEND"]
