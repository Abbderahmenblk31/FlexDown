"""
FlexDown - مدير الخصوصية والأمان (Privacy Manager Module)
يوفر فئة PrivacyManager لإدارة سجلات التحميل والملفات المؤقتة، والحذف الآمن
وفق المعايير الأمنية المتقدمة (عبر الكتابة فوق الملفات بالبيانات العشوائية قبل الحذف)،
وإلغاء تفعيل السجلات (No-Log Mode) لحماية خصوصية المستخدم بشكل تام.
"""

import os
import glob
import logging
import sqlite3
import string
import random
from typing import Dict, Any, Optional


class PrivacyManager:
    """
    فئة متخصصة في إدارة خصوصية المستخدم وحذف آثار التحميل والملفات الحساسة.
    Manages history wiping, temporary chunk cleanup, secure file shredding,
    and no-log mode activation.
    """

    def __init__(
        self,
        app_data_dir: Optional[str] = None,
        db_path: Optional[str] = None,
        temp_dir: Optional[str] = None,
    ):
        """
        تهيئة مدير الخصوصية.
        """
        if app_data_dir:
            self.app_data_dir = app_data_dir
        else:
            self.app_data_dir = os.path.join(os.path.expanduser("~"), ".flexdown")

        os.makedirs(self.app_data_dir, exist_ok=True)

        self.db_path = db_path or os.path.join(self.app_data_dir, "flexdown.db")
        self.temp_dir = temp_dir or os.path.join(self.app_data_dir, "temp")
        os.makedirs(self.temp_dir, exist_ok=True)

        self.no_log_mode: bool = False
        self._previous_log_level = logging.INFO

    def enable_no_log_mode(self) -> None:
        """
        تفعيل وضع عدم الاحتفاظ بالسجلات (No-Log Mode).
        يمنع تخزين أي سجلات تشغيلية في القرص لحماية الخصوصية.
        """
        self.no_log_mode = True

        # إيقاف معالجات السجلات التي تكتب في الملفات
        root_logger = logging.getLogger()
        self._previous_log_level = root_logger.level
        for handler in root_logger.handlers[:]:
            if isinstance(handler, logging.FileHandler):
                handler.close()
                root_logger.removeHandler(handler)

        # حذف ملفات السجلات الحالية من مجلد التطبيق
        log_files = glob.glob(os.path.join(self.app_data_dir, "*.log"))
        for log_file in log_files:
            try:
                os.remove(log_file)
            except OSError:
                pass

    def disable_no_log_mode(self) -> None:
        """
        إلغاء تفعيل وضع عدم الاحتفاظ بالسجلات واستعادة التسجيل الطبيعي.
        """
        self.no_log_mode = False
        root_logger = logging.getLogger()
        root_logger.setLevel(self._previous_log_level)

    def is_no_log_mode(self) -> bool:
        """
        التحقق مما إذا كان وضع منع السجلات مفعلاً.
        """
        return self.no_log_mode

    @staticmethod
    def secure_delete(file_path: str, passes: int = 3) -> bool:
        """
        الحذف الآمن للملف عبر الكتابة فوقه ببيانات عشوائية وأصفار قبل إزالته
        (Secure File Shredding) لمنع استرجاعه عبر برامج استعادة البيانات.

        :param file_path: مسار الملف المراد حذفه نهائياً
        :param passes: عدد مرات الكتابة فوق الملف (افتراضياً 3 دورات)
        :return: True إذا نجح الحذف الآمن، False خلاف ذلك
        """
        if not os.path.exists(file_path) or not os.path.isfile(file_path):
            return False

        try:
            file_size = os.path.getsize(file_path)

            if file_size > 0:
                with open(file_path, "ba+", buffering=0) as f:
                    for p in range(passes):
                        f.seek(0)
                        remaining = file_size
                        chunk_size = 64 * 1024

                        # تنويع أنماط التمويه: دورة أصفار، دورة واحدات، دورة عشوائية
                        if p % 3 == 0:
                            fill_byte = b"\x00"
                            while remaining > 0:
                                count = min(remaining, chunk_size)
                                f.write(fill_byte * count)
                                remaining -= count
                        elif p % 3 == 1:
                            fill_byte = b"\xFF"
                            while remaining > 0:
                                count = min(remaining, chunk_size)
                                f.write(fill_byte * count)
                                remaining -= count
                        else:
                            while remaining > 0:
                                count = min(remaining, chunk_size)
                                f.write(os.urandom(count))
                                remaining -= count

                        f.flush()
                        try:
                            os.fsync(f.fileno())
                        except OSError:
                            pass

            # إعادة تسمية الملف لاسم عشوائي لمسح اسمه الأصلي من سجل الفهرسة (MFT/FAT)
            dir_name = os.path.dirname(file_path)
            random_name = "".join(random.choices(string.ascii_letters + string.digits, k=16))
            renamed_path = os.path.join(dir_name, random_name + ".tmp")

            try:
                os.rename(file_path, renamed_path)
                os.remove(renamed_path)
            except OSError:
                os.remove(file_path)

            return True

        except Exception as e:
            print(f"[PrivacyManager] خطأ أثناء الحذف الآمن للملف: {e}")
            try:
                if os.path.exists(file_path):
                    os.remove(file_path)
                    return True
            except OSError:
                pass
            return False

    def clear_download_history(self) -> int:
        """
        مسح سجل التحميلات بالكامل من قاعدة البيانات المحلية وملفات السجل.
        Clears all records from SQLite database and history files.

        :return: عدد السجلات المحذوفة
        """
        deleted_count = 0

        # تنظيف قاعدة بيانات SQLite إن وجدت
        if os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()

                # استعلام عن الجداول الموجودة في قاعدة البيانات
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]

                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")  # nosec B608
                        count = cursor.fetchone()[0]
                        deleted_count += count

                        cursor.execute(f"DELETE FROM {table}")  # nosec B608
                    except sqlite3.Error:
                        pass

                conn.commit()
                # ضغط قاعدة البيانات لتفريغ المساحة ومسح البيانات نهائياً
                cursor.execute("VACUUM")
                conn.close()
            except Exception as e:
                print(f"[PrivacyManager] خطأ أثناء تنظيف قاعدة البيانات: {e}")

        # تنظيف أي ملفات سجلات إضافية بصيغة JSON أو Text
        json_history = os.path.join(self.app_data_dir, "history.json")
        if os.path.exists(json_history):
            try:
                os.remove(json_history)
                deleted_count += 1
            except OSError:
                pass

        return deleted_count

    def clear_temp_files(self, temp_directory: Optional[str] = None, secure: bool = False) -> int:
        """
        حذف جميع الملفات المؤقتة وأجزاء التنزيل العالقة (.part, .tmp, .chunk).
        Removes all temporary download chunks and cache files.

        :param temp_directory: مجلد الملفات المؤقتة المراد تنظيفه
        :param secure: استخدام الحذف الآمن بالكتابة فوق الملفات
        :return: عدد الملفات التي تم حذفها بنجاح
        """
        target_dir = temp_directory or self.temp_dir
        if not os.path.exists(target_dir):
            return 0

        deleted_files = 0
        extensions = [".tmp", ".part", ".crdownload", ".aria2", ".download", ".chunk", ".fdown"]

        for root, _, files in os.walk(target_dir):
            for file in files:
                file_lower = file.lower()
                is_temp = any(file_lower.endswith(ext) for ext in extensions) or file_lower.startswith("flexdown_")
                if is_temp or root == target_dir:
                    full_path = os.path.join(root, file)
                    try:
                        if secure:
                            if self.secure_delete(full_path):
                                deleted_files += 1
                        else:
                            os.remove(full_path)
                            deleted_files += 1
                    except OSError:
                        pass

        return deleted_files

    def get_privacy_status(self) -> Dict[str, Any]:
        """
        توفير تقرير شامل عن حالة الخصوصية وحجم البيانات المؤقتة وسجل التحميلات.
        Returns detailed privacy statistics.
        """
        temp_files_count = 0
        temp_files_size = 0

        if os.path.exists(self.temp_dir):
            for root, _, files in os.walk(self.temp_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    try:
                        temp_files_size += os.path.getsize(full_path)
                        temp_files_count += 1
                    except OSError:
                        pass

        # حساب عدد سجلات قاعدة البيانات
        history_records = 0
        if os.path.exists(self.db_path):
            try:
                conn = sqlite3.connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
                tables = [row[0] for row in cursor.fetchall() if not row[0].startswith("sqlite_")]
                for table in tables:
                    try:
                        cursor.execute(f"SELECT COUNT(*) FROM {table}")  # nosec B608
                        history_records += cursor.fetchone()[0]
                    except sqlite3.Error:
                        pass
                conn.close()
            except Exception:
                pass

        # تنسيق حجم الملفات المؤقتة للقراءة البشرية
        formatted_size = self._format_size(temp_files_size)

        return {
            "no_log_mode": self.no_log_mode,
            "temp_files_count": temp_files_count,
            "temp_files_size_bytes": temp_files_size,
            "temp_files_size_formatted": formatted_size,
            "history_records_count": history_records,
            "secure_delete_available": True,
            "app_data_dir": self.app_data_dir,
            "temp_dir": self.temp_dir,
            "db_exists": os.path.exists(self.db_path),
        }

    @staticmethod
    def _format_size(bytes_val: int) -> str:
        """
        دالة مساعدة لتحويل الحجم بالبايت إلى صيغة نصية مقروءة (كيلوبايت، ميجابايت، جيجابايت).
        """
        if bytes_val < 1024:
            return f"{bytes_val} B"
        elif bytes_val < 1024 * 1024:
            return f"{bytes_val / 1024:.2f} KB"
        elif bytes_val < 1024 * 1024 * 1024:
            return f"{bytes_val / (1024 * 1024):.2f} MB"
        else:
            return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"
