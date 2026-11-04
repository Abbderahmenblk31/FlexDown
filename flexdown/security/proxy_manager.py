"""
FlexDown - مدير خوادم البروكسي (Proxy Manager Module)
يوفر فئة ProxyManager لإدارة إعدادات البروكسي واختبار الاتصال وتزويد محرك التحميل
بإعدادات التوجيه والوكيل المناسبة (HTTP / HTTPS / SOCKS4 / SOCKS5).
"""

import os
import json
from typing import Optional, Dict, Any
from urllib.parse import quote
import requests


class ProxyManager:
    """
    فئة إدارة وتكوين خوادم البروكسي لبرنامج FlexDown.
    Manages HTTP/HTTPS and SOCKS proxy configurations for requests and download workers.
    """

    PROXY_TYPES = ["http", "https", "socks4", "socks5"]
    DEFAULT_CONFIG_FILENAME = "proxy_config.json"

    def __init__(self, config_path: Optional[str] = None):
        """
        تهيئة مدير البروكسي مع تحديد مسار ملف الإعدادات الافتراضي.
        """
        if config_path:
            self.config_path = config_path
        else:
            base_dir = os.path.join(os.path.expanduser("~"), ".flexdown")
            os.makedirs(base_dir, exist_ok=True)
            self.config_path = os.path.join(base_dir, self.DEFAULT_CONFIG_FILENAME)

        self.proxy_type: str = "http"
        self.host: str = ""
        self.port: int = 8080
        self.username: Optional[str] = None
        self.password: Optional[str] = None
        self.enabled: bool = False

        # محاولة تحميل الإعدادات المحفوظة إن وجدت
        if os.path.exists(self.config_path):
            self.load()

    def set_proxy(
        self,
        proxy_type: str,
        host: str,
        port: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        enabled: bool = True,
    ) -> None:
        """
        تعيين بيانات خادم البروكسي والتحقق من صحتها.
        Sets and validates proxy parameters.

        :param proxy_type: نوع البروكسي ('http', 'https', 'socks4', 'socks5')
        :param host: اسم النطاق أو عنوان IP للخادم
        :param port: منفذ الاتصال (1-65535)
        :param username: اسم المستخدم (اختياري)
        :param password: كلمة المرور (اختياري)
        :param enabled: تفعيل البروكسي فوراً
        """
        cleaned_type = str(proxy_type).strip().lower()
        if cleaned_type not in self.PROXY_TYPES:
            raise ValueError(
                f"نوع البروكسي '{proxy_type}' غير مدعوم. الأنواع المدعومة: {', '.join(self.PROXY_TYPES)}"
            )

        cleaned_host = str(host).strip()
        if not cleaned_host:
            raise ValueError("عنوان خادم البروكسي (Host) لا يمكن أن يكون فارغاً.")

        try:
            port_num = int(port)
            if not (1 <= port_num <= 65535):
                raise ValueError("رقم المنفذ يجب أن يكون بين 1 و 65535.")
        except (TypeError, ValueError) as e:
            raise ValueError(f"منفذ غير صالح: {port}") from e

        self.proxy_type = cleaned_type
        self.host = cleaned_host
        self.port = port_num
        self.username = username.strip() if username and username.strip() else None
        self.password = password if password else None
        self.enabled = bool(enabled)

    def get_proxy_url(self) -> Optional[str]:
        """
        بناء الرابط الكامل للبروكسي بالصيغة القياسية:
        scheme://[user:pass@]host:port
        Returns the formatted proxy URL or None if not configured/enabled.
        """
        if not self.enabled or not self.host or not self.port:
            return None

        # التعامل مع بروتوكولات SOCKS وتوجيه الـ DNS
        scheme = self.proxy_type.lower()

        auth_part = ""
        if self.username:
            user_encoded = quote(self.username, safe="")
            if self.password:
                pass_encoded = quote(self.password, safe="")
                auth_part = f"{user_encoded}:{pass_encoded}@"
            else:
                auth_part = f"{user_encoded}@"

        return f"{scheme}://{auth_part}{self.host}:{self.port}"

    def get_proxy_dict(self) -> Dict[str, str]:
        """
        توليد قاموس التوجيه المتوافق مع مكتبة requests ومحركات التحميل.
        Returns a dictionary suitable for requests.get(..., proxies=proxy_dict).
        """
        url = self.get_proxy_url()
        if not url:
            return {}

        return {
            "http": url,
            "https": url,
        }

    def clear_proxy(self) -> None:
        """
        إلغاء ومسح بيانات البروكسي وإعادة الضبط إلى الوضع الافتراضي.
        Clears all proxy configurations.
        """
        self.proxy_type = "http"
        self.host = ""
        self.port = 8080
        self.username = None
        self.password = None
        self.enabled = False

    def test_proxy(
        self,
        test_url: str = "https://httpbin.org/ip",
        timeout: int = 10,
    ) -> bool:
        """
        اختبار الاتصال بالإنترنت عبر خادم البروكسي المحدد.
        Tests proxy connectivity by requesting httpbin.org/ip.

        :param test_url: الرابط المستخدم لاختبار الاتصال
        :param timeout: مهلة الانتظار بالثواني
        :return: True إذا نجح الاتصال بالبروكسي، False في حالة الفشل
        """
        proxies = self.get_proxy_dict()
        if not proxies:
            # إذا لم يكن هناك بروكسي مفعل أو محدد، لا يمكن اختباره
            return False

        try:
            response = requests.get(
                test_url,
                proxies=proxies,
                timeout=timeout,
                headers={"User-Agent": "FlexDown-ProxyTester/1.0"},
            )
            return response.status_code == 200
        except Exception:
            return False

    def to_dict(self) -> Dict[str, Any]:
        """
        تحويل إعدادات البروكسي الحالية إلى قاموس بيانات.
        """
        return {
            "enabled": self.enabled,
            "proxy_type": self.proxy_type,
            "host": self.host,
            "port": self.port,
            "username": self.username,
            "password": self.password,
        }

    def from_dict(self, data: Dict[str, Any]) -> None:
        """
        استعادة إعدادات البروكسي من قاموس بيانات.
        """
        if not isinstance(data, dict):
            return

        self.enabled = bool(data.get("enabled", False))
        ptype = str(data.get("proxy_type", "http")).lower()
        self.proxy_type = ptype if ptype in self.PROXY_TYPES else "http"
        self.host = str(data.get("host", ""))
        self.port = int(data.get("port", 8080))
        self.username = data.get("username") or None
        self.password = data.get("password") or None

    def save(self, config_path: Optional[str] = None) -> bool:
        """
        حفظ إعدادات البروكسي في ملف التهيئة JSON.
        Saves proxy configuration to disk.
        """
        target_path = config_path or self.config_path
        try:
            os.makedirs(os.path.dirname(os.path.abspath(target_path)), exist_ok=True)
            with open(target_path, "w", encoding="utf-8") as f:
                json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ProxyManager] خطأ أثناء حفظ ملف الإعدادات: {e}")
            return False

    def load(self, config_path: Optional[str] = None) -> bool:
        """
        تحميل إعدادات البروكسي من ملف التهيئة JSON.
        Loads proxy configuration from disk.
        """
        target_path = config_path or self.config_path
        if not os.path.exists(target_path):
            return False

        try:
            with open(target_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.from_dict(data)
            return True
        except Exception as e:
            print(f"[ProxyManager] خطأ أثناء تحميل ملف الإعدادات: {e}")
            return False
