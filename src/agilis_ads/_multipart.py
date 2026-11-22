"""Builds ``multipart/form-data`` bodies the way the API expects them.

Array fields become repeated ``name[]`` parts, the crop becomes ``crop[x]``,
``crop[y]`` and ``crop[w]``, and the image is read once so that a retried
request sends exactly the same bytes.
"""

from __future__ import annotations

import mimetypes
import os
import uuid
from typing import Any, List, Mapping, Optional, Tuple, Union

__all__ = ["FilePart", "Part", "encode_multipart", "form_parts", "read_image"]

FilePart = Tuple[str, bytes, str]  # (file name, content, content type)
Part = Tuple[str, Union[str, FilePart]]

_CONTENT_TYPES = {
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".gif": "image/gif",
    ".webp": "image/webp",
    ".heic": "image/heic",
    ".heif": "image/heif",
    ".avif": "image/avif",
    ".bmp": "image/bmp",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
}

_FILE_FIELDS = frozenset({"image"})


def content_type_for(file_name: str, content: bytes = b"") -> str:
    """The content type for a file name, falling back to the file's first bytes."""
    ext = os.path.splitext(file_name)[1].lower()
    if ext in _CONTENT_TYPES:
        return _CONTENT_TYPES[ext]
    guessed = mimetypes.guess_type(file_name)[0] if ext else None
    if guessed:
        return guessed
    return _sniff(content) or "application/octet-stream"


def _sniff(content: bytes) -> Optional[str]:
    if content.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content[:6] in (b"GIF87a", b"GIF89a"):
        return "image/gif"
    if content[:4] == b"RIFF" and content[8:12] == b"WEBP":
        return "image/webp"
    return None


def _default_name(content_type: str) -> str:
    ext = {
        "image/png": ".png",
        "image/jpeg": ".jpg",
        "image/gif": ".gif",
        "image/webp": ".webp",
    }.get(content_type, "")
    return "image" + ext


def _read(source: Any) -> Tuple[Optional[str], bytes]:
    if isinstance(source, (bytes, bytearray, memoryview)):
        return None, bytes(source)
    if isinstance(source, (str, os.PathLike)):
        path = os.fspath(source)
        with open(path, "rb") as handle:
            return os.path.basename(path), handle.read()
    read = getattr(source, "read", None)
    if callable(read):
        data = read()
        if isinstance(data, str):
            raise TypeError("the image stream must be opened in binary mode ('rb')")
        name = getattr(source, "name", None)
        file_name = os.path.basename(name) if isinstance(name, str) and name else None
        return file_name, bytes(data)
    raise TypeError(
        "image must be a file path, bytes, a binary stream, or a (file_name, content) tuple"
    )


def read_image(value: Any) -> FilePart:
    """Normalise an image argument into ``(file name, bytes, content type)``."""
    if isinstance(value, tuple):
        if len(value) != 2 or not isinstance(value[0], str):
            raise TypeError("an image tuple must be (file_name, bytes_or_stream)")
        _, content = _read(value[1])
        file_name: Optional[str] = value[0]
    else:
        file_name, content = _read(value)
    if not file_name:
        content_type = _sniff(content) or "application/octet-stream"
        return _default_name(content_type), content, content_type
    return file_name, content, content_type_for(file_name, content)


def _scalar(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float, str)):
        return str(value)
    raise TypeError(f"unsupported form value of type {type(value).__name__}")


def form_parts(params: Mapping[str, Any]) -> List[Part]:
    """Turn a parameters mapping into an ordered list of form parts."""
    parts: List[Part] = []
    for name, value in params.items():
        if value is None:
            continue
        if name in _FILE_FIELDS:
            parts.append((name, read_image(value)))
        elif name == "crop" and isinstance(value, Mapping):
            for key in ("x", "y", "w", "h"):
                if value.get(key) is not None:
                    parts.append((f"crop[{key}]", _scalar(value[key])))
        elif isinstance(value, (list, tuple)):
            for item in value:
                parts.append((f"{name}[]", _scalar(item)))
        else:
            parts.append((name, _scalar(value)))
    return parts


def _quote(text: str) -> str:
    return text.replace('"', "%22").replace("\r", "%0D").replace("\n", "%0A")


def encode_multipart(parts: List[Part], boundary: Optional[str] = None) -> Tuple[bytes, str]:
    """Encode parts as ``multipart/form-data``. Returns ``(body, content_type)``."""
    boundary = boundary or f"agilis-{uuid.uuid4().hex}"
    chunks: List[bytes] = []
    for name, value in parts:
        chunks.append(f"--{boundary}\r\n".encode("ascii"))
        if isinstance(value, tuple):
            file_name, content, content_type = value
            chunks.append(
                (
                    f'Content-Disposition: form-data; name="{_quote(name)}"; '
                    f'filename="{_quote(file_name)}"\r\n'
                    f"Content-Type: {content_type}\r\n\r\n"
                ).encode()
            )
            chunks.append(content)
        else:
            chunks.append(f'Content-Disposition: form-data; name="{_quote(name)}"\r\n\r\n'.encode())
            chunks.append(value.encode("utf-8"))
        chunks.append(b"\r\n")
    chunks.append(f"--{boundary}--\r\n".encode("ascii"))
    return b"".join(chunks), f"multipart/form-data; boundary={boundary}"
