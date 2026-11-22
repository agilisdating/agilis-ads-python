"""Test images generated in code, so no large binary files are committed."""

from __future__ import annotations

import struct
import zlib

EVENT_IMAGE_SIZE = (1280, 720)  # the smallest image an Event accepts


def _chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def gradient_png(width: int = EVENT_IMAGE_SIZE[0], height: int = EVENT_IMAGE_SIZE[1]) -> bytes:
    """An RGB PNG of the given size with a simple colour gradient."""
    rows = bytearray()
    for y in range(height):
        rows.append(0)  # no filter
        blue = 255 * y // max(1, height - 1)
        for x in range(width):
            rows += bytes((255 * x // max(1, width - 1), 120, blue))
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(bytes(rows), 9))
        + _chunk(b"IEND", b"")
    )


def png_size(data: bytes) -> tuple[int, int]:
    """The width and height in a PNG's header."""
    assert data.startswith(b"\x89PNG\r\n\x1a\n")
    width, height = struct.unpack(">II", data[16:24])
    return width, height
