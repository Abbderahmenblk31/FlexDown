"""
أدوات معالجة والتحقق من الروابط (URL Utilities)
يوفر هذا الملف دوالاً للتحقق من صحة الروابط، وتحديد منصة الوسائط (يوتيوب، فيسبوك، إلخ)،
وكشف قوائم التشغيل، والتحقق مما إذا كان الرابط مباشراً لملف.
"""

import re
import urllib.parse


from flexdown.constants import (
    PLATFORM_YOUTUBE,
    PLATFORM_FACEBOOK,
    PLATFORM_INSTAGRAM,
    PLATFORM_TIKTOK,
    PLATFORM_TWITTER,
    PLATFORM_SOUNDCLOUD,
    PLATFORM_VIMEO,
    PLATFORM_GENERIC,
    PLATFORM_ICONS,
    DIRECT_DOWNLOAD_EXTENSIONS,
)
from flexdown.utils.file_utils import get_file_extension

# التعبيرات النمطية للتعرف على المنصات
_PLATFORM_PATTERNS = [
    (PLATFORM_YOUTUBE, re.compile(r'(https?://)?(www\.|m\.)?(youtube\.com|youtu\.be)/', re.IGNORECASE)),
    (PLATFORM_FACEBOOK, re.compile(r'(https?://)?(www\.|m\.|web\.)?(facebook\.com|fb\.watch|fb\.com)/', re.IGNORECASE)),
    (PLATFORM_INSTAGRAM, re.compile(r'(https?://)?(www\.)?instagram\.com/', re.IGNORECASE)),
    (PLATFORM_TIKTOK, re.compile(r'(https?://)?(www\.|vm\.|vt\.)?tiktok\.com/', re.IGNORECASE)),
    (PLATFORM_TWITTER, re.compile(r'(https?://)?(www\.)?(twitter\.com|x\.com)/', re.IGNORECASE)),
    (PLATFORM_SOUNDCLOUD, re.compile(r'(https?://)?(www\.|m\.)?soundcloud\.com/', re.IGNORECASE)),
    (PLATFORM_VIMEO, re.compile(r'(https?://)?(www\.|player\.)?vimeo\.com/', re.IGNORECASE)),
]

# نمط التحقق العام من صحة الرابط
_URL_REGEX = re.compile(
    r'^(https?|ftp)://'  # http://, https://, ftp://
    r'([a-zA-Z0-9\-_]+(\.[a-zA-Z0-9\-_]+)+|localhost|(\d{1,3}\.){3}\d{1,3})'  # domain or ip
    r'(:\d+)?'  # port
    r'(/.*)?$',  # path
    re.IGNORECASE
)


def normalize_url(url: str) -> str:
    """
    تنظيف الرابط وإصلاح البادئات المشوهة أو المبتورة وإضافة بروتوكول https:// إن كان مفقوداً.
    Normalize URL by trimming, repairing truncated playlist/video prefixes, and adding https://.

    :param url: الرابط الأولي
    :return: الرابط بصيغته القياسية
    """
    if not url or not isinstance(url, str):
        return ""

    cleaned = url.strip()
    if not cleaned:
        return ""

    # إزالة أي علامات زائدة أو مبتورة في البداية مثل = أو ? أو & أو مسافات
    cleaned = re.sub(r'^[=?&\s]+', '', cleaned)

    # إصلاح روابط قوائم التشغيل المبتورة (مثل list=PL... أو playlist?list=PL...)
    if cleaned.startswith(('list=', 'playlist?list=')):
        if not cleaned.startswith('playlist?'):
            cleaned = f"playlist?{cleaned}"
        return f"https://www.youtube.com/{cleaned}"

    # إذا كان الرابط معرف قائمة تشغيل يوتيوب مباشر (PL, UU, LL, FL, RD, OLAK5uy_ ...)
    if re.match(r'^(PL|UU|LL|FL|RD|OLAK5uy_)[a-zA-Z0-9_\-]+$', cleaned):
        return f"https://www.youtube.com/playlist?list={cleaned}"

    # إذا كان الرابط معرف فيديو يوتيوب مبتور (watch?v=...)
    if cleaned.startswith('watch?v='):
        return f"https://www.youtube.com/{cleaned}"

    # إذا كان الرابط يبدأ بـ youtube.com أو youtu.be بدون بروتوكول
    if cleaned.startswith(('www.youtube.com', 'youtube.com', 'm.youtube.com', 'youtu.be')):
        return f"https://{cleaned}"

    # إذا لم يكن هناك أي بروتوكول
    if not re.match(r'^[a-zA-Z]+://', cleaned):
        cleaned = f"https://{cleaned}"

    return cleaned


