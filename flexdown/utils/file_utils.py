# -*- coding: utf-8 -*-
"""
Utility functions for handling filenames, sizes, speeds, durations, and paths.
All functions are pure Python and have no external dependencies.
"""

import os
import re
import shutil
import urllib.parse
from pathlib import Path
from typing import Union

# Invalid filename characters (covers Windows and POSIX restrictions)
INVALID_FILENAME_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')

# Windows reserved device names
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    "COM1", "COM2", "COM3", "COM4", "COM5", "COM6", "COM7", "COM8", "COM9",
    "LPT1", "LPT2", "LPT3", "LPT4", "LPT5", "LPT6", "LPT7", "LPT8", "LPT9",
}


def sanitize_filename(name: str, max_length: int = 240, replacement: str = "_") -> str:
    """Return a safe filename while preserving Unicode (e.g. Arabic, French),
    spaces, dashes, brackets, and alphanumeric characters.

    The function:
    * Decodes any URL‑encoding.
    * Strips directory components.
    * Removes invalid filesystem characters (< > : " / \\ | ? * and control chars).
    * Replaces Windows reserved device names with a ``file_`` prefix.
    * Preserves the original extension (lower‑cased).
    * Truncates the result to ``max_length`` while keeping the extension.
    """
    if not isinstance(name, str) or not name.strip():
        return "downloaded_file"

    # Decode URL encoding and normalise path separators
    name = urllib.parse.unquote(name.strip())
    name = os.path.basename(name.replace("\\", "/"))

    stem, ext = os.path.splitext(name)
    # Remove filesystem-illegal characters only
    cleaned = INVALID_FILENAME_CHARS.sub("", stem)
    # Strip forbidden trailing characters in Windows (spaces and dots)
    cleaned = cleaned.strip(". ")
    if not cleaned:
        cleaned = "downloaded_file"

    if cleaned.upper() in WINDOWS_RESERVED_NAMES:
        cleaned = f"file_{cleaned}"

    cleaned_name = f"{cleaned}{ext.lower()}"
    if len(cleaned_name) > max_length:
        keep_len = max(10, max_length - len(ext))
        cleaned_name = f"{cleaned[:keep_len].rstrip('. ')}{ext.lower()}"
    return cleaned_name


def format_size(bytes_val: Union[int, float, None]) -> str:
    """Convert a size in bytes to a human‑readable IEC string.

    Returns values like ``1.0 KiB``, ``12.3 MiB`` etc.  Bytes are shown as an integer.
    """
    if bytes_val is None or bytes_val < 0:
        return "0 B"
    if bytes_val == 0:
        return "0 B"

    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    size = float(bytes_val)
    unit_index = 0
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1

    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    return f"{size:.1f} {units[unit_index]}"


def format_speed(bytes_per_sec: Union[int, float, None]) -> str:
    """Human‑readable speed string (e.g. ``1.2 MiB/s``)."""
    if bytes_per_sec is None or bytes_per_sec <= 0:
        return "0 B/s"
    return f"{format_size(bytes_per_sec)}/s"


def format_duration(seconds: Union[int, float, None]) -> str:
    """Return a friendly duration string.

    * ``0s`` for zero or missing values.
    * ``<m>m <s>s`` for durations under one hour.
    * ``<h>h <m>m <s>s`` for one hour or more.
    """
    if seconds is None or seconds < 0:
        return "0s"
    total = int(seconds)
    if total == 0:
        return "0s"
    h, remainder = divmod(total, 3600)
    m, s = divmod(remainder, 60)
    parts = []
    if h:
        parts.append(f"{h}h")
    if m:
        parts.append(f"{m}m")
    if s or not parts:
        parts.append(f"{s}s")
    return " ".join(parts)


def ensure_unique_path(path: Union[str, Path]) -> Path:
    """Return a unique, non‑existing file path.

    If ``path`` already exists, ``(1)``, ``(2)`` … is appended before the suffix.
    """
    target = Path(path).resolve()
    if not target.exists():
        return target
    directory = target.parent
    stem = target.stem
    suffix = target.suffix
    counter = 1
    while True:
        candidate = directory / f"{stem} ({counter}){suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def get_file_extension(url: str) -> str:
    """Extract a clean, lower‑case file extension from a URL or path.

    Returns an empty string when no extension is found.
    """
    if not url or not isinstance(url, str):
        return ""
    try:
        parsed = urllib.parse.urlparse(url)
        path = parsed.path or url
        filename = os.path.basename(path)
        filename = urllib.parse.unquote(filename)
        ext = os.path.splitext(filename)[1]
        if ext.startswith('.'):
            ext = ext[1:]
        ext = re.sub(r'[^a-zA-Z0-9]', '', ext)
        return ext.lower()
    except Exception:
        return ""


def get_free_disk_space(dir_path: Union[str, Path]) -> int:
    """Return free bytes for the filesystem containing ``dir_path``."""
    try:
        target = Path(dir_path)
        while not target.exists() and target.parent != target:
            target = target.parent
        return shutil.disk_usage(str(target)).free
    except Exception:
        return 0


def safe_delete_file(path: Union[str, Path]) -> bool:
    """Delete a file if it exists; return ``True`` on success or if it was already missing."""
    try:
        target = Path(path)
        if target.is_file() or target.is_symlink():
            target.unlink(missing_ok=True)
        return True
    except Exception:
        return False
