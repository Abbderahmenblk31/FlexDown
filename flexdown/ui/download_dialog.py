"""
نافذة إضافة تنزيل جديد (FlexDown Add Download Dialog)
تتيح للمستخدم إدخال الرابط، وفحصه واستخراج الصيغ المتاحة (yt-dlp والتحميل المباشر)،
واختيار الجودة المطلوبة، ومجلد الحفظ، وخيارات التحويل والتشفير والجدولة.
"""

import os
import urllib.parse
from typing import Optional, List, Dict, Any

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QDateTimeEdit,
    QFileDialog,
    QMessageBox,
    QGroupBox,
    QApplication,
    QAbstractItemView,
    QScrollArea,
    QFrame,
    QWidget,
)
from PyQt6.QtCore import Qt, QDateTime, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap

import requests

from flexdown.models.download_item import DownloadItem, DownloadStatus, MediaType
from flexdown.utils.file_utils import format_size, format_duration, sanitize_filename, get_file_extension
from flexdown.utils.url_utils import detect_platform, is_valid_url, is_direct_download, normalize_url
from flexdown.core.ytdlp_backend import FormatFetcher
from flexdown.core.turbo_downloader import DirectFileProbeWorker
from flexdown.utils.config import Config, get_config
from flexdown.i18n.translator import AppTranslator, get_translator


class _ThumbnailLoader(QThread):
    """خيط غير حاجب لتحميل صورة المعاينة (Thumbnail) من الرابط"""
    loaded = pyqtSignal(bytes)
    failed = pyqtSignal()

    def __init__(self, url: str, parent=None):
        super().__init__(parent)
        self.url = url

    def run(self):
        try:
            resp = requests.get(self.url, timeout=8)
            if resp.status_code == 200:
                self.loaded.emit(resp.content)
            else:
                self.failed.emit()
        except Exception:
            self.failed.emit()


