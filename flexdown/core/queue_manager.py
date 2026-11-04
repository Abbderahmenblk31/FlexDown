"""
FlexDown - Queue Manager Module
وحدة إدارة قائمة التنزيلات والتحكم في عدد التحميلات المتزامنة وبدء وإيقاف واستئناف العمليات.
"""

import os
import time
from typing import Dict, List, Optional, Any, Union
from PyQt6.QtCore import QObject, pyqtSignal, QThread

from flexdown.constants import (
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_DOWNLOAD_DIR,
    PLATFORM_GENERIC,
)
from flexdown.models.download_item import DownloadItem, DownloadStatus
from flexdown.utils.url_utils import detect_platform, is_direct_download
from flexdown.core.ytdlp_backend import YtDlpWorker
from flexdown.core.http_downloader import HttpDownloadWorker
from flexdown.core.turbo_downloader import TurboDownloadWorker


class QueueManager(QObject):
    """
    مدير قائمة التنزيلات (Queue Manager).
    يتولى تنسيق وجدولة التنزيلات المتزامنة، وإسناد العمال المناسبين لكل رابط (yt-dlp أو HTTP direct)،
    ومعالجة الإشارات وتحديث حالة التقدم.
    """
    # إشارات مدير القائمة
    download_started = pyqtSignal(str)          # (item_id)
    download_completed = pyqtSignal(str)        # (item_id)
    download_failed = pyqtSignal(str, str)      # (item_id, error_message)
    queue_updated = pyqtSignal()                # يتم إطلاقها عند أي تغيير في القائمة أو التقدم
    all_completed = pyqtSignal()                # تطلق عند اكتمال كافة التحميلات في القائمة

    def __init__(self, max_concurrent: int = DEFAULT_MAX_CONCURRENT, parent=None):
        super().__init__(parent)
        self._max_concurrent: int = max(1, max_concurrent)
        self._items: Dict[str, DownloadItem] = {}
        self._active_workers: Dict[str, QThread] = {}

    @property
    def max_concurrent(self) -> int:
        """الحد الأقصى لعدد التنزيلات المتزامنة."""
        return self._max_concurrent

    @max_concurrent.setter
    def max_concurrent(self, value: int) -> None:
        """تحديث الحد الأقصى للتنزيلات المتزامنة ومعالجة القائمة."""
        self._max_concurrent = max(1, int(value))
        self._process_queue()

    def set_max_concurrent(self, value: int) -> None:
        """تحديث سعة التحميل المتزامن."""
        self.max_concurrent = value

    def add(self, item: DownloadItem) -> None:
        """
        إضافة عنصر تنزيل جديد إلى القائمة.
        Add a new download item to the queue.
        """
        if not item or not item.id:
            return

        # التأكد من مجلد الحفظ الافتراضي إن لم يُحدد
        if not item.output_dir:
            item.output_dir = str(DEFAULT_DOWNLOAD_DIR)

        self._items[item.id] = item
        self.queue_updated.emit()
        self._process_queue()

    def get_item(self, item_id: str) -> Optional[DownloadItem]:
        """الحصول على عنصر التنزيل بواسطة معرفه الفريد."""
        return self._items.get(item_id)

    def get_all_items(self) -> List[DownloadItem]:
        """إرجاع قائمة بكافة عناصر التنزيل المحفوظة بالترتيب."""
        return list(self._items.values())

    def get_active_count(self) -> int:
        """عدد التنزيلات الجارية حالياً في الخيوط النشطة."""
        return len(self._active_workers)

    def get_queue_count(self) -> int:
        """عدد العناصر التي تنتظر دورها في قائمة الانتظار."""
        return sum(1 for item in self._items.values() if item.status == DownloadStatus.QUEUED)

    def pause(self, item_id: str) -> None:
        """
        إيقاف التنزيل مؤقتاً وحفظ حالة الملف للاستئناف لاحقاً.
        Pause a running or queued download.
        """
        item = self._items.get(item_id)
        if not item:
            return

        # إذا كان قيد التنزيل الفعلي
        if item_id in self._active_workers:
            worker = self._active_workers.pop(item_id)
            if hasattr(worker, "cancel"):
                worker.cancel()

        item.status = DownloadStatus.PAUSED
        item.speed = 0.0
        item.eta = 0

        self.queue_updated.emit()
        self._process_queue()

    def resume(self, item_id: str) -> None:
        """
        استئناف تنزيل متوقف أو فشل أو ملغى وإعادته لطابور الانتظار.
        Resume a paused, cancelled, or failed download.
        """
        item = self._items.get(item_id)
        if not item:
            return

        if item.status in (DownloadStatus.PAUSED, DownloadStatus.FAILED, DownloadStatus.CANCELLED):
            item.status = DownloadStatus.QUEUED
            item.error_message = ""
            self.queue_updated.emit()
            self._process_queue()

    def cancel(self, item_id: str) -> None:
        """
        إلغاء عملية التنزيل الجارية.
        Cancel a download.
        """
        item = self._items.get(item_id)
        if not item:
            return

        if item_id in self._active_workers:
            worker = self._active_workers.pop(item_id)
            if hasattr(worker, "cancel"):
                worker.cancel()

        item.status = DownloadStatus.CANCELLED
        item.speed = 0.0
        item.eta = 0

        self.queue_updated.emit()
        self._process_queue()

    def remove(self, item_id: str) -> None:
        """
        حذف العنصر نهائياً من القائمة مع إيقاف الخيط إذا كان نشطاً.
        Remove item completely from the queue.
        """
        if item_id in self._active_workers:
            worker = self._active_workers.pop(item_id)
            if hasattr(worker, "cancel"):
                worker.cancel()

        if item_id in self._items:
            del self._items[item_id]

        self.queue_updated.emit()
        self._process_queue()

    def pause_all(self) -> None:
        """إيقاف كافة التنزيلات النشطة وقائمة الانتظار مؤقتاً."""
        for item_id in list(self._active_workers.keys()):
            worker = self._active_workers.pop(item_id)
            if hasattr(worker, "cancel"):
                worker.cancel()

        for item in self._items.values():
            if item.status in (DownloadStatus.DOWNLOADING, DownloadStatus.QUEUED, DownloadStatus.ANALYZING):
                item.status = DownloadStatus.PAUSED
                item.speed = 0.0
                item.eta = 0

        self.queue_updated.emit()

    def resume_all(self) -> None:
        """استئناف كافة التنزيلات المتوقفة."""
        for item in self._items.values():
            if item.status == DownloadStatus.PAUSED:
                item.status = DownloadStatus.QUEUED
                item.error_message = ""

        self.queue_updated.emit()
        self._process_queue()

    def cancel_all(self) -> None:
        """إلغاء كافة التنزيلات الجارية والمجدولة في القائمة."""
        for item_id in list(self._active_workers.keys()):
            worker = self._active_workers.pop(item_id)
            if hasattr(worker, "cancel"):
                worker.cancel()

        cancellable = (
            DownloadStatus.DOWNLOADING,
            DownloadStatus.QUEUED,
            DownloadStatus.PAUSED,
            DownloadStatus.ANALYZING,
        )
        for item in self._items.values():
            if item.status in cancellable:
                item.status = DownloadStatus.CANCELLED
                item.speed = 0.0
                item.eta = 0

        self.queue_updated.emit()

    def _process_queue(self) -> None:
        """
        معالجة قائمة الانتظار وبدء عناصر جديدة إذا توفرت مسارات تنزيل فارغة.
        Process the queue and start next downloads if concurrency limit allows.
        """
        available_slots = self._max_concurrent - len(self._active_workers)
        if available_slots <= 0:
            return

        # البحث عن العناصر التالية في حالة الانتظار
        for item in self._items.values():
            if available_slots <= 0:
                break

            if item.status == DownloadStatus.QUEUED and item.id not in self._active_workers:
                self._start_download(item)
                available_slots -= 1

    def _start_download(self, item: DownloadItem) -> None:
        """
        بدء التنزيل الفعلي للعنصر بعد إنشاء الخيط الملائم لنوع الرابط.
        Start actual download worker based on URL type.
        """
        item.status = DownloadStatus.DOWNLOADING
        item.error_message = ""
        self.download_started.emit(item.id)
        self.queue_updated.emit()

        url = item.url
        platform = detect_platform(url)

        # تحديد ما إذا كان الرابط يتطلب yt-dlp أو تنزيل فائق السرعة عبر Turbo متعدد الاتصالات (16 مسار)
        use_ytdlp = False
        if item.format_id in ("turbo", "direct"):
            use_ytdlp = False
        elif platform != PLATFORM_GENERIC:
            use_ytdlp = True
        elif item.audio_only or (item.format_id and item.format_id not in ("turbo", "direct")) or item.convert_to:
            use_ytdlp = True
        elif not is_direct_download(url):
            # الروابط غير المباشرة قد تكون صفحات ويب تدعمها yt-dlp
            use_ytdlp = True

        worker: Union[YtDlpWorker, HttpDownloadWorker, TurboDownloadWorker]
        if use_ytdlp:
            options = {
                'format': item.format_id or None,
                'audio_only': item.audio_only,
                'audio_format': getattr(item, 'audio_format', 'mp3') or 'mp3',
                'audio_quality': getattr(item, 'audio_quality', '320') or '320',
                'convert_to': item.convert_to if not item.audio_only else None,
                'proxy': item.proxy,
                'item_id': item.id,
                'filename': item.filename,
            }
            worker = YtDlpWorker(url=item.url, output_dir=item.output_dir, options=options)
            worker.progress.connect(lambda p, i=item.id: self._on_worker_progress(i, p))
            worker.finished.connect(lambda path, info, i=item.id: self._on_ytdlp_finished(i, path, info))
            worker.error.connect(lambda err, i=item.id: self._on_worker_error(i, err))
        else:
            worker = TurboDownloadWorker(
                url=item.url,
                output_dir=item.output_dir,
                filename=item.filename,
                proxy=item.proxy,
                max_connections=16,
            )
            worker.progress.connect(lambda p, i=item.id: self._on_worker_progress(i, p))
            worker.finished.connect(lambda path, success, i=item.id: self._on_http_finished(i, path, success))
            worker.error.connect(lambda err, i=item.id: self._on_worker_error(i, err))
            worker.hash_ready.connect(lambda path, h, i=item.id: self._on_hash_ready(i, path, h))

        self._active_workers[item.id] = worker
        worker.start()

    def _on_worker_progress(self, item_id: str, progress_data: Dict[str, Any]) -> None:
        """تحديث بيانات التقدم عند وصول إشارة من الخيط العامل."""
        item = self._items.get(item_id)
        if not item:
            return

        status = progress_data.get('status')
        if status == 'converting':
            item.status = DownloadStatus.CONVERTING
            item.speed = 0.0
            item.eta = 0
            self.queue_updated.emit()
            return

        if item.status not in (DownloadStatus.DOWNLOADING, DownloadStatus.CONVERTING):
            return

        item.downloaded_bytes = progress_data.get('downloaded_bytes', item.downloaded_bytes)
        total = progress_data.get('total_bytes', 0)
        if total and total > 0:
            item.filesize = total

        item.speed = progress_data.get('speed', 0.0)
        item.eta = progress_data.get('eta', 0)
        if "connections" in progress_data:
            item.connections = progress_data["connections"]

        filename = progress_data.get('filename')
        if filename and not item.filename:
            item.filename = filename
            item.title = filename

        self.queue_updated.emit()

    def _on_hash_ready(self, item_id: str, file_path: str, sha256_hash: str) -> None:
        """حفظ وتأكيد بصمة SHA-256 للملف عند اكتماله بأمان تام."""
        item = self._items.get(item_id)
        if item:
            item.sha256 = sha256_hash
            self.queue_updated.emit()

    def _on_ytdlp_finished(self, item_id: str, file_path: str, info_dict: Dict[str, Any]) -> None:
        """معالجة نجاح تنزيل yt-dlp."""
        item = self._items.get(item_id)
        if item_id in self._active_workers:
            del self._active_workers[item_id]

        if not item:
            self._check_all_completed()
            self._process_queue()
            return

        if item.status in (DownloadStatus.CANCELLED, DownloadStatus.PAUSED):
            self._check_all_completed()
            self._process_queue()
            return

        item.status = DownloadStatus.COMPLETED
        item.completed_at = time.time()
        item.speed = 0.0
        item.eta = 0

        if file_path:
            item.filename = os.path.basename(file_path)
            item.output_dir = os.path.dirname(file_path)
            if os.path.exists(file_path):
                size = os.path.getsize(file_path)
                item.filesize = size
                item.downloaded_bytes = size

        if info_dict:
            if not item.title and info_dict.get('title'):
                item.title = info_dict.get('title', '')
            if info_dict.get('duration') and item.duration <= 0:
                item.duration = float(info_dict.get('duration', 0.0))
            if info_dict.get('thumbnail') and not item.thumbnail_url:
                item.thumbnail_url = info_dict.get('thumbnail', '')

        self.download_completed.emit(item_id)
        self.queue_updated.emit()
        self._check_all_completed()
        self._process_queue()

    def _on_http_finished(self, item_id: str, file_path: str, success: bool) -> None:
        """معالجة نتيجة خيط التنزيل المباشر HTTP."""
        item = self._items.get(item_id)
        if item_id in self._active_workers:
            del self._active_workers[item_id]

        if not item:
            self._check_all_completed()
            self._process_queue()
            return

        if item.status in (DownloadStatus.CANCELLED, DownloadStatus.PAUSED):
            self._check_all_completed()
            self._process_queue()
            return

        if success:
            item.status = DownloadStatus.COMPLETED
            item.completed_at = time.time()
            item.speed = 0.0
            item.eta = 0

            if file_path:
                item.filename = os.path.basename(file_path)
                item.output_dir = os.path.dirname(file_path)
                if os.path.exists(file_path):
                    size = os.path.getsize(file_path)
                    item.filesize = size
                    item.downloaded_bytes = size

            self.download_completed.emit(item_id)
        else:
            item.status = DownloadStatus.FAILED
            item.speed = 0.0
            item.eta = 0
            if not item.error_message:
                item.error_message = "Download failed or interrupted."
            self.download_failed.emit(item_id, item.error_message)

        self.queue_updated.emit()
        self._check_all_completed()
        self._process_queue()

    def _on_worker_error(self, item_id: str, error_message: str) -> None:
        """معالجة الخطأ الصادر عن خيط التنزيل."""
        item = self._items.get(item_id)
        if item_id in self._active_workers:
            del self._active_workers[item_id]

        if not item:
            self._check_all_completed()
            self._process_queue()
            return

        if item.status in (DownloadStatus.CANCELLED, DownloadStatus.PAUSED):
            self._check_all_completed()
            self._process_queue()
            return

        item.status = DownloadStatus.FAILED
        item.error_message = error_message
        item.speed = 0.0
        item.eta = 0

        self.download_failed.emit(item_id, error_message)
        self.queue_updated.emit()
        self._check_all_completed()
        self._process_queue()

    def _check_all_completed(self) -> None:
        """التحقق مما إذا كانت جميع التنزيلات في القائمة قد اكتملت بنجاح حقيقي."""
        if not self._items:
            return

        has_active = len(self._active_workers) > 0
        has_pending = any(item.status == DownloadStatus.QUEUED for item in self._items.values())

        if not has_active and not has_pending:
            # التحقق من أن جميع العناصر اكتملت بنجاح فعلاً
            all_successful = all(
                item.status == DownloadStatus.COMPLETED for item in self._items.values()
            )
            if all_successful:
                self.all_completed.emit()
