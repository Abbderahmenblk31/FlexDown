"""
إدارة وسجل التنزيلات (Download History & State Persistence)
يتولى هذا الملف حفظ واسترجاع سجل التنزيلات السابقة إلى ملف JSON في ~/.flexdown/history.json،
مع دعم الاستعلام، والحذف، واحترام إعداد الخصوصية (no_history)، وحماية العمليات المتزامنة.
"""

import os
import json
import tempfile
import threading
from pathlib import Path
from typing import List, Optional, Dict, Any, Union

from flexdown.constants import HISTORY_FILE
from flexdown.models.download_item import DownloadItem, DownloadStatus, MediaType
from flexdown.utils.config import Config, get_config


class DownloadHistory:
    """
    فئة إدارة سجل التنزيلات الدائم.
    Persists and manages download history records in a JSON file.
    """

    def __init__(
        self,
        history_file: Optional[Path] = None,
        config: Optional[Config] = None
    ):
        """
        تهيئة سجل التنزيلات.

        :param history_file: مسار مخصص لملف السجل، أو الافتراضي ~/.flexdown/history.json
        :param config: مثيل مدير الإعدادات للتحقق من خيار no_history
        """
        self._lock = threading.RLock()
        self.history_file: Path = Path(history_file) if history_file else HISTORY_FILE
        self.config: Config = config if config is not None else get_config()
        self._records: List[DownloadItem] = []
        self._records_map: Dict[str, DownloadItem] = {}

        # تحميل السجل المحفوظ
        self.load_history()

    def load_history(self) -> List[DownloadItem]:
        """
        تحميل السجل من ملف JSON إلى الذاكرة.
        Load history records from JSON file.
        """
        with self._lock:
            self._records.clear()
            self._records_map.clear()

            # إذا كان خيار عدم حفظ السجل مفعلاً، لا نقرأ الملف
            if self.config.no_history:
                return []

            if not self.history_file.exists():
                return []

            try:
                with open(self.history_file, "r", encoding="utf-8") as f:
                    raw_data = json.load(f)

                if isinstance(raw_data, list):
                    for entry in raw_data:
                        if isinstance(entry, dict):
                            try:
                                item = DownloadItem.from_dict(entry)
                                self._records.append(item)
                                self._records_map[item.id] = item
                            except Exception:
                                continue
            except Exception:
                # في حال تعذر القراءة أو تلف البيانات
                self._records = []
                self._records_map = {}

            return list(self._records)

    def save_history(self) -> bool:
        """
        حفظ عناصر السجل في ملف JSON بشكل ذري وآمن.
        Save history records to JSON file atomically.
        """
        with self._lock:
            # احترام إعداد خصوصية السجل
            if self.config.no_history:
                # إذا كانت الخصوصية مفعلة، نحذف الملف لضمان عدم بقاء أي أثر
                if self.history_file.exists():
                    try:
                        self.history_file.unlink(missing_ok=True)
                    except Exception:
                        pass
                return True

            try:
                parent_dir = self.history_file.parent
                parent_dir.mkdir(parents=True, exist_ok=True)

                data_to_save = [item.to_dict() for item in self._records]

                # حفظ آمن عبر ملف مؤقت
                temp_file = tempfile.NamedTemporaryFile(
                    mode="w",
                    dir=parent_dir,
                    encoding="utf-8",
                    delete=False
                )
                with temp_file as f:
                    json.dump(data_to_save, f, indent=2, ensure_ascii=False)

                os.replace(temp_file.name, self.history_file)
                return True
            except Exception:
                try:
                    with open(self.history_file, "w", encoding="utf-8") as f:
                        json.dump([item.to_dict() for item in self._records], f, indent=2, ensure_ascii=False)
                    return True
                except Exception:
                    return False

    def add_record(self, item: Union[DownloadItem, Dict[str, Any]]) -> None:
        """
        إضافة أو تحديث عنصر في السجل مع الحفظ في الملف.
        Add or update a record in history.

        :param item: كائن DownloadItem أو قاموس بيانات
        """
        with self._lock:
            # التحقق من إعداد عدم حفظ السجل
            if self.config.no_history:
                return

            if isinstance(item, dict):
                item_obj = DownloadItem.from_dict(item)
            else:
                item_obj = item

            # إذا كان العنصر موجوداً مسبقاً بنفس المعرف، نقوم بتحديثه
            if item_obj.id in self._records_map:
                existing_item = self._records_map[item_obj.id]
                idx = self._records.index(existing_item)
                self._records[idx] = item_obj
                self._records_map[item_obj.id] = item_obj
            else:
                # إضافة العنصر في بداية القائمة (الأحدث أولاً)
                self._records.insert(0, item_obj)
                self._records_map[item_obj.id] = item_obj

            self.save_history()

    def get_history(
        self,
        limit: Optional[int] = None,
        status: Optional[Union[str, DownloadStatus]] = None,
        media_type: Optional[Union[str, MediaType]] = None
    ) -> List[DownloadItem]:
        """
        استرجاع قائمة سجل التنزيلات مع إمكانية التصفية وتحديد الحد الأقصى.
        Retrieve history records with optional filters.

        :param limit: الحد الأقصى لعدد السجلات
        :param status: تصفية حسب حالة التنزيل
        :param media_type: تصفية حسب نوع الوسائط
        :return: قائمة بعناصر التنزيل
        """
        with self._lock:
            if self.config.no_history:
                return []

            results = list(self._records)

            # تصفية حسب الحالة إن حددت
            if status is not None:
                status_enum = status if isinstance(status, DownloadStatus) else DownloadStatus.from_str(str(status))
                results = [item for item in results if item.status == status_enum]

            # تصفية حسب نوع الوسائط إن حدد
            if media_type is not None:
                media_enum = media_type if isinstance(media_type, MediaType) else MediaType.from_str(str(media_type))
                results = [item for item in results if item.media_type == media_enum]

            if limit is not None and limit > 0:
                results = results[:limit]

            return results

    def get_record(self, item_id: str) -> Optional[DownloadItem]:
        """
        استرجاع عنصر محدد بواسطة معرفه الفريد.
        Get a specific record by ID.
        """
        with self._lock:
            return self._records_map.get(item_id)

    def remove_record(self, item_id: str) -> bool:
        """
        حذف عنصر محدد من السجل والملف.
        Remove a specific record by ID.

        :param item_id: المعرف الفريد للتنزيل
        :return: True إذا تم الحذف بنجاح، وإلا False
        """
        with self._lock:
            item = self._records_map.pop(item_id, None)
            if item is not None:
                if item in self._records:
                    self._records.remove(item)
                self.save_history()
                return True
            return False

    def update_record(self, item: DownloadItem) -> bool:
        """
        تحديث بيانات عنصر موجود مسبقاً في السجل.
        Update an existing record in history.
        """
        with self._lock:
            if item.id in self._records_map:
                old = self._records_map[item.id]
                idx = self._records.index(old)
                self._records[idx] = item
                self._records_map[item.id] = item
                self.save_history()
                return True
            return False

    def clear_history(self) -> bool:
        """
        مسح جميع عناصر السجل وحذف الملف أو تصفيره.
        Clear all history records from memory and disk.
        """
        with self._lock:
            self._records.clear()
            self._records_map.clear()

            try:
                if self.history_file.exists():
                    self.history_file.unlink(missing_ok=True)
                return True
            except Exception:
                # محاولة كتابة مصفوفة فارغة كبديل
                try:
                    with open(self.history_file, "w", encoding="utf-8") as f:
                        f.write("[]")
                    return True
                except Exception:
                    return False

    def __len__(self) -> int:
        with self._lock:
            return len(self._records)
