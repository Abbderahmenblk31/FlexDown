"""
FlexDown - Scheduler Module
وحدة جدولة التنزيلات باستخدام مؤقتات QTimer المدمجة في PyQt لتفادي مشاكل الخيوط والتوافق مع واجهة المستخدم.
"""

from datetime import datetime
from typing import Dict, List, Optional, Union, Any
from PyQt6.QtCore import QObject, QTimer, pyqtSignal

from flexdown.models.download_item import DownloadItem, DownloadStatus


class DownloadScheduler(QObject):
    """
    مجدول التنزيلات الذكي (Download Scheduler).
    يقوم بجدولة بدء التنزيل في تاريخ ووقت محددين باستخدام مؤقتات QTimer أحادية الإطلاق (singleShot).
    """
    # إشارة انطلاق مهمة التنزيل عند حلول الوقت المجدول
    job_triggered = pyqtSignal(object)           # يُطلق عنصر التنزيل DownloadItem
    job_scheduled = pyqtSignal(object, str)      # (DownloadItem, iso_time_str)
    job_cancelled = pyqtSignal(str)              # (download_id)

    def __init__(self, parent=None):
        super().__init__(parent)
        # قاموس لتخزين المهام المجدولة: {item_id: {'item': DownloadItem, 'scheduled_time': datetime, 'timer': QTimer}}
        self._scheduled_jobs: Dict[str, Dict[str, Any]] = {}

    def schedule_download(self, item: DownloadItem, target_time: Union[datetime, str]) -> bool:
        """
        جدولة تنزيل عنصر في وقت وتاريخ محددين.
        Schedule a download item for a specific datetime.

        :param item: عنصر التنزيل DownloadItem
        :param target_time: كائن datetime أو نص بتنسيق ISO
        :return: True إذا تمت الجدولة بنجاح
        """
        if not item or not item.id:
            return False

        # تحويل النص إلى كائن datetime إذا كان مدخلاً كنص
        dt: datetime
        if isinstance(target_time, str):
            clean_str = target_time.strip()
            # محاولة قراءة صيغ الوقت الشائعة
            try:
                dt = datetime.fromisoformat(clean_str)
            except ValueError:
                formats = [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M",
                    "%Y/%m/%d %H:%M:%S",
                    "%Y/%m/%d %H:%M",
                    "%d-%m-%Y %H:%M",
                    "%H:%M:%S",
                    "%H:%M",
                ]
                parsed_dt = None
                for fmt in formats:
                    try:
                        p = datetime.strptime(clean_str, fmt)
                        # إذا كان التنسيق للوقت فقط، نستخدم تاريخ اليوم
                        if fmt in ("%H:%M:%S", "%H:%M"):
                            now = datetime.now()
                            p = p.replace(year=now.year, month=now.month, day=now.day)
                        parsed_dt = p
                        break
                    except ValueError:
                        continue

                if not parsed_dt:
                    return False
                dt = parsed_dt
        elif isinstance(target_time, datetime):
            dt = target_time
        else:
            return False

        # حساب الفارق الزمني بالميلي ثانية
        now = datetime.now()
        delta = dt - now
        delay_ms = int(delta.total_seconds() * 1000)

        # إذا كان الوقت المحدد في الماضي، نجعل التأخير فورياً (1 ميلي ثانية)
        if delay_ms < 0:
            delay_ms = 1

        # إلغاء أي جدولة سابقة لنفس العنصر إن وُجدت
        if item.id in self._scheduled_jobs:
            self.cancel_scheduled(item.id)

        # تحديث حالة العنصر ووقت الجدولة
        item.status = DownloadStatus.SCHEDULED
        item.scheduled_time = dt.isoformat()

        # إعداد مؤقت QTimer أحادي الإطلاق
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.timeout.connect(lambda i=item.id: self._on_timer_triggered(i))

        self._scheduled_jobs[item.id] = {
            'item': item,
            'scheduled_time': dt,
            'timer': timer
        }

        # بدء العد التنازلي للمؤقت
        timer.start(delay_ms)

        self.job_scheduled.emit(item, dt.isoformat())
        return True

    def cancel_scheduled(self, download_id: str) -> bool:
        """
        إلغاء جدولة تنزيل محدد قبل حلول موعده.
        Cancel a scheduled job by its download id.
        """
        if download_id not in self._scheduled_jobs:
            return False

        job = self._scheduled_jobs.pop(download_id)
        timer: Optional[QTimer] = job.get('timer')
        if timer and timer.isActive():
            timer.stop()
            timer.deleteLater()

        item: Optional[DownloadItem] = job.get('item')
        if item and item.status == DownloadStatus.SCHEDULED:
            item.status = DownloadStatus.CANCELLED
            item.scheduled_time = None

        self.job_cancelled.emit(download_id)
        return True

    def get_scheduled_jobs(self) -> List[Dict[str, Any]]:
        """
        إرجاع قائمة بكافة المهام المجدولة حالياً مع الوقت المتبقي.
        Get list of all currently scheduled jobs.
        """
        now = datetime.now()
        jobs_list = []

        for item_id, job in self._scheduled_jobs.items():
            dt: datetime = job['scheduled_time']
            remaining = max(0, int((dt - now).total_seconds()))
            jobs_list.append({
                'id': item_id,
                'item': job['item'],
                'scheduled_time': dt,
                'scheduled_time_str': dt.strftime("%Y-%m-%d %H:%M:%S"),
                'remaining_seconds': remaining
            })

        # ترتيب المهام حسب موعد الاستحقاق الأقرب
        jobs_list.sort(key=lambda x: x['scheduled_time'])
        return jobs_list

    def _on_timer_triggered(self, download_id: str) -> None:
        """استجابة المؤقت عند حلول الوقت المحدد لبدء التنزيل."""
        if download_id not in self._scheduled_jobs:
            return

        job = self._scheduled_jobs.pop(download_id)
        item: DownloadItem = job['item']

        # تحديث حالة العنصر لإعادته إلى طابور التنزيل
        item.status = DownloadStatus.QUEUED

        # إطلاق إشارة تحفيز التنزيل لتبدأ العملية عبر مدير القائمة
        self.job_triggered.emit(item)
