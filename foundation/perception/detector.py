"""Detect capability: identify file format and MIME type before parsing."""
from __future__ import annotations

import os
from typing import TypedDict

import magic

EXTENSION_FORMAT_MAP = {
    ".docx": "docx",
    ".xlsx": "xlsx",
    ".pdf": "pdf",
}

SUPPORTED_MIME_TYPES = {
    "docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",  # docx is a zip container; some libmagic builds report this
    },
    "xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/zip",
    },
    "pdf": {
        "application/pdf",
    },
}


class DetectedFormat(TypedDict):
    format: str
    mime: str
    size: int


def detect_format(path: str) -> DetectedFormat:
    if not os.path.isfile(path):
        raise ValueError(f"File not found: {path}")

    ext = os.path.splitext(path)[1].lower()
    fmt = EXTENSION_FORMAT_MAP.get(ext)
    if fmt is None:
        raise ValueError(
            f"Unsupported file extension '{ext}'. "
            f"Supported: {sorted(EXTENSION_FORMAT_MAP)}"
        )

    mime = magic.from_file(path, mime=True)
    if mime not in SUPPORTED_MIME_TYPES[fmt]:
        raise ValueError(
            f"File extension '{ext}' suggests format '{fmt}', but detected MIME "
            f"type '{mime}' does not match. File may be corrupted or mislabeled: {path}"
        )

    size = os.path.getsize(path)
    return {"format": fmt, "mime": mime, "size": size}
