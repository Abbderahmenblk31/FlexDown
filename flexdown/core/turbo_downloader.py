"""
FlexDown - Turbo Multi-Segment Download Accelerator Module
وحدة التسريع الفائق متعدد الاتصالات (16 مسار متزامن) للملفات المباشرة وكافة أنواع الملفات
مع الفحص اللحظي للروابط (URL Probing) والتحقق من سلامة الملفات عبر SHA-256.
"""

import os
import re
import sys
import hashlib
import shutil
import subprocess
import urllib.parse
from typing import Optional, Dict, Any
from PyQt6.QtCore import QThread, pyqtSignal

import requests
from flexdown.utils.file_utils import sanitize_filename, get_file_extension
from flexdown.utils.url_utils import normalize_url, is_valid_url


def get_aria2_path() -> Optional[str]:
    """البحث عن مسار aria2c المدمج في التطبيق أو المثبت في النظام."""
    # 1. البحث في مجلد bin المدمج في حزمة البرنامج
    base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    bundled_aria = os.path.join(base_dir, "bin", "aria2c.exe" if sys.platform == "win32" else "aria2c")
    if os.path.exists(bundled_aria):
        return bundled_aria

    # في حالة بيئة PyInstaller _internal
    if hasattr(sys, "_MEIPASS"):
        meipass_aria = os.path.join(sys._MEIPASS, "bin", "aria2c.exe" if sys.platform == "win32" else "aria2c")
        if os.path.exists(meipass_aria):
            return meipass_aria

    # بجوار ملف التنفيذ FlexDown.exe
    exe_dir = os.path.dirname(sys.executable)
    exe_aria = os.path.join(exe_dir, "bin", "aria2c.exe" if sys.platform == "win32" else "aria2c")
    if os.path.exists(exe_aria):
        return exe_aria
    internal_aria = os.path.join(exe_dir, "_internal", "bin", "aria2c.exe" if sys.platform == "win32" else "aria2c")
    if os.path.exists(internal_aria):
        return internal_aria

    # 2. البحث في PATH النظام
    system_aria = shutil.which("aria2c")
    if system_aria and os.path.exists(system_aria):
        return system_aria

    return None


def parse_size_to_bytes(size_str: str) -> int:
    """تحويل نص الحجم (مثل 10.5MiB أو 1.2GiB) إلى بايتات."""
    if not size_str:
        return 0
    m = re.match(r"^([0-9.]+)\s*([A-Za-z]+)?$", size_str.strip())
    if not m:
        return 0
    val = float(m.group(1))
    unit = (m.group(2) or "B").upper()

    multipliers = {
        "B": 1,
        "KIB": 1024,
        "KB": 1000,
        "MIB": 1024 ** 2,
        "MB": 1000 ** 2,
        "GIB": 1024 ** 3,
        "GB": 1000 ** 3,
        "TIB": 1024 ** 4,
        "TB": 1000 ** 4,
    }
    return int(val * multipliers.get(unit, 1))


def compute_file_sha256(file_path: str, callback=None) -> str:
    """حساب بصمة SHA-256 للملف للتحقق من الأمان وسلامة البيانات."""
    if not os.path.exists(file_path):
        return ""
    hasher = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(1024 * 1024):
                hasher.update(chunk)
        return hasher.hexdigest()
    except Exception:
        return ""


