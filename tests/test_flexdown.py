# tests/test_flexdown.py
"""Basic unit tests for FlexDown utility modules.
These tests cover URL validation, platform detection, and file‑utility helpers.
Run with: `pytest -q` from the project root.
"""

from pathlib import Path

from flexdown.utils.file_utils import (
    sanitize_filename,
    format_size,
    format_speed,
    format_duration,
    ensure_unique_path,
    get_file_extension,
)
from flexdown.utils.url_utils import (
    is_valid_url,
    detect_platform,
    get_platform_icon_name,
    is_playlist_url,
    is_direct_download,
    normalize_url,
)
from flexdown.core.turbo_downloader import (
    detect_file_category,
    parse_size_to_bytes,
    compute_file_sha256,
    get_aria2_path,
)

# ---------- file_utils ----------


def test_sanitize_filename():
    dirty = "my*illegal|name?.mp4"
    clean = sanitize_filename(dirty)
    assert "*" not in clean and "|" not in clean and "?" not in clean
    assert clean == "myillegalname.mp4"


def test_format_size():
    assert format_size(0) == "0 B"
    assert format_size(1024) == "1.0 KiB"
    assert format_size(10 * 1024**2) == "10.0 MiB"


def test_format_speed():
    assert format_speed(0) == "0 B/s"
    assert format_speed(1024) == "1.0 KiB/s"
    assert format_speed(5 * 1024**2) == "5.0 MiB/s"


def test_format_duration():
    assert format_duration(0) == "0s"
    assert format_duration(65) == "1m 5s"
    assert format_duration(3665) == "1h 1m 5s"


def test_ensure_unique_path(tmp_path: Path):
    p1 = tmp_path / "file.txt"
    p1.write_text("a")
    p2 = ensure_unique_path(p1)
    assert p2 != p1
    assert not p2.exists()


def test_get_file_extension():
    assert get_file_extension("http://example.com/video.mp4") == "mp4"
    assert get_file_extension("https://site.org/archive.tar.gz") == "gz"
    assert get_file_extension("noextension") == ""

# ---------- url_utils ----------


def test_is_valid_url():
    assert is_valid_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
    assert not is_valid_url("not a url")


def test_detect_platform():
    assert detect_platform("https://www.youtube.com/watch?v=abc") == "youtube"
    assert detect_platform("https://vimeo.com/12345") == "vimeo"
    assert detect_platform("https://unknown.example.com") == "generic"


def test_get_platform_icon_name():
    assert get_platform_icon_name("youtube") == "youtube"
    assert get_platform_icon_name("tiktok") == "tiktok"
    assert get_platform_icon_name("unknown") == "generic"


def test_is_playlist_url():
    assert is_playlist_url("https://www.youtube.com/playlist?list=PL123")
    assert not is_playlist_url("https://youtu.be/dQw4w9WgXcQ")


def test_is_direct_download():
    assert is_direct_download("https://example.com/file.pdf")
    assert not is_direct_download("https://youtube.com/watch?v=abc")


def test_normalize_url_and_playlist_repair():
    assert normalize_url("=PL-bW-IO3g5rpADllPzXQTKGlTKewSNUi8") == (
        "https://www.youtube.com/playlist?list=PL-bW-IO3g5rpADllPzXQTKGlTKewSNUi8"
    )
    assert normalize_url("list=PL123") == "https://www.youtube.com/playlist?list=PL123"
    assert is_valid_url("=PL-bW-IO3g5rpADllPzXQTKGlTKewSNUi8")
    assert is_playlist_url("=PL-bW-IO3g5rpADllPzXQTKGlTKewSNUi8")
    assert is_playlist_url("https://www.youtube.com/playlist?list=PLQpQQFZKzl7o")


# ---------- turbo_downloader ----------


def test_detect_file_category():
    assert detect_file_category("setup.exe") == "PROGRAM"
    assert detect_file_category("archive.zip") == "ARCHIVE"
    assert detect_file_category("ubuntu.iso") == "ARCHIVE"
    assert detect_file_category("document.pdf") == "DOCUMENT"
    assert detect_file_category("movie.mp4") == "VIDEO"
    assert detect_file_category("song.mp3") == "AUDIO"


def test_parse_size_to_bytes():
    assert parse_size_to_bytes("10MiB") == 10 * 1024 * 1024
    assert parse_size_to_bytes("1GiB") == 1024 * 1024 * 1024
    assert parse_size_to_bytes("500B") == 500


def test_compute_file_sha256(tmp_path: Path):
    test_file = tmp_path / "sample.bin"
    test_file.write_bytes(b"FlexDownTurboSpeed")
    sha = compute_file_sha256(str(test_file))
    assert len(sha) == 64
    import hashlib
    expected = hashlib.sha256(b"FlexDownTurboSpeed").hexdigest()
    assert sha == expected


def test_get_aria2_path():
    aria_path = get_aria2_path()
    assert aria_path is not None
    assert Path(aria_path).exists()
