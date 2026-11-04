"""
ثوابت تطبيق فليكس داون (FlexDown Constants)
يحتوي هذا الملف على جميع الثوابت الأساسية للتطبيق:
- معلومات التطبيق والإصدار
- المسارات الافتراضية
- صيغ الوسائط المدعومة
- إعدادات جودة الفيديو والصوت
- أسماء المنصات والشبكات المدعومة
- الإعدادات الافتراضية للشبكة والتنزيل
"""

from pathlib import Path
from typing import Final, List, Dict, Optional

# ==========================================
# معلومات التطبيق الأساسية (App Metadata)
# ==========================================
APP_NAME: Final[str] = "FlexDown"
APP_NAME_AR: Final[str] = "فليكس داون"
VERSION: Final[str] = "1.0.0"
APP_ID: Final[str] = "com.flexdown.desktop.manager"
ORGANIZATION_NAME: Final[str] = "FlexDown"
APP_DESCRIPTION: Final[str] = "مدير تنزيل متطور متعدد الخيوط مع دعم المنصات والتشفير"

# ==========================================
# المسارات الافتراضية (Default Paths)
# ==========================================
# مجلد حفظ التنزيلات الافتراضي: ~/Downloads/FlexDown
DEFAULT_DOWNLOAD_DIR: Final[Path] = Path.home() / "Downloads" / "FlexDown"

# مجلد إعدادات وبيانات التطبيق: ~/.flexdown
CONFIG_DIR: Final[Path] = Path.home() / ".flexdown"

# ملف الإعدادات
CONFIG_FILE: Final[Path] = CONFIG_DIR / "config.json"

# ملف سجل التنزيلات
HISTORY_FILE: Final[Path] = CONFIG_DIR / "history.json"

# امتداد الملفات المشفرة بواسطة فليكس داون
ENCRYPTED_FILE_EXTENSION: Final[str] = ".fldx"

# ==========================================
# صيغ الملفات المدعومة (Supported Formats)
# ==========================================
SUPPORTED_VIDEO_FORMATS: Final[List[str]] = [
    "mp4", "mkv", "webm", "avi", "mov", "flv", "ts", "m4v", "wmv", "3gp"
]

SUPPORTED_AUDIO_FORMATS: Final[List[str]] = [
    "mp3", "m4a", "aac", "wav", "flac", "opus", "ogg", "wma", "aiff"
]

SUPPORTED_IMAGE_FORMATS: Final[List[str]] = [
    "jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "tiff", "ico", "heic"
]

SUPPORTED_DOCUMENT_FORMATS: Final[List[str]] = [
    "pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "rtf", "odt", "csv", "epub"
]

SUPPORTED_ARCHIVE_FORMATS: Final[List[str]] = [
    "zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso", "dmg", "pkg", "exe",
    "msi", "apk", "bin", "dat", "img", "deb", "rpm", "jar"
]

# جميع الصيغ المباشرة الشائعة للتحقق السريع
DIRECT_DOWNLOAD_EXTENSIONS: Final[set] = set(
    SUPPORTED_VIDEO_FORMATS +
    SUPPORTED_AUDIO_FORMATS +
    SUPPORTED_IMAGE_FORMATS +
    SUPPORTED_DOCUMENT_FORMATS +
    SUPPORTED_ARCHIVE_FORMATS
)

# ==========================================
# خيارات الجودة (Quality Presets)
# ==========================================
# جودات الفيديو المدعومة
QUALITY_BEST: Final[str] = "best"
QUALITY_2160P: Final[str] = "2160p"  # 4K
QUALITY_1440P: Final[str] = "1440p"  # 2K
QUALITY_1080P: Final[str] = "1080p"  # FHD
QUALITY_720P: Final[str] = "720p"    # HD
QUALITY_480P: Final[str] = "480p"    # SD
QUALITY_360P: Final[str] = "360p"
QUALITY_240P: Final[str] = "240p"
QUALITY_WORST: Final[str] = "worst"

VIDEO_QUALITIES: Final[List[dict]] = [
    {"id": QUALITY_BEST, "label_en": "Best Available", "label_ar": "أفضل جودة متاحة"},
    {"id": QUALITY_2160P, "label_en": "4K (2160p)", "label_ar": "فائقة الدقة 4K (2160p)"},
    {"id": QUALITY_1440P, "label_en": "2K (1440p)", "label_ar": "عالية جداً 2K (1440p)"},
    {"id": QUALITY_1080P, "label_en": "Full HD (1080p)", "label_ar": "عالية الدقة (1080p)"},
    {"id": QUALITY_720P, "label_en": "HD (720p)", "label_ar": "دقة متوسطة (720p)"},
    {"id": QUALITY_480P, "label_en": "SD (480p)", "label_ar": "دقة قياسية (480p)"},
    {"id": QUALITY_360P, "label_en": "Low (360p)", "label_ar": "منخفضة (360p)"},
]