def detect_file_category(filename: str, content_type: str = "") -> str:
    """تحديد تصنيف الملف بناءً على الامتداد ونوع المحتوى."""
    ext = get_file_extension(filename).lower()
    ctype = (content_type or "").lower()

    programs = {"exe", "msi", "apk", "dmg", "pkg", "deb", "rpm", "bin", "appimage", "jar", "bat", "cmd"}
    archives = {"zip", "rar", "7z", "tar", "gz", "bz2", "xz", "iso", "img", "vhd", "tgz"}
    documents = {"pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "txt", "rtf", "odt", "csv", "epub"}
    videos = {"mp4", "mkv", "avi", "mov", "flv", "webm", "wmv", "m4v", "3gp", "ts"}
    audios = {"mp3", "wav", "flac", "aac", "m4a", "ogg", "opus", "wma"}
    images = {"jpg", "jpeg", "png", "gif", "webp", "bmp", "svg", "ico", "tiff"}

    if ext in programs or "executable" in ctype or "octet-stream" in ctype and ext in programs:
        return "PROGRAM"
    if ext in archives or "zip" in ctype or "compressed" in ctype or "tar" in ctype or "iso" in ctype:
        return "ARCHIVE"
    if ext in documents or "pdf" in ctype or "document" in ctype or "sheet" in ctype:
        return "DOCUMENT"
    if ext in videos or "video/" in ctype:
        return "VIDEO"
    if ext in audios or "audio/" in ctype:
        return "AUDIO"
    if ext in images or "image/" in ctype:
        return "IMAGE"

    return "OTHER"


def probe_download_url(
    url: str,
    proxy: Optional[str] = None,
    headers: Optional[Dict[str, str]] = None,
    timeout: int = 6
) -> Dict[str, Any]:
    """
    فحص سريع للرابط (URL Probe) عبر طلب Range 0-0 للحصول على اسم الملف والحجم
    ودعم التجزئة دون استهلاك صبيب الإنترنت.
    """
    clean_url = normalize_url(url)
    if not is_valid_url(clean_url):
        return {"success": False, "error": "Invalid URL"}

    # حل روابط صفحات APKPure تلقائياً إلى رابط التنزيل المباشر
    target_probe_url = clean_url
    if "apkpure.com" in clean_url.lower() and "d.apkpure.com" not in clean_url.lower():
        all_pkgs = re.findall(r'([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)', clean_url)
        real_pkgs = [p for p in all_pkgs if p.lower() not in (
            "apkpure.com", "winudf.com", "m.apkpure.com", "pure.com"
        )]
        if real_pkgs:
            target_probe_url = f"https://d.apkpure.com/b/APK/{real_pkgs[-1]}?version=latest"

    req_headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 FlexDown/1.0.0"
        ),
        "Accept": "*/*",
        "Range": "bytes=0-0",  # يطلب فقط البايت الأول لاختبار Range ومعرفة الحجم فورياً
    }
    if "apkpure.com" in clean_url.lower() or "winudf.com" in clean_url.lower():
        req_headers["Referer"] = "https://apkpure.com/"
    if headers:
        req_headers.update(headers)

    proxies = {"http": proxy, "https": proxy} if proxy else None

    try:
        resp = requests.get(
            target_probe_url,
            headers=req_headers,
            proxies=proxies,
            stream=True,
            allow_redirects=True,
            timeout=timeout,
        )

        final_url = resp.url or target_probe_url
        status = resp.status_code
        h = resp.headers

        # 1. استخراج اسم الملف
        filename = ""
        cd = h.get("Content-Disposition") or h.get("content-disposition", "")
        if cd:
            m_star = re.search(r"filename\*=UTF-8''([^;]+)", cd, re.IGNORECASE)
            if m_star:
                filename = urllib.parse.unquote_plus(m_star.group(1))
            else:
                m_plain = re.search(r'filename=["\']?([^";\']+)', cd, re.IGNORECASE)
                if m_plain:
                    filename = urllib.parse.unquote_plus(m_plain.group(1).strip())

        if not filename:
            parsed = urllib.parse.urlparse(final_url)
            base = os.path.basename(parsed.path)
            if "." in base:
                filename = urllib.parse.unquote_plus(base)

        if not filename:
            filename = "downloaded_file"

        filename = sanitize_filename(filename)

        # 2. استخراج الحجم الكلي ودعم التجزئة (Range Support)
        total_size = 0
        supports_range = False

        if status == 206:
            # 206 Partial Content -> السيرفر يدعم التجزئة المتعددة 16 اتصالاً!
            supports_range = True
            cr = h.get("Content-Range") or h.get("content-range", "")
            if cr and "/" in cr:
                try:
                    total_size = int(cr.split("/")[-1])
                except ValueError:
                    total_size = int(h.get("Content-Length") or 0)
            else:
                total_size = int(h.get("Content-Length") or 0)
        elif status == 200:
            # 200 OK -> السيرفر قد لا يدعم Range أو أرسل الملف من البداية
            total_size = int(h.get("Content-Length") or 0)
            supports_range = (h.get("Accept-Ranges") or "").lower() == "bytes"
        else:
            resp.raise_for_status()

        ctype = (h.get("Content-Type") or "").lower()
        is_html = "text/html" in ctype and total_size < 500000

        category = detect_file_category(filename, ctype)

        return {
            "success": True,
            "filename": filename,
            "filesize": total_size,
            "supports_range": supports_range,
            "content_type": ctype,
            "is_html": is_html,
            "category": category,
            "final_url": final_url,
            "target_url": target_probe_url,
            "status_code": status,
        }

    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "filename": os.path.basename(urllib.parse.urlparse(clean_url).path) or "download_file",
            "filesize": 0,
            "supports_range": False,
            "is_html": False,
            "category": "OTHER",
            "final_url": clean_url,
        }


