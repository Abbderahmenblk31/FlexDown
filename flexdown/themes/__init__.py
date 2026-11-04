"""
FlexDown Themes Package
حزمة المظاهر والتصميمات الجمالية (Dark Theme & Light Theme)
"""

import os


def get_theme_path(theme_name: str = "dark") -> str:
    """
    الحصول على المسار الكامل لملف نمط المظهر (.qss).
    """
    themes_dir = os.path.dirname(os.path.abspath(__file__))
    clean_name = theme_name.lower().replace(".qss", "")
    return os.path.join(themes_dir, f"{clean_name}.qss")


def load_theme(theme_name: str = "dark") -> str:
    """
    قراءة وتحميل نصوص التنسيق CSS/QSS للمظهر المطلوب.
    """
    path = get_theme_path(theme_name)
    if not os.path.exists(path):
        path = get_theme_path("dark")

    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"[Themes] تعذر تحميل المظهر {theme_name}: {e}")
        return ""
