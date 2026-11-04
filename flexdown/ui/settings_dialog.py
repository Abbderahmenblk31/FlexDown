"""
نافذة إعدادات فليكس داون (FlexDown Settings Dialog)
توفر واجهة مبوبة (QTabWidget) للتحكم في كافة خيارات البرنامج:
- الإعدادات العامة (اللغة، المظهر، التشغيل والتصغير، الإشعارات)
- إعدادات التنزيل (المجلد الافتراضي، التحميلات المتزامنة، الاستئناف التلقائي، حد السرعة)
- الأمان والخصوصية (تشفير الملفات، مسح السجل والملفات المؤقتة)
- إعدادات البروكسي (الوكيل، المنافذ، بيانات الاعتماد واختبار الاتصال)
"""

import os
import threading
from typing import Optional
from urllib.parse import urlparse

from PyQt6.QtWidgets import (
    QDialog,
    QTabWidget,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QCheckBox,
    QComboBox,
    QSpinBox,
    QFileDialog,
    QMessageBox,
    QGroupBox,
)
from PyQt6.QtCore import pyqtSignal

from flexdown.utils.config import Config, get_config
from flexdown.i18n.translator import AppTranslator, get_translator
from flexdown.security.proxy_manager import ProxyManager
from flexdown.security.privacy import PrivacyManager


