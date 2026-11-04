"""
FlexDown - yt-dlp Backend Module
وحدة التعامل مع مكتبة yt-dlp لاستخراج وتنزيل الوسائط المتعددة من منصات الفيديو والصوت.
"""

import os
import shutil
import re
from typing import Optional, Dict, Any, List
from PyQt6.QtCore import QThread, pyqtSignal

import yt_dlp
from yt_dlp.utils import DownloadCancelled
from flexdown.utils.url_utils import normalize_url, is_playlist_url


class _YtDlpQuietLogger:
    """مسجل مخصص لتجنب إخراج النصوص غير المرغوب فيها إلى الطرفية."""

    def debug(self, msg: str) -> None:
        pass

    def info(self, msg: str) -> None:
        pass

    def warning(self, msg: str) -> None:
        pass

    def error(self, msg: str) -> None:
        pass

    def critical(self, msg: str) -> None:
        pass


def _get_node_runtime() -> Optional[Dict[str, Any]]:
    """البحث عن بيئة تشغيل Node.js لحل تحديات التشفير في يوتيوب"""
    node_bin = shutil.which('node')
    if not node_bin:
        common_node_paths = [
            r'C:\Program Files\nodejs\node.exe',
            r'C:\Program Files (x86)\nodejs\node.exe',
            os.path.expanduser(r'~\AppData\Roaming\nvm\current\node.exe'),
        ]
        for p in common_node_paths:
            if os.path.exists(p):
                node_bin = p
                break
    if node_bin:
        return {'node': {'path': node_bin}}
    return None


def _get_impersonate_target():
    """الحصول على هدف انتحال المتصفح لتجاوز حماية Cloudflare و TikTok SlardarWAF"""
    try:
        from yt_dlp.networking.impersonate import ImpersonateTarget
        return ImpersonateTarget('chrome', '110', 'windows', '10')
    except Exception:
        return None


