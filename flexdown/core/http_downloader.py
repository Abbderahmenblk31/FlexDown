"""
FlexDown - HTTP Downloader Module
وحدة تنزيل الروابط المباشرة عبر بروتوكولات HTTP/HTTPS مع دعم استئناف التحميل
(Range Header) والبروكسي وحساب السرعة اللحظية.
"""

import os
import re
import time
import urllib.parse
from typing import Optional, Dict
from PyQt6.QtCore import QThread, pyqtSignal
import requests


class HttpDownloadWorker(QThread):
    """
    خيط تنزيل الملفات المباشرة عبر بروتوكول HTTP/HTTPS.
    يدعم استئناف التحميل عبر HTTP Range وحساب السرعة في الوقت الفعلي والبروكسي والإلغاء.
    """
    CHUNK_SIZE: int = 8192

    # إشارات الخيط
    # {'downloaded_bytes', 'total_bytes', 'speed', 'eta', 'percent', 'filename', 'status'}
    progress = pyqtSignal(dict)
    finished = pyqtSignal(str, bool)  # (file_path, success)
    error = pyqtSignal(str)          # (error_message)

    def __init__(
        self,
        url: str,
        output_path: str,
        proxy: Optional[str] = None,
        headers: Optional[Dict[str, str]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.url = url.strip()
        self.output_path = output_path
        self.proxy = proxy.strip() if proxy else None
        self.headers = headers or {}
        self._is_cancelled = False

    def cancel(self) -> None:
        """إلغاء أو إيقاف التنزيل الجاري."""
        self._is_cancelled = True

    def _resolve_dest_path(self, response: requests.Response) -> str:
        """تحديد المسار النهائي واسم الملف من الترويسات أو الرابط."""
        # إذا كان output_path مجلداً قائماً أو مسار مجلد
        if os.path.isdir(self.output_path) or not os.path.splitext(self.output_path)[1]:
            filename = None

            # محاولة استخراج اسم الملف من ترويسة Content-Disposition
            cd = response.headers.get("content-disposition")
            if cd:
                fname_star = re.search(r"filename\*=UTF-8''([^;]+)", cd, re.IGNORECASE)
                if fname_star:
                    filename = urllib.parse.unquote(fname_star.group(1))
                else:
                    fname_match = re.search(r'filename=["\']?([^"\';]+)["\']?', cd, re.IGNORECASE)
                    if fname_match:
                        filename = fname_match.group(1).strip()

            # إذا لم يتوفر، نستخرجه من مسار الرابط
            if not filename:
                parsed = urllib.parse.urlparse(self.url)
                base = os.path.basename(parsed.path)
                if base:
                    filename = urllib.parse.unquote(base)

            if not filename:
                filename = "flexdown_download"

            # تنظيف المحارف غير المسموح بها في أنظمة ويندوز
            filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
            os.makedirs(self.output_path, exist_ok=True)
            return os.path.join(self.output_path, filename)
        else:
            # إذا كان مسار ملف كامل
            parent_dir = os.path.dirname(self.output_path)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            return self.output_path

    def run(self) -> None:
        """بدء عملية التنزيل المباشر مع دعم الاستئناف وتحديثات التقدم."""
        dest_file = ""
        part_file = ""
        try:
            # إعداد إعدادات الاتصال والبروكسي
            proxies = None
            if self.proxy:
                proxies = {
                    "http": self.proxy,
                    "https": self.proxy
                }

            req_headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/124.0.0.0 Safari/537.36 FlexDown/1.0.0"
                ),
                **self.headers
            }

            # خطوة أولية: الحصول على معلومات الرابط واسم الملف
            with requests.get(
                self.url,
                headers=req_headers,
                proxies=proxies,
                stream=True,
                allow_redirects=True,
                timeout=20
            ) as init_resp:
                init_resp.raise_for_status()
                dest_file = self._resolve_dest_path(init_resp)
                part_file = dest_file + ".part"

            if self._is_cancelled:
                self.finished.emit(dest_file, False)
                return

            # فحص حجم الملف الجزئي الحالي لدعم الاستئناف (Resume)
            existing_bytes = 0
            if os.path.exists(part_file):
                existing_bytes = os.path.getsize(part_file)

            download_headers = dict(req_headers)
            if existing_bytes > 0:
                download_headers["Range"] = f"bytes={existing_bytes}-"

            # فتح الاتصال الفعلي لتنزيل التدفق
            with requests.get(
                self.url,
                headers=download_headers,
                proxies=proxies,
                stream=True,
                allow_redirects=True,
                timeout=30
            ) as response:

                # فحص دعم الاستئناف من الخادم
                if response.status_code == 206:
                    # الخادم يدعم الاستئناف بنجاح (Partial Content)
                    mode = "ab"
                    content_range = response.headers.get("content-range", "")
                    total_bytes = 0
                    if content_range and "/" in content_range:
                        try:
                            total_bytes = int(content_range.split("/")[-1])
                        except ValueError:
                            total_bytes = existing_bytes + int(response.headers.get("content-length", 0))
                    else:
                        total_bytes = existing_bytes + int(response.headers.get("content-length", 0))
                    downloaded_bytes = existing_bytes

                elif response.status_code == 200:
                    # الخادم لا يدعم الاستئناف أو تم الطلب من البداية
                    mode = "wb"
                    existing_bytes = 0
                    downloaded_bytes = 0
                    total_bytes = int(response.headers.get("content-length", 0))

                elif response.status_code == 416:
                    # 416 Range Not Satisfiable: الملف قد يكون مكتملاً بالفعل
                    if os.path.exists(part_file) and existing_bytes > 0:
                        if os.path.exists(dest_file):
                            os.remove(dest_file)
                        os.rename(part_file, dest_file)
                        self.progress.emit({
                            'downloaded_bytes': existing_bytes,
                            'total_bytes': existing_bytes,
                            'speed': 0,
                            'eta': 0,
                            'percent': 100.0,
                            'filename': os.path.basename(dest_file),
                            'status': 'completed'
                        })
                        self.finished.emit(dest_file, True)
                        return
                    else:
                        response.raise_for_status()
                else:
                    response.raise_for_status()

                # متغيرات حساب السرعة في الوقت الفعلي
                last_time = time.time()
                bytes_since_last = 0
                speed = 0.0

                # كتابة البيانات المقروءة على دفعات بحجم CHUNK_SIZE
                with open(part_file, mode) as f:
                    for chunk in response.iter_content(chunk_size=self.CHUNK_SIZE):
                        if self._is_cancelled:
                            # تم الإلغاء، يتم إغلاق الملف والاحتفاظ بملف .part للاستئناف
                            self.finished.emit(dest_file, False)
                            return

                        if chunk:
                            f.write(chunk)
                            chunk_len = len(chunk)
                            downloaded_bytes += chunk_len
                            bytes_since_last += chunk_len

                            # حساب السرعة كل 250 ميلي ثانية لتفادي استهلاك المعالج
                            now = time.time()
                            delta = now - last_time
                            if delta >= 0.25:
                                speed = bytes_since_last / delta
                                bytes_since_last = 0
                                last_time = now

                                eta = int((total_bytes - downloaded_bytes) /
                                          speed) if speed > 0 and total_bytes > downloaded_bytes else 0
                                percent = round((downloaded_bytes / total_bytes) * 100.0, 2) if total_bytes > 0 else 0.0

                                self.progress.emit({
                                    'downloaded_bytes': downloaded_bytes,
                                    'total_bytes': total_bytes,
                                    'speed': speed,
                                    'eta': eta,
                                    'percent': percent,
                                    'filename': os.path.basename(dest_file),
                                    'status': 'downloading'
                                })

            # اكتمال التنزيل بنجاح - إعادة تسمية الملف من .part إلى الملف النهائي
            if not self._is_cancelled:
                if os.path.exists(dest_file):
                    os.remove(dest_file)
                os.rename(part_file, dest_file)

                final_size = os.path.getsize(dest_file)
                self.progress.emit({
                    'downloaded_bytes': final_size,
                    'total_bytes': final_size,
                    'speed': 0,
                    'eta': 0,
                    'percent': 100.0,
                    'filename': os.path.basename(dest_file),
                    'status': 'completed'
                })
                self.finished.emit(dest_file, True)

        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))
                self.finished.emit(dest_file if dest_file else self.output_path, False)
