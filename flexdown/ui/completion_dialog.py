"""
نافذة إشعار اكتمال التنزيل التفاعلية (IDM-Style Download Complete Dialog)
FlexDown - Centered Download Complete Dialog

تظهر هذه النافذة المنبثقة في منتصف الشاشة فور انتهاء أي تنزيل (على غرار برنامج IDM الشهير)،
وتتيح للمستخدم:
1. تشغيل/فتح الملف مباشرة (Open File)
2. فتح المجلد الحاوي وتحديد الملف داخله في مستكشف ويندوز (Open Folder)
3. إغلاق النافذة (Close)
مع عرض معلومات شاملة: اسم الملف، حجمه، نوعه، ومسار حفظه.
"""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QIcon, QPixmap, QDesktopServices, QFont
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QApplication,
    QStyle,
    QMessageBox,
)

from flexdown.models.download_item import DownloadItem
from flexdown.utils.file_utils import format_size


class DownloadCompleteDialog(QDialog):
    """
    نافذة اكتمال التنزيل في منتصف الشاشة على غرار IDM.
    Centered IDM-style Download Completion Popup Dialog.
    """

    def __init__(self, item: DownloadItem, parent=None, is_arabic: bool = False):
        super().__init__(parent)
        self.item = item
        self.is_arabic = is_arabic

        self._setup_window_properties()
        self._init_ui()
        self._center_on_screen()

    def _setup_window_properties(self) -> None:
        """تهيئة خصائص النافذة الأساسية"""
        title = "اكتمل التنزيل - FlexDown" if self.is_arabic else "Download Complete - FlexDown"
        self.setWindowTitle(title)
        self.setFixedSize(540, 260)

        # ضبط النمط ليكون نافذة حوار مستقلة تظهر فوق النوافذ
        self.setWindowFlags(
            Qt.WindowType.Dialog
            | Qt.WindowType.WindowCloseButtonHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, True)

        # تحميل الأيقونة الرسمية
        icon_path = Path(__file__).resolve().parent.parent.parent / "resources" / "icons" / "app.png"
        if icon_path.exists():
            self.setWindowIcon(QIcon(str(icon_path)))

    def _init_ui(self) -> None:
        """بناء عناصر واجهة النافذة"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # 1. بطاقة المحتوى العلوية
        card = QFrame(self)
        card.setObjectName("cardFrame")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(16, 16, 16, 16)
        card_layout.setSpacing(16)

        # الأيقونة الرمزية (Checkmark أو App Icon)
        icon_lbl = QLabel(card)
        icon_lbl.setFixedSize(56, 56)
        icon_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)

        check_path = Path(__file__).resolve().parent.parent.parent / "resources" / "icons" / "check.png"
        if check_path.exists():
            pix = QPixmap(str(check_path)).scaled(
                52, 52, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
            )
            icon_lbl.setPixmap(pix)
        else:
            icon = self.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton)
            icon_lbl.setPixmap(icon.pixmap(48, 48))

        card_layout.addWidget(icon_lbl)

        # التفاصيل النصية
        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)

        # العنوان الرئيسي
        lbl_status = QLabel(
            "تم التنزيل بنجاح!" if self.is_arabic else "Download Completed Successfully!",
            card
        )
        font_status = QFont()
        font_status.setBold(True)
        font_status.setPointSize(11)
        lbl_status.setFont(font_status)
        lbl_status.setStyleSheet("color: #2ecc71; font-weight: bold;")
        info_layout.addWidget(lbl_status)

        # اسم الملف
        filename = self.item.filename or self.item.title or "downloaded_file"
        lbl_name = QLabel(filename, card)
        lbl_name.setObjectName("detTitle")
        lbl_name.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        lbl_name.setWordWrap(True)
        lbl_name.setToolTip(filename)
        info_layout.addWidget(lbl_name)

        # معلومات الحجم ومسار المجلد
        size_str = format_size(self.item.filesize) if self.item.filesize > 0 else self.item.size_str
        lbl_details = QLabel(
            f"<b>الحجم:</b> {size_str} &nbsp;|&nbsp; <b>النوع:</b> {self.item.extension.upper() or 'FILE'}"
            if self.is_arabic
            else f"<b>Size:</b> {size_str} &nbsp;|&nbsp; <b>Type:</b> {self.item.extension.upper() or 'FILE'}",
            card
        )
        lbl_details.setObjectName("detMuted")
        info_layout.addWidget(lbl_details)

        # مسار الحفظ
        out_dir = str(self.item.output_dir or "")
        lbl_dir = QLabel(
            f"<b>المجلد:</b> {out_dir}" if self.is_arabic else f"<b>Folder:</b> {out_dir}",
            card
        )
        lbl_dir.setObjectName("detMuted")
        lbl_dir.setToolTip(out_dir)
        info_layout.addWidget(lbl_dir)

        card_layout.addLayout(info_layout, 1)
        main_layout.addWidget(card)

        # 2. أزرار التحكم السفلية (IDM Style Action Buttons)
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(10)

        # زر فتح الملف المباشر (Open File)
        btn_open = QPushButton(self)
        btn_open.setText("فتح الملف" if self.is_arabic else "Open File")
        btn_open.setObjectName("primaryButton")
        btn_open.setFixedHeight(36)
        btn_open.setDefault(True)
        btn_open.setCursor(Qt.CursorShape.PointingHandCursor)

        play_icon_path = Path(__file__).resolve().parent.parent.parent / "resources" / "icons" / "play.png"
        if play_icon_path.exists():
            btn_open.setIcon(QIcon(str(play_icon_path)))
        else:
            btn_open.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

        btn_open.clicked.connect(self._open_file)
        buttons_layout.addWidget(btn_open)

        # زر فتح المجلد وتحديد الملف (Open Folder)
        btn_folder = QPushButton(self)
        btn_folder.setText("فتح المجلد" if self.is_arabic else "Open Folder")
        btn_folder.setFixedHeight(36)
        btn_folder.setCursor(Qt.CursorShape.PointingHandCursor)

        folder_icon_path = Path(__file__).resolve().parent.parent.parent / "resources" / "icons" / "folder.png"
        if folder_icon_path.exists():
            btn_folder.setIcon(QIcon(str(folder_icon_path)))
        else:
            btn_folder.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DirIcon))

        btn_folder.clicked.connect(self._open_folder)
        buttons_layout.addWidget(btn_folder)

        # زر إغلاق (Close)
        btn_close = QPushButton(self)
        btn_close.setText("إغلاق" if self.is_arabic else "Close")
        btn_close.setFixedHeight(36)
        btn_close.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_close.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogCloseButton))
        btn_close.clicked.connect(self.close)
        buttons_layout.addWidget(btn_close)

        main_layout.addLayout(buttons_layout)

    def _center_on_screen(self) -> None:
        """توسيط النافذة تماماً في منتصف شاشة العرض الرئيسية"""
        screen = QApplication.primaryScreen()
        if screen:
            screen_geo = screen.availableGeometry()
            x = (screen_geo.width() - self.width()) // 2 + screen_geo.x()
            y = (screen_geo.height() - self.height()) // 2 + screen_geo.y()
            self.move(x, y)

    def _resolve_file_path(self) -> Optional[Path]:
        """الحصول على المسار المؤكد للملف الناتج"""
        # أولاً: محاولة مسار item.full_path
        file_path = self.item.full_path
        if file_path.exists():
            return file_path

        # ثانياً: البحث داخل المجلد عن الملف بالاسم
        if self.item.output_dir:
            dir_path = Path(self.item.output_dir)
            if dir_path.exists():
                candidate = dir_path / self.item.filename
                if candidate.exists():
                    return candidate

                # فحص أي ملف يبدأ بنفس الاسم في حال تغيرت اللاحقة
                stem = Path(self.item.filename).stem
                for f in dir_path.iterdir():
                    if f.is_file() and f.stem == stem:
                        return f

        return file_path if file_path.exists() else None

    def _open_file(self) -> None:
        """تشغيل الملف المنزّل بالبرنامج الافتراضي أو مشغل الوسائط"""
        file_path = self._resolve_file_path()
        if not file_path or not file_path.exists():
            if self.is_arabic:
                msg = f"الملف غير موجود في المسار:\n{self.item.full_path}"
            else:
                msg = f"File does not exist at path:\n{self.item.full_path}"
            QMessageBox.warning(self, "Warning", msg)
            return

        try:
            # إذا كان الملف وسائط (فيديو أو صوت) وكان مشغل VLC متوفراً،
            # نشغله به لضمان تشغيل كافة الترميزات فوراً وبدون أي طلب لكوديكات مدفوعة
            vlc_candidates = [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            ]
            vlc_exe = next((p for p in vlc_candidates if os.path.exists(p)), None)
            ext = file_path.suffix.lower()
            if vlc_exe and ext in ('.mp4', '.mkv', '.avi', '.webm', '.mov', '.flv', '.mp3', '.m4a', '.wav', '.flac'):
                subprocess.Popen([vlc_exe, str(file_path)])
                self.close()
                return

            # تشغيل باستخدام تطبيق النظام الافتراضي (على ويندوز)
            if sys.platform == "win32":
                os.startfile(str(file_path))
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))
            self.close()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to open file:\n{e}")

    def _open_folder(self) -> None:
        """فتح مستكشف الملفات في ويندوز مع تحديد وتظليل الملف مباشرة (IDM-style)"""
        file_path = self._resolve_file_path()

        if file_path and file_path.exists() and sys.platform == "win32":
            try:
                # تحديد الملف داخل Explorer
                subprocess.Popen(f'explorer.exe /select,"{os.path.abspath(str(file_path))}"')
                self.close()
                return
            except Exception:
                pass

        # فتح المجلد الأب كخيار احتياطي
        folder = self.item.output_dir
        if not folder or not os.path.exists(folder):
            if file_path and file_path.parent.exists():
                folder = str(file_path.parent)
            else:
                folder = os.path.expanduser("~/Downloads")

        if os.path.exists(folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
            self.close()
        else:
            QMessageBox.warning(self, "Warning", f"Folder not found: {folder}")