class DirectFileProbeWorker(QThread):
    """خيط فحص الروابط المباشرة للحصول على معلومات الملف دون تجميد الواجهة."""
    probe_finished = pyqtSignal(dict)  # result dictionary

    def __init__(self, url: str, proxy: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.url = url
        self.proxy = proxy

    def run(self):
        info = probe_download_url(self.url, proxy=self.proxy)
        self.probe_finished.emit(info)


class TurboDownloadWorker(QThread):
    """
    محرك التنزيل فائق السرعة متعدد الاتصالات (Turbo 16-Connections Engine).
    يستعمل aria2c المدمج لتقسيم الملف إلى 16 جزءاً متزامناً عبر Range Headers
    مع حساب السرعة الحقيقية وتقدير الوقت المتبقي، وفحص سلامة التشفير SHA-256.
    """
    # الإشارات المتوافقة مع النظام:
    # {'downloaded_bytes', 'total_bytes', 'speed', 'eta', 'percent', 'filename', 'status', 'connections'}
    progress = pyqtSignal(dict)
    finished = pyqtSignal(str, bool)     # (file_path, success)
    error = pyqtSignal(str)              # (error_message)
    hash_ready = pyqtSignal(str, str)    # (file_path, sha256_hash)

    def __init__(
        self,
        url: str,
        output_dir: str,
        filename: Optional[str] = None,
        proxy: Optional[str] = None,
        max_connections: int = 16,
        headers: Optional[Dict[str, str]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.url = normalize_url(url.strip())
        self.output_dir = output_dir
        self.filename = filename
        self.proxy = proxy
        self.max_connections = max(1, min(16, max_connections))
        self.headers = headers or {}
        self._is_cancelled = False
        self._process: Optional[subprocess.Popen] = None
        self._dest_file_path: str = ""

    def cancel(self) -> None:
        """إيقاف عملية التنزيل الجارية وحفظ حالة الاستئناف."""
        self._is_cancelled = True
        if self._process and self._process.poll() is None:
            try:
                self._process.terminate()
            except Exception:
                try:
                    self._process.kill()
                except Exception:
                    pass

    def run(self) -> None:
        """بدء عملية التنزيل المسرع."""
        os.makedirs(self.output_dir, exist_ok=True)
        aria_bin = get_aria2_path()

        # إذا تعذر العثور على aria2c، نستخدم محرك HTTP البديل
        if not aria_bin:
            self._run_fallback_downloader()
            return

        # تحديد اسم الملف إن لم يكن معلوماً مع فك التشفير والتنظيف
        target_fn = self.filename
        if not target_fn:
            parsed = urllib.parse.urlparse(self.url)
            target_fn = os.path.basename(parsed.path) or "flexdown_download"
        target_fn = urllib.parse.unquote_plus(target_fn)
        target_fn = sanitize_filename(target_fn)
        self._dest_file_path = os.path.join(self.output_dir, target_fn)

        # حل روابط APKPure تلقائياً إن وجدت
        download_url = self.url
        if "apkpure.com" in download_url.lower() and "d.apkpure.com" not in download_url.lower():
            all_pkgs = re.findall(r'([a-zA-Z0-9_]+(?:\.[a-zA-Z0-9_]+)+)', download_url)
            real_pkgs = [p for p in all_pkgs if p.lower() not in (
                "apkpure.com", "winudf.com", "m.apkpure.com", "pure.com"
            )]
            if real_pkgs:
                download_url = f"https://d.apkpure.com/b/APK/{real_pkgs[-1]}?version=latest"

        cmd = [
            aria_bin,
            "-x", str(self.max_connections),
            "-s", str(self.max_connections),
            "-j", "4",
            "-k", "1M",
            "--file-allocation=none",
            "--summary-interval=1",
            "--console-log-level=warn",
            "--allow-overwrite=true",
            "--auto-file-renaming=false",
            "--check-certificate=true",
            "--dir", self.output_dir,
            "--out", target_fn,
        ]

        if self.proxy:
            cmd.extend(["--all-proxy", self.proxy])

        user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36 FlexDown/1.0.0"
        )
        cmd.extend(["--header", f"User-Agent: {user_agent}"])

        has_referer = any(k.lower() == "referer" for k in (self.headers or {}))
        if not has_referer:
            if "apkpure.com" in self.url.lower() or "winudf.com" in self.url.lower():
                cmd.extend(["--header", "Referer: https://apkpure.com/"])
            else:
                p_ref = urllib.parse.urlparse(self.url)
                if p_ref.netloc:
                    cmd.extend(["--header", f"Referer: {p_ref.scheme}://{p_ref.netloc}/"])

        if self.headers:
            for k, v in self.headers.items():
                if k.lower() != "user-agent":
                    cmd.extend(["--header", f"{k}: {v}"])

        cmd.append(download_url)

        creationflags = 0
        if sys.platform == "win32":
            creationflags = 0x08000000  # CREATE_NO_WINDOW: يمنع ظهور شاشة الدوس السوداء نهائياً

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                encoding="utf-8",
                errors="replace",
                creationflags=creationflags,
            )

            # نمط مطابقة أسطر تقدم aria2c:
            # [#gid 4.5MiB/10MiB(45%) CN:16 DL:1.5MiB ETA:3s]
            progress_regex = re.compile(
                r"\[#[a-f0-9]+\s+([0-9.]+[A-Za-z]+)/([0-9.]+[A-Za-z]+)\(([0-9.]+)%\)"
                r"\s+CN:(\d+)\s+DL:([0-9.]+[A-Za-z]+)(?:\s+ETA:([^\s\]]+))?"
            )

            if self._process.stdout:
                for line in self._process.stdout:
                    if self._is_cancelled:
                        break

                    line_str = line.strip()
                    m = progress_regex.search(line_str)
                    if m:
                        downloaded_str = m.group(1)
                        total_str = m.group(2)
                        pct_str = m.group(3)
                        conns_str = m.group(4)
                        speed_str = m.group(5)
                        eta_str = m.group(6) or "0s"

                        d_bytes = parse_size_to_bytes(downloaded_str)
                        t_bytes = parse_size_to_bytes(total_str)
                        sp_bytes = parse_size_to_bytes(speed_str)
                        pct_val = float(pct_str)
                        conns_val = int(conns_str)

                        # تقدير وقت الإنجاز بالثواني
                        eta_sec = 0
                        if "m" in eta_str and "s" in eta_str:
                            em = re.match(r"(\d+)m(\d+)s", eta_str)
                            if em:
                                eta_sec = int(em.group(1)) * 60 + int(em.group(2))
                        elif "s" in eta_str:
                            es = re.match(r"(\d+)s", eta_str)
                            if es:
                                eta_sec = int(es.group(1))

                        self.progress.emit({
                            "downloaded_bytes": d_bytes,
                            "total_bytes": t_bytes,
                            "speed": sp_bytes,
                            "eta": eta_sec,
                            "percent": pct_val,
                            "filename": target_fn,
                            "status": "downloading",
                            "connections": conns_val,
                        })

            self._process.wait()
            rc = self._process.returncode

            if self._is_cancelled:
                self.finished.emit(self._dest_file_path, False)
                return

            if rc == 0 and os.path.exists(self._dest_file_path):
                final_size = os.path.getsize(self._dest_file_path)

                # إشعار الاكتمال 100%
                self.progress.emit({
                    "downloaded_bytes": final_size,
                    "total_bytes": final_size,
                    "speed": 0,
                    "eta": 0,
                    "percent": 100.0,
                    "filename": target_fn,
                    "status": "completed",
                    "connections": 0,
                })

                # حساب بصمة SHA-256 للأمان
                sha256 = compute_file_sha256(self._dest_file_path)
                if sha256:
                    self.hash_ready.emit(self._dest_file_path, sha256)

                self.finished.emit(self._dest_file_path, True)
            else:
                if not self._is_cancelled:
                    # في حالة فشل السيرفر مع aria2، نحاول عبر المحرك الاحتياطي
                    self._run_fallback_downloader()

        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))
                self.finished.emit(self._dest_file_path, False)

    def _run_fallback_downloader(self) -> None:
        """تشغيل محرك التحميل الاحتياطي Python HttpDownloadWorker."""
        from flexdown.core.http_downloader import HttpDownloadWorker
        worker = HttpDownloadWorker(
            url=self.url,
            output_path=self._dest_file_path or os.path.join(self.output_dir, self.filename or "download_file"),
            proxy=self.proxy,
            headers=self.headers,
        )
        worker.progress.connect(self.progress.emit)
        worker.finished.connect(self.finished.emit)
        worker.error.connect(self.error.emit)
        worker.start()
        worker.wait()