class FormatFetcher(QThread):
    """
    خيط لاستخراج معلومات وصيغ الوسائط المتاحة للرابط بدون تنزيل الملف الفعلي.
    Formats Fetcher Thread - Extracts media metadata and format list without downloading.
    """
    # إشارات الخيط
    formats_ready = pyqtSignal(dict, list)  # (info_dict, formats_list)
    error = pyqtSignal(str)                 # (error_message)

    def __init__(self, url: str, proxy: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.url = url.strip()
        self.proxy = proxy.strip() if proxy else None
        self._is_cancelled = False

    def cancel(self) -> None:
        """إلغاء عملية فحص الروابط."""
        self._is_cancelled = True

    def run(self) -> None:
        """تنفيذ استخراج بيانات الفيديو والصيغ المتاحة."""
        # Add bundled ffmpeg to PATH if available
        bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bin')
        if os.path.exists(bin_dir) and bin_dir not in os.environ.get('PATH', ''):
            os.environ['PATH'] = bin_dir + os.pathsep + os.environ.get('PATH', '')

        node_rt = _get_node_runtime()
        imp_target = _get_impersonate_target()
        target_url = normalize_url(self.url)
        ydl_opts: Dict[str, Any] = {
            'extract_flat': 'in_playlist',
            'skip_download': True,
            'quiet': True,
            'no_warnings': True,
            'logger': _YtDlpQuietLogger(),
            'remote_components': {'ejs:github'},
            'geo_bypass': True,
        }
        if node_rt:
            ydl_opts['js_runtimes'] = node_rt
        if imp_target:
            ydl_opts['impersonate'] = imp_target

        if self.proxy:
            ydl_opts['proxy'] = self.proxy

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if self._is_cancelled:
                    return

                # استخراج البيانات الوصفية (Metadata)
                info = ydl.extract_info(target_url, download=False)
                if not info or self._is_cancelled:
                    return

                # التحقق مما إذا كان الرابط يشير لقائمة تشغيل (Playlist)
                is_playlist = info.get('_type') == 'playlist' or 'entries' in info
                if is_playlist:
                    raw_entries = info.get('entries') or []
                    entries: List[Dict[str, Any]] = []
                    for e in raw_entries:
                        if not e:
                            continue
                        v_url = e.get('url') or e.get('webpage_url')
                        if not v_url and e.get('id'):
                            v_url = f"https://www.youtube.com/watch?v={e['id']}"
                        v_title = e.get('title') or "Untitled Video"
                        v_duration = float(e.get('duration') or 0.0)
                        v_thumb = e.get('thumbnail')
                        if not v_thumb and e.get('thumbnails'):
                            thumbs = e.get('thumbnails')
                            if isinstance(thumbs, list) and thumbs:
                                v_thumb = thumbs[-1].get('url', '')
                        entries.append({
                            'id': str(e.get('id', '')),
                            'url': str(v_url),
                            'title': str(v_title),
                            'duration': v_duration,
                            'thumbnail': str(v_thumb or ''),
                        })

                    total_duration = sum(e['duration'] for e in entries)
                    playlist_title = info.get('title') or "YouTube Playlist"
                    playlist_thumb = info.get('thumbnail') or (entries[0]['thumbnail'] if entries else '')

                    # جودات الفيديو القياسية لقوائم التشغيل
                    PLAYLIST_VIDEO_PRESETS = [
                        ("bestvideo[height<=2160]+bestaudio/best[height<=2160]", "4K Ultra HD (2160p)", 4500),
                        ("bestvideo[height<=1440]+bestaudio/best[height<=1440]", "2K Quad HD (1440p)", 2500),
                        ("bestvideo[height<=1080]+bestaudio/best[height<=1080]", "1080p Full HD", 1500),
                        ("bestvideo[height<=720]+bestaudio/best[height<=720]",   "720p HD", 900),
                        ("bestvideo[height<=480]+bestaudio/best[height<=480]",   "480p SD", 500),
                        ("bestvideo[height<=360]+bestaudio/best[height<=360]",   "360p", 300),
                        ("bestvideo+bestaudio/best",                             "Best Available Quality", 1800),
                    ]

                    video_formats: List[Dict[str, Any]] = []
                    for fmt_spec, label, kbps in PLAYLIST_VIDEO_PRESETS:
                        est_size = int((kbps * 1000 / 8) * total_duration) if total_duration > 0 else 0
                        video_formats.append({
                            'format_id': fmt_spec,
                            'ext': 'mp4',
                            'resolution': label,
                            'filesize': est_size,
                            'vcodec': 'h264/vp9',
                            'acodec': 'aac',
                            'fps': None,
                            'tbr': kbps,
                            'format_note': label,
                            'group': 'video',
                            'audio_only': False,
                            'codec': 'MP4 (Video + Audio)',
                        })

                    # جودات الصوت القياسية لقوائم التشغيل
                    PLAYLIST_AUDIO_PRESETS = [
                        (320, "320 kbps (Ultra High Quality)", "mp3", "mp3"),
                        (256, "256 kbps (Very High Quality)",  "mp3", "mp3"),
                        (192, "192 kbps (High Quality)",       "mp3", "mp3"),
                        (128, "128 kbps (Standard Quality)",   "mp3", "mp3"),
                        (320, "320 kbps (Original Quality)",   "m4a", "m4a"),
                        (256, "256 kbps (High Quality)",       "m4a", "m4a"),
                        (192, "192 kbps (Standard Quality)",   "m4a", "m4a"),
                        (128, "128 kbps (Compact)",            "m4a", "m4a"),
                    ]

                    audio_formats: List[Dict[str, Any]] = []
                    for br, label, ext, fmt in PLAYLIST_AUDIO_PRESETS:
                        est_size = int((br * 1000 / 8) * total_duration) if total_duration > 0 else 0
                        audio_formats.append({
                            'format_id': 'bestaudio/best',
                            'ext': ext,
                            'resolution': label,
                            'filesize': est_size,
                            'vcodec': 'none',
                            'acodec': fmt,
                            'fps': None,
                            'tbr': br,
                            'format_note': f"{br}k",
                            'group': 'audio_only',
                            'audio_only': True,
                            'audio_format': fmt,
                            'audio_quality': str(br),
                            'codec': f"{fmt.upper()} ({br} kbps)",
                        })

                    parsed_formats = video_formats + audio_formats
                    info['is_playlist'] = True
                    info['title'] = playlist_title
                    info['entries'] = entries
                    info['playlist_count'] = len(entries)
                    info['duration'] = total_duration
                    info['thumbnail'] = playlist_thumb
                    info['grouped_formats'] = {
                        'video': video_formats,
                        'audio_only': audio_formats,
                        'video_audio': video_formats,
                        'video_only': [],
                    }
                    info['clean_formats'] = parsed_formats

                    if not self._is_cancelled:
                        self.formats_ready.emit(info, parsed_formats)
                    return

                # استخراج الصيغ وتنسيقها إلى الجودات القياسية المعروفة
                raw_formats = info.get('formats', [])
                duration = float(info.get('duration') or 0.0)

                # البحث عن أفضل مسار صوتي لتقدير الحجم المدمج
                audio_streams = [
                    f for f in raw_formats
                    if f.get('acodec') not in ('none', '', None) and f.get('vcodec') in ('none', '', None)
                ]
                best_audio = max(audio_streams, key=lambda f: f.get(
                    'abr') or f.get('tbr') or 0) if audio_streams else None
                best_audio_size = 0
                if best_audio:
                    best_audio_size = best_audio.get('filesize') or best_audio.get('filesize_approx') or 0
                    if not best_audio_size and duration > 0:
                        abr = best_audio.get('abr') or 128
                        best_audio_size = int((abr * 1000 / 8) * duration)
                if not best_audio_size and duration > 0:
                    best_audio_size = int((128 * 1000 / 8) * duration)

                # 1. جودات الفيديو المعروفة القياسية (YouTube Standard Presets)
                STANDARD_RES = [
                    (4320, "8K Ultra HD (4320p)"),
                    (2160, "4K Ultra HD (2160p)"),
                    (1440, "2K Quad HD (1440p)"),
                    (1080, "1080p Full HD"),
                    (720,  "720p HD"),
                    (480,  "480p SD"),
                    (360,  "360p"),
                    (240,  "240p"),
                    (144,  "144p"),
                ]

                video_formats: List[Dict[str, Any]] = []
                used_heights = set()

                for h, label in STANDARD_RES:
                    matching = [
                        f for f in raw_formats
                        if f.get('vcodec') not in ('none', '', None)
                        and (f.get('height') == h or abs((f.get('height') or 0) - h) <= 4)
                    ]
                    if matching:
                        used_heights.add(h)

                        def format_score(f, target_h=h):
                            vcodec = str(f.get('vcodec', '')).lower()
                            # في الدقات العالية (4K / 8K)، يستخدم يوتيوب VP9 و AV1 حصراً
                            if target_h >= 1440:
                                codec_score = 3 if ('av01' in vcodec or 'av1' in vcodec) else (
                                    2 if ('vp9' in vcodec or 'vp09' in vcodec) else 1
                                )
                            else:
                                codec_score = 3 if vcodec.startswith(('avc', 'h264')) else (
                                    2 if ('vp9' in vcodec or 'vp09' in vcodec) else 1
                                )
                            ext_score = 1 if f.get('ext') == 'mp4' else 0
                            fps = f.get('fps') or 0
                            bitrate = f.get('tbr') or f.get('vbr') or 0
                            return (codec_score, ext_score, fps, bitrate)

                        matching.sort(key=format_score, reverse=True)
                        chosen = matching[0]
                        vid_size = chosen.get('filesize') or chosen.get('filesize_approx') or 0
                        if not vid_size and duration > 0:
                            vbr = chosen.get('vbr') or chosen.get('tbr') or 0
                            if vbr > 0:
                                vid_size = int((vbr * 1000 / 8) * duration)

                        has_builtin_audio = chosen.get('acodec') not in ('none', '', None)
                        if has_builtin_audio:
                            fmt_id = str(chosen.get('format_id', ''))
                            total_size = vid_size
                        else:
                            fmt_id = f"{chosen.get('format_id', '')}+bestaudio/best"
                            total_size = (vid_size + best_audio_size) if vid_size > 0 else 0

                        fps = chosen.get('fps')
                        fps_str = f" ({fps}fps)" if fps and fps > 30 else ""

                        video_formats.append({
                            'format_id': fmt_id,
                            'ext': 'mp4',
                            'resolution': f"{label}{fps_str}",
                            'filesize': total_size,
                            'vcodec': str(chosen.get('vcodec', 'h264')),
                            'acodec': 'aac',
                            'fps': fps,
                            'tbr': chosen.get('tbr') or chosen.get('vbr') or 0,
                            'format_note': label,
                            'group': 'video',
                            'audio_only': False,
                            'codec': 'MP4 (Video + Audio)',
                        })

                # فحص أي دقة فيديو غير قياسية متاحة (إن وجدت)
                other_video_streams = [
                    f for f in raw_formats
                    if f.get('vcodec') not in ('none', '', None)
                    and f.get('height') and not any(abs(f.get('height') - uh) <= 4 for uh in used_heights)
                ]
                if other_video_streams:
                    distinct_heights = sorted(list(set(f.get('height') for f in other_video_streams)), reverse=True)
                    for oh in distinct_heights:
                        m_list = [f for f in other_video_streams if f.get('height') == oh]

                        def stream_compat_score(f):
                            vc = str(f.get('vcodec', '')).lower()
                            is_h264 = 2 if ('avc' in vc or 'h264' in vc) else (
                                0 if ('hevc' in vc or 'h265' in vc or 'bytevc1' in vc) else 1)
                            tbr = f.get('tbr') or f.get('vbr') or 0
                            return (is_h264, tbr)

                        m_list.sort(key=stream_compat_score, reverse=True)
                        ch = m_list[0]
                        v_sz = ch.get('filesize') or ch.get('filesize_approx') or 0
                        has_ba = ch.get('acodec') not in ('none', '', None)
                        fmt_id = str(ch.get('format_id', '')) if has_ba else f"{ch.get('format_id', '')}+bestaudio/best"
                        tot_sz = v_sz if has_ba else (v_sz + best_audio_size if v_sz else 0)

                        vcodec_raw = str(ch.get('vcodec', '')).lower()
                        is_hevc = 'h265' in vcodec_raw or 'hevc' in vcodec_raw or 'bytevc1' in vcodec_raw
                        tag = " (HEVC)" if is_hevc else " (H.264 - Recommended)"

                        video_formats.append({
                            'format_id': fmt_id,
                            'ext': 'mp4',
                            'resolution': f"{oh}p{tag}",
                            'filesize': tot_sz,
                            'vcodec': str(ch.get('vcodec', 'video')),
                            'acodec': 'aac',
                            'fps': ch.get('fps'),
                            'tbr': ch.get('tbr') or 0,
                            'format_note': f"{oh}p",
                            'group': 'video',
                            'audio_only': False,
                            'codec': 'MP4 (HEVC)' if is_hevc else 'MP4 (H.264 Universal)',
                        })

                # ترتيب الدقات من الأعلى إلى الأدنى (8K ثم 4K ثم 2K ثم 1080p وهكذا)
                def get_res_height(item):
                    h_val = item.get('height')
                    if h_val:
                        return int(h_val)
                    res_str = str(item.get('resolution', '')) + " " + str(item.get('format_note', ''))
                    m = re.search(r'(\d{3,4})p', res_str)
                    return int(m.group(1)) if m else 0

                video_formats.sort(key=get_res_height, reverse=True)

                # 2. جودات الصوت القياسية المطلوبة (من 128 إلى 320 كيلوبت/ث)
                AUDIO_PRESETS = [
                    {"bitrate": 320, "label": "320 kbps (Ultra High Quality)", "ext": "mp3", "fmt": "mp3"},
                    {"bitrate": 256, "label": "256 kbps (Very High Quality)",  "ext": "mp3", "fmt": "mp3"},
                    {"bitrate": 192, "label": "192 kbps (High Quality)",       "ext": "mp3", "fmt": "mp3"},
                    {"bitrate": 128, "label": "128 kbps (Standard Quality)",   "ext": "mp3", "fmt": "mp3"},
                    {"bitrate": 320, "label": "320 kbps (Original Quality)",   "ext": "m4a", "fmt": "m4a"},
                    {"bitrate": 256, "label": "256 kbps (High Quality)",       "ext": "m4a", "fmt": "m4a"},
                    {"bitrate": 192, "label": "192 kbps (Standard Quality)",   "ext": "m4a", "fmt": "m4a"},
                    {"bitrate": 128, "label": "128 kbps (Compact)",            "ext": "m4a", "fmt": "m4a"},
                ]

                audio_formats: List[Dict[str, Any]] = []
                for p in AUDIO_PRESETS:
                    bitrate_val = int(str(p["bitrate"]))
                    a_size = int((bitrate_val * 1000 / 8) * duration) if duration > 0 else 0
                    audio_formats.append({
                        'format_id': 'bestaudio/best',
                        'ext': p['ext'],
                        'resolution': p['label'],
                        'filesize': a_size,
                        'vcodec': 'none',
                        'acodec': p['fmt'],
                        'fps': None,
                        'tbr': p['bitrate'],
                        'format_note': f"{p['bitrate']}k",
                        'group': 'audio_only',
                        'audio_only': True,
                        'audio_format': p['fmt'],
                        'audio_quality': str(p['bitrate']),
                        'codec': f"{p['fmt'].upper()} ({p['bitrate']} kbps)",
                    })

                parsed_formats = video_formats + audio_formats

                grouped_formats = {
                    'video': video_formats,
                    'audio_only': audio_formats,
                    'video_audio': video_formats,
                    'video_only': [],
                }

                info['grouped_formats'] = grouped_formats
                info['clean_formats'] = parsed_formats

                if not self._is_cancelled:
                    self.formats_ready.emit(info, parsed_formats)

        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))


