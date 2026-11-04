#!/usr/bin/env python3
"""
ملف التشغيل الرئيسي لبرنامج فليكس داون (FlexDown Desktop Download Manager)
FlexDown Main Application Entry Point

يقوم هذا الملف بتهيئة بيئة التشغيل، وتطبيق التنسيقات (Dark/Light QSS)،
وضبط اتجاه الواجهة (RTL للعربية / LTR للإنجليزية)، وبدء تشغيل النافذة الرئيسية.
"""

import sys
import os
from pathlib import Path

# إضافة مسار المشروع إلى sys.path لضمان استيراد الحزم بشكل صحيح
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# إضافة مجلد bin (FFmpeg) إلى PATH للنظام
BIN_DIR = BASE_DIR / "bin"
if BIN_DIR.exists() and str(BIN_DIR) not in os.environ.get("PATH", ""):
    os.environ["PATH"] = str(BIN_DIR) + os.pathsep + os.environ.get("PATH", "")

from PyQt6.QtWidgets import QApplication  # noqa: E402
from PyQt6.QtCore import Qt, qInstallMessageHandler, QtMsgType  # noqa: E402
from PyQt6.QtGui import QIcon, QFont  # noqa: E402


def _qt_message_handler(mode, context, message):
    # كتم رسائل التحذير غير الضارة الخاصة بالخطوط في Qt
    if "setPointSize" in message:
        return
    if mode in (QtMsgType.QtCriticalMsg, QtMsgType.QtFatalMsg):
        sys.stderr.write(f"Qt Error: {message}\n")


qInstallMessageHandler(_qt_message_handler)

from flexdown.constants import (  # noqa: E402
    APP_NAME,
    VERSION,
    ORGANIZATION_NAME,
)
from flexdown.utils.config import get_config  # noqa: E402
from flexdown.themes import load_theme  # noqa: E402
from flexdown.i18n.translator import get_translator  # noqa: E402
from flexdown.ui.main_window import MainWindow  # noqa: E402


def main():
    """
    الدالة الرئيسية لبدء تشغيل التطبيق.
    Main function to initialize and run FlexDown application.
    """
    # تهيئة تطبيق كيو تي (PyQt6 Application)
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    app.setApplicationVersion(VERSION)
    app.setOrganizationName(ORGANIZATION_NAME)
    app.setApplicationDisplayName(f"{APP_NAME} - v{VERSION}")

    # ضبط معرف التطبيق في ويندوز لضمان ظهور الأيقونة المخصصة في شريط المهام
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("FlexDown.Downloader.App.1.0")
        except Exception:
            pass

    # ضبط أيقونة التطبيق الرسمية
    icon_path = BASE_DIR / "resources" / "icons" / "app.ico"
    if not icon_path.exists():
        icon_path = BASE_DIR / "resources" / "icons" / "app.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    # تحميل الإعدادات
    config = get_config()

    # ضبط لغة واتجاه الواجهة (RTL للعربية)
    current_lang = config.language
    if current_lang == "ar":
        app.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
    else:
        app.setLayoutDirection(Qt.LayoutDirection.LeftToRight)

    # ضبط الخط العام لدعم العربية والإنجليزية بوضوح
    app_font = QFont("Segoe UI", 10)
    app_font.setStyleHint(QFont.StyleHint.SansSerif)
    app.setFont(app_font)

    # تطبيق المظهر (Dark / Light)
    theme_name = "dark" if config.dark_mode else "light"
    stylesheet = load_theme(theme_name)
    if stylesheet:
        app.setStyleSheet(stylesheet)

    # تهيئة مترجم النصوص
    translator = get_translator(current_lang)

    # إنشاء النافذة الرئيسية
    window = MainWindow(config=config, translator=translator)
    window.show()

    # بدء حلقة الأحداث (Event Loop)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
