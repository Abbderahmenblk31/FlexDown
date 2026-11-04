"""
FlexDown - محرك الترجمة والتدويل (Internationalization & Translator Module)
يوفر فئة AppTranslator لإدارة اللغات والترجمات، مع دعم التخطيط من اليمين لليسار (RTL) للغة العربية.
"""

import os
import json
import glob
from typing import Dict, Any, List, Optional

# محاولة استيراد واجهات Qt لتحديد اتجاه واجهة المستخدم (RTL / LTR)
try:
    from PyQt6.QtCore import Qt
    from PyQt6.QtWidgets import QApplication
except ImportError:
    Qt = None  # type: ignore[assignment,misc]
    QApplication = None  # type: ignore[assignment,misc]


class AppTranslator:
    """
    فئة مسؤولة عن ترجمة نصوص التطبيق وتغيير اتجاه الواجهة (RTL/LTR).
    AppTranslator handles string localization, language switching, and Qt layout direction.
    """

    RTL_LANGUAGES = ["ar", "fa", "he", "ur"]
    DEFAULT_LANGUAGE = "en"
    FALLBACK_LANGUAGE = "en"

    LANGUAGE_NAMES = {
        "en": "English",
        "ar": "العربية",
    }

    def __init__(self, language: str = "en"):
        """
        تهيئة محرك الترجمة وتحميل قاموس النصوص.
        :param language: رمز اللغة المختارة (الافتراضي 'ar' العربية)
        """
        self.locale_dir = os.path.dirname(os.path.abspath(__file__))
        self.current_language: str = language
        self.translations: Dict[str, str] = {}
        self.fallback_translations: Dict[str, str] = {}
        self.app_instance: Optional[Any] = None

        # تحميل لغة الاسترداد (الإنجليزية) ولغة العرض الحالية
        self._load_fallback()
        self.set_language(language)

    def _load_fallback(self) -> None:
        """
        تحميل قاموس اللغة الإنجليزية كاحتياط في حال نقص أي مفتاح في اللغة الحالية.
        """
        fallback_path = os.path.join(self.locale_dir, f"{self.FALLBACK_LANGUAGE}.json")
        if os.path.exists(fallback_path):
            try:
                with open(fallback_path, "r", encoding="utf-8") as f:
                    self.fallback_translations = json.load(f)
            except Exception as e:
                print(f"[Translator] خطأ في تحميل ملف اللغة الاحتياطية: {e}")
                self.fallback_translations = {}

    def set_language(self, language: str) -> bool:
        """
        تغيير لغة التطبيق الحالية وإعادة تحميل النصوص من ملف JSON المناسب.
        Sets and reloads the current language strings.

        :param language: رمز اللغة (مثال: 'ar' أو 'en')
        :return: True عند نجاح التحميل، False عند الفشل
        """
        lang_code = language.strip().lower()
        file_path = os.path.join(self.locale_dir, f"{lang_code}.json")

        if not os.path.exists(file_path):
            # محاولة البحث عن لغة افتراضية إن لم يوجد الملف
            if lang_code != self.DEFAULT_LANGUAGE:
                file_path = os.path.join(self.locale_dir, f"{self.DEFAULT_LANGUAGE}.json")
                lang_code = self.DEFAULT_LANGUAGE

        if os.path.exists(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    self.translations = json.load(f)
                self.current_language = lang_code

                # إعادة تطبيق اتجاه الواجهة إذا كان تطبيق Qt مثبتاً
                if self.app_instance is not None:
                    self.install(self.app_instance)

                return True
            except Exception as e:
                print(f"[Translator] خطأ في تحميل ملف اللغة {file_path}: {e}")
                return False
        else:
            print(f"[Translator] لم يتم العثور على ملف اللغة: {file_path}")
            return False

    def is_rtl(self) -> bool:
        """
        التحقق مما إذا كانت اللغة الحالية تدعم الكتابة والتخطيط من اليمين إلى اليسار (RTL).
        Returns True if the current language layout is Right-to-Left.
        """
        return self.current_language.lower() in self.RTL_LANGUAGES

    def install(self, app: Any) -> None:
        """
        تطبيق اتجاه الواجهة المناسب (RTL / LTR) على كائن QApplication.
        Sets application layout direction according to the language (RTL for Arabic).

        :param app: كائن تطبيق Qt (QApplication)
        """
        self.app_instance = app

        if app is None or Qt is None:
            return

        try:
            # التحقق من نوع LayoutDirection في PyQt6 أو PyQt5
            if hasattr(Qt, "LayoutDirection"):
                direction = (
                    Qt.LayoutDirection.RightToLeft
                    if self.is_rtl()
                    else Qt.LayoutDirection.LeftToRight
                )
            else:
                # توافقية مع بعض إصدارات PyQt القديمة
                direction = Qt.RightToLeft if self.is_rtl() else Qt.LeftToRight

            app.setLayoutDirection(direction)
        except Exception as e:
            print(f"[Translator] تعذر تطبيق اتجاه الواجهة: {e}")

    def get_available_languages(self) -> List[str]:
        """
        استكشاف اللغات المتاحة في مجلد i18n عبر البحث عن ملفات JSON.
        Returns a list of available language codes.
        """
        pattern = os.path.join(self.locale_dir, "*.json")
        languages = []
        for file in glob.glob(pattern):
            base_name = os.path.splitext(os.path.basename(file))[0]
            languages.append(base_name)
        return sorted(languages)

    def get_language_display_name(self, lang_code: str) -> str:
        """
        الحصول على الاسم الظاهر للغة (مثال: 'العربية' لـ 'ar').
        """
        return self.LANGUAGE_NAMES.get(lang_code, lang_code.upper())

    def __call__(self, key: str, **kwargs) -> str:
        """
        استرجاع النص المترجم بواسطة المفتاح مع دعم تنسيق المعاملات.
        Translates a string key with optional format arguments.

        :param key: مفتاح النص المطلوب
        :param kwargs: المعاملات المتغيرة المطلوب إدراجها في النص
        :return: النص المترجم بعد التنسيق
        """
        # البحث في قاموس اللغة الحالية أولاً، ثم في اللغة الاحتياطية، ثم المفتاح الأصلي
        text = self.translations.get(key)
        if text is None:
            text = self.fallback_translations.get(key, key)

        if kwargs:
            try:
                return text.format(**kwargs)
            except (KeyError, ValueError, IndexError):
                return text

        return text

    def t(self, key: str, **kwargs) -> str:
        """
        دالة بديلة لـ __call__ لتسهيل الاستدعاء.
        """
        return self(key, **kwargs)


# نسخة عامة ومشتركة (Global Singleton) لتسهيل الاستخدام في كامل أرجاء البرنامج
_global_translator: Optional[AppTranslator] = None


def get_translator(language: str = "en") -> AppTranslator:
    """
    الحصول على كائن المترجم العام المشترك.
    """
    global _global_translator
    if _global_translator is None:
        _global_translator = AppTranslator(language=language)
    elif language and _global_translator.current_language != language:
        _global_translator.set_language(language)
    return _global_translator


def _(key: str, **kwargs) -> str:
    """
    دالة الاختصار القياسية للترجمة (_("key")).
    Standard gettext-style translation shortcut function.
    """
    translator = get_translator()
    return translator(key, **kwargs)