class YtDlpWorker(QThread):
    """
    خيط تنفيذ التنزيل عبر yt-dlp مع دعم استئناف التحميل واختيار الجودة وتحويل الصوت.
    YtDlp Worker Thread - Downloads video/audio using yt-dlp with progress tracking and cancel support.
    """
    # إشارات الخيط
    # {'downloaded_bytes', 'total_bytes', 'speed', 'eta', 'percent', 'filename', 'status'}
    progress = pyqtSignal(dict)
    finished = pyqtSignal(str, dict)        # (file_path, info_dict)
    error = pyqtSignal(str)                 # (error_message)

    def __init__(self, url: str, output_dir: str, options: Optional[Dict[str, Any]] = None, parent=None):
        super().__init__(parent)
        self.url = url.strip()
        self.output_dir = output_dir
        self.options = options or {}
        self._is_cancelled = False
        self._downloaded_file_path: Optional[str] = None
        self._last_info_dict: Dict[str, Any] = {}

    def cancel(self) -> None:
        """إلغاء عملية التنزيل الجارية فوراً."""
        self._is_cancelled = True

    def _progress_hook(self, d: Dict[str, Any]) -> None:
        """دالة رد النداء (Callback Hook) المربوطة بـ yt-dlp لتتبع تقدم التنزيل."""
        if self._is_cancelled:
            # رفع استثناء لإيقاف yt-dlp فوراً عند طلب الإلغاء
            raise DownloadCancelled("Download cancelled by user")

        status_raw = d.get('status', 'downloading')
        filename = d.get('filename', '')
        if filename:
            self._downloaded_file_path = filename

        downloaded_bytes = d.get('downloaded_bytes', 0) or 0
        total_bytes = d.get('total_bytes') or d.get('total_bytes_estimate', 0) or 0
        speed = d.get('speed', 0) or 0
        eta = d.get('eta', 0) or 0

        percent = 0.0
        if total_bytes > 0:
            percent = round((downloaded_bytes / total_bytes) * 100.0, 2)
        elif status_raw == 'finished':
            percent = 100.0

        progress_payload = {
            'downloaded_bytes': downloaded_bytes,
            'total_bytes': total_bytes,
            'speed': speed,
            'eta': eta,
            'percent': percent,
            'filename': os.path.basename(filename) if filename else '',
            'status': status_raw
        }

        self.progress.emit(progress_payload)

    def _postprocessor_hook(self, d: Dict[str, Any]) -> None:
        """Postprocessor callback hook for FFmpeg conversion/extraction."""
        if self._is_cancelled:
            raise DownloadCancelled("Download cancelled by user")

        status = d.get('status')
        pp = d.get('postprocessor', '')
        if status == 'started':
            self.progress.emit({
                'downloaded_bytes': 0,
                'total_bytes': 0,
                'speed': 0,
                'eta': 0,
                'percent': 99.0,
                'filename': '',
                'status': 'converting',
                'postprocessor': pp,
            })

    def run(self) -> None:
        """بدء عملية التنزيل داخل الخيط."""
        os.makedirs(self.output_dir, exist_ok=True)

        # قالب اسم الملف الناتج لمنع تضارب الملفات المؤقتة في حالة التحميل المتزامن لنفس الفيديو
        custom_fn = self.options.get('filename')
        audio_only = self.options.get('audio_only', False)
        audio_fmt = self.options.get('audio_format', 'mp3')
        audio_quality = self.options.get('audio_quality')
        fmt_id = self.options.get('format')
        is_playlist = is_playlist_url(self.url)

        if is_playlist:
            if audio_only and audio_quality:
                outtmpl = os.path.join(self.output_dir, "%(title).120B [%(audio_format)s].%(ext)s")
            else:
                outtmpl = os.path.join(self.output_dir, "%(title).150B.%(ext)s")
        elif custom_fn and not custom_fn.startswith('http'):
            base_fn, _ = os.path.splitext(custom_fn)
            outtmpl = os.path.join(self.output_dir, f"{base_fn}.%(ext)s")
        elif audio_only and audio_quality:
            outtmpl = os.path.join(self.output_dir, f"%(title).120B [{audio_fmt.upper()} {audio_quality}k].%(ext)s")
        elif fmt_id and '+' in fmt_id:
            outtmpl = os.path.join(self.output_dir, "%(title).120B [%(resolution)s].%(ext)s")
        else:
            outtmpl = os.path.join(self.output_dir, '%(title).150B.%(ext)s')

        # استكشاف مسار أداة FFmpeg المتاحة لدمج الصوت مع الفيديو
        from flexdown.core.format_converter import FormatConverter
        ffmpeg_bin = FormatConverter.get_ffmpeg_path()
        bin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'bin')
        if os.path.exists(bin_dir) and bin_dir not in os.environ.get('PATH', ''):
            os.environ['PATH'] = bin_dir + os.pathsep + os.environ.get('PATH', '')

        node_rt = _get_node_runtime()
        imp_target = _get_impersonate_target()

        ydl_opts: Dict[str, Any] = {
            'outtmpl': outtmpl,
            'continuedl': True,          # استئناف التحميل في حالة الانقطاع
            'progress_hooks': [self._progress_hook],
            'postprocessor_hooks': [self._postprocessor_hook],
            'logger': _YtDlpQuietLogger(),
            'quiet': True,
            'no_warnings': True,
            'remote_components': {'ejs:github'},
            'geo_bypass': True,
            'http_chunk_size': 2 * 1024 * 1024,  # 2MB chunks to defeat YouTube throttling and maximize download speed
            'concurrent_fragment_downloads': 5,  # multi-part parallel connections
            'nocheckcertificate': self.options.get('nocheckcertificate', False),
            'retries': 10,
            'fragment_retries': 10,
            'file_access_retries': 5,
            'extractor_retries': 5,
            'socket_timeout': 30,
            'retry_sleep_functions': {'http': lambda n: min(2 * (n + 1), 6)},
            'buffersize': 1024 * 64,
            'http_headers': {
                'User-Agent': (
                    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                    'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
                ),
                'Accept-Language': 'en-US,en;q=0.9',
            },
        }

        if node_rt:
            ydl_opts['js_runtimes'] = node_rt
        if imp_target:
            ydl_opts['impersonate'] = imp_target

        # تعيين مسار FFmpeg إن كان متوفراً
        if ffmpeg_bin and (os.path.exists(ffmpeg_bin) or shutil.which(ffmpeg_bin)):
            ydl_opts['ffmpeg_location'] = ffmpeg_bin

        # دعم البروكسي (Proxy)
        proxy = self.options.get('proxy')
        if proxy:
            ydl_opts['proxy'] = proxy

        # معالجات ما بعد التنزيل (Postprocessors)
        postprocessors: List[Dict[str, Any]] = []

        # تحديد التنسيق / الجودة وضمان دمج الصوت دائماً في مقاطع الفيديو
        audio_only = self.options.get('audio_only', False)
        if audio_only:
            ydl_opts['format'] = 'bestaudio/best'
            audio_format = str(self.options.get('audio_format', 'mp3')).lower()
            audio_quality = str(self.options.get('audio_quality', '320'))
            postprocessors.append({
                'key': 'FFmpegExtractAudio',
                'preferredcodec': audio_format,
                'preferredquality': audio_quality,
            })
        else:
            format_spec = self.options.get('format')
            if not format_spec or format_spec in ('best', 'auto', 'direct', ''):
                ydl_opts['format'] = 'bestvideo+bestaudio/best'

            elif '+' in format_spec:
                ydl_opts['format'] = format_spec
            else:
                # إذا اختار المستخدم جودة فيديو محددة (مثل 1080p أو معرف مسار فيديو DASH)
                # نقوم بدمج أفضل مسار صوت معه حتى لا يكون الفيديو بلا صوت
                ydl_opts['format'] = f"{format_spec}+bestaudio/best"

            # ضمان دمج الحاويات كملف MP4 صالح للتشغيل على كافة الأجهزة
            ydl_opts['merge_output_format'] = 'mp4'

        # تضمين الصورة المصغرة (Thumbnail)
        if self.options.get('embed_thumbnail', False):
            ydl_opts['writethumbnail'] = True
            postprocessors.append({'key': 'FFmpegThumbnailsConvertor', 'format': 'jpg'})
            postprocessors.append({'key': 'EmbedThumbnail'})

        # تحميل وتضمين الترجمات (Subtitles)
        if self.options.get('write_subtitles', False):
            ydl_opts['writesubtitles'] = True
            ydl_opts['subtitleslangs'] = self.options.get('subtitles_langs', ['all', '-live_chat'])

        # تحويل الفيديو إلى صيغة محددة (convert_to)
        convert_to = self.options.get('convert_to')
        if convert_to and not self.options.get('audio_only', False):
            postprocessors.append({
                'key': 'FFmpegVideoConvertor',
                'preferedformat': convert_to,
            })

        if postprocessors:
            ydl_opts['postprocessors'] = postprocessors

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                if self._is_cancelled:
                    return

                # تنفيذ التنزيل
                info = ydl.extract_info(self.url, download=True)
                if not info:
                    raise Exception("Failed to extract video information or download file.")

                self._last_info_dict = info

                # تحديد المسار النهائي للملف بعد المعالجة
                final_path = ""
                if info.get('_type') == 'playlist':
                    final_path = self.output_dir
                else:
                    try:
                        final_path = ydl.prepare_filename(info)

                        # تعديل الامتداد إذا تم تحويل الصوت
                        if self.options.get('audio_only', False):
                            audio_fmt = self.options.get('audio_format', 'mp3')
                            base, _ = os.path.splitext(final_path)
                            candidate = f"{base}.{audio_fmt}"
                            if os.path.exists(candidate):
                                final_path = candidate
                        # تعديل الامتداد إذا تم تحويل الفيديو
                        elif convert_to:
                            base, _ = os.path.splitext(final_path)
                            candidate = f"{base}.{convert_to}"
                            if os.path.exists(candidate):
                                final_path = candidate

                        # إذا لم يتطابق مسار prepare_filename، نستخدم مسار hook إذا وُجد
                        if not os.path.exists(final_path) and self._downloaded_file_path:
                            if os.path.exists(self._downloaded_file_path):
                                final_path = self._downloaded_file_path
                    except Exception:
                        final_path = self._downloaded_file_path or ""

                if not self._is_cancelled:
                    self.finished.emit(final_path, info)

        except DownloadCancelled:
            # تم الإلغاء بشكل طبيعي من قبل المستخدم
            return
        except Exception as e:
            if not self._is_cancelled:
                err_raw = str(e)
                # إذا حدث خطأ Range أو انقطاع أدى لفساد ملف .part،
                # يتم حذفه لتفادي الدوران في حلقة الفشل عند إعادة المحاولة
                if "bytes read" in err_raw and "more expected" in err_raw:
                    try:
                        for fname in os.listdir(self.output_dir):
                            if fname.endswith('.part'):
                                fpath = os.path.join(self.output_dir, fname)
                                try:
                                    os.remove(fpath)
                                except Exception:
                                    pass
                    except Exception:
                        pass
                err_str = re.sub(r'\x1b\[[0-9;]*m', '', err_raw).strip()
                self.error.emit(err_str)