class AddDownloadDialog(QDialog):
    """
    نافذة إضافة تنزيل جديد مع دعم فحص الرابط ومعاينة الوسائط واختيار الجودات والخيارات المتقدمة.
    Add Download Dialog supporting URL analysis, format selection, preview thumbnail, and options.
    """

    def __init__(
        self,
        parent=None,
        initial_url: str = "",
        config: Optional[Config] = None,
        translator: Optional[AppTranslator] = None,
    ):
        super().__init__(parent)
        self.config = config or get_config()
        self._translator = translator or get_translator()

        # متغيرات البيانات
        self._raw_formats: List[Dict[str, Any]] = []
        self._current_info: Dict[str, Any] = {}
        self._fetcher: Optional[FormatFetcher] = None
        self._probe_worker: Optional[DirectFileProbeWorker] = None
        self._thumb_loader: Optional[_ThumbnailLoader] = None

        # إعدادات النافذة
        self.resize(650, 720)
        self.setMinimumSize(600, 680)
        self.setModal(True)
        self.setWindowTitle(self.tr("dialog_add_title") or "Add New Download")

        self._init_ui()

        # إدراج الرابط الأولي إن وجد
        if initial_url:
            self.txt_url.setText(initial_url.strip())
            self._analyze_url()
        else:
            # محاولة قراءة الحافظة تلقائياً إذا كانت تحتوي على رابط صالح
            clipboard_text = QApplication.clipboard().text().strip()
            if clipboard_text and is_valid_url(clipboard_text):
                self.txt_url.setText(clipboard_text)

    def tr(self, key: str, **kwargs) -> str:
        """ترجمة النصوص باستخدام محرك الترجمة"""
        if self._translator:
            return self._translator(key, **kwargs)
        return key

    def _init_ui(self) -> None:
        """بناء عناصر وتخطيط النافذة مع دعم التمرير السلس والتوافقية مع كافة الشاشات"""
        dialog_layout = QVBoxLayout(self)
        dialog_layout.setContentsMargins(12, 12, 12, 12)
        dialog_layout.setSpacing(8)

        scroll_area = QScrollArea(self)
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)

        content_widget = QWidget()
        main_layout = QVBoxLayout(content_widget)
        main_layout.setContentsMargins(4, 4, 4, 4)
        main_layout.setSpacing(12)

        # 1. القسم العلوي: إدخال الرابط وفحصه (Top Section)
        self._create_top_section(main_layout)

        # 2. قسم معلومات الوسائط والمعاينة (Info Section - يظهر بعد الفحص)
        self._create_info_section(main_layout)

        # 2.5 قسم عناصر قائمة التشغيل (Playlist Section)
        self._create_playlist_section(main_layout)

        # 3. قسم الجودات والصيغ (Quality & Formats Section)
        self._create_quality_section(main_layout)

        # 4. قسم الخيارات المتقدمة (Options Section)
        self._create_options_section(main_layout)

        scroll_area.setWidget(content_widget)
        dialog_layout.addWidget(scroll_area, 1)

        # 5. القسم السفلي: أزرار التنزيل والإلغاء (Bottom Action Buttons)
        self._create_bottom_buttons(dialog_layout)

    # ==========================================
    # القسم العلوي: إدخال الرابط (Top Section)
    # ==========================================
    def _create_top_section(self, parent_layout: QVBoxLayout) -> None:
        top_group = QGroupBox("Download URL", self)
        top_layout = QVBoxLayout(top_group)
        top_layout.setSpacing(8)

        # سطر الرابط مع زر اللصق وزر الفحص
        row_url = QHBoxLayout()
        row_url.setSpacing(8)

        self.txt_url = QLineEdit(top_group)
        self.txt_url.setPlaceholderText(
            self.tr("dialog_add_url_placeholder") or "Paste download link here (YouTube, HTTP, Direct link...)"
        )
        self.txt_url.setMinimumHeight(38)
        self.txt_url.returnPressed.connect(self._analyze_url)

        self.btn_paste = QPushButton("Paste", top_group)
        self.btn_paste.setMinimumHeight(38)
        self.btn_paste.clicked.connect(self._paste_url)

        self.btn_analyze = QPushButton("Analyze", top_group)
        self.btn_analyze.setObjectName("btnAnalyze")
        self.btn_analyze.setMinimumHeight(38)
        self.btn_analyze.clicked.connect(self._analyze_url)

        row_url.addWidget(self.txt_url, 1)
        row_url.addWidget(self.btn_paste)
        row_url.addWidget(self.btn_analyze)

        top_layout.addLayout(row_url)

        # تسمية لحالة الفحص
        self.lbl_status = QLabel("", top_group)
        self.lbl_status.setStyleSheet("color: #8e9bb0; font-size: 11px;")
        top_layout.addWidget(self.lbl_status)

        parent_layout.addWidget(top_group)

    # ==========================================
    # قسم معلومات الوسائط (Info Section)
    # ==========================================
    def _create_info_section(self, parent_layout: QVBoxLayout) -> None:
        self.grp_info = QGroupBox("Media Information", self)
        info_layout = QHBoxLayout(self.grp_info)
        info_layout.setContentsMargins(10, 10, 10, 10)
        info_layout.setSpacing(12)

        # صورة المعاينة (160x90)
        self.lbl_thumbnail = QLabel(self.grp_info)
        self.lbl_thumbnail.setFixedSize(160, 90)
        self.lbl_thumbnail.setStyleSheet(
            "background-color: #111526; border: 1px solid #23314f; border-radius: 6px;"
        )
        self.lbl_thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.lbl_thumbnail.setText("Preview")
        info_layout.addWidget(self.lbl_thumbnail)

        # النصوص الوصفية
        meta_layout = QVBoxLayout()
        meta_layout.setSpacing(4)

        self.lbl_title = QLabel("Title: --", self.grp_info)
        self.lbl_title.setStyleSheet("font-weight: bold; font-size: 13px; color: #ffffff;")
        self.lbl_title.setWordWrap(True)

        self.lbl_duration = QLabel("Duration: --:--", self.grp_info)
        self.lbl_duration.setStyleSheet("color: #8e9bb0; font-size: 12px;")

        self.lbl_platform = QLabel("Platform: Generic", self.grp_info)
        self.lbl_platform.setStyleSheet("color: #e94560; font-weight: bold; font-size: 12px;")

        meta_layout.addWidget(self.lbl_title)
        meta_layout.addWidget(self.lbl_duration)
        meta_layout.addWidget(self.lbl_platform)
        meta_layout.addStretch()

        info_layout.addLayout(meta_layout, 1)

        # إخفاء القسم مبدئياً حتى انتهاء الفحص
        self.grp_info.setVisible(False)
        parent_layout.addWidget(self.grp_info)

    # ==========================================
    # قسم عناصر قائمة التشغيل (Playlist Section)
    # ==========================================
    def _create_playlist_section(self, parent_layout: QVBoxLayout) -> None:
        """قسم استعراض واختيار فيديوهات قائمة التشغيل"""
        self.grp_playlist = QGroupBox("Playlist Items", self)
        playlist_layout = QVBoxLayout(self.grp_playlist)
        playlist_layout.setSpacing(6)
        playlist_layout.setContentsMargins(10, 10, 10, 10)

        header_row = QHBoxLayout()
        self.chk_playlist_select_all = QCheckBox("Select All Videos", self.grp_playlist)
        self.chk_playlist_select_all.setChecked(True)
        self.chk_playlist_select_all.toggled.connect(self._on_playlist_select_all_toggled)

        self.lbl_playlist_count = QLabel("0 videos selected", self.grp_playlist)
        self.lbl_playlist_count.setStyleSheet("color: #00cec9; font-weight: bold; font-size: 11px;")

        header_row.addWidget(self.chk_playlist_select_all)
        header_row.addStretch()
        header_row.addWidget(self.lbl_playlist_count)
        playlist_layout.addLayout(header_row)

        self.table_playlist = QTableWidget(self.grp_playlist)
        self.table_playlist.setColumnCount(3)
        self.table_playlist.setHorizontalHeaderLabels(["#", "Video Title", "Duration"])
        self.table_playlist.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table_playlist.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table_playlist.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_playlist.verticalHeader().setVisible(False)
        self.table_playlist.setAlternatingRowColors(True)
        self.table_playlist.setMinimumHeight(150)
        self.table_playlist.itemChanged.connect(self._on_playlist_item_changed)

        playlist_layout.addWidget(self.table_playlist)
        self.grp_playlist.setVisible(False)
        parent_layout.addWidget(self.grp_playlist)

    def _on_playlist_select_all_toggled(self, checked: bool) -> None:
        """تحديد أو إلغاء تحديد كافة عناصر قائمة التشغيل"""
        self.table_playlist.blockSignals(True)
        state = Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked
        for r in range(self.table_playlist.rowCount()):
            it = self.table_playlist.item(r, 0)
            if it:
                it.setCheckState(state)
        self.table_playlist.blockSignals(False)
        self._update_playlist_selection_status()

    def _on_playlist_item_changed(self, item: QTableWidgetItem) -> None:
        """تحديث عدد الفيديوهات المحددة عند تغيير خانة الاختيار"""
        if item and item.column() == 0:
            self._update_playlist_selection_status()

    def _update_playlist_selection_status(self) -> None:
        """حساب وتحديث نص الحالة وزر التحميل حسب الفيديوهات المحددة"""
        if not self._current_info.get("is_playlist"):
            return
        total = self.table_playlist.rowCount()
        selected = 0
        for r in range(total):
            it = self.table_playlist.item(r, 0)
            if it and it.checkState() == Qt.CheckState.Checked:
                selected += 1

        self.lbl_playlist_count.setText(f"Selected: {selected} / {total} videos")
        self.btn_download.setText(f"Start Download ({selected} Videos)")
        self.btn_download.setEnabled(selected > 0)

    # ==========================================
    # قسم اختيار الجودة والصيغة (Quality Section)
    # ==========================================
    def _create_quality_section(self, parent_layout: QVBoxLayout) -> None:
        self.grp_quality = QGroupBox("Available Formats & Qualities", self)
        quality_layout = QVBoxLayout(self.grp_quality)
        quality_layout.setSpacing(8)

        # شريط تصفية الصوت فقط
        filter_layout = QHBoxLayout()
        self.chk_audio_only = QCheckBox("Extract Audio Only (128 kbps - 320 kbps)", self.grp_quality)
        self.chk_audio_only.toggled.connect(self._on_audio_only_toggled)

        self.lbl_format_count = QLabel("", self.grp_quality)
        self.lbl_format_count.setStyleSheet("color: #8e9bb0; font-size: 11px;")

        filter_layout.addWidget(self.chk_audio_only)
        filter_layout.addStretch()
        filter_layout.addWidget(self.lbl_format_count)
        quality_layout.addLayout(filter_layout)

        # جدول الصيغ (Quality, Format, Size, Codec)
        self.table_formats = QTableWidget(self.grp_quality)
        self.table_formats.setColumnCount(4)
        self.table_formats.setHorizontalHeaderLabels([
            "Quality / Resolution",
            "Format",
            "Estimated Size",
            "Type / Codec"
        ])
        self.table_formats.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table_formats.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table_formats.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table_formats.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table_formats.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_formats.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table_formats.setAlternatingRowColors(True)
        self.table_formats.verticalHeader().setVisible(False)
        self.table_formats.setMinimumHeight(140)
        self.table_formats.itemSelectionChanged.connect(self._on_format_selection_changed)

        quality_layout.addWidget(self.table_formats)

        # بطاقة إبراز الجودة المختارة بوضوح تام (Prominent Selected Quality Badge)
        self.card_selected_quality = QFrame(self.grp_quality)
        self.card_selected_quality.setObjectName("selectedQualityBadge")
        self.card_selected_quality.setStyleSheet("""
            QFrame#selectedQualityBadge {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #162447, stop:1 #1f4068);
                border: 2px solid #e94560;
                border-radius: 8px;
                padding: 6px;
            }
        """)
        card_badge_layout = QVBoxLayout(self.card_selected_quality)
        card_badge_layout.setContentsMargins(12, 8, 12, 8)
        card_badge_layout.setSpacing(4)

        self.lbl_selected_quality_title = QLabel("🎯 Selected Quality: None", self.card_selected_quality)
        self.lbl_selected_quality_title.setStyleSheet("font-size: 13px; font-weight: bold; color: #00fff0;")

        self.lbl_selected_quality_detail = QLabel(
            "Click any format from the table above to choose quality",
            self.card_selected_quality
        )
        self.lbl_selected_quality_detail.setStyleSheet("font-size: 11px; color: #e2e8f0;")

        card_badge_layout.addWidget(self.lbl_selected_quality_title)
        card_badge_layout.addWidget(self.lbl_selected_quality_detail)

        quality_layout.addWidget(self.card_selected_quality)
        parent_layout.addWidget(self.grp_quality)

    # ==========================================
    # قسم الخيارات المتقدمة (Options Section)
    # ==========================================
    def _create_options_section(self, parent_layout: QVBoxLayout) -> None:
        grp_options = QGroupBox("Save & Conversion Options", self)
        opt_layout = QVBoxLayout(grp_options)
        opt_layout.setSpacing(12)
        opt_layout.setContentsMargins(12, 14, 12, 14)

        # 1. مجلد الحفظ
        save_layout = QHBoxLayout()
        lbl_save = QLabel("Save to:", grp_options)
        lbl_save.setMinimumWidth(60)
        self.txt_save_dir = QLineEdit(grp_options)
        default_dir = str(self.config.output_dir) if self.config else os.path.expanduser("~/Downloads/FlexDown")
        self.txt_save_dir.setText(default_dir)

        self.btn_browse = QPushButton("Browse...", grp_options)
        self.btn_browse.clicked.connect(self._browse_folder)

        save_layout.addWidget(lbl_save)
        save_layout.addWidget(self.txt_save_dir, 1)
        save_layout.addWidget(self.btn_browse)
        opt_layout.addLayout(save_layout)

        # 2. تحويل الصيغة بعد التنزيل
        conv_layout = QHBoxLayout()
        self.chk_convert = QCheckBox("Convert format after download:", grp_options)
        self.chk_convert.toggled.connect(self._on_convert_toggled)

        self.cmb_convert_format = QComboBox(grp_options)
        self.cmb_convert_format.addItems([
            "mp4", "mkv", "avi", "mov", "mp3", "wav", "flac", "aac", "ogg"
        ])
        self.cmb_convert_format.setEnabled(False)
        self.cmb_convert_format.setVisible(False)
        self.cmb_convert_format.setMinimumWidth(90)

        conv_layout.addWidget(self.chk_convert)
        conv_layout.addWidget(self.cmb_convert_format)
        conv_layout.addStretch()
        opt_layout.addLayout(conv_layout)

        # 3. تشفير الملف
        self.chk_encrypt = QCheckBox("Encrypt file after download (Password protection):", grp_options)
        self.chk_encrypt.toggled.connect(self._on_encrypt_toggled)
        opt_layout.addWidget(self.chk_encrypt)

        self.enc_container = QWidget(grp_options)
        enc_pass_layout = QHBoxLayout(self.enc_container)
        enc_pass_layout.setContentsMargins(24, 0, 0, 0)
        enc_pass_layout.setSpacing(8)

        self.lbl_enc_pass = QLabel("Password:", self.enc_container)
        self.txt_enc_pass = QLineEdit(self.enc_container)
        self.txt_enc_pass.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_enc_pass.setPlaceholderText("Enter password...")

        self.lbl_enc_confirm = QLabel("Confirm:", self.enc_container)
        self.txt_enc_confirm = QLineEdit(self.enc_container)
        self.txt_enc_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_enc_confirm.setPlaceholderText("Confirm password...")

        enc_pass_layout.addWidget(self.lbl_enc_pass)
        enc_pass_layout.addWidget(self.txt_enc_pass, 1)
        enc_pass_layout.addWidget(self.lbl_enc_confirm)
        enc_pass_layout.addWidget(self.txt_enc_confirm, 1)

        self.enc_container.setVisible(False)
        opt_layout.addWidget(self.enc_container)

        # 4. جدولة التنزيل
        sched_layout = QHBoxLayout()
        self.chk_schedule = QCheckBox("Schedule download for later:", grp_options)
        self.chk_schedule.toggled.connect(self._on_schedule_toggled)

        self.dt_schedule = QDateTimeEdit(grp_options)
        self.dt_schedule.setCalendarPopup(True)
        default_dt = QDateTime.currentDateTime().addSecs(15 * 60)
        self.dt_schedule.setDateTime(default_dt)
        self.dt_schedule.setDisplayFormat("yyyy-MM-dd HH:mm")
        self.dt_schedule.setEnabled(False)
        self.dt_schedule.setVisible(False)

        sched_layout.addWidget(self.chk_schedule)
        sched_layout.addWidget(self.dt_schedule)
        sched_layout.addStretch()
        opt_layout.addLayout(sched_layout)

        # 5. مجلد فرعي لقائمة التشغيل
        self.chk_playlist_subfolder = QCheckBox("Save all videos in a subfolder named after playlist", grp_options)
        self.chk_playlist_subfolder.setChecked(True)
        self.chk_playlist_subfolder.setVisible(False)
        opt_layout.addWidget(self.chk_playlist_subfolder)

        parent_layout.addWidget(grp_options)

    # ==========================================
    # القسم السفلي: أزرار التنزيل والإلغاء
    # ==========================================
    def _create_bottom_buttons(self, parent_layout: QVBoxLayout) -> None:
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_cancel = QPushButton(self.tr("dialog_add_cancel_btn") or "Cancel", self)
        self.btn_cancel.setMinimumHeight(38)
        self.btn_cancel.setMinimumWidth(100)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_download = QPushButton(self.tr("dialog_add_download_btn") or "Start Download", self)
        self.btn_download.setObjectName("primaryButton")
        self.btn_download.setMinimumHeight(38)
        self.btn_download.setMinimumWidth(140)
        self.btn_download.setDefault(True)
        self.btn_download.setStyleSheet("""
            QPushButton#primaryButton {
                background-color: #e94560;
                color: #ffffff;
                font-weight: bold;
                font-size: 13px;
                border-radius: 6px;
                padding: 6px 16px;
            }
            QPushButton#primaryButton:hover {
                background-color: #ff5975;
            }
            QPushButton#primaryButton:pressed {
                background-color: #c7354e;
            }
        """)
        self.btn_download.clicked.connect(self._on_download_clicked)

        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_download)

        parent_layout.addLayout(btn_layout)

    # ==========================================
    # معالجات الأحداث والوظائف (Event Handlers)
    # ==========================================
    def _paste_url(self) -> None:
        """لصق النص من الحافظة وفحصه تلقائياً"""
        text = QApplication.clipboard().text().strip()
        if text:
            cleaned = normalize_url(text)
            self.txt_url.setText(cleaned)
            self._analyze_url()

    def _browse_folder(self) -> None:
        """اختيار مجلد الحفظ"""
        current_dir = self.txt_save_dir.text().strip() or os.path.expanduser("~/Downloads")
        selected = QFileDialog.getExistingDirectory(
            self,
            "Select Download Directory",
            current_dir,
            QFileDialog.Option.ShowDirsOnly,
        )
        if selected:
            self.txt_save_dir.setText(selected)

    def _on_convert_toggled(self, checked: bool) -> None:
        self.cmb_convert_format.setEnabled(checked)
        self.cmb_convert_format.setVisible(checked)

    def _on_encrypt_toggled(self, checked: bool) -> None:
        self.enc_container.setVisible(checked)
        self.txt_enc_pass.setEnabled(checked)
        self.txt_enc_confirm.setEnabled(checked)
        if checked:
            self.txt_enc_pass.setFocus()

    def _on_schedule_toggled(self, checked: bool) -> None:
        self.dt_schedule.setEnabled(checked)
        self.dt_schedule.setVisible(checked)

    def _on_audio_only_toggled(self, checked: bool) -> None:
        """تصفية جدول الجودات لعرض الصوتيات فقط أو الكل"""
        self._populate_formats_table(self._raw_formats)

    def _analyze_url(self) -> None:
        """فحص الرابط واستخراج الصيغ المتاحة بتقنية الفحص السريع والذكي"""
        raw_url = self.txt_url.text().strip()
        if not raw_url:
            self.lbl_status.setText("Please enter a valid URL first.")
            self.lbl_status.setStyleSheet("color: #e67e22;")
            return

        url = normalize_url(raw_url)
        if url != raw_url:
            self.txt_url.setText(url)

        if not is_valid_url(url):
            self.lbl_status.setText("Warning: The entered URL is not valid.")
            self.lbl_status.setStyleSheet("color: #d63031;")
            return

        # إلغاء أي فحص سابق قيد التشغيل
        if self._fetcher and self._fetcher.isRunning():
            self._fetcher.cancel()
            self._fetcher.wait(300)
        if self._probe_worker and self._probe_worker.isRunning():
            self._probe_worker.terminate()
            self._probe_worker.wait(300)

        self.btn_analyze.setEnabled(False)
        self.lbl_status.setText("Analyzing URL and probing file details...")
        self.lbl_status.setStyleSheet("color: #00cec9; font-weight: bold;")

        platform = detect_platform(url)
        proxy_str = self.config.proxy if self.config else None

        if platform != "generic":
            # منصات الفيديو والشبكات الاجتماعية (YouTube, TikTok, Facebook, etc.) تفحص عبر yt-dlp
            self._start_ytdlp_fetch(url)
        else:
            # الروابط المباشرة وكافة أنواع الملفات (.exe, .iso, .zip, .rar, .pdf, إلخ) تفحص فورياً عبر Range probe
            self._probe_worker = DirectFileProbeWorker(url=url, proxy=proxy_str, parent=self)
            self._probe_worker.probe_finished.connect(lambda res: self._on_direct_probe_ready(url, res))
            self._probe_worker.start()

    def _start_ytdlp_fetch(self, url: str) -> None:
        """تشغيل مستخرج الجودات والوسائط yt-dlp"""
        proxy_str = self.config.proxy if self.config else None
        self._fetcher = FormatFetcher(url=url, proxy=proxy_str, parent=self)
        self._fetcher.formats_ready.connect(self._on_formats_ready)
        self._fetcher.error.connect(self._on_fetch_error)
        self._fetcher.start()

    def _on_direct_probe_ready(self, url: str, probe: Dict[str, Any]) -> None:
        """معالجة نتيجة الفحص السريع للرابط المباشر"""
        if probe.get("success") and not probe.get("is_html"):
            self.btn_analyze.setEnabled(True)
            if probe.get("target_url") and probe.get("target_url") != url:
                self.txt_url.setText(probe["target_url"])

            fn = probe.get("filename") or "downloaded_file"
            fsize = probe.get("filesize", 0)
            supports_range = probe.get("supports_range", False)
            cat = probe.get("category", "OTHER")
            ext = get_file_extension(fn) or "bin"

            status_msg = (
                "🚀 Turbo Multi-Segment Ready (16 Parallel Streams, Range Supported)"
                if supports_range else
                "Direct Download Ready (Standard Stream)"
            )
            self.lbl_status.setText(status_msg)
            self.lbl_status.setStyleSheet("color: #00b894; font-weight: bold;")

            self.grp_playlist.setVisible(False)
            self.chk_playlist_subfolder.setVisible(False)
            self.grp_info.setVisible(True)

            self.lbl_title.setText(f"File: {fn}")
            self.lbl_duration.setText(f"Type: {cat} | Size: {format_size(fsize) if fsize > 0 else '--'}")
            mode_lbl = "⚡ 16 Parallel Connections (IDM-Power)" if supports_range else "Single Stream"
            self.lbl_platform.setText(f"Turbo Mode: {mode_lbl}")
            self.lbl_thumbnail.setText(f"[{cat}]")

            fmt_id = "turbo" if supports_range else "direct"
            res_text = "🚀 Turbo Accelerated (16x)" if supports_range else "Standard Direct"
            codec_text = "aria2c Multi-Segment" if supports_range else "HTTP Stream"

            direct_format = [{
                "format_id": fmt_id,
                "resolution": res_text,
                "ext": ext,
                "filesize": fsize,
                "vcodec": codec_text,
                "acodec": "N/A",
                "group": "direct",
                "audio_only": False,
            }]
            self._raw_formats = direct_format
            self._current_info = {
                "title": fn,
                "duration": 0,
                "thumbnail": "",
                "filesize": fsize,
                "ext": ext,
                "is_direct": True,
            }
            self._populate_formats_table(direct_format)
        else:
            # إذا كان الرابط صفحة ويب HTML أو فشل الفحص السريع، نجرب yt-dlp
            self._start_ytdlp_fetch(url)

    def _on_formats_ready(self, info: Dict[str, Any], formats: List[Dict[str, Any]]) -> None:
        """معالجة نتيجة استخراج الصيغ بنجاح"""
        self.btn_analyze.setEnabled(True)
        self._current_info = info or {}
        self._raw_formats = formats or []

        is_playlist = bool(info.get("is_playlist"))
        title = info.get("title", "Untitled")
        duration = float(info.get("duration", 0.0))

        if is_playlist:
            entries = info.get("entries") or []
            self.lbl_status.setText(f"Playlist analyzed successfully: {len(entries)} videos found.")
            self.lbl_status.setStyleSheet("color: #00b894; font-weight: bold;")

            self.grp_playlist.setVisible(True)
            self.chk_playlist_subfolder.setVisible(True)

            self.table_playlist.blockSignals(True)
            self.table_playlist.setRowCount(len(entries))
            for i, entry in enumerate(entries):
                item_check = QTableWidgetItem(f" {i+1}")
                item_check.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                item_check.setCheckState(Qt.CheckState.Checked)
                item_check.setData(Qt.ItemDataRole.UserRole, entry)

                item_title = QTableWidgetItem(str(entry.get("title", "Untitled")))
                item_title.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

                dur_sec = float(entry.get("duration") or 0.0)
                item_dur = QTableWidgetItem(format_duration(dur_sec))
                item_dur.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)

                self.table_playlist.setItem(i, 0, item_check)
                self.table_playlist.setItem(i, 1, item_title)
                self.table_playlist.setItem(i, 2, item_dur)
            self.table_playlist.blockSignals(False)

            self.chk_playlist_select_all.setChecked(True)
            self._update_playlist_selection_status()

            self.grp_info.setVisible(True)
            self.lbl_title.setText(f"📁 Playlist: {title}")
            self.lbl_duration.setText(f"Total Duration: {format_duration(duration)} ({len(entries)} items)")
            self.lbl_platform.setText("Platform: YOUTUBE PLAYLIST")
        else:
            self.lbl_status.setText("URL analyzed successfully.")
            self.lbl_status.setStyleSheet("color: #00b894; font-weight: bold;")
            self.grp_playlist.setVisible(False)
            self.chk_playlist_subfolder.setVisible(False)
            self.btn_download.setText(self.tr("dialog_add_download_btn") or "Start Download")
            self.btn_download.setEnabled(True)

            # إذا كان الرابط صوتياً فقط، نقوم بتفعيل خيار الصوت فقط تلقائياً
            has_video = any(f.get("group") == "video" for f in self._raw_formats)
            if not has_video:
                self.chk_audio_only.setChecked(True)

            self.grp_info.setVisible(True)
            self.lbl_title.setText(f"Title: {title}")
            self.lbl_duration.setText(f"Duration: {format_duration(duration)}")
            url = self.txt_url.text().strip()
            platform_name = detect_platform(url)
            self.lbl_platform.setText(f"Platform: {platform_name.upper()}")

        # تحميل الصورة المصغرة (Thumbnail)
        thumb_url = info.get("thumbnail")
        if thumb_url:
            self._load_thumbnail(thumb_url)
        else:
            self.lbl_thumbnail.setText("No Image")

        # ملء جدول الجودات
        self._populate_formats_table(self._raw_formats)

        # تحميل الصورة المصغرة (Thumbnail)
        thumb_url = info.get("thumbnail")
        if thumb_url:
            self._load_thumbnail(thumb_url)
        else:
            self.lbl_thumbnail.setText("No Image")

        # ملء جدول الجودات
        self._populate_formats_table(self._raw_formats)

    def _on_fetch_error(self, err_msg: str) -> None:
        """معالجة الخطأ الصادر أثناء فحص yt-dlp (مثل الروابط المباشرة لملفات zip, iso, etc.)"""
        self.btn_analyze.setEnabled(True)
        url = self.txt_url.text().strip()

        # إذا كان الرابط مباشراً لملف عادي، نضيف خيار تنزيل قياسي
        if is_direct_download(url) or "." in os.path.basename(urllib.parse.urlparse(url).path):
            self.lbl_status.setText("Direct file download link detected.")
            self.lbl_status.setStyleSheet("color: #00b894;")

            parsed = urllib.parse.urlparse(url)
            filename = os.path.basename(parsed.path) or "downloaded_file"
            ext = get_file_extension(filename) or "bin"

            self.grp_info.setVisible(True)
            self.lbl_title.setText(f"File: {filename}")
            self.lbl_duration.setText("Direct File")
            self.lbl_platform.setText("Platform: HTTP Direct")
            self.lbl_thumbnail.setText("File")

            direct_format = [{
                "format_id": "direct",
                "resolution": "Original",
                "ext": ext,
                "filesize": 0,
                "vcodec": "direct",
                "acodec": "direct",
                "group": "direct",
                "audio_only": False,
            }]
            self._raw_formats = direct_format
            self._current_info = {
                "title": filename,
                "duration": 0,
                "thumbnail": "",
            }
            self._populate_formats_table(direct_format)
        else:
            self.lbl_status.setText(f"Could not extract media info: {err_msg[:60]}")
            self.lbl_status.setStyleSheet("color: #d63031;")

    def _load_thumbnail(self, url: str) -> None:
        """بدء تحميل الصورة المصغرة في خيط منفصل"""
        self.lbl_thumbnail.setText("Loading...")
        self._thumb_loader = _ThumbnailLoader(url, self)
        self._thumb_loader.loaded.connect(self._on_thumbnail_data)
        self._thumb_loader.failed.connect(lambda: self.lbl_thumbnail.setText("No Preview"))
        self._thumb_loader.start()

    def _on_thumbnail_data(self, data: bytes) -> None:
        """عرض صورة المعاينة بعد تحميلها"""
        pix = QPixmap()
        if pix.loadFromData(data):
            scaled = pix.scaled(
                160, 90,
                Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                Qt.TransformationMode.SmoothTransformation,
            )
            self.lbl_thumbnail.setPixmap(scaled)

    def _populate_formats_table(self, formats: List[Dict[str, Any]]) -> None:
        """تعبئة جدول الصيغ مع تطبيق التصفية للصوتيات إذا كانت مفعلة"""
        self.table_formats.setRowCount(0)
        audio_only = self.chk_audio_only.isChecked()

        filtered_formats: List[Dict[str, Any]] = []
        for fmt in formats:
            group = fmt.get("group", "")
            is_audio = fmt.get("audio_only", False) or group == "audio_only" or (
                "audio" in group and "video" not in group)
            if audio_only:
                if is_audio:
                    filtered_formats.append(fmt)
            else:
                if not is_audio:
                    filtered_formats.append(fmt)

        if not filtered_formats and formats:
            filtered_formats = formats

        self.table_formats.setRowCount(len(filtered_formats))
        self.lbl_format_count.setText(f"Available: {len(filtered_formats)}")

        for row, fmt in enumerate(filtered_formats):
            res = fmt.get("resolution", "N/A")
            ext = fmt.get("ext", "N/A")
            fsize = fmt.get("filesize", 0)
            size_str = format_size(fsize) if fsize > 0 else "--"
            codec_str = fmt.get("codec") or fmt.get("vcodec") or "N/A"

            item_res = QTableWidgetItem(str(res))
            item_ext = QTableWidgetItem(str(ext).upper())
            item_size = QTableWidgetItem(size_str)
            item_codec = QTableWidgetItem(str(codec_str))

            item_res.setData(Qt.ItemDataRole.UserRole, fmt)

            for it in (item_res, item_ext, item_size, item_codec):
                it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)

            self.table_formats.setItem(row, 0, item_res)
            self.table_formats.setItem(row, 1, item_ext)
            self.table_formats.setItem(row, 2, item_size)
            self.table_formats.setItem(row, 3, item_codec)

        # تحديد الصف الأول تلقائياً كخيار افتراضي
        if filtered_formats:
            self.table_formats.selectRow(0)
            self._on_format_selection_changed()

    def _on_format_selection_changed(self) -> None:
        """تحديث بطاقة الجودة المختارة وزر التحميل فورياً وبشكل بارز جداً"""
        if not hasattr(self, "card_selected_quality"):
            return
        selected_rows = self.table_formats.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        fmt_item = self.table_formats.item(row, 0)
        if not fmt_item:
            return
        fmt_data = fmt_item.data(Qt.ItemDataRole.UserRole) or {}
        res = fmt_data.get("resolution", "Default")
        ext = str(fmt_data.get("ext", "mp4")).upper()
        fsize = fmt_data.get("filesize", 0)
        size_str = format_size(fsize) if fsize > 0 else "غير محدد"
        codec = fmt_data.get("codec") or fmt_data.get("vcodec") or "Media Stream"
        is_audio = fmt_data.get("audio_only", False)

        is_ar = (self.config.language == "ar") if self.config else True
        if is_ar:
            type_lbl = "صوت نقي (Audio Only)" if is_audio else "فيديو وصوت عالي الدقة"
            self.lbl_selected_quality_title.setText(f"🎯 الجودة المختارة: {res} • {ext}")
            self.lbl_selected_quality_detail.setText(
                f"📦 الصيغة: {ext}  |  💾 الحجم التقريبي: {size_str}  |  ⚡ النوع: {type_lbl} ({codec})"
            )
            self.btn_download.setText(f"🚀 بدء التنزيل ({res})")
        else:
            type_lbl = "High Quality Audio" if is_audio else "HD Video + Audio"
            self.lbl_selected_quality_title.setText(f"🎯 Selected Quality: {res} • {ext}")
            self.lbl_selected_quality_detail.setText(
                f"📦 Format: {ext}  |  💾 Approx Size: {size_str}  |  ⚡ Type: {type_lbl} ({codec})"
            )
            self.btn_download.setText(f"🚀 Start Download ({res})")

    def _on_download_clicked(self) -> None:
        """التحقق من صحة المدخلات وبناء عناصر التنزيل ثم إغلاق النافذة بنجاح"""
        url = self.txt_url.text().strip()
        if not url:
            QMessageBox.warning(self, "Warning", "Please enter a valid URL first.")
            return

        save_dir = self.txt_save_dir.text().strip()
        if not save_dir:
            QMessageBox.warning(self, "Warning", "Please select a valid destination folder.")
            return

        # التحقق من كلمات مرور التشفير إن كان مفعلاً
        if self.chk_encrypt.isChecked():
            p1 = self.txt_enc_pass.text()
            p2 = self.txt_enc_confirm.text()
            if not p1:
                QMessageBox.warning(self, "Encryption Warning", "Please enter a password to encrypt the file.")
                return
            if p1 != p2:
                QMessageBox.warning(self, "Encryption Warning", "Passwords do not match.")
                return

        self.accept()

    def get_download_items(self) -> List[DownloadItem]:
        """
        بناء وإرجاع قائمة بعناصر التنزيل DownloadItem المحددة من قبل المستخدم.
        Builds and returns a list of DownloadItem instances from current dialog settings.
        Supports expanding playlist entries into individual download items.
        """
        url = self.txt_url.text().strip()
        save_dir = self.txt_save_dir.text().strip() or os.path.expanduser("~/Downloads/FlexDown")
        os.makedirs(save_dir, exist_ok=True)

        audio_only = self.chk_audio_only.isChecked()
        convert_to = self.cmb_convert_format.currentText() if self.chk_convert.isChecked() else None
        encrypt = self.chk_encrypt.isChecked()

        # الجدولة
        scheduled_iso = None
        if self.chk_schedule.isChecked():
            dt = self.dt_schedule.dateTime().toPyDateTime()
            scheduled_iso = dt.isoformat()

        title = self._current_info.get("title", "")
        duration = float(self._current_info.get("duration", 0.0))
        thumbnail = self._current_info.get("thumbnail", "")

        platform_str = detect_platform(url)

        # ==========================================
        # معالجة قوائم التشغيل (Playlist Expansion)
        # ==========================================
        if self._current_info.get("is_playlist"):
            playlist_title = self._current_info.get("title") or "YouTube Playlist"
            if self.chk_playlist_subfolder.isChecked():
                target_dir = os.path.join(save_dir, sanitize_filename(playlist_title))
            else:
                target_dir = save_dir
            os.makedirs(target_dir, exist_ok=True)

            format_id = "bestvideo[height<=1080]+bestaudio/best[height<=1080]"
            ext = "mp3" if audio_only else "mp4"
            audio_fmt = "mp3"
            audio_q = "320"
            is_audio = audio_only

            selected_rows = self.table_formats.selectionModel().selectedRows()
            if selected_rows:
                fmt_item = self.table_formats.item(selected_rows[0].row(), 0)
                fmt_data = fmt_item.data(Qt.ItemDataRole.UserRole) if fmt_item else {}
                format_id = fmt_data.get("format_id", format_id)
                ext = fmt_data.get("ext", ext)
                is_audio = fmt_data.get("audio_only", audio_only)
                audio_fmt = fmt_data.get("audio_format", "mp3")
                audio_q = fmt_data.get("audio_quality", "320")

            selected_entries = []
            for r in range(self.table_playlist.rowCount()):
                it = self.table_playlist.item(r, 0)
                if it and it.checkState() == Qt.CheckState.Checked:
                    entry_data = it.data(Qt.ItemDataRole.UserRole)
                    if entry_data:
                        selected_entries.append(entry_data)

            if not selected_entries:
                selected_entries = self._current_info.get("entries", [])

            items: List[DownloadItem] = []
            for entry in selected_entries:
                v_title = entry.get("title") or "Untitled Video"
                clean_title = sanitize_filename(v_title)
                v_filename = f"{clean_title}.{ext}" if ext else clean_title
                v_duration = float(entry.get("duration") or 0.0)
                v_thumb = entry.get("thumbnail") or ""
                v_url = entry.get("url") or url

                media_type = MediaType.AUDIO if is_audio else MediaType.VIDEO

                item = DownloadItem(
                    url=v_url,
                    output_dir=target_dir,
                    filename=v_filename,
                    title=v_title,
                    extension=ext,
                    filesize=0,
                    media_type=media_type,
                    thumbnail_url=v_thumb,
                    duration=v_duration,
                    status=DownloadStatus.SCHEDULED if scheduled_iso else DownloadStatus.QUEUED,
                    format_id=format_id,
                    audio_only=is_audio,
                    audio_format=audio_fmt,
                    audio_quality=audio_q,
                    convert_to=convert_to,
                    encrypt=encrypt,
                    scheduled_time=scheduled_iso,
                    proxy=self.config.proxy if self.config else None,
                )
                items.append(item)

            return items

        # ==========================================
        # تنزيل ملف فردي (Single Video / File)
        # ==========================================
        selected_rows = self.table_formats.selectionModel().selectedRows()
        items = []

        if selected_rows:
            for index in selected_rows:
                row = index.row()
                fmt_item = self.table_formats.item(row, 0)
                fmt_data = fmt_item.data(Qt.ItemDataRole.UserRole) if fmt_item else {}

                format_id = fmt_data.get("format_id", "")
                res = fmt_data.get("resolution", "")
                ext = fmt_data.get("ext", "")
                filesize = fmt_data.get("filesize", 0)
                is_audio = fmt_data.get("audio_only", audio_only)
                audio_fmt = fmt_data.get("audio_format", "mp3")
                audio_q = fmt_data.get("audio_quality", "320")

                raw_title = title or self._current_info.get("title") or ""
                if not raw_title:
                    p = urllib.parse.urlparse(url)
                    raw_title = os.path.splitext(os.path.basename(p.path))[0] or "FlexDown_Download"

                clean_title = sanitize_filename(raw_title)

                # إضافة وسم الجودة بوضوح تام لاسم الملف ليظهر بالجدول
                q_label = str(res or "")
                tag = ""
                if is_audio and audio_q and f"{audio_q}k" not in clean_title:
                    tag = f"[{audio_q}k]"
                    q_label = f"{audio_q}k"
                elif res and res not in ("N/A", "Default", "direct", "turbo"):
                    short_tag = res.split()[0]
                    if short_tag not in clean_title:
                        tag = f"[{short_tag}]"

                if tag and tag not in clean_title:
                    base_name = f"{clean_title} {tag}"
                else:
                    base_name = clean_title

                if ext and not base_name.lower().endswith(f".{ext.lower()}"):
                    filename = f"{base_name}.{ext}"
                else:
                    filename = base_name

                media_type = MediaType.AUDIO if is_audio else (
                    MediaType.VIDEO if platform_str != "generic" else MediaType.OTHER
                )

                item = DownloadItem(
                    url=url,
                    output_dir=save_dir,
                    filename=filename,
                    title=f"{raw_title} {tag}".strip(),
                    quality_label=q_label,
                    extension=ext,
                    filesize=filesize,
                    media_type=media_type,
                    thumbnail_url=thumbnail,
                    duration=duration,
                    status=DownloadStatus.SCHEDULED if scheduled_iso else DownloadStatus.QUEUED,
                    format_id=format_id,
                    audio_only=is_audio,
                    audio_format=audio_fmt,
                    audio_quality=audio_q,
                    convert_to=convert_to,
                    encrypt=encrypt,
                    scheduled_time=scheduled_iso,
                    proxy=self.config.proxy if self.config else None,
                )
                items.append(item)
        else:
            # تنزيل افتراضي بدون اختيار صف محدد
            clean_title = sanitize_filename(title or "flexdown_download")
            ext = get_file_extension(url) or ("mp3" if audio_only else "mp4")
            if ext and not clean_title.lower().endswith(f".{ext.lower()}"):
                filename = f"{clean_title}.{ext}"
            else:
                filename = clean_title

            media_type = MediaType.AUDIO if audio_only else (
                MediaType.VIDEO if platform_str != "generic" else MediaType.OTHER
            )

            item = DownloadItem(
                url=url,
                output_dir=save_dir,
                filename=filename,
                title=title or filename,
                extension=ext,
                filesize=0,
                media_type=media_type,
                thumbnail_url=thumbnail,
                duration=duration,
                status=DownloadStatus.SCHEDULED if scheduled_iso else DownloadStatus.QUEUED,
                format_id="",
                audio_only=audio_only,
                audio_format="mp3",
                audio_quality="320",
                convert_to=convert_to,
                encrypt=encrypt,
                scheduled_time=scheduled_iso,
                proxy=self.config.proxy if self.config else None,
            )
            items.append(item)

        return items
