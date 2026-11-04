"""
نموذج عنصر التنزيل وحالاته (Download Item & Status Models)
يحتوي هذا الملف على تعداد حالات التنزيل، وأنواع الوسائط، وفئة DownloadItem
التي تمثل عنصراً فردياً في قائمة التنزيلات مع كامل تفاصيل تقدمه وحالته وإعداداته.
"""

import time
import uuid
from enum import Enum
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, Dict, Any

from flexdown.utils.file_utils import (
    format_size,
    format_speed,
    format_duration,
    sanitize_filename,
)


class MediaType(str, Enum):
    """
    أنواع الوسائط والملفات المدعومة
    Supported media and file types.
    """
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"
    IMAGE = "IMAGE"
    DOCUMENT = "DOCUMENT"
    OTHER = "OTHER"

    @classmethod
    def from_str(cls, value: str) -> "MediaType":
        """تحويل نص إلى نوع وسائط بأمان"""
        try:
            return cls(value.upper())
        except (ValueError, AttributeError):
            return cls.OTHER

    @property
    def label_ar(self) -> str:
        """التسمية باللغة العربية"""
        labels = {
            MediaType.VIDEO: "فيديو",
            MediaType.AUDIO: "صوت",
            MediaType.IMAGE: "صورة",
            MediaType.DOCUMENT: "مستند",
            MediaType.OTHER: "أخرى",
        }
        return labels.get(self, "أخرى")


class DownloadStatus(str, Enum):
    """
    حالات التنزيل الممكنة
    Download states lifecycle.
    """
    QUEUED = "QUEUED"          # في طابور الانتظار
    ANALYZING = "ANALYZING"    # جاري فحص الرابط واستخراج البيانات
    DOWNLOADING = "DOWNLOADING"  # جاري التنزيل الفعلي
    PAUSED = "PAUSED"          # متوقف مؤقتاً
    CONVERTING = "CONVERTING"  # جاري تحويل الصيغة عبر FFmpeg
    ENCRYPTING = "ENCRYPTING"  # جاري تشفير الملف
    COMPLETED = "COMPLETED"    # اكتمل التنزيل بنجاح
    FAILED = "FAILED"          # فشل التنزيل
    CANCELLED = "CANCELLED"    # تم إلغاء التنزيل
    SCHEDULED = "SCHEDULED"    # مجدول لوقت لاحق

    @classmethod
    def from_str(cls, value: str) -> "DownloadStatus":
        """تحويل نص إلى حالة تنزيل بأمان"""
        try:
            return cls(value.upper())
        except (ValueError, AttributeError):
            return cls.QUEUED

    @property
    def is_active(self) -> bool:
        """هل التنزيل في حالة نشطة حالياً"""
        return self in (
            DownloadStatus.ANALYZING,
            DownloadStatus.DOWNLOADING,
            DownloadStatus.CONVERTING,
            DownloadStatus.ENCRYPTING,
        )

    @property
    def is_finished(self) -> bool:
        """هل انتهت دورة حياة التنزيل (نجاح، فشل، أو إلغاء)"""
        return self in (
            DownloadStatus.COMPLETED,
            DownloadStatus.FAILED,
            DownloadStatus.CANCELLED,
        )

    @property
    def label_ar(self) -> str:
        """اسم الحالة باللغة العربية"""
        labels = {
            DownloadStatus.QUEUED: "في الانتظار",
            DownloadStatus.ANALYZING: "جاري الفحص...",
            DownloadStatus.DOWNLOADING: "جاري التنزيل...",
            DownloadStatus.PAUSED: "متوقف مؤقتاً",
            DownloadStatus.CONVERTING: "جاري التحويل...",
            DownloadStatus.ENCRYPTING: "جاري التشفير...",
            DownloadStatus.COMPLETED: "مكتمل",
            DownloadStatus.FAILED: "فشل التنزيل",
            DownloadStatus.CANCELLED: "ملغى",
            DownloadStatus.SCHEDULED: "مجدول",
        }
        return labels.get(self, self.value)

    @property
    def label_en(self) -> str:
        """اسم الحالة باللغة الإنجليزية"""
        labels = {
            DownloadStatus.QUEUED: "Queued",
            DownloadStatus.ANALYZING: "Analyzing...",
            DownloadStatus.DOWNLOADING: "Downloading...",
            DownloadStatus.PAUSED: "Paused",
            DownloadStatus.CONVERTING: "Converting...",
            DownloadStatus.ENCRYPTING: "Encrypting...",
            DownloadStatus.COMPLETED: "Completed",
            DownloadStatus.FAILED: "Failed",
            DownloadStatus.CANCELLED: "Cancelled",
            DownloadStatus.SCHEDULED: "Scheduled",
        }
        return labels.get(self, self.value)


