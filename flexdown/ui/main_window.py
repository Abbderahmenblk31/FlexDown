"""
النافذة الرئيسية لبرنامج فليكس داون (FlexDown Main Window)
نافذة تحكم احترافية وعصرية تشبه IDM مع دعم كامل للغة العربية (RTL) والمظهر الداكن:
- شريط القوائم (File, Downloads, Tools, Settings, Help)
- شريط الأدوات بأيقونات 28x28 مع نصوص تحت الأيقونات
- حقل إدخال الرابط السريع بالأعلى
- جدول التنزيلات التفاعلي مع أشرطة تقدم مخصصة (DownloadProgressBar)
- لوحة التفاصيل السفلية القابلة للطي
- شريط الحالة (التحميلات النشطة، السرعة الإجمالية، والمساحة المتوفرة بالقرص)
- أيقونة صينية النظام (System Tray) مع التصغير التلقائي وقائمة الإجراءات
- دعم السحب والإفلات (Drag & Drop) لكافة الروابط والملفات
"""

import os
import sys
import subprocess
import json
from pathlib import Path
from typing import Optional, Dict, List, Any

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QToolBar,
    QStatusBar,
    QMenu,
    QSystemTrayIcon,
    QFileDialog,
    QMessageBox,
    QDialog,
    QPlainTextEdit,
    QFrame,
    QApplication,
    QAbstractItemView,
    QStyle,
    QComboBox,
)
from PyQt6.QtCore import Qt, QTimer, QSize, QUrl
from PyQt6.QtGui import QAction, QIcon, QKeySequence, QDesktopServices

from flexdown.constants import (
    APP_NAME,
    VERSION,
    DEFAULT_DOWNLOAD_DIR,
)
from flexdown.models.download_item import DownloadItem, DownloadStatus
from flexdown.core.queue_manager import QueueManager
from flexdown.utils.config import Config, get_config
from flexdown.i18n.translator import AppTranslator, get_translator
from flexdown.utils.file_utils import (
    format_size,
    format_speed,
    get_free_disk_space,
)
from flexdown.utils.url_utils import (
    detect_platform,
    is_valid_url,
    is_playlist_url,
    normalize_url,
    is_direct_download,
)
from flexdown.ui.widgets.progress_widget import DownloadProgressBar
from flexdown.ui.download_dialog import AddDownloadDialog
from flexdown.ui.settings_dialog import SettingsDialog
from flexdown.ui.completion_dialog import DownloadCompleteDialog
from flexdown.ui.extension_dialog import BrowserIntegrationDialog
from flexdown.core.bridge_server import BridgeServer
from flexdown.themes import load_theme


