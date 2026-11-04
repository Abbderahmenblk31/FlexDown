"""
إدارة إعدادات تطبيق فليكس داون (FlexDown Configuration Manager)
يتولى هذا الملف قراءة وكتابة إعدادات المستخدم من وإلى ملف JSON في ~/.flexdown/config.json
مع تطبيق القيم الافتراضية، ومزامنة التغييرات وحماية الوصول المتزامن عبر الخيوط.
"""

import os
import json
import tempfile
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from flexdown.constants import (
    CONFIG_FILE,
    DEFAULT_DOWNLOAD_DIR,
    DEFAULT_LANGUAGE,
    DEFAULT_DARK_MODE,
    DEFAULT_MAX_CONCURRENT,
    DEFAULT_AUTO_RESUME,
    DEFAULT_SHOW_NOTIFICATIONS,
    DEFAULT_MINIMIZE_TO_TRAY,
    DEFAULT_PROXY,
    DEFAULT_ENCRYPT_BY_DEFAULT,
    DEFAULT_NO_HISTORY,
    DEFAULT_MAX_RETRIES,
    DEFAULT_SPEED_LIMIT,
)


class Config:
    """
    فئة إدارة إعدادات التطبيق.
    Manages application configuration, reading and writing to ~/.flexdown/config.json.
    """

    DEFAULT_SETTINGS: Dict[str, Any] = {
        "language": DEFAULT_LANGUAGE,
        "dark_mode": DEFAULT_DARK_MODE,
        "output_dir": str(DEFAULT_DOWNLOAD_DIR),
        "max_concurrent": DEFAULT_MAX_CONCURRENT,
        "auto_resume": DEFAULT_AUTO_RESUME,
        "show_notifications": DEFAULT_SHOW_NOTIFICATIONS,
        "minimize_to_tray": DEFAULT_MINIMIZE_TO_TRAY,
        "proxy": DEFAULT_PROXY,
        "encrypt_by_default": DEFAULT_ENCRYPT_BY_DEFAULT,
        "no_history": DEFAULT_NO_HISTORY,
        "max_retries": DEFAULT_MAX_RETRIES,
        "speed_limit": DEFAULT_SPEED_LIMIT,
    }

    _instance: Optional["Config"] = None
    _singleton_lock: threading.Lock = threading.Lock()

    def __init__(self, config_path: Optional[Path] = None):
        """
        تهيئة مدير الإعدادات وتحميل القيم من الملف.

        :param config_path: مسار مخصص لملف الإعدادات، أو الافتراضي ~/.flexdown/config.json
        """
        self._lock = threading.RLock()
        self.config_path: Path = Path(config_path) if config_path else CONFIG_FILE
        self._settings: Dict[str, Any] = dict(self.DEFAULT_SETTINGS)
        self.load()

    @classmethod
    def get_instance(cls, config_path: Optional[Path] = None) -> "Config":
        """
        الحصول على النسخة المشتركة (Singleton) لمدير الإعدادات.
        Get singleton instance of the configuration manager.
        """
        with cls._singleton_lock:
            if cls._instance is None:
                cls._instance = cls(config_path)
            return cls._instance

    def load(self) -> None:
        """
        قراءة الإعدادات من ملف JSON ودمجها مع القيم الافتراضية.
        Load configuration from JSON file, merging with default settings.
        """
        with self._lock:
            if not self.config_path.exists():
                # إنشاء مجلد الإعدادات والملف الافتراضي إذا لم يكن موجوداً
                self.save()
                return

            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, dict):
                        # دمج الإعدادات المحفوظة مع الإعدادات الافتراضية لضمان وجود جميع الحقول
                        merged = dict(self.DEFAULT_SETTINGS)
                        merged.update(data)
                        self._settings = merged
                    else:
                        # في حال تلف الملف بتنسيق غير كائن، نعيد تعيينه
                        self._settings = dict(self.DEFAULT_SETTINGS)
                        self.save()
            except Exception:
                # في حال تعذر القراءة أو تلف الـ JSON نعتمد الافتراضي ونحفظه
                self._settings = dict(self.DEFAULT_SETTINGS)
                self.save()

    def save(self) -> bool:
        """
        حفظ الإعدادات الحالية في ملف JSON بشكل آمن (Atomic Write).
        Save current configuration to JSON file safely using atomic write.

        :return: True إذا تم الحفظ بنجاح، وإلا False
        """
        with self._lock:
            try:
                # التأكد من وجود المجلد الأب
                parent_dir = self.config_path.parent
                parent_dir.mkdir(parents=True, exist_ok=True)

                # كتابة آمنة عبر ملف مؤقت لتفادي تلف البيانات في حال الانقطاع المفاجئ
                temp_file = tempfile.NamedTemporaryFile(
                    mode="w",
                    dir=parent_dir,
                    encoding="utf-8",
                    delete=False
                )
                with temp_file as f:
                    json.dump(self._settings, f, indent=4, ensure_ascii=False)

                # استبدال ذري للملف
                os.replace(temp_file.name, self.config_path)
                return True
            except Exception:
                # محاولة كتابة مباشرة كبديل إن فشل الاستبدال الذري
                try:
                    with open(self.config_path, "w", encoding="utf-8") as f:
                        json.dump(self._settings, f, indent=4, ensure_ascii=False)
                    return True
                except Exception:
                    return False

    def get(self, key: str, default: Any = None) -> Any:
        """
        الحصول على قيمة إعداد معين.
        Get setting value by key.
        """
        with self._lock:
            return self._settings.get(key, default)

    def set(self, key: str, value: Any, auto_save: bool = True) -> None:
        """
        تعيين قيمة إعداد وحفظ الملف تلقائياً.
        Set setting value and optionally save to disk.
        """
        with self._lock:
            self._settings[key] = value
            if auto_save:
                self.save()

    def update(self, new_settings: Dict[str, Any], auto_save: bool = True) -> None:
        """
        تحديث مجموعة من الإعدادات دفعة واحدة.
        Update multiple settings at once.
        """
        with self._lock:
            self._settings.update(new_settings)
            if auto_save:
                self.save()

    def reset(self) -> None:
        """
        إعادة ضبط كافة الإعدادات إلى القيم الافتراضية.
        Reset all settings to defaults.
        """
        with self._lock:
            self._settings = dict(self.DEFAULT_SETTINGS)
            self.save()

    def to_dict(self) -> Dict[str, Any]:
        """
        الحصول على نسخة من الإعدادات كقاموس.
        Get a copy of settings dictionary.
        """
        with self._lock:
            return dict(self._settings)

    # ==========================================
    # الخصائص المباشرة للإعدادات (Properties)
    # ==========================================

    @property
    def language(self) -> str:
        """لغة الواجهة ('ar' أو 'en')"""
        return str(self.get("language", DEFAULT_LANGUAGE))

    @language.setter
    def language(self, value: str) -> None:
        self.set("language", str(value))

    @property
    def dark_mode(self) -> bool:
        """تفعيل المظهر الداكن"""
        return bool(self.get("dark_mode", DEFAULT_DARK_MODE))

    @dark_mode.setter
    def dark_mode(self, value: bool) -> None:
        self.set("dark_mode", bool(value))

    @property
    def output_dir(self) -> str:
        """مجلد تنزيل الملفات"""
        path_str = self.get("output_dir", str(DEFAULT_DOWNLOAD_DIR))
        # التوسع في ~ لمسار المستخدم
        expanded = os.path.expanduser(path_str)
        return expanded

    @output_dir.setter
    def output_dir(self, value: str) -> None:
        self.set("output_dir", str(value))

    @property
    def max_concurrent(self) -> int:
        """أقصى عدد للتنزيلات المتزامنة"""
        try:
            return int(self.get("max_concurrent", DEFAULT_MAX_CONCURRENT))
        except (ValueError, TypeError):
            return DEFAULT_MAX_CONCURRENT

    @max_concurrent.setter
    def max_concurrent(self, value: int) -> None:
        self.set("max_concurrent", max(1, int(value)))

    @property
    def auto_resume(self) -> bool:
        """استئناف التنزيلات غير المكتملة تلقائياً عند التشغيل"""
        return bool(self.get("auto_resume", DEFAULT_AUTO_RESUME))

    @auto_resume.setter
    def auto_resume(self, value: bool) -> None:
        self.set("auto_resume", bool(value))

    @property
    def show_notifications(self) -> bool:
        """إظهار إشعارات سطح المكتب"""
        return bool(self.get("show_notifications", DEFAULT_SHOW_NOTIFICATIONS))

    @show_notifications.setter
    def show_notifications(self, value: bool) -> None:
        self.set("show_notifications", bool(value))

    @property
    def minimize_to_tray(self) -> bool:
        """التصغير إلى شريط المهام (System Tray) عند الإغلاق"""
        return bool(self.get("minimize_to_tray", DEFAULT_MINIMIZE_TO_TRAY))

    @minimize_to_tray.setter
    def minimize_to_tray(self, value: bool) -> None:
        self.set("minimize_to_tray", bool(value))

    @property
    def proxy(self) -> Optional[str]:
        """عنوان البروكسي (مثل http://127.0.0.1:8080) أو None"""
        val = self.get("proxy", DEFAULT_PROXY)
        return str(val) if val else None

    @proxy.setter
    def proxy(self, value: Optional[str]) -> None:
        self.set("proxy", str(value).strip() if value else None)

    @property
    def encrypt_by_default(self) -> bool:
        """تشفير الملفات المحملة تلقائياً"""
        return bool(self.get("encrypt_by_default", DEFAULT_ENCRYPT_BY_DEFAULT))

    @encrypt_by_default.setter
    def encrypt_by_default(self, value: bool) -> None:
        self.set("encrypt_by_default", bool(value))

    @property
    def no_history(self) -> bool:
        """عدم حفظ سجل التنزيلات للخصوصية"""
        return bool(self.get("no_history", DEFAULT_NO_HISTORY))

    @no_history.setter
    def no_history(self, value: bool) -> None:
        self.set("no_history", bool(value))

    @property
    def max_retries(self) -> int:
        """الحد الأقصى لمرات إعادة المحاولة عند انقطاع الاتصال"""
        try:
            return int(self.get("max_retries", DEFAULT_MAX_RETRIES))
        except (ValueError, TypeError):
            return DEFAULT_MAX_RETRIES

    @max_retries.setter
    def max_retries(self, value: int) -> None:
        self.set("max_retries", max(0, int(value)))

    @property
    def speed_limit(self) -> int:
        """حد السرعة الإجمالي بالبايت/ثانية (0 يعني غير محدود)"""
        try:
            return int(self.get("speed_limit", DEFAULT_SPEED_LIMIT))
        except (ValueError, TypeError):
            return DEFAULT_SPEED_LIMIT

    @speed_limit.setter
    def speed_limit(self, value: int) -> None:
        self.set("speed_limit", max(0, int(value)))

    # دعم المعاملات المشابهة للقاموس
    def __getitem__(self, key: str) -> Any:
        with self._lock:
            return self._settings[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        with self._lock:
            return key in self._settings


def get_config() -> Config:
    """دالة مساعدة مريحة للحصول على مثيل الإعدادات المشترك"""
    return Config.get_instance()
