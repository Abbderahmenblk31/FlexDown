"""
نافذة إعداد وتفعيل إضافة المتصفح (Browser Integration Setup Dialog)
FlexDown - Chrome & Edge Extension Integration Dialog
"""

import os
import subprocess
from pathlib import Path

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon, QDesktopServices
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QMessageBox,
)


class BrowserIntegrationDialog(QDialog):
    """
    نافذة توجيه المستخدم لتفعيل إضافة المتصفح بنقرة واحدة (IDM-Style Integration).
    """

    def __init__(self, parent=None, is_arabic: bool = True):
        super().__init__(parent)
        self.is_arabic = is_arabic
        self._init_window()
        self._init_ui()

    def _init_window(self) -> None:
        title = "تفعيل إضافة المتصفح - FlexDown" if self.is_arabic else "Browser Integration - FlexDown"
        self.setWindowTitle(title)
        self.setFixedSize(580, 440)
        self.setWindowFlags(Qt.WindowType.Dialog | Qt.WindowType.WindowCloseButtonHint)

        icon_path = Path(__file__).resolve().parent.parent.parent / "resources" / "icons" / "app.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _get_extension_path(self) -> Path:
        """الحصول على مسار مجلد إضافة المتصفح"""
        base_dir = Path(__file__).resolve().parent.parent.parent
        ext_path = base_dir / "browser_extension"
        if not ext_path.exists():
            # فحص مسار مجلد سطح المكتب
            desktop_ext = Path.home() / "OneDrive" / "Bureau" / "FlexDown" / "browser_extension"
            if desktop_ext.exists():
                return desktop_ext
        return ext_path

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        # Header Card
        card = QFrame(self)
        card.setObjectName("cardFrame")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(16, 14, 16, 14)
        card_layout.setSpacing(8)

        status_text = (
            "🟢 خادم الربط المحلي نشط ويعمل (127.0.0.1:18888)"
            if self.is_arabic
            else "🟢 Local Bridge Server Active (127.0.0.1:18888)"
        )
        status_lbl = QLabel(status_text, card)
        status_lbl.setStyleSheet("color: #10b981; font-weight: bold; font-size: 11pt;")
        card_layout.addWidget(status_lbl)

        if self.is_arabic:
            desc_text = (
                "تتيح لك هذه الإضافة ظهور شعار <b>FlexDown</b> فوق أي مقطع فيديو تشاهده على أي موقع "
                "(YouTube, TikTok, Facebook, Twitter وغيرها) "
                "لتنزيل الفيديو أو الصوت فوراً بنقرة واحدة دون الحاجة لنسخ الرابط يدوياً!"
            )
        else:
            desc_text = (
                "This module shows a floating <b>FlexDown</b> button over any web video "
                "(YouTube, TikTok, Facebook, Twitter, etc.) "
                "to download video or audio with one click without copying URLs!"
            )
        lbl_desc = QLabel(desc_text, card)
        lbl_desc.setWordWrap(True)
        lbl_desc.setStyleSheet("color: #cbd5e1; font-size: 9.5pt;")
        card_layout.addWidget(lbl_desc)

        layout.addWidget(card)

        # Steps
        steps_card = QFrame(self)
        steps_card.setObjectName("cardFrame")
        steps_layout = QVBoxLayout(steps_card)
        steps_layout.setContentsMargins(16, 14, 16, 14)
        steps_layout.setSpacing(10)

        steps_title_text = "طريقة التفعيل في خطوتين سريعتين:" if self.is_arabic else "Quick 2-Step Setup:"
        steps_title = QLabel(steps_title_text, steps_card)
        steps_title.setStyleSheet("font-weight: bold; color: #38bdf8;")
        steps_layout.addWidget(steps_title)

        if self.is_arabic:
            steps_content = (
                "<b>1.</b> اضغط على زر <b>صفحة إضافات Edge</b> أدناه، ثم فعّل "
                "<b>وضع المطور (Mode développeur)</b> على يسار الصفحة.<br/>"
                "<b>2.</b> اضغط على <b>فتح مجلد الإضافة</b>، ثم <b>اسحب المجلد المظلل بالفأرة "
                "(Drag & Drop) وأفلته مباشرة</b> داخل نافذة Edge!<br/>"
                "<small style='color: #94a3b8;'>(أو اضغط 'Charger les extensions décompressées' "
                "ثم الصق المسار المنسوخ تلقائياً).</small>"
            )
        else:
            steps_content = (
                "<b>1.</b> Click <b>Edge Extensions</b> below and toggle ON "
                "<b>Developer mode (Mode développeur)</b> on the left.<br/>"
                "<b>2.</b> Click <b>Open Extension Folder</b>, then <b>drag and drop the highlighted folder</b> "
                "directly into Edge!<br/>"
                "<small style='color: #94a3b8;'>(Or click 'Load unpacked' and paste the path copied "
                "automatically).</small>"
            )
        lbl_steps = QLabel(steps_content, steps_card)
        lbl_steps.setWordWrap(True)
        lbl_steps.setStyleSheet("color: #e2e8f0; line-height: 1.5;")
        steps_layout.addWidget(lbl_steps)

        layout.addWidget(steps_card)

        # Action Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        btn_open_folder = QPushButton("📁 فتح وتحديد مجلد الإضافة" if self.is_arabic else "📁 Open & Select Folder", self)
        btn_open_folder.setObjectName("primaryButton")
        btn_open_folder.setFixedHeight(38)
        btn_open_folder.clicked.connect(self._open_folder)
        btn_layout.addWidget(btn_open_folder)

        btn_open_edge = QPushButton("🌐 إضافات Edge" if self.is_arabic else "🌐 Edge Extensions", self)
        btn_open_edge.setFixedHeight(38)
        btn_open_edge.clicked.connect(lambda: self._open_browser_url("edge://extensions"))
        btn_layout.addWidget(btn_open_edge)

        btn_open_firefox = QPushButton("🦊 إضافات Firefox" if self.is_arabic else "🦊 Firefox Extensions", self)
        btn_open_firefox.setFixedHeight(38)
        btn_open_firefox.clicked.connect(lambda: self._open_browser_url("firefox://debugging"))
        btn_layout.addWidget(btn_open_firefox)

        btn_open_chrome = QPushButton("🌐 Chrome" if self.is_arabic else "🌐 Chrome", self)
        btn_open_chrome.setFixedHeight(38)
        btn_open_chrome.clicked.connect(lambda: self._open_browser_url("chrome://extensions"))
        btn_layout.addWidget(btn_open_chrome)

        layout.addLayout(btn_layout)

        # Close
        btn_close = QPushButton("تم / إغلاق" if self.is_arabic else "Done / Close", self)
        btn_close.setFixedHeight(34)
        btn_close.clicked.connect(self.accept)
        layout.addWidget(btn_close)

    def _open_folder(self) -> None:
        ext_path = self._get_extension_path()
        if ext_path.exists():
            from PyQt6.QtWidgets import QApplication
            QApplication.clipboard().setText(os.path.abspath(str(ext_path)))
            subprocess.Popen(f'explorer.exe /select,"{os.path.abspath(str(ext_path))}"')
        else:
            QMessageBox.warning(self, "Warning", f"Extension folder not found at:\n{ext_path}")

    def _open_browser_url(self, url: str) -> None:
        try:
            # فتح عبر بروتوكول المتصفح أو مستعرض النظام
            if "edge://" in url:
                subprocess.Popen(["cmd.exe", "/c", "start", "msedge.exe", "edge://extensions"])
            elif "firefox://" in url:
                ff_path = r"C:\Program Files\Mozilla Firefox\firefox.exe"
                if os.path.exists(ff_path):
                    subprocess.Popen([ff_path, "about:debugging#/runtime/this-firefox"])
                else:
                    subprocess.Popen(["cmd.exe", "/c", "start", "firefox.exe", "about:debugging#/runtime/this-firefox"])
            elif "chrome://" in url:
                subprocess.Popen(["cmd.exe", "/c", "start", "chrome.exe", "chrome://extensions"])
            else:
                QDesktopServices.openUrl(QUrl(url))
        except Exception:
            QDesktopServices.openUrl(QUrl(url))
