"""
حزمة الأدوات المساعدة لتطبيق فليكس داون (FlexDown Utilities)
"""

from flexdown.utils.config import Config, get_config
from flexdown.utils.file_utils import (
    sanitize_filename,
    format_size,
    format_speed,
    format_duration,
    ensure_unique_path,
    get_file_extension,
    get_free_disk_space,
    safe_delete_file,
)
from flexdown.utils.url_utils import (
    is_valid_url,
    normalize_url,
    detect_platform,
    get_platform_icon_name,
    is_playlist_url,
    is_direct_download,
)

__all__ = [
    "Config",
    "get_config",
    "sanitize_filename",
    "format_size",
    "format_speed",
    "format_duration",
    "ensure_unique_path",
    "get_file_extension",
    "get_free_disk_space",
    "safe_delete_file",
    "is_valid_url",
    "normalize_url",
    "detect_platform",
    "get_platform_icon_name",
    "is_playlist_url",
    "is_direct_download",
]
