"""
FlexDown UI Package
حزمة واجهة المستخدم لبرنامج فليكس داون (FlexDown Desktop Download Manager)
"""

from flexdown.ui.main_window import MainWindow
from flexdown.ui.download_dialog import AddDownloadDialog
from flexdown.ui.settings_dialog import SettingsDialog
from flexdown.ui.completion_dialog import DownloadCompleteDialog
from flexdown.ui.widgets.progress_widget import DownloadProgressBar

__all__ = [
    "MainWindow",
    "AddDownloadDialog",
    "SettingsDialog",
    "DownloadCompleteDialog",
    "DownloadProgressBar",
]