def is_valid_url(url: str) -> bool:
    """
    التحقق من صحة وصلاحية رابط الإنترنت بعد تنظيفه وإصلاح أي نقص فيه.
    Validate if a string is a well-formed HTTP, HTTPS, or FTP URL.

    :param url: الرابط المراد اختباره
    :return: True إذا كان الرابط صالحاً، وإلا False
    """
    if not url or not isinstance(url, str):
        return False

    url_str = normalize_url(url)
    if not url_str:
        return False

    try:
        parsed = urllib.parse.urlparse(url_str)
        if parsed.scheme.lower() not in ("http", "https", "ftp", "ftps"):
            return False
        if not parsed.netloc:
            return False
        # يجب أن يحتوي النطاق على نقطة أو يكون localhost أو IP
        if "." not in parsed.netloc and parsed.netloc != "localhost":
            return False
        return bool(_URL_REGEX.match(url_str))
    except Exception:
        return False


def detect_platform(url: str) -> str:
    """
    تحديد اسم المنصة المشغلة للرابط (يوتيوب، فيسبوك، تيك توك، تويتر، إلخ).
    Detect platform name from URL.

    :param url: رابط الوسائط
    :return: اسم المنصة (مثل 'youtube', 'facebook', أو 'generic')
    """
    if not url:
        return PLATFORM_GENERIC

    url_to_test = normalize_url(url)

    for platform_name, pattern in _PLATFORM_PATTERNS:
        if pattern.search(url_to_test):
            return platform_name

    return PLATFORM_GENERIC


def get_platform_icon_name(platform: str) -> str:
    """Return the platform identifier (e.g., "youtube") for icon lookup.
    Tests expect the raw platform key, not a filename.
    """
    normalized = (platform or "").lower().strip()
    return normalized if normalized in PLATFORM_ICONS else PLATFORM_GENERIC


def is_playlist_url(url: str) -> bool:
    """
    التحقق مما إذا كان الرابط يشير إلى قائمة تشغيل (Playlist) أو ألبوم.
    Detect if the given URL points to a playlist or collection.

    :param url: الرابط المراد فحصه
    :return: True إذا كان الرابط يشير لقائمة تشغيل
    """
    if not url or not isinstance(url, str):
        return False

    url_str = normalize_url(url)
    platform = detect_platform(url_str)

    try:
        parsed = urllib.parse.urlparse(url_str)
        query_params = urllib.parse.parse_qs(parsed.query)

        # التحقق من يوتيوب: وجود معامل list= أو مسار playlist
        if platform == PLATFORM_YOUTUBE:
            if "list" in query_params:
                list_id = query_params["list"][0]
                return bool(list_id)
            if "/playlist" in parsed.path.lower():
                return True

        # التحقق من ساوند كلاود: وجود /sets/
        if platform == PLATFORM_SOUNDCLOUD:
            if "/sets/" in parsed.path.lower():
                return True

        # التحقق من منصات أخرى: وجود كلمات playlist أو album أو collection في المسار
        path_lower = parsed.path.lower()
        if any(term in path_lower for term in ("/playlist/", "/playlists/", "/album/", "/albums/", "/sets/")):
            return True

        return False
    except Exception:
        return False


def is_direct_download(url: str) -> bool:
    """
    التحقق مما إذا كان الرابط يشير مباشرة إلى ملف قابل للتنزيل (فيديو، صورة، ملف مضغوط، مستند).
    Detect if URL points directly to a downloadable file.

    :param url: الرابط
    :return: True إذا كان الرابط يحمل امتداد ملف مباشر معروف
    """
    if not url or not isinstance(url, str):
        return False

    # إذا كانت منصة وسائط اجتماعية شهيرة، فالغالب أنها صفحة ويب وليست رابط ملف مباشر
    platform = detect_platform(url)
    if platform != PLATFORM_GENERIC:
        # منصات الفيديو تستخدم yt-dlp للاستخراج وليست روابط مباشرة
        return False

    ext = get_file_extension(url)
    if not ext:
        return False

    return ext in DIRECT_DOWNLOAD_EXTENSIONS