class MainWindow(QMainWindow):
    """
    النافذة الرئيسية لبرنامج FlexDown.
    Professional download manager main window featuring IDM-like workflows,
    rich statistics, custom progress bars, and full localization.
    """

    def __init__(
        self,
        config: Optional[Config] = None,
        queue_manager: Optional[QueueManager] = None,
        translator: Optional[AppTranslator] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.config: Config = config or get_config()
        self.queue_manager: QueueManager = queue_manager or QueueManager(
            max_concurrent=self.config.max_concurrent
        )
        self._translator: AppTranslator = translator or get_translator(self.config.language)

        # ربط خريطة الصفوف والعناصر
        self._item_rows: Dict[str, int] = {}
        self._details_collapsed: bool = False

        # إعدادات النافذة الأساسية
        self.setMinimumSize(1000, 650)
        self.resize(1150, 720)
        self.setWindowTitle(f"{APP_NAME} - {self.tr('app_tagline') or 'مدير التنزيل المتقدم'}")
        self.setAcceptDrops(True)
        self.setWindowIcon(self._get_icon(QStyle.StandardPixmap.SP_ArrowDown, "app"))

        # بناء واجهة المستخدم بالكامل
        self._init_menu_bar()
        self._init_toolbar()
        self._init_central_ui()
        self._init_status_bar()
        self._init_system_tray()

        # ربط إشارات مدير قائمة التحميل
        self._connect_queue_signals()

        # تشغيل مؤقت تحديث شريط الحالة كل ثانية
        self._status_timer = QTimer(self)
        self._status_timer.timeout.connect(self._update_status_bar)
        self._status_timer.start(1000)

        # التحديث الأولي للجدول وشريط الحالة
        self._refresh_table()
        self._update_status_bar()

        # تشغيل خادم الربط المحلي لإضافة المتصفح (Browser Extension Bridge)
        self._bridge_server = BridgeServer(port=18888, parent=self)
        self._bridge_server.download_requested.connect(self._on_bridge_download_requested)
        self._bridge_server.start()

        # مراقبة الحافظة الذكية لالتقاط الروابط تلقائياً مثل IDM
        self._last_clipboard_url = ""
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.dataChanged.connect(self._on_clipboard_changed)

    def tr(self, key: str, **kwargs) -> str:
        """ترجمة النصوص بالاعتماد على محرك الترجمة AppTranslator"""
        if self._translator:
            return self._translator(key, **kwargs)
        return key

    def _get_icon(self, standard_pixmap: QStyle.StandardPixmap, name: Optional[str] = None) -> QIcon:
        """الحصول على أيقونة قياسية من سمة النظام أو مجلد الموارد إن توفرت"""
        if name:
            res_path = Path(__file__).parent.parent.parent / "resources" / "icons" / f"{name}.png"
            if res_path.exists():
                return QIcon(str(res_path))
        return self.style().standardIcon(standard_pixmap)

    # ==========================================
    # شريط القوائم (Menu Bar)
    # ==========================================
    def _init_menu_bar(self) -> None:
        menubar = self.menuBar()

        # 1. File Menu
        file_menu = menubar.addMenu(self.tr("menu_file") or "File")

        act_add = QAction(self._get_icon(QStyle.StandardPixmap.SP_FileIcon, "add"),
                          self.tr("menu_file_add_url") or "Add Download URL...", self)
        act_add.setShortcut(QKeySequence("Ctrl+N"))
        act_add.triggered.connect(self._add_download_url)
        file_menu.addAction(act_add)

        act_batch = QAction(self._get_icon(QStyle.StandardPixmap.SP_FileDialogNewFolder),
                            self.tr("menu_file_add_batch") or "Add Batch Downloads...", self)
        act_batch.triggered.connect(self._add_batch_urls)
        file_menu.addAction(act_batch)

        file_menu.addSeparator()

        act_import = QAction(self.tr("menu_file_import_urls") or "Import URLs from File...", self)
        act_import.triggered.connect(self._import_urls)
        file_menu.addAction(act_import)

        act_export = QAction(self.tr("menu_file_export_urls") or "Export URLs to File...", self)
        act_export.triggered.connect(self._export_urls)
        file_menu.addAction(act_export)

        file_menu.addSeparator()

        act_exit = QAction(self._get_icon(QStyle.StandardPixmap.SP_DialogCloseButton),
                           self.tr("menu_file_exit") or "Exit", self)
        act_exit.setShortcut(QKeySequence("Ctrl+Q"))
        act_exit.triggered.connect(self.close)
        file_menu.addAction(act_exit)

        # 2. Downloads Menu
        dl_menu = menubar.addMenu(self.tr("menu_downloads") or "Downloads")

        act_pause_all = QAction(self._get_icon(QStyle.StandardPixmap.SP_MediaPause),
                                self.tr("menu_downloads_pause_all") or "Pause All", self)
        act_pause_all.triggered.connect(self.queue_manager.pause_all)
        dl_menu.addAction(act_pause_all)

        act_resume_all = QAction(self._get_icon(QStyle.StandardPixmap.SP_MediaPlay),
                                 self.tr("menu_downloads_resume_all") or "Resume All", self)
        act_resume_all.triggered.connect(self.queue_manager.resume_all)
        dl_menu.addAction(act_resume_all)

        act_cancel_all = QAction(self._get_icon(QStyle.StandardPixmap.SP_DialogCancelButton),
                                 self.tr("menu_downloads_cancel_all") or "Cancel All", self)
        act_cancel_all.triggered.connect(self.queue_manager.cancel_all)
        dl_menu.addAction(act_cancel_all)

        dl_menu.addSeparator()

        act_clear_comp = QAction(self._get_icon(QStyle.StandardPixmap.SP_TrashIcon),
                                 self.tr("menu_edit_clear_completed") or "Clear Completed", self)
        act_clear_comp.triggered.connect(self._clear_completed)
        dl_menu.addAction(act_clear_comp)

        # 3. Tools Menu
        tools_menu = menubar.addMenu(self.tr("menu_tools") or "Tools")

        act_converter = QAction(self._get_icon(QStyle.StandardPixmap.SP_BrowserReload),
                                self.tr("menu_tools_converter") or "Media Converter...", self)
        act_converter.triggered.connect(self._open_converter_dialog)
        tools_menu.addAction(act_converter)

        act_scheduler = QAction(self._get_icon(QStyle.StandardPixmap.SP_DialogYesButton),
                                self.tr("menu_downloads_schedule") or "Download Scheduler...", self)
        act_scheduler.triggered.connect(self._open_scheduler_dialog)
        tools_menu.addAction(act_scheduler)

        tools_menu.addSeparator()

        act_browser_ext = QAction(self._get_icon(QStyle.StandardPixmap.SP_DriveNetIcon),
                                  "Browser Integration (Chrome / Edge)...", self)
        act_browser_ext.triggered.connect(self._open_browser_integration_dialog)
        tools_menu.addAction(act_browser_ext)

        # 4. Settings Menu
        settings_menu = menubar.addMenu(self.tr("menu_settings") or "Settings")

        act_pref = QAction(self._get_icon(QStyle.StandardPixmap.SP_FileDialogDetailedView),
                           self.tr("menu_settings_preferences") or "Preferences...", self)
        act_pref.triggered.connect(self._open_settings)
        settings_menu.addAction(act_pref)

        act_proxy = QAction(self._get_icon(QStyle.StandardPixmap.SP_DriveNetIcon),
                            self.tr("menu_tools_proxy") or "Proxy Settings...", self)
        act_proxy.triggered.connect(self._open_proxy_settings)
        settings_menu.addAction(act_proxy)

        # Language Submenu
        lang_sub = settings_menu.addMenu(self.tr("menu_settings_language") or "Language")
        act_en = QAction("English", self)
        act_en.setCheckable(True)
        act_en.setChecked(self.config.language == "en")
        act_en.triggered.connect(lambda: self._change_language("en"))
        lang_sub.addAction(act_en)

        act_ar = QAction("العربية (Arabic)", self)
        act_ar.setCheckable(True)
        act_ar.setChecked(self.config.language == "ar")
        act_ar.triggered.connect(lambda: self._change_language("ar"))
        lang_sub.addAction(act_ar)

        settings_menu.addSeparator()

        # Day / Night Theme Toggle in Settings
        self.act_menu_theme = QAction(self)
        self.act_menu_theme.setShortcut(QKeySequence("F10"))
        self.act_menu_theme.triggered.connect(self._toggle_theme)
        settings_menu.addAction(self.act_menu_theme)

        # 5. Help Menu
        help_menu = menubar.addMenu(self.tr("menu_help") or "Help")

        act_about = QAction(self._get_icon(QStyle.StandardPixmap.SP_DialogHelpButton),
                            self.tr("menu_help_about") or "About FlexDown...", self)
        act_about.triggered.connect(self._show_about)
        help_menu.addAction(act_about)

    # ==========================================
    # Toolbar
    # ==========================================
    def _init_toolbar(self) -> None:
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setIconSize(QSize(28, 28))
        toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        # Main Action Buttons
        act_add = QAction(self._get_icon(QStyle.StandardPixmap.SP_FileIcon, "add"),
                          self.tr("toolbar_add") or "Add URL", self)
        act_add.triggered.connect(self._add_download_url)
        toolbar.addAction(act_add)

        act_pause = QAction(self._get_icon(QStyle.StandardPixmap.SP_MediaPause, "pause"),
                            self.tr("toolbar_pause") or "Pause", self)
        act_pause.triggered.connect(self._on_toolbar_pause)
        toolbar.addAction(act_pause)

        act_resume = QAction(self._get_icon(QStyle.StandardPixmap.SP_MediaPlay, "resume"),
                             self.tr("toolbar_resume") or "Resume", self)
        act_resume.triggered.connect(self._on_toolbar_resume)
        toolbar.addAction(act_resume)

        act_cancel = QAction(self._get_icon(QStyle.StandardPixmap.SP_DialogCancelButton,
                             "cancel"), self.tr("toolbar_cancel") or "Cancel", self)
        act_cancel.triggered.connect(self._on_toolbar_cancel)
        toolbar.addAction(act_cancel)

        act_remove = QAction(self._get_icon(QStyle.StandardPixmap.SP_TrashIcon, "delete"),
                             self.tr("toolbar_delete") or "Delete", self)
        act_remove.triggered.connect(self._on_toolbar_remove)
        toolbar.addAction(act_remove)

        toolbar.addSeparator()

        act_settings = QAction(self._get_icon(QStyle.StandardPixmap.SP_FileDialogDetailedView,
                               "settings"), self.tr("toolbar_settings") or "Settings", self)
        act_settings.triggered.connect(self._open_settings)
        toolbar.addAction(act_settings)

        toolbar.addSeparator()

        # Day / Night Theme Toggle Action in Toolbar
        self.act_theme_toggle = QAction(self)
        self.act_theme_toggle.triggered.connect(self._toggle_theme)
        toolbar.addAction(self.act_theme_toggle)

        # Update labels and icons for theme actions
        self._update_theme_action_ui()

    def _update_theme_action_ui(self) -> None:
        """تحديث نص وأيقونة زر تبديل الوضع النهاري / الليلي"""
        is_dark = getattr(self.config, "dark_mode", True)
        if is_dark:
            text = "Light Mode"
            tip = "Switch to Light / Day Mode (F10)"
            icon = self._get_icon(QStyle.StandardPixmap.SP_DriveHDIcon, "sun")
        else:
            text = "Dark Mode"
            tip = "Switch to Dark / Night Mode (F10)"
            icon = self._get_icon(QStyle.StandardPixmap.SP_DriveCDIcon, "moon")

        if hasattr(self, "act_theme_toggle"):
            self.act_theme_toggle.setText(text)
            self.act_theme_toggle.setToolTip(tip)
            self.act_theme_toggle.setIcon(icon)

        if hasattr(self, "act_menu_theme"):
            self.act_menu_theme.setText(f"Switch to {'Light' if is_dark else 'Dark'} Mode")
            self.act_menu_theme.setToolTip(tip)
            self.act_menu_theme.setIcon(icon)

    def _toggle_theme(self) -> None:
        """تبديل المظهر فوراً بين الوضع الليلي والنهاري وحفظ الإعدادات"""
        self.config.dark_mode = not self.config.dark_mode
        self.config.save()

        theme_name = "dark" if self.config.dark_mode else "light"
        stylesheet = load_theme(theme_name)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(stylesheet or "")

        self._update_theme_action_ui()

        # إعادة تطبيق الأنماط على كافة العناصر والبطاقات لضمان التحديث الشامل 100%
        self.style().unpolish(self)
        self.style().polish(self)
        for w in self.findChildren(QWidget):
            w.style().unpolish(w)
            w.style().polish(w)
        self.update()

    # ==========================================
    # Central Widget Layout
    # ==========================================

    def _init_central_ui(self) -> None:
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(10)

        # 1. Top Quick URL bar
        self._create_quick_url_bar(layout)

        # 2. Middle Downloads Table
        self._create_downloads_table(layout)

        # 3. Bottom Collapsible Details Panel
        self._create_details_panel(layout)

    def _create_quick_url_bar(self, parent_layout: QVBoxLayout) -> None:
        url_frame = QFrame(self)
        url_frame.setObjectName("cardFrame")
        url_layout = QHBoxLayout(url_frame)
        url_layout.setContentsMargins(8, 8, 8, 8)
        url_layout.setSpacing(8)

        self.txt_quick_url = QLineEdit(url_frame)
        self.txt_quick_url.setPlaceholderText(
            self.tr("dialog_add_url_placeholder") or "Enter or paste download URL here (YouTube, HTTP, Direct link...)"
        )
        self.txt_quick_url.setMinimumHeight(36)
        self.txt_quick_url.returnPressed.connect(self._on_quick_analyze)

        btn_paste = QPushButton("Paste", url_frame)
        btn_paste.setMinimumHeight(36)
        btn_paste.clicked.connect(self._paste_to_quick_url)

        btn_analyze = QPushButton("Analyze", url_frame)
        btn_analyze.setMinimumHeight(36)
        btn_analyze.clicked.connect(self._on_quick_analyze)

        btn_download = QPushButton("Quick Download", url_frame)
        btn_download.setObjectName("primaryButton")
        btn_download.setMinimumHeight(36)
        btn_download.clicked.connect(self._on_quick_download)

        url_layout.addWidget(self.txt_quick_url, 1)
        url_layout.addWidget(btn_paste)
        url_layout.addWidget(btn_analyze)
        url_layout.addWidget(btn_download)

        parent_layout.addWidget(url_frame)

    def _create_downloads_table(self, parent_layout: QVBoxLayout) -> None:
        self.table = QTableWidget(self)
        self.table.setColumnCount(8)
        self.table.setHorizontalHeaderLabels([
            "#",
            self.tr("col_filename") or "File Name",
            self.tr("col_size") or "Size",
            self.tr("col_progress") or "Progress",
            self.tr("col_speed") or "Speed",
            self.tr("col_eta") or "Time Left",
            self.tr("col_status") or "Status",
            self.tr("col_platform") or "Platform",
        ])

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Interactive)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(3, 210)

        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.verticalHeader().setVisible(False)
        self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self._on_table_context_menu)
        self.table.cellClicked.connect(lambda row, col: self.table.selectRow(row))
        self.table.itemSelectionChanged.connect(self._on_table_selection_changed)
        self.table.itemDoubleClicked.connect(self._on_table_double_clicked)

        parent_layout.addWidget(self.table, 1)

    def _create_details_panel(self, parent_layout: QVBoxLayout) -> None:
        self.details_container = QWidget(self)
        cont_layout = QVBoxLayout(self.details_container)
        cont_layout.setContentsMargins(0, 0, 0, 0)
        cont_layout.setSpacing(4)

        header_bar = QHBoxLayout()
        self.btn_toggle_details = QPushButton("▼ Download Details", self.details_container)
        self.btn_toggle_details.setFlat(True)
        self.btn_toggle_details.setObjectName("detToggle")
        self.btn_toggle_details.clicked.connect(self._toggle_details_panel)
        header_bar.addWidget(self.btn_toggle_details)
        header_bar.addStretch()

        cont_layout.addLayout(header_bar)

        self.details_card = QFrame(self.details_container)
        self.details_card.setObjectName("cardFrame")
        card_layout = QGridLayout(self.details_card)
        card_layout.setContentsMargins(10, 8, 10, 8)
        card_layout.setSpacing(8)

        self.lbl_det_title = QLabel("File: No selection", self.details_card)
        self.lbl_det_title.setObjectName("detTitle")

        self.lbl_det_url = QLabel("URL: --", self.details_card)
        self.lbl_det_url.setObjectName("detMuted")
        self.lbl_det_url.setWordWrap(True)

        self.lbl_det_path = QLabel("Folder: --", self.details_card)
        self.lbl_det_path.setObjectName("detMuted")

        self.lbl_det_stats = QLabel("Size: -- | Speed: -- | Time Left: --", self.details_card)
        self.lbl_det_stats.setObjectName("detStats")

        self.lbl_det_status = QLabel("Status: --", self.details_card)
        self.lbl_det_status.setObjectName("detStatus")

        btn_open_folder = QPushButton("Open Folder", self.details_card)
        btn_open_folder.clicked.connect(self._open_selected_folder)

        card_layout.addWidget(self.lbl_det_title, 0, 0, 1, 2)
        card_layout.addWidget(self.lbl_det_url, 1, 0, 1, 2)
        card_layout.addWidget(self.lbl_det_path, 2, 0)
        card_layout.addWidget(btn_open_folder, 2, 1, Qt.AlignmentFlag.AlignRight)
        card_layout.addWidget(self.lbl_det_stats, 3, 0)
        card_layout.addWidget(self.lbl_det_status, 3, 1, Qt.AlignmentFlag.AlignRight)

        cont_layout.addWidget(self.details_card)
        parent_layout.addWidget(self.details_container)

    def _toggle_details_panel(self) -> None:
        """طي أو إظهار لوحة تفاصيل التنزيل"""
        self._details_collapsed = not self._details_collapsed
        self.details_card.setVisible(not self._details_collapsed)
        arrow = "▲" if self._details_collapsed else "▼"
        self.btn_toggle_details.setText(f"{arrow} Download Details")

    # ==========================================
    # Status Bar
    # ==========================================
    def _init_status_bar(self) -> None:
        status_bar = QStatusBar(self)
        self.setStatusBar(status_bar)

        self.lbl_active_count = QLabel("Active: 0", self)
        self.lbl_active_count.setObjectName("statusActive")

        self.lbl_total_speed = QLabel("Total Speed: 0 B/s", self)
        self.lbl_total_speed.setObjectName("statusSpeed")

        self.lbl_free_space = QLabel("Free Disk Space: --", self)
        self.lbl_free_space.setObjectName("statusDisk")

        status_bar.addWidget(self.lbl_active_count)
        status_bar.addWidget(self.lbl_total_speed, 1)
        status_bar.addPermanentWidget(self.lbl_free_space)

    def _update_status_bar(self) -> None:
        """تحديث إحصائيات شريط الحالة دورياً كل ثانية"""
        items = self.queue_manager.get_all_items()
        active_items = [it for it in items if it.status.is_active]

        # 1. عدد التنزيلات النشطة
        count = len(active_items)
        self.lbl_active_count.setText(f"Active: {count}")

        # 2. Total Speed
        total_speed_bytes = sum(it.speed for it in active_items)
        self.lbl_total_speed.setText(f"Total Speed: {format_speed(total_speed_bytes)}")

        # 3. Free Disk Space
        out_dir = self.config.output_dir or str(DEFAULT_DOWNLOAD_DIR)
        free_bytes = get_free_disk_space(out_dir)
        self.lbl_free_space.setText(f"Free Space: {format_size(free_bytes)}")

        # Update System Tray Tooltip
        if hasattr(self, "tray_icon") and self.tray_icon.isSystemTrayAvailable():
            self.tray_icon.setToolTip(f"{APP_NAME}: {count} active download(s) | {format_speed(total_speed_bytes)}")

    # ==========================================
    # System Tray
    # ==========================================
    def _init_system_tray(self) -> None:
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return

        self.tray_icon = QSystemTrayIcon(self)
        icon = self._get_icon(QStyle.StandardPixmap.SP_ArrowDown, "app")
        self.tray_icon.setIcon(icon)

        # Right click tray context menu
        tray_menu = QMenu(self)

        act_show = QAction("Show / Hide Window", self)
        act_show.triggered.connect(self._toggle_window_visibility)
        tray_menu.addAction(act_show)

        tray_menu.addSeparator()

        act_pause_all = QAction("Pause All", self)
        act_pause_all.triggered.connect(self.queue_manager.pause_all)
        tray_menu.addAction(act_pause_all)

        act_resume_all = QAction("Resume All", self)
        act_resume_all.triggered.connect(self.queue_manager.resume_all)
        tray_menu.addAction(act_resume_all)

        tray_menu.addSeparator()

        act_quit = QAction("Exit", self)
        act_quit.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(act_quit)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()

    def _on_tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self._toggle_window_visibility()

    def _toggle_window_visibility(self) -> None:
        if self.isVisible():
            if self.isMinimized():
                self.showNormal()
                self.activateWindow()
            else:
                self.hide()
        else:
            self.showNormal()
            self.activateWindow()

    # ==========================================
    # Queue Signals
    # ==========================================
    def _connect_queue_signals(self) -> None:
        self.queue_manager.download_started.connect(self._on_download_started)
        self.queue_manager.download_completed.connect(self._on_download_completed)
        self.queue_manager.download_failed.connect(self._on_download_failed)
        self.queue_manager.queue_updated.connect(self._on_queue_updated)
        self.queue_manager.all_completed.connect(self._on_all_completed)

    def _on_download_started(self, item_id: str) -> None:
        item = self.queue_manager.get_item(item_id)
        if item:
            self._update_download_row(item_id, item.to_dict())

    def _on_download_completed(self, item_id: str) -> None:
        item = self.queue_manager.get_item(item_id)
        if item:
            self._update_download_row(item_id, item.to_dict())

            # إظهار نافذة اكتمال التنزيل في منتصف الشاشة على غرار IDM
            try:
                is_ar = (self.config.language == "ar")
                dialog = DownloadCompleteDialog(item=item, parent=self, is_arabic=is_ar)
                dialog.show()
                dialog.raise_()
                dialog.activateWindow()
            except Exception as ex:
                print(f"[UI] Error displaying completion dialog: {ex}")

    def _on_download_failed(self, item_id: str, error_message: str) -> None:
        item = self.queue_manager.get_item(item_id)
        if item:
            self._update_download_row(item_id, item.to_dict())

    def _on_queue_updated(self) -> None:
        items = self.queue_manager.get_all_items()
        if len(items) != self.table.rowCount():
            self._refresh_table()
        else:
            for item in items:
                self._update_download_row(item.id, item.to_dict())

    def _on_all_completed(self) -> None:
        pass

    # ==========================================
    # Table Management
    # ==========================================

    def _refresh_table(self) -> None:
        items = self.queue_manager.get_all_items()
        curr_row = self.table.currentRow()
        self.table.setRowCount(len(items))
        self._item_rows.clear()

        for row, item in enumerate(items):
            self._item_rows[item.id] = row
            self._populate_row(row, item)

        if len(items) > 0:
            if 0 <= curr_row < len(items):
                self.table.selectRow(curr_row)
            elif not self.table.selectionModel().selectedRows():
                self.table.selectRow(0)

    def _populate_row(self, row: int, item: DownloadItem) -> None:
        it_num = QTableWidgetItem(str(row + 1))
        it_num.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        it_num.setData(Qt.ItemDataRole.UserRole, item.id)

        it_name = QTableWidgetItem(item.filename or item.title or "unnamed")
        it_name.setData(Qt.ItemDataRole.UserRole, item.id)
        it_name.setToolTip(item.url)

        it_size = QTableWidgetItem(item.size_str)
        it_size.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        bar = DownloadProgressBar(self.table)
        bar.update_progress(item.downloaded_bytes, item.filesize, item.status)

        it_speed = QTableWidgetItem(item.speed_str)
        it_speed.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        it_eta = QTableWidgetItem(item.eta_str)
        it_eta.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        status_text = item.status.label_en if self.config.language != "ar" else item.status.label_ar
        it_status = QTableWidgetItem(status_text)
        it_status.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        platform_name = detect_platform(item.url).capitalize()
        it_plat = QTableWidgetItem(platform_name)
        it_plat.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        for it in (it_num, it_name, it_size, it_speed, it_eta, it_status, it_plat):
            it.setFlags(it.flags() & ~Qt.ItemFlag.ItemIsEditable)

        self.table.setItem(row, 0, it_num)
        self.table.setItem(row, 1, it_name)
        self.table.setItem(row, 2, it_size)
        self.table.setCellWidget(row, 3, bar)
        self.table.setItem(row, 4, it_speed)
        self.table.setItem(row, 5, it_eta)
        self.table.setItem(row, 6, it_status)
        self.table.setItem(row, 7, it_plat)

    def _update_download_row(self, download_id: str, data: Dict[str, Any]) -> None:
        row = self._item_rows.get(download_id)
        if row is None or row >= self.table.rowCount():
            return

        item = self.queue_manager.get_item(download_id)
        if not item:
            return

        it_name = self.table.item(row, 1)
        if it_name and item.filename and it_name.text() != item.filename:
            it_name.setText(item.filename)

        it_size = self.table.item(row, 2)
        if it_size and it_size.text() != item.size_str:
            it_size.setText(item.size_str)

        bar = self.table.cellWidget(row, 3)
        if isinstance(bar, DownloadProgressBar):
            bar.update_progress(item.downloaded_bytes, item.filesize, item.status)

        it_speed = self.table.item(row, 4)
        if it_speed:
            it_speed.setText(item.speed_str)

        it_eta = self.table.item(row, 5)
        if it_eta:
            it_eta.setText(item.eta_str)

        it_status = self.table.item(row, 6)
        if it_status:
            status_text = item.status.label_en if self.config.language != "ar" else item.status.label_ar
            it_status.setText(status_text)
            if item.error_message:
                tip = f"Error: {item.error_message}\n(Double-click or click Resume to retry)"
                it_status.setToolTip(tip)
                if isinstance(bar, DownloadProgressBar):
                    bar.setToolTip(tip)

        selected_ids = self._get_selected_item_ids()
        if selected_ids and selected_ids[0] == download_id:
            self._update_details_card(item)

    # ==========================================
    # Toolbar & Context Menu Handlers
    # ==========================================
    def _get_selected_item_ids(self) -> List[str]:
        ids: List[str] = []
        rows_seen = set()

        if self.table.selectionModel():
            for index in self.table.selectionModel().selectedRows():
                rows_seen.add(index.row())

        if not rows_seen and self.table.selectionModel():
            for index in self.table.selectionModel().selectedIndexes():
                rows_seen.add(index.row())

        if not rows_seen:
            cr = self.table.currentRow()
            if 0 <= cr < self.table.rowCount():
                rows_seen.add(cr)

        if not rows_seen and self.table.rowCount() == 1:
            rows_seen.add(0)

        for r in sorted(rows_seen):
            it = self.table.item(r, 0)
            if it:
                item_id = it.data(Qt.ItemDataRole.UserRole)
                if item_id and item_id not in ids:
                    ids.append(item_id)

        return ids

    def _on_toolbar_pause(self) -> None:
        target_ids = self._get_selected_item_ids()
        if not target_ids:
            target_ids = [it.id for it in self.queue_manager.get_all_items() if it.status.is_active]
        for item_id in target_ids:
            self.queue_manager.pause(item_id)
        self._refresh_table()

    def _on_toolbar_resume(self) -> None:
        target_ids = self._get_selected_item_ids()
        if not target_ids:
            cands = [it.id for it in self.queue_manager.get_all_items()
                     if it.status in (DownloadStatus.PAUSED, DownloadStatus.FAILED, DownloadStatus.CANCELLED)]
            target_ids = cands[:1] if cands else []
        for item_id in target_ids:
            self.queue_manager.resume(item_id)
        self._refresh_table()

    def _on_toolbar_cancel(self) -> None:
        target_ids = self._get_selected_item_ids()
        if not target_ids:
            target_ids = [it.id for it in self.queue_manager.get_all_items() if it.status.is_active]
        for item_id in target_ids:
            self.queue_manager.cancel(item_id)
        self._refresh_table()

    def _on_toolbar_remove(self) -> None:
        selected_ids = self._get_selected_item_ids()
        if not selected_ids:
            return

        reply = QMessageBox.question(
            self,
            "Confirm Removal",
            f"Are you sure you want to remove {len(selected_ids)} download(s) from the list?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            for item_id in selected_ids:
                self.queue_manager.remove(item_id)
            self._refresh_table()

    def _clear_completed(self) -> None:
        items = self.queue_manager.get_all_items()
        completed_ids = [it.id for it in items if it.status == DownloadStatus.COMPLETED]
        if not completed_ids:
            QMessageBox.information(self, "Information", "There are no completed downloads to remove.")
            return

        for item_id in completed_ids:
            self.queue_manager.remove(item_id)
        self._refresh_table()

    def _on_table_context_menu(self, pos) -> None:
        selected_ids = self._get_selected_item_ids()
        if not selected_ids:
            return

        menu = QMenu(self)

        act_pause = menu.addAction(self._get_icon(QStyle.StandardPixmap.SP_MediaPause), "Pause")
        act_pause.triggered.connect(self._on_toolbar_pause)

        act_resume = menu.addAction(self._get_icon(QStyle.StandardPixmap.SP_MediaPlay), "Resume")
        act_resume.triggered.connect(self._on_toolbar_resume)

        act_cancel = menu.addAction(self._get_icon(QStyle.StandardPixmap.SP_DialogCancelButton), "Cancel")
        act_cancel.triggered.connect(self._on_toolbar_cancel)

        menu.addSeparator()

        act_open_file = menu.addAction(self._get_icon(QStyle.StandardPixmap.SP_FileIcon), "Open File")
        act_open_file.triggered.connect(self._open_selected_file)

        act_open_folder = menu.addAction(self._get_icon(QStyle.StandardPixmap.SP_DirIcon), "Open Containing Folder")
        act_open_folder.triggered.connect(self._open_selected_folder)

        act_copy_url = menu.addAction("Copy URL")
        act_copy_url.triggered.connect(self._copy_selected_url)

        menu.addSeparator()

        act_remove = menu.addAction(self._get_icon(QStyle.StandardPixmap.SP_TrashIcon), "Remove from List")
        act_remove.triggered.connect(self._on_toolbar_remove)

        menu.exec(self.table.viewport().mapToGlobal(pos))

    def _on_table_double_clicked(self, item: QTableWidgetItem) -> None:
        row = item.row()
        it_num = self.table.item(row, 0)
        if not it_num:
            return

        item_id = it_num.data(Qt.ItemDataRole.UserRole)
        dl_item = self.queue_manager.get_item(item_id)
        if not dl_item:
            return

        if dl_item.status == DownloadStatus.COMPLETED:
            self._open_selected_file()
        elif dl_item.status in (DownloadStatus.PAUSED, DownloadStatus.FAILED, DownloadStatus.CANCELLED):
            self.queue_manager.resume(item_id)
        elif dl_item.status == DownloadStatus.DOWNLOADING:
            self.queue_manager.pause(item_id)

    def _on_table_selection_changed(self) -> None:
        selected_ids = self._get_selected_item_ids()
        if not selected_ids:
            self.lbl_det_title.setText("File: No selection")
            self.lbl_det_url.setText("URL: --")
            self.lbl_det_path.setText("Folder: --")
            self.lbl_det_stats.setText("Size: -- | Speed: -- | Time Left: --")
            self.lbl_det_status.setText("Status: --")
            return

        item = self.queue_manager.get_item(selected_ids[0])
        if item:
            self._update_details_card(item)

    def _update_details_card(self, item: DownloadItem) -> None:
        self.lbl_det_title.setText(f"File: {item.filename or item.title or 'Unnamed'}")
        self.lbl_det_url.setText(f"URL: {item.url}")
        self.lbl_det_path.setText(f"Folder: {item.output_dir}")

        q_str = f"Quality: {item.quality_label} | " if item.quality_label else ""
        stats = (
            f"{q_str}Size: {item.downloaded_str} / {item.size_str} | "
            f"Speed: {item.speed_str} | Time Left: {item.eta_str}"
        )
        self.lbl_det_stats.setText(stats)

        status_lbl = item.status.label_en if self.config.language != "ar" else item.status.label_ar
        if item.error_message:
            status_lbl += f" ({item.error_message})"
        self.lbl_det_status.setText(f"Status: {status_lbl}")

    def _open_selected_file(self) -> None:
        selected_ids = self._get_selected_item_ids()
        if not selected_ids:
            return

        item = self.queue_manager.get_item(selected_ids[0])
        if not item:
            return

        file_path = item.full_path
        if not file_path.exists() and item.output_dir:
            cand = Path(item.output_dir) / item.filename
            if cand.exists():
                file_path = cand

        if file_path.exists():
            vlc_candidates = [
                r"C:\Program Files\VideoLAN\VLC\vlc.exe",
                r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
            ]
            vlc_exe = next((p for p in vlc_candidates if os.path.exists(p)), None)
            ext = file_path.suffix.lower()
            if vlc_exe and ext in ('.mp4', '.mkv', '.avi', '.webm', '.mov', '.flv', '.mp3', '.m4a', '.wav', '.flac'):
                subprocess.Popen([vlc_exe, str(file_path)])
                return

            if sys.platform == "win32":
                os.startfile(str(file_path))
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(file_path)))
        else:
            QMessageBox.warning(
                self,
                "Warning",
                f"File does not exist at specified path:\n{file_path}",
            )

    def _open_selected_folder(self) -> None:
        selected_ids = self._get_selected_item_ids()
        if not selected_ids:
            folder = self.config.output_dir or str(DEFAULT_DOWNLOAD_DIR)
        else:
            item = self.queue_manager.get_item(selected_ids[0])
            folder = item.output_dir if item else self.config.output_dir

        if os.path.exists(folder):
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        else:
            QMessageBox.warning(self, "Warning", f"Folder does not exist:\n{folder}")

    def _copy_selected_url(self) -> None:
        selected_ids = self._get_selected_item_ids()
        if not selected_ids:
            return
        item = self.queue_manager.get_item(selected_ids[0])
        if item and item.url:
            QApplication.clipboard().setText(item.url)

    # ==========================================
    # إجراءات إضافة التنزيلات (Add Downloads)
    # ==========================================
    def _add_download_url(self, prefilled_url: str = "") -> None:
        """فتح نافذة إضافة تنزيل جديد AddDownloadDialog"""
        dlg = AddDownloadDialog(
            parent=self,
            initial_url=prefilled_url,
            config=self.config,
            translator=self._translator,
        )
        if dlg.exec() == QDialog.DialogCode.Accepted:
            items = dlg.get_download_items()
            for it in items:
                self.queue_manager.add(it)
            self._refresh_table()

    def _add_batch_urls(self) -> None:
        """نافذة إضافة دفعة من الروابط دفعة واحدة (Batch URLs)"""
        dlg = QDialog(self)
        dlg.setWindowTitle("إضافة روابط متعددة (Batch Downloads)")
        dlg.resize(550, 420)
        dlg.setModal(True)

        layout = QVBoxLayout(dlg)
        lbl_hint = QLabel("ألصق قائمة الروابط هنا (رابط واحد في كل سطر):", dlg)
        layout.addWidget(lbl_hint)

        txt_batch = QPlainTextEdit(dlg)
        txt_batch.setPlaceholderText("https://...\nhttps://...\n...")
        layout.addWidget(txt_batch, 1)

        btn_layout = QHBoxLayout()
        btn_cancel = QPushButton("Cancel", dlg)
        btn_cancel.clicked.connect(dlg.reject)

        btn_add = QPushButton("Add to Queue", dlg)
        btn_add.setObjectName("primaryButton")
        btn_add.setDefault(True)

        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_add)
        layout.addLayout(btn_layout)

        def on_add():
            lines = txt_batch.toPlainText().splitlines()
            valid_urls = [line.strip() for line in lines if line.strip() and is_valid_url(line.strip())]
            if not valid_urls:
                QMessageBox.warning(dlg, "Warning", "No valid URLs found.")
                return

            out_dir = self.config.output_dir or str(DEFAULT_DOWNLOAD_DIR)
            os.makedirs(out_dir, exist_ok=True)

            for url in valid_urls:
                item = DownloadItem(
                    url=url,
                    output_dir=out_dir,
                    proxy=self.config.proxy,
                )
                self.queue_manager.add(item)

            dlg.accept()
            self._refresh_table()
            QMessageBox.information(
                self,
                "Batch Added",
                f"Successfully added {len(valid_urls)} downloads to the queue.",
            )

        btn_add.clicked.connect(on_add)
        dlg.exec()

    def _paste_to_quick_url(self) -> None:
        """لصق النص من الحافظة إلى شريط الإدخال السريع"""
        text = QApplication.clipboard().text().strip()
        if text:
            cleaned = normalize_url(text)
            self.txt_quick_url.setText(cleaned)

    def _on_quick_analyze(self) -> None:
        """فحص الرابط السريع عبر فتح نافذة التنزيل"""
        raw_url = self.txt_quick_url.text().strip()
        if not raw_url:
            QMessageBox.warning(self, "Warning", "Please enter or paste a URL first.")
            return
        url = normalize_url(raw_url)
        self._add_download_url(prefilled_url=url)
        self.txt_quick_url.clear()

    def _on_quick_download(self) -> None:
        """بدء التنزيل السريع فوراً بإعدادات تلقائية دون فتح نافذة الحوار"""
        raw_url = self.txt_quick_url.text().strip()
        if not raw_url:
            QMessageBox.warning(self, "Warning", "Please enter or paste a URL first.")
            return

        url = normalize_url(raw_url)
        if not is_valid_url(url):
            QMessageBox.warning(self, "Warning", "The entered URL is not valid.")
            return

        # إذا كان الرابط يشير إلى قائمة تشغيل، نفتح نافذة تفاصيل القائمة لاختيار العناصر والجودة
        if is_playlist_url(url):
            self._add_download_url(prefilled_url=url)
            self.txt_quick_url.clear()
            return

        out_dir = self.config.output_dir or str(DEFAULT_DOWNLOAD_DIR)
        os.makedirs(out_dir, exist_ok=True)

        item = DownloadItem(
            url=url,
            output_dir=out_dir,
            proxy=self.config.proxy,
        )
        self.queue_manager.add(item)
        self.txt_quick_url.clear()
        self._refresh_table()

    # ==========================================
    # Import / Export URLs
    # ==========================================
    def _import_urls(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Import URLs",
            "",
            "URL Lists (*.txt *.json);;All Files (*.*)"
        )
        if not path:
            return

        urls: List[str] = []
        try:
            if path.endswith(".json"):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        for entry in data:
                            if isinstance(entry, str):
                                urls.append(entry)
                            elif isinstance(entry, dict) and "url" in entry:
                                urls.append(entry["url"])
            else:
                with open(path, "r", encoding="utf-8") as f:
                    urls = [line.strip() for line in f if line.strip()]
        except Exception as e:
            QMessageBox.critical(self, "Import Error", f"Failed to read file: {e}")
            return

        valid_urls = [u for u in urls if is_valid_url(u)]
        out_dir = self.config.output_dir or str(DEFAULT_DOWNLOAD_DIR)

        for u in valid_urls:
            item = DownloadItem(url=u, output_dir=out_dir, proxy=self.config.proxy)
            self.queue_manager.add(item)

        self._refresh_table()
        QMessageBox.information(self, "Import Completed", f"Successfully imported {len(valid_urls)} URLs.")

    def _export_urls(self) -> None:
        items = self.queue_manager.get_all_items()
        if not items:
            QMessageBox.information(self, "Information", "No URLs in the list to export.")
            return

        path, _ = QFileDialog.getSaveFileName(
            self,
            "Export URLs",
            "flexdown_urls.txt",
            "Text Files (*.txt);;JSON Files (*.json)"
        )
        if not path:
            return

        try:
            if path.endswith(".json"):
                data = [it.to_dict() for it in items]
                with open(path, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
            else:
                with open(path, "w", encoding="utf-8") as f:
                    for it in items:
                        f.write(f"{it.url}\n")
            QMessageBox.information(self, "Export Completed", f"URLs successfully exported to:\n{path}")
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to save file: {e}")

    # ==========================================
    # Preferences & Settings
    # ==========================================
    def _open_settings(self) -> None:
        dlg = SettingsDialog(
            config=self.config,
            translator=self._translator,
            parent=self,
        )
        dlg.settings_applied.connect(self._on_settings_applied)
        dlg.exec()

    def _open_proxy_settings(self) -> None:
        dlg = SettingsDialog(
            config=self.config,
            translator=self._translator,
            parent=self,
        )
        dlg.tab_widget.setCurrentIndex(3)
        dlg.settings_applied.connect(self._on_settings_applied)
        dlg.exec()

    def _on_settings_applied(self, new_settings: Dict[str, Any]) -> None:
        if "max_concurrent" in new_settings:
            self.queue_manager.set_max_concurrent(new_settings["max_concurrent"])

        if "language" in new_settings and new_settings["language"] != self._translator.current_language:
            self._change_language(new_settings["language"])

    def _change_language(self, lang_code: str) -> None:
        self.config.language = lang_code
        self._translator.set_language(lang_code)

        app = QApplication.instance()
        if app:
            self._translator.install(app)

        QMessageBox.information(
            self,
            "Language Changed",
            "Application language updated. Please restart FlexDown for all changes to take effect.",
        )

    # ==========================================
    # Tools & About Dialogs
    # ==========================================
    def _open_converter_dialog(self) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("Media Converter")
        dlg.resize(480, 260)
        layout = QVBoxLayout(dlg)

        layout.addWidget(QLabel("Select media file to convert:"))
        file_row = QHBoxLayout()
        txt_path = QLineEdit(dlg)
        btn_browse = QPushButton("Browse...", dlg)
        file_row.addWidget(txt_path)
        file_row.addWidget(btn_browse)
        layout.addLayout(file_row)

        layout.addWidget(QLabel("Target format:"))
        cmb_target = QComboBox(dlg)
        cmb_target.addItems(["mp4", "mkv", "avi", "mov", "mp3", "wav", "flac", "aac"])
        layout.addWidget(cmb_target)

        def browse():
            p, _ = QFileDialog.getOpenFileName(dlg, "Select Media File", "", "Media Files (*.*)")
            if p:
                txt_path.setText(p)

        btn_browse.clicked.connect(browse)

        btn_convert = QPushButton("Start Conversion", dlg)
        btn_convert.setObjectName("primaryButton")
        layout.addStretch()
        layout.addWidget(btn_convert)

        def convert():
            p = txt_path.text().strip()
            if not p or not os.path.exists(p):
                QMessageBox.warning(dlg, "Warning", "Please select a valid media file.")
                return
            target_ext = cmb_target.currentText()
            out_file = os.path.splitext(p)[0] + f"_converted.{target_ext}"

            try:
                subprocess.Popen(["ffmpeg", "-i", p, out_file])
                QMessageBox.information(dlg, "Converting", f"Started FFmpeg conversion to:\n{out_file}")
                dlg.accept()
            except FileNotFoundError:
                QMessageBox.warning(dlg, "FFmpeg Warning", "FFmpeg executable was not found in system or bundled path.")

        btn_convert.clicked.connect(convert)
        dlg.exec()

    def _open_scheduler_dialog(self) -> None:
        items = [it for it in self.queue_manager.get_all_items() if it.scheduled_time]
        dlg = QDialog(self)
        dlg.setWindowTitle("Scheduled Downloads")
        dlg.resize(550, 350)
        layout = QVBoxLayout(dlg)

        if not items:
            msg = "No scheduled downloads currently.\nYou can schedule a download from the Add Download dialog."
            lbl = QLabel(msg, dlg)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(lbl)
        else:
            tbl = QTableWidget(dlg)
            tbl.setColumnCount(3)
            tbl.setHorizontalHeaderLabels(["File", "Scheduled Time", "URL"])
            tbl.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            tbl.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            tbl.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            tbl.setRowCount(len(items))

            for r, it in enumerate(items):
                tbl.setItem(r, 0, QTableWidgetItem(it.filename or it.title))
                tbl.setItem(r, 1, QTableWidgetItem(str(it.scheduled_time)))
                tbl.setItem(r, 2, QTableWidgetItem(it.url))
            layout.addWidget(tbl)

        btn_close = QPushButton("Close", dlg)
        btn_close.clicked.connect(dlg.accept)
        layout.addWidget(btn_close)
        dlg.exec()

    def _open_browser_integration_dialog(self) -> None:
        """عرض نافذة تفعيل إضافة المتصفح لربط التنزيل بزر شعار التطبيق المباشر"""
        dlg = BrowserIntegrationDialog(parent=self, is_arabic=(self.config.language == "ar"))
        dlg.exec()

    def _on_clipboard_changed(self) -> None:
        """التقاط الروابط تلقائياً من الحافظة بمجرد نسخها مثل IDM تماماً"""
        try:
            clipboard = QApplication.clipboard()
            if not clipboard:
                return
            text = clipboard.text().strip()
            if not text or text == self._last_clipboard_url:
                return

            if len(text) > 2000 or "\n" in text or "\r" in text:
                return

            if not is_valid_url(text):
                return

            platform = detect_platform(text)
            url_lower = text.lower()
            is_target = False

            # منصات الوسائط (YouTube, TikTok, Facebook, Instagram, Twitter, etc.)
            if platform != "generic":
                is_target = True
            # ملفات قابلة للتنزيل المباشر أو مواقع التحميل
            elif is_direct_download(text) or any(ext in url_lower for ext in (
                ".apk", ".exe", ".iso", ".zip", ".rar", ".7z", ".pdf", ".mp4", ".mp3", ".msi"
            )) or "apkpure.com" in url_lower or "mediafire.com" in url_lower:
                is_target = True

            if is_target:
                self._last_clipboard_url = text
                # إظهار وتنشيط نافذة التطبيق فوراً مثل IDM
                self.showNormal()
                self.activateWindow()
                self.raise_()
                self._add_download_url(prefilled_url=text)
        except Exception:
            pass

    def _on_bridge_download_requested(self, payload: Dict[str, Any]) -> None:
        """معالجة طلب التنزيل الوارد مباشرة من إضافة المتصفح عبر نقر زر شعار التطبيق"""
        url = payload.get("url", "").strip()
        if not url:
            return

        audio_only = bool(payload.get("audio_only", False))
        mode = payload.get("mode", "quick")
        title = payload.get("title", "")
        format_id = payload.get("format_id", "")
        audio_quality = str(payload.get("audio_quality", "320"))
        audio_format = payload.get("audio_format", "mp3")
        res = payload.get("res", "")

        if mode == "dialog":
            self.showNormal()
            self.activateWindow()
            self.raise_()
            self._add_download_url(prefilled_url=url)
        else:
            out_dir = self.config.output_dir or str(DEFAULT_DOWNLOAD_DIR)
            os.makedirs(out_dir, exist_ok=True)

            display_title = title
            if res and not audio_only and title:
                display_title = f"{title} [{res}p]"
            elif audio_only and audio_quality and title:
                display_title = f"{title} [{audio_quality}k]"

            item = DownloadItem(
                url=url,
                title=display_title,
                output_dir=out_dir,
                audio_only=audio_only,
                audio_format=audio_format,
                audio_quality=audio_quality,
                format_id=format_id,
                proxy=self.config.proxy
            )
            self.queue_manager.add(item)
            self._refresh_table()

    def _cleanup(self) -> None:
        """تنظيف الموارد وإيقاف خادم الجسر عند إغلاق التطبيق"""
        if hasattr(self, "_bridge_server"):
            self._bridge_server.stop()

    def _show_about(self) -> None:

        msg = f"""
        <h2>{APP_NAME}</h2>
        <p><b>Version:</b> {VERSION}</p>
        <p>Advanced High-Speed Multithreaded Desktop Download Manager</p>
        <hr/>
        <p><b>Features:</b></p>
        <ul>
            <li>High-Speed Multithreaded IDM-like Engine</li>
            <li>YouTube, Facebook, TikTok, SoundCloud & HTTP Direct support</li>
            <li>AES-256 Military-Grade File Encryption</li>
            <li>Zero-Trace Privacy Mode & Temp Cache Cleaner</li>
            <li>Proxy Support (HTTP, HTTPS, SOCKS5)</li>
            <li>Clean & Modern Interface</li>
        </ul>
        <p>© 2026 FlexDown Team. All rights reserved.</p>
        """
        QMessageBox.about(self, f"About {APP_NAME}", msg)

    # ==========================================
    # Drag & Drop & Window Close Handlers
    # ==========================================
    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls() or event.mimeData().hasText():
            event.acceptProposedAction()

    def dropEvent(self, event) -> None:
        urls: List[str] = []
        if event.mimeData().hasUrls():
            for u in event.mimeData().urls():
                url_str = u.toString().strip()
                if is_valid_url(url_str):
                    urls.append(url_str)
        elif event.mimeData().hasText():
            text = event.mimeData().text().strip()
            for line in text.splitlines():
                u_line = line.strip()
                if is_valid_url(u_line):
                    urls.append(u_line)

        if len(urls) == 1:
            self._add_download_url(prefilled_url=urls[0])
        elif len(urls) > 1:
            out_dir = self.config.output_dir or str(DEFAULT_DOWNLOAD_DIR)
            for u in urls:
                item = DownloadItem(url=u, output_dir=out_dir, proxy=self.config.proxy)
                self.queue_manager.add(item)
            self._refresh_table()
            QMessageBox.information(
                self,
                "Links Added",
                f"Successfully added {len(urls)} dropped link(s) to the queue.",
            )

    def closeEvent(self, event) -> None:
        if self.config.minimize_to_tray and hasattr(self, "tray_icon") and self.tray_icon.isSystemTrayAvailable():
            event.ignore()
            self.hide()
        else:
            self._cleanup()
            event.accept()