# جودات الصوت المدعومة
QUALITY_AUDIO_BEST: Final[str] = "bestaudio"
QUALITY_AUDIO_320K: Final[str] = "320k"
QUALITY_AUDIO_256K: Final[str] = "256k"
QUALITY_AUDIO_192K: Final[str] = "192k"
QUALITY_AUDIO_128K: Final[str] = "128k"
QUALITY_AUDIO_64K: Final[str] = "64k"

AUDIO_QUALITIES: Final[List[dict]] = [
    {"id": QUALITY_AUDIO_BEST, "label_en": "Best Audio", "label_ar": "أفضل جودة صوت"},
    {"id": QUALITY_AUDIO_320K, "label_en": "320 kbps (High)", "label_ar": "320 كيلوبت/ث (عالية)"},
    {"id": QUALITY_AUDIO_256K, "label_en": "256 kbps", "label_ar": "256 كيلوبت/ث"},
    {"id": QUALITY_AUDIO_192K, "label_en": "192 kbps (Standard)", "label_ar": "192 كيلوبت/ث (قياسية)"},
    {"id": QUALITY_AUDIO_128K, "label_en": "128 kbps (Good)", "label_ar": "128 كيلوبت/ث (جيدة)"},
    {"id": QUALITY_AUDIO_64K, "label_en": "64 kbps (Low)", "label_ar": "64 كيلوبت/ث (منخفضة)"},
]

# ==========================================
# منصات الوسائط المدعومة (Supported Platforms)
# ==========================================
PLATFORM_YOUTUBE: Final[str] = "youtube"
PLATFORM_FACEBOOK: Final[str] = "facebook"
PLATFORM_INSTAGRAM: Final[str] = "instagram"
PLATFORM_TIKTOK: Final[str] = "tiktok"
PLATFORM_TWITTER: Final[str] = "twitter"
PLATFORM_SOUNDCLOUD: Final[str] = "soundcloud"
PLATFORM_VIMEO: Final[str] = "vimeo"
PLATFORM_GENERIC: Final[str] = "generic"

PLATFORM_NAMES: Final[Dict[str, Dict[str, str]]] = {
    PLATFORM_YOUTUBE: {"en": "YouTube", "ar": "يوتيوب"},
    PLATFORM_FACEBOOK: {"en": "Facebook", "ar": "فيسبوك"},
    PLATFORM_INSTAGRAM: {"en": "Instagram", "ar": "إنستغرام"},
    PLATFORM_TIKTOK: {"en": "TikTok", "ar": "تيك توك"},
    PLATFORM_TWITTER: {"en": "Twitter / X", "ar": "تويتر / إكس"},
    PLATFORM_SOUNDCLOUD: {"en": "SoundCloud", "ar": "ساوند كلاود"},
    PLATFORM_VIMEO: {"en": "Vimeo", "ar": "فيميو"},
    PLATFORM_GENERIC: {"en": "Direct / Web", "ar": "مباشر / ويب"},
}

PLATFORM_ICONS: Final[Dict[str, str]] = {
    PLATFORM_YOUTUBE: "youtube.svg",
    PLATFORM_FACEBOOK: "facebook.svg",
    PLATFORM_INSTAGRAM: "instagram.svg",
    PLATFORM_TIKTOK: "tiktok.svg",
    PLATFORM_TWITTER: "twitter.svg",
    PLATFORM_SOUNDCLOUD: "soundcloud.svg",
    PLATFORM_VIMEO: "vimeo.svg",
    PLATFORM_GENERIC: "generic.svg",
}

# ==========================================
# الإعدادات الافتراضية (Default Settings)
# ==========================================
DEFAULT_LANGUAGE: Final[str] = "en"
DEFAULT_DARK_MODE: Final[bool] = True
DEFAULT_MAX_CONCURRENT: Final[int] = 3
DEFAULT_AUTO_RESUME: Final[bool] = True
DEFAULT_SHOW_NOTIFICATIONS: Final[bool] = False
DEFAULT_MINIMIZE_TO_TRAY: Final[bool] = True

DEFAULT_PROXY: Final[Optional[str]] = None
DEFAULT_ENCRYPT_BY_DEFAULT: Final[bool] = False
DEFAULT_NO_HISTORY: Final[bool] = False
DEFAULT_MAX_RETRIES: Final[int] = 10
DEFAULT_SPEED_LIMIT: Final[int] = 0  # 0 يعني بلا حدود (bytes/s)

# ==========================================
# إعدادات الشبكة والتنزيل المتقدمة (Network Defaults)
# ==========================================
DEFAULT_CHUNK_SIZE: Final[int] = 1024 * 1024  # 1 ميجابايت للقطعة
DEFAULT_BUFFER_SIZE: Final[int] = 64 * 1024   # 64 كيلوبايت للتدفق
DEFAULT_TIMEOUT_SECONDS: Final[int] = 30
DEFAULT_USER_AGENT: Final[str] = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36 FlexDown/1.0.0"
)