@dataclass
class DownloadItem:
    """
    فئة تمثل عنصر تنزيل فردي بكافة خصائصه ومؤشرات تقدمه وإعداداته.
    Represents an individual download item in the FlexDown manager.
    """
    # المعرف الفريد والروابط الأساسية
    id: str = field(default_factory=lambda: uuid.uuid4().hex)
    url: str = ""
    output_dir: str = ""
    filename: str = ""
    title: str = ""
    extension: str = ""
    filesize: int = 0
    media_type: MediaType = MediaType.OTHER

    # بيانات المعاينة والوسائط
    thumbnail_url: str = ""
    duration: float = 0.0  # المدة بالثواني للمقاطع الصوتية والمرئية

    # حالة التقدم والتنزيل
    status: DownloadStatus = DownloadStatus.QUEUED
    downloaded_bytes: int = 0
    speed: float = 0.0     # سرعة التنزيل بالبايت في الثانية
    eta: int = 0           # الوقت التقديري المتبقي بالثواني
    error_message: str = ""

    format_id: str = ""              # معرف الجودة أو التنسيق من yt-dlp
    quality_label: str = ""          # تسمية الجودة المختارة بوضوح (مثل '1080p' أو '320 kbps')
    audio_only: bool = False         # استخراج الصوت فقط
    audio_format: str = "mp3"        # صيغة الصوت عند استخراج الصوت فقط (mp3, m4a)
    audio_quality: str = "320"       # جودة الصوت بالكيلوبت/ث (128, 192, 256, 320)
    convert_to: Optional[str] = None  # تحويل إلى صيغة معينة (مثل 'mp3', 'mp4')
    encrypt: bool = False            # تشفير الملف بعد التنزيل
    proxy: Optional[str] = None      # بروكسي مخصص لهذا التنزيل

    # الجدولة والتوقيت
    scheduled_time: Optional[str] = None  # وقت الجدولة (تنسيق ISO أو نص)
    created_at: float = field(default_factory=time.time)
    completed_at: Optional[float] = None

    # التسريع متعدد الاتصالات والأمان
    connections: int = 0                  # عدد الاتصالات المتزامنة النشطة (حتى 16 اتصال)
    sha256: str = ""                      # بصمة التجزئة SHA-256 للتحقق من سلامة وأمان الملف

    def __post_init__(self):
        """التحقق وضبط القيم بعد التهيئة"""
        if isinstance(self.status, str):
            self.status = DownloadStatus.from_str(self.status)
        if isinstance(self.media_type, str):
            self.media_type = MediaType.from_str(self.media_type)
        if not self.title and self.filename:
            self.title = self.filename
        if not self.filename and self.title:
            self.filename = sanitize_filename(self.title)

    # ==========================================
    # الخصائص المحسوبة (Computed Properties)
    # ==========================================

    @property
    def progress_percent(self) -> float:
        """
        نسبة التقدم المئوية (من 0.0 إلى 100.0).
        Percentage progress (0.0 to 100.0).
        """
        if self.status == DownloadStatus.COMPLETED:
            return 100.0

        if self.filesize > 0 and self.downloaded_bytes >= 0:
            pct = (float(self.downloaded_bytes) / float(self.filesize)) * 100.0
            return min(100.0, max(0.0, round(pct, 2)))

        return 0.0

    @property
    def speed_str(self) -> str:
        """نص سرعة التنزيل منسقاً (مثل '2.34 MB/s') مع مؤشر القنوات المتزامنة"""
        if not self.status.is_active or self.status == DownloadStatus.PAUSED:
            return "0 B/s"
        base_spd = format_speed(self.speed)
        if self.connections > 1:
            return f"{base_spd} (⚡{self.connections}x)"
        return base_spd

    @property
    def size_str(self) -> str:
        """نص الحجم الإجمالي منسقاً (مثل '520.10 MB')"""
        if self.filesize <= 0:
            return "--"
        return format_size(self.filesize)

    @property
    def downloaded_str(self) -> str:
        """نص الحجم المنزّل حالياً منسقاً"""
        return format_size(self.downloaded_bytes)

    @property
    def eta_str(self) -> str:
        """نص الوقت التقديري المتبقي (مثل '02:45' أو '--:--')"""
        if not self.status.is_active or self.eta <= 0:
            return "--:--"
        return format_duration(self.eta)

    @property
    def duration_str(self) -> str:
        """نص مدة مقطع الفيديو أو الصوت (مثل '12:30')"""
        if self.duration <= 0:
            return "--:--"
        return format_duration(self.duration)

    @property
    def status_display(self) -> str:
        """نص حالة التنزيل المعروض للمستخدم باللغة المناسبة"""
        return self.status.label_ar

    @property
    def status_display_en(self) -> str:
        """نص حالة التنزيل المعروض بالإنجليزية"""
        return self.status.label_en

    @property
    def full_path(self) -> Path:
        """المسار الكامل للملف الناتج على القرص"""
        dir_path = Path(self.output_dir) if self.output_dir else Path.cwd()
        name = self.filename if self.filename else f"{self.id}.{self.extension or 'bin'}"
        return dir_path / name

    # ==========================================
    # التحويل والتسلسل (Serialization)
    # ==========================================

    def to_dict(self) -> Dict[str, Any]:
        """
        تحويل عنصر التنزيل إلى قاموس مناسب للحفظ كـ JSON.
        Convert DownloadItem to JSON-serializable dictionary.
        """
        return {
            "id": self.id,
            "url": self.url,
            "output_dir": str(self.output_dir),
            "filename": self.filename,
            "title": self.title,
            "extension": self.extension,
            "filesize": int(self.filesize),
            "media_type": self.media_type.value,
            "thumbnail_url": self.thumbnail_url,
            "duration": float(self.duration),
            "status": self.status.value,
            "downloaded_bytes": int(self.downloaded_bytes),
            "speed": float(self.speed),
            "eta": int(self.eta),
            "error_message": self.error_message,
            "format_id": self.format_id,
            "quality_label": self.quality_label,
            "audio_only": bool(self.audio_only),
            "audio_format": self.audio_format,
            "audio_quality": self.audio_quality,
            "convert_to": self.convert_to,
            "encrypt": bool(self.encrypt),
            "proxy": self.proxy,
            "scheduled_time": self.scheduled_time,
            "created_at": float(self.created_at),
            "completed_at": float(self.completed_at) if self.completed_at is not None else None,
            "connections": int(self.connections),
            "sha256": str(self.sha256),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "DownloadItem":
        """
        إنشاء عنصر تنزيل من قاموس بيانات.
        Create a DownloadItem instance from dictionary.
        """
        return cls(
            id=str(data.get("id", uuid.uuid4().hex)),
            url=str(data.get("url", "")),
            output_dir=str(data.get("output_dir", "")),
            filename=str(data.get("filename", "")),
            title=str(data.get("title", "")),
            extension=str(data.get("extension", "")),
            filesize=int(data.get("filesize", 0)),
            media_type=MediaType.from_str(data.get("media_type", "OTHER")),
            thumbnail_url=str(data.get("thumbnail_url", "")),
            duration=float(data.get("duration", 0.0)),
            status=DownloadStatus.from_str(data.get("status", "QUEUED")),
            downloaded_bytes=int(data.get("downloaded_bytes", 0)),
            speed=float(data.get("speed", 0.0)),
            eta=int(data.get("eta", 0)),
            error_message=str(data.get("error_message", "")),
            format_id=str(data.get("format_id", "")),
            quality_label=str(data.get("quality_label", "")),
            audio_only=bool(data.get("audio_only", False)),
            audio_format=str(data.get("audio_format", "mp3")),
            audio_quality=str(data.get("audio_quality", "320")),
            convert_to=data.get("convert_to"),
            encrypt=bool(data.get("encrypt", False)),
            proxy=data.get("proxy"),
            scheduled_time=data.get("scheduled_time"),
            created_at=float(data.get("created_at", time.time())),
            completed_at=float(data["completed_at"]) if data.get("completed_at") is not None else None,
            connections=int(data.get("connections", 0)),
            sha256=str(data.get("sha256", "")),
        )
