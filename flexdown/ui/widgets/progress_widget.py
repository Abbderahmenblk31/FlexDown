"""
شريط التقدم المخصص لتنزيلات فليكس داون (FlexDown Custom Download Progress Bar)
يوفر فئة DownloadProgressBar مع تأثير تدرج لوني وتغيير الألوان بحسب حالة التنزيل
(أخضر للمكتمل، أصفر للمتوقف، أحمر للأخطاء، وتدرج وردي-كحلي للتحميل النشط).
"""

from typing import Union, Optional
from PyQt6.QtWidgets import QProgressBar
from PyQt6.QtCore import Qt

from flexdown.models.download_item import DownloadStatus
from flexdown.utils.file_utils import format_size


class DownloadProgressBar(QProgressBar):
    """
    شريط تقدم مخصص للتنزيلات يدعم الحالات المختلفة وتأثيرات التدرج اللوني.
    Custom Progress Bar supporting different states (Completed, Paused, Error, Downloading)
    with gradient styling and informative progress text.
    """

    # الأنماط والتدرجات اللونية لمختلف الحالات
    _GRADIENT_DOWNLOADING = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e94560, stop:1 #0f3460)"
    _GRADIENT_CONVERTING = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #8e44ad, stop:1 #3498db)"
    _GRADIENT_COMPLETED = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #00b894, stop:1 #00cec9)"
    _GRADIENT_PAUSED = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #e67e22, stop:1 #f1c40f)"
    _GRADIENT_ERROR = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #d63031, stop:1 #e74c3c)"
    _GRADIENT_CANCELLED = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #636e72, stop:1 #b2bec3)"
    _GRADIENT_QUEUED = "qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2c3e50, stop:1 #34495e)"

    def __init__(self, parent=None):
        """تهيئة شريط التقدم بالخصائص الافتراضية والتصميم الداكن"""
        super().__init__(parent)
        self._current_status: DownloadStatus = DownloadStatus.QUEUED
        self._downloaded_bytes: int = 0
        self._total_bytes: int = 0

        self.setRange(0, 100)
        self.setValue(0)
        self.setTextVisible(True)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setMinimumHeight(22)
        self.setMaximumHeight(26)

        # تطبيق النمط الافتراضي
        self._apply_style(self._GRADIENT_DOWNLOADING)

    def _apply_style(self, chunk_gradient: str) -> None:
        """
        تطبيق نمط QSS مع حواف مستديرة وتدرج لوني للمحتوى.
        Apply QSS styling with rounded corners and gradient chunk.
        """
        style = f"""
        QProgressBar {{
            background-color: #111526;
            color: #ffffff;
            border: 1px solid #23314f;
            border-radius: 6px;
            text-align: center;
            font-size: 11px;
            font-weight: bold;
        }}
        QProgressBar::chunk {{
            background: {chunk_gradient};
            border-radius: 5px;
        }}
        """
        self.setStyleSheet(style)

    def setDownloadState(self, status: Union[DownloadStatus, str]) -> None:
        """
        تحديث لون شريط التقدم بحسب حالة التنزيل.
        Update bar color based on download state.

        :param status: حالة التنزيل (DownloadStatus enum أو نص)
        """
        if isinstance(status, str):
            status = DownloadStatus.from_str(status)

        self._current_status = status

        if status == DownloadStatus.COMPLETED:
            self._apply_style(self._GRADIENT_COMPLETED)
        elif status == DownloadStatus.CONVERTING:
            self._apply_style(self._GRADIENT_CONVERTING)
        elif status == DownloadStatus.PAUSED:
            self._apply_style(self._GRADIENT_PAUSED)
        elif status in (DownloadStatus.FAILED, DownloadStatus.CANCELLED):
            if status == DownloadStatus.FAILED:
                self._apply_style(self._GRADIENT_ERROR)
            else:
                self._apply_style(self._GRADIENT_CANCELLED)
        elif status == DownloadStatus.QUEUED:
            self._apply_style(self._GRADIENT_QUEUED)
        else:
            # DOWNLOADING, ANALYZING, ENCRYPTING
            self._apply_style(self._GRADIENT_DOWNLOADING)

        self._update_format_text()

    def update_progress(
        self,
        downloaded_bytes: int,
        total_bytes: int,
        status: Optional[Union[DownloadStatus, str]] = None,
    ) -> None:
        """
        تحديث نسبة التقدم والنص المعروض بالبايتات والحجم الإجمالي.
        Update progress percentage, byte counts, and display text.
        """
        self._downloaded_bytes = max(0, downloaded_bytes)
        self._total_bytes = max(0, total_bytes)

        if status is not None:
            self.setDownloadState(status)

        if self._current_status == DownloadStatus.CONVERTING:
            self.setValue(99)
        elif self._total_bytes > 0:
            percentage = int((self._downloaded_bytes / self._total_bytes) * 100)
            percentage = min(100, max(0, percentage))
            self.setValue(percentage)
        elif self._current_status == DownloadStatus.COMPLETED:
            self.setValue(100)
        else:
            self.setValue(0)

        self._update_format_text()

    def _update_format_text(self) -> None:
        """
        بناء النص المنسق لعرض النسبة المئوية والحجم المحمل / الإجمالي.
        Format progress text to show percentage and downloaded/total size.
        """
        dl_str = format_size(self._downloaded_bytes)

        if self._current_status == DownloadStatus.COMPLETED:
            tot_str = format_size(self._total_bytes or self._downloaded_bytes)
            self.setFormat(f"100% ({tot_str})")
        elif self._current_status == DownloadStatus.CONVERTING:
            self.setFormat("Converting (FFmpeg)...")
        elif self._current_status == DownloadStatus.FAILED:
            self.setFormat("Failed")
        elif self._current_status == DownloadStatus.CANCELLED:
            self.setFormat("Cancelled")
        elif self._current_status == DownloadStatus.PAUSED:
            if self._total_bytes > 0:
                pct = self.value()
                tot_str = format_size(self._total_bytes)
                self.setFormat(f"{pct}% ({dl_str} / {tot_str}) - Paused")
            else:
                self.setFormat(f"Paused ({dl_str})")
        elif self._total_bytes > 0:
            pct = self.value()
            tot_str = format_size(self._total_bytes)
            self.setFormat(f"{pct}% ({dl_str} / {tot_str})")
        elif self._downloaded_bytes > 0:
            self.setFormat(f"{dl_str}")
        else:
            if self._current_status == DownloadStatus.QUEUED:
                self.setFormat("Queued")
            elif self._current_status == DownloadStatus.ANALYZING:
                self.setFormat("Analyzing...")
            else:
                self.setFormat("0%")