class SettingsDialog(QDialog):
    """
    نافذة الإعدادات الشاملة بتصميم مبوب داكن ومتناسق مع هوية فليكس داون.
    Tabbed Settings Dialog for FlexDown application.
    """
    # إشارة عند تطبيق أو حفظ الإعدادات لتحديث الواجهة الرئيسية
    settings_applied = pyqtSignal(dict)

    def __init__(
        self,
        config: Optional[Config] = None,
        translator: Optional[AppTranslator] = None,
        parent=None,
    ):
        super().__init__(parent)
        self.config = config or get_config()
        self._translator = translator or get_translator()
        self.proxy_manager = ProxyManager()

        self.setFixedSize(550, 520)
        self.setModal(True)
        self.setWindowTitle(self.tr("menu_settings_preferences") or "Preferences")

        self._init_ui()
        self._load_settings()

    def tr(self, key: str, **kwargs) -> str:
        """ترجمة النصوص باستخدام محرك الترجمة الخاص بالتطبيق"""
        if self._translator:
            return self._translator(key, **kwargs)
        return key

    def _init_ui(self) -> None:
        """بناء مكونات الواجهة وتخطيط التبويبات"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(12)

        # التبويبات الرئيسية
        self.tab_widget = QTabWidget(self)
        main_layout.addWidget(self.tab_widget)

        # إنشاء التبويبات
        self._create_general_tab()
        self._create_downloads_tab()
        self._create_security_tab()
        self._create_proxy_tab()

        # أزرار الإجراءات السفلية (حفظ، تطبيق، إلغاء)
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)
        btn_layout.addStretch()

        self.btn_apply = QPushButton(self.tr("btn_apply") or "Apply", self)
        self.btn_apply.setObjectName("btnApply")
        self.btn_apply.clicked.connect(self._on_apply)

        self.btn_cancel = QPushButton(self.tr("btn_cancel") or "Cancel", self)
        self.btn_cancel.clicked.connect(self.reject)

        self.btn_save = QPushButton(self.tr("btn_save") or "Save Settings", self)
        self.btn_save.setObjectName("primaryButton")
        self.btn_save.setDefault(True)
        self.btn_save.clicked.connect(self._on_save)

        btn_layout.addWidget(self.btn_apply)
        btn_layout.addWidget(self.btn_cancel)
        btn_layout.addWidget(self.btn_save)

        main_layout.addLayout(btn_layout)

    # ==========================================
    # General Tab
    # ==========================================
    def _create_general_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Appearance & Language Group
        grp_appearance = QGroupBox(self.tr("settings_appearance_tab") or "Appearance & Language", tab)
        app_grid = QGridLayout(grp_appearance)
        app_grid.setSpacing(10)

        # Language
        lbl_lang = QLabel(self.tr("menu_settings_language") or "Interface Language:", grp_appearance)
        self.cmb_language = QComboBox(grp_appearance)
        self.cmb_language.addItem("English", "en")
        self.cmb_language.addItem("العربية (Arabic)", "ar")
        app_grid.addWidget(lbl_lang, 0, 0)
        app_grid.addWidget(self.cmb_language, 0, 1)

        # Theme
        lbl_theme = QLabel(self.tr("menu_settings_theme") or "Theme:", grp_appearance)
        self.cmb_theme = QComboBox(grp_appearance)
        self.cmb_theme.addItem("Dark Theme", "dark")
        self.cmb_theme.addItem("Light Theme", "light")
        app_grid.addWidget(lbl_theme, 1, 0)
        app_grid.addWidget(self.cmb_theme, 1, 1)

        layout.addWidget(grp_appearance)

        # System Behavior Group
        grp_system = QGroupBox("Startup & System Behavior", tab)
        sys_layout = QVBoxLayout(grp_system)
        sys_layout.setSpacing(8)

        self.chk_start_minimized = QCheckBox(
            "Start FlexDown minimized",
            grp_system
        )
        self.chk_minimize_to_tray = QCheckBox(
            self.tr("settings_minimize_to_tray") or "Minimize to system tray on window close",
            grp_system
        )
        self.chk_show_notifications = QCheckBox(
            self.tr("settings_notifications") or "Show desktop notifications when downloads complete",
            grp_system
        )

        sys_layout.addWidget(self.chk_start_minimized)
        sys_layout.addWidget(self.chk_minimize_to_tray)
        sys_layout.addWidget(self.chk_show_notifications)

        layout.addWidget(grp_system)
        layout.addStretch()

        self.tab_widget.addTab(tab, self.tr("settings_general_tab") or "General")

    # ==========================================
    # Downloads Tab
    # ==========================================
    def _create_downloads_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Save Directory
        grp_dir = QGroupBox(self.tr("settings_save_folder") or "Default Download Folder", tab)
        dir_layout = QHBoxLayout(grp_dir)
        dir_layout.setSpacing(8)

        self.txt_output_dir = QLineEdit(grp_dir)
        self.btn_browse_dir = QPushButton("Browse...", grp_dir)
        self.btn_browse_dir.clicked.connect(self._browse_output_dir)

        dir_layout.addWidget(self.txt_output_dir)
        dir_layout.addWidget(self.btn_browse_dir)
        layout.addWidget(grp_dir)

        # Performance & Network
        grp_perf = QGroupBox(self.tr("settings_connection_tab") or "Network & Connection", tab)
        perf_grid = QGridLayout(grp_perf)
        perf_grid.setSpacing(10)

        # Max Concurrent
        lbl_concurrent = QLabel(self.tr("settings_max_concurrent") or "Max concurrent downloads:", grp_perf)
        self.spin_concurrent = QSpinBox(grp_perf)
        self.spin_concurrent.setRange(1, 10)
        self.spin_concurrent.setValue(3)
        perf_grid.addWidget(lbl_concurrent, 0, 0)
        perf_grid.addWidget(self.spin_concurrent, 0, 1)

        # Retries
        lbl_retries = QLabel("Max retry attempts:", grp_perf)
        self.spin_retries = QSpinBox(grp_perf)
        self.spin_retries.setRange(1, 50)
        self.spin_retries.setValue(10)
        perf_grid.addWidget(lbl_retries, 1, 0)
        perf_grid.addWidget(self.spin_retries, 1, 1)

        # Speed limit
        lbl_speed = QLabel(self.tr("settings_speed_limit") or "Global download speed limit (0 = Unlimited):", grp_perf)
        self.spin_speed_limit = QSpinBox(grp_perf)
        self.spin_speed_limit.setRange(0, 1000000)
        self.spin_speed_limit.setSuffix(" KB/s")
        self.spin_speed_limit.setValue(0)
        perf_grid.addWidget(lbl_speed, 2, 0)
        perf_grid.addWidget(self.spin_speed_limit, 2, 1)

        layout.addWidget(grp_perf)

        # Auto resume
        self.chk_auto_resume = QCheckBox(
            self.tr("settings_auto_resume") or "Automatically resume incomplete downloads on startup",
            tab
        )
        layout.addWidget(self.chk_auto_resume)

        layout.addStretch()
        self.tab_widget.addTab(tab, self.tr("menu_downloads") or "Downloads")

    # ==========================================
    # Security Tab
    # ==========================================
    def _create_security_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(15)

        # Encryption Group
        grp_enc = QGroupBox(self.tr("encryption_title") or "File Encryption", tab)
        enc_layout = QVBoxLayout(grp_enc)
        enc_layout.setSpacing(10)

        self.chk_encrypt_default = QCheckBox("Encrypt all downloaded files by default with AES-256", grp_enc)
        self.chk_encrypt_default.toggled.connect(self._on_encrypt_default_toggled)

        pass_layout = QHBoxLayout()
        lbl_pass = QLabel("Default Encryption Password:", grp_enc)
        self.txt_enc_password = QLineEdit(grp_enc)
        self.txt_enc_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.txt_enc_password.setPlaceholderText("Enter a strong password...")
        self.txt_enc_password.setEnabled(False)

        pass_layout.addWidget(lbl_pass)
        pass_layout.addWidget(self.txt_enc_password)

        enc_layout.addWidget(self.chk_encrypt_default)
        enc_layout.addLayout(pass_layout)
        layout.addWidget(grp_enc)

        # Privacy Group
        grp_privacy = QGroupBox(self.tr("privacy_title") or "Privacy & History Cleaning", tab)
        priv_layout = QVBoxLayout(grp_privacy)
        priv_layout.setSpacing(10)

        self.chk_no_history = QCheckBox(
            self.tr("privacy_no_log_mode")
            or "Do not save download history to disk (Private Mode)",
            grp_privacy,
        )
        priv_layout.addWidget(self.chk_no_history)

        clean_btns_layout = QHBoxLayout()
        self.btn_clear_history = QPushButton(
            self.tr("privacy_clear_history")
            or "Clear Entire Download History",
            grp_privacy,
        )
        self.btn_clear_history.clicked.connect(self._clear_history)

        self.btn_clear_temp = QPushButton(
            self.tr("privacy_clear_temp")
            or "Clean Temporary Chunks & Cache",
            grp_privacy,
        )
        self.btn_clear_temp.clicked.connect(self._clear_temp_files)

        clean_btns_layout.addWidget(self.btn_clear_history)
        clean_btns_layout.addWidget(self.btn_clear_temp)
        priv_layout.addLayout(clean_btns_layout)

        layout.addWidget(grp_privacy)
        layout.addStretch()
        self.tab_widget.addTab(tab, self.tr("settings_privacy_tab") or "Security & Privacy")

    # ==========================================
    # Proxy Tab
    # ==========================================
    def _create_proxy_tab(self) -> None:
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)

        self.chk_enable_proxy = QCheckBox(self.tr("proxy_enable") or "Enable connection through Proxy server", tab)
        self.chk_enable_proxy.toggled.connect(self._on_proxy_enable_toggled)
        layout.addWidget(self.chk_enable_proxy)

        self.grp_proxy_details = QGroupBox(self.tr("proxy_title") or "Proxy Server Configuration", tab)
        grid = QGridLayout(self.grp_proxy_details)
        grid.setSpacing(10)

        lbl_type = QLabel(self.tr("proxy_type") or "Proxy Type:", self.grp_proxy_details)
        self.cmb_proxy_type = QComboBox(self.grp_proxy_details)
        self.cmb_proxy_type.addItems(["HTTP", "HTTPS", "SOCKS4", "SOCKS5"])
        grid.addWidget(lbl_type, 0, 0)
        grid.addWidget(self.cmb_proxy_type, 0, 1)

        lbl_host = QLabel(self.tr("proxy_host") or "Host Address:", self.grp_proxy_details)
        self.txt_proxy_host = QLineEdit(self.grp_proxy_details)
        self.txt_proxy_host.setPlaceholderText("e.g. 127.0.0.1 or proxy.domain.com")
        grid.addWidget(lbl_host, 1, 0)
        grid.addWidget(self.txt_proxy_host, 1, 1)

        lbl_port = QLabel(self.tr("proxy_port") or "Port:", self.grp_proxy_details)
        self.spin_proxy_port = QSpinBox(self.grp_proxy_details)
        self.spin_proxy_port.setRange(1, 65535)
        self.spin_proxy_port.setValue(8080)
        grid.addWidget(lbl_port, 2, 0)
        grid.addWidget(self.spin_proxy_port, 2, 1)

        lbl_user = QLabel(self.tr("proxy_username") or "Username (Optional):", self.grp_proxy_details)
        self.txt_proxy_user = QLineEdit(self.grp_proxy_details)
        grid.addWidget(lbl_user, 3, 0)
        grid.addWidget(self.txt_proxy_user, 3, 1)

        lbl_pass = QLabel(self.tr("proxy_password") or "Password (Optional):", self.grp_proxy_details)
        self.txt_proxy_pass = QLineEdit(self.grp_proxy_details)
        self.txt_proxy_pass.setEchoMode(QLineEdit.EchoMode.Password)
        grid.addWidget(lbl_pass, 4, 0)
        grid.addWidget(self.txt_proxy_pass, 4, 1)

        layout.addWidget(self.grp_proxy_details)

        proxy_actions = QHBoxLayout()
        self.btn_test_proxy = QPushButton(self.tr("proxy_test_connection") or "Test Proxy Connection", tab)
        self.btn_test_proxy.clicked.connect(self._test_proxy_connection)
        self.lbl_proxy_test_status = QLabel("", tab)

        proxy_actions.addWidget(self.btn_test_proxy)
        proxy_actions.addWidget(self.lbl_proxy_test_status)
        proxy_actions.addStretch()

        layout.addLayout(proxy_actions)
        layout.addStretch()
        self.tab_widget.addTab(tab, "Proxy")

    # ==========================================
    # تحميل وحفظ الإعدادات (Load & Save)
    # ==========================================
    def _load_settings(self) -> None:
        """قراءة الإعدادات من كائن Config وتعبئة الحقول"""
        # العامة
        current_lang = self.config.language
        lang_idx = self.cmb_language.findData(current_lang)
        if lang_idx >= 0:
            self.cmb_language.setCurrentIndex(lang_idx)

        current_theme = "dark" if self.config.dark_mode else "light"
        theme_idx = self.cmb_theme.findData(current_theme)
        if theme_idx >= 0:
            self.cmb_theme.setCurrentIndex(theme_idx)

        self.chk_start_minimized.setChecked(bool(self.config.get("start_minimized", False)))
        self.chk_minimize_to_tray.setChecked(bool(self.config.minimize_to_tray))
        self.chk_show_notifications.setChecked(bool(self.config.show_notifications))

        # التنزيلات
        self.txt_output_dir.setText(str(self.config.output_dir))
        self.spin_concurrent.setValue(self.config.max_concurrent)
        self.chk_auto_resume.setChecked(bool(self.config.auto_resume))
        self.spin_retries.setValue(self.config.max_retries)
        self.spin_speed_limit.setValue(int(self.config.speed_limit // 1024))

        # الأمان والخصوصية
        self.chk_encrypt_default.setChecked(bool(self.config.encrypt_by_default))
        saved_pass = str(self.config.get("default_encryption_password", ""))
        self.txt_enc_password.setText(saved_pass)
        self.txt_enc_password.setEnabled(self.chk_encrypt_default.isChecked())
        self.chk_no_history.setChecked(bool(self.config.no_history))

        # البروكسي
        proxy_url = self.config.proxy
        if proxy_url:
            self.chk_enable_proxy.setChecked(True)
            self._parse_and_populate_proxy_url(proxy_url)
        else:
            self.chk_enable_proxy.setChecked(False)
            self._update_proxy_ui_state(False)

    def _parse_and_populate_proxy_url(self, proxy_str: str) -> None:
        """تحليل رابط البروكسي وتوزيعه على حقول الإدخال"""
        try:
            parsed = urlparse(proxy_str)
            scheme = parsed.scheme.upper()
            idx = self.cmb_proxy_type.findText(scheme)
            if idx >= 0:
                self.cmb_proxy_type.setCurrentIndex(idx)

            if parsed.hostname:
                self.txt_proxy_host.setText(parsed.hostname)
            if parsed.port:
                self.spin_proxy_port.setValue(parsed.port)
            if parsed.username:
                self.txt_proxy_user.setText(parsed.username)
            if parsed.password:
                self.txt_proxy_pass.setText(parsed.password)
        except Exception:
            pass
        self._update_proxy_ui_state(True)

    def _update_proxy_ui_state(self, enabled: bool) -> None:
        """تفعيل أو تعطيل حقول البروكسي بناء على حالة الاختيار"""
        self.grp_proxy_details.setEnabled(enabled)
        self.btn_test_proxy.setEnabled(enabled)

    def _on_proxy_enable_toggled(self, checked: bool) -> None:
        self._update_proxy_ui_state(checked)

    def _on_encrypt_default_toggled(self, checked: bool) -> None:
        self.txt_enc_password.setEnabled(checked)

    def _browse_output_dir(self) -> None:
        """اختيار مجلد التنزيل الافتراضي عبر مستعرض المجلدات"""
        initial_dir = self.txt_output_dir.text().strip() or os.path.expanduser("~/Downloads")
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            "Select Default Download Directory",
            initial_dir,
            QFileDialog.Option.ShowDirsOnly,
        )
        if selected_dir:
            self.txt_output_dir.setText(selected_dir)

    def _build_proxy_url(self) -> Optional[str]:
        """تجميع رابط البروكسي من الحقول"""
        if not self.chk_enable_proxy.isChecked():
            return None

        host = self.txt_proxy_host.text().strip()
        if not host:
            return None

        ptype = self.cmb_proxy_type.currentText().lower()
        port = self.spin_proxy_port.value()
        user = self.txt_proxy_user.text().strip()
        password = self.txt_proxy_pass.text()

        auth = ""
        if user:
            if password:
                auth = f"{user}:{password}@"
            else:
                auth = f"{user}@"

        return f"{ptype}://{auth}{host}:{port}"

    def _save_all(self) -> bool:
        """تطبيق وحفظ جميع الإعدادات المدخلة في كائن Config"""
        lang = self.cmb_language.currentData()
        theme = self.cmb_theme.currentData()
        dark_mode = (theme == "dark")
        start_minimized = self.chk_start_minimized.isChecked()
        min_to_tray = self.chk_minimize_to_tray.isChecked()
        notifications = self.chk_show_notifications.isChecked()

        out_dir = self.txt_output_dir.text().strip()
        if not out_dir:
            out_dir = os.path.expanduser("~/Downloads/FlexDown")

        os.makedirs(out_dir, exist_ok=True)

        concurrent = self.spin_concurrent.value()
        retries = self.spin_retries.value()
        speed_kb = self.spin_speed_limit.value()
        speed_bytes = speed_kb * 1024
        auto_resume = self.chk_auto_resume.isChecked()

        encrypt_def = self.chk_encrypt_default.isChecked()
        enc_pass = self.txt_enc_password.text()
        no_hist = self.chk_no_history.isChecked()

        proxy_url = self._build_proxy_url()

        # تحديث كائن Config
        settings_dict = {
            "language": lang,
            "dark_mode": dark_mode,
            "start_minimized": start_minimized,
            "minimize_to_tray": min_to_tray,
            "show_notifications": notifications,
            "output_dir": out_dir,
            "max_concurrent": concurrent,
            "max_retries": retries,
            "speed_limit": speed_bytes,
            "auto_resume": auto_resume,
            "encrypt_by_default": encrypt_def,
            "default_encryption_password": enc_pass,
            "no_history": no_hist,
            "proxy": proxy_url,
        }

        self.config.update(settings_dict, auto_save=True)

        # حفظ إعدادات البروكسي
        if proxy_url:
            self.proxy_manager.set_proxy(
                proxy_type=self.cmb_proxy_type.currentText().lower(),
                host=self.txt_proxy_host.text().strip(),
                port=self.spin_proxy_port.value(),
                username=self.txt_proxy_user.text().strip() or None,
                password=self.txt_proxy_pass.text() or None,
                enabled=True
            )
            self.proxy_manager.save()
        else:
            self.proxy_manager.clear_proxy()
            self.proxy_manager.save()

        self.settings_applied.emit(settings_dict)
        return True

    def _on_apply(self) -> None:
        """Apply settings immediately without closing the dialog"""
        if self._save_all():
            QMessageBox.information(
                self,
                "Applied",
                "Settings applied successfully.",
            )

    def _on_save(self) -> None:
        """Save settings and close dialog"""
        if self._save_all():
            self.accept()

    def _clear_history(self) -> None:
        """Clear download history via PrivacyManager"""
        reply = QMessageBox.question(
            self,
            "Confirm Clear",
            "Are you sure you want to clear the entire download history? This action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            priv = PrivacyManager()
            count = priv.clear_download_history()
            QMessageBox.information(
                self,
                "History Cleared",
                f"Download history cleared successfully ({count} records deleted).",
            )

    def _clear_temp_files(self) -> None:
        """Clear temporary files via PrivacyManager"""
        reply = QMessageBox.question(
            self,
            "Confirm Cleanup",
            "Are you sure you want to delete all temporary files and incomplete chunks?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            priv = PrivacyManager()
            count = priv.clear_temp_files()
            QMessageBox.information(
                self,
                "Cleanup Complete",
                f"Temporary files cleaned successfully ({count} files removed).",
            )

    def _test_proxy_connection(self) -> None:
        """Test proxy connection in background thread"""
        proxy_url = self._build_proxy_url()
        if not proxy_url:
            QMessageBox.warning(
                self,
                "Notice",
                "Please enter proxy host and port first to test the connection.",
            )
            return

        self.btn_test_proxy.setEnabled(False)
        self.lbl_proxy_test_status.setText("Testing connection...")
        self.lbl_proxy_test_status.setStyleSheet("color: #e67e22;")

        def run_test():
            test_mgr = ProxyManager()
            try:
                test_mgr.set_proxy(
                    proxy_type=self.cmb_proxy_type.currentText().lower(),
                    host=self.txt_proxy_host.text().strip(),
                    port=self.spin_proxy_port.value(),
                    username=self.txt_proxy_user.text().strip() or None,
                    password=self.txt_proxy_pass.text() or None,
                    enabled=True,
                )
                success = test_mgr.test_proxy(timeout=6)
            except Exception:
                success = False

            # Update UI on completion
            self.btn_test_proxy.setEnabled(True)
            if success:
                self.lbl_proxy_test_status.setText("✓ Proxy connection successful")
                self.lbl_proxy_test_status.setStyleSheet("color: #00b894; font-weight: bold;")
            else:
                self.lbl_proxy_test_status.setText("✗ Proxy connection failed")
                self.lbl_proxy_test_status.setStyleSheet("color: #d63031; font-weight: bold;")

        threading.Thread(target=run_test, daemon=True).start()
