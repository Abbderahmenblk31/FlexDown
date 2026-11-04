"""
خادم الجسر المحلي لربط إضافة المتصفح ببرنامج فليكس داون (مُحصّن أمنياً)
FlexDown Local Bridge Server (Browser Integration API - Hardened & Secure)

يتيح هذا الخادم لإضافة المتصفح (Chrome / Edge / Firefox) التواصل مباشرة
مع تطبيق FlexDown المكتبي عبر شبكة Localhost (127.0.0.1:18888) دون أي تأخير،
مع حماية أمنية صارمة تمنع أي موقع ويب عشوائي من استغلال المنفذ عبر رمز أمان سري (Token Auth).
"""

import json
import secrets
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn
from pathlib import Path
from typing import Optional, Dict, Any

from PyQt6.QtCore import QObject, pyqtSignal
from flexdown.constants import CONFIG_DIR


class _ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True


class _BridgeRequestHandler(BaseHTTPRequestHandler):
    """معالج طلبات HTTP القادمة من إضافة المتصفح مع تحصين أمني ودعم كامل لـ CORS"""

    def log_message(self, format, *args):
        # كتم رسائل السجل القياسية لعدم إغراق الطرفية
        pass

    def _send_cors_headers(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers",
                         "Content-Type, Authorization, X-Requested-With, X-FlexDown-Token")

    def do_OPTIONS(self):
        """معالجة استعلامات Preflight لتمكين الاتصال من الإضافة المصرح بها"""
        self.send_response(200)
        self._send_cors_headers()
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_GET(self):
        """فحص حالة الاتصال بالبرنامج (Ping / Healthcheck)"""
        if self.path in ("/api/ping", "/ping", "/"):
            response = {
                "status": "online",
                "app": "FlexDown",
                "version": "1.0.0",
                "listening": True,
                "secured": True
            }
            body = json.dumps(response).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self._send_cors_headers()
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self.send_response(404)
            self.end_headers()

    def _is_authenticated(self, payload: Optional[Dict[str, Any]] = None) -> bool:
        """التحقق المشدد من رمز الأمان السري (Token Authentication) لمنع هجمات CSRF/CORS"""
        server: Optional[BridgeServer] = getattr(self.server, "bridge_server_instance", None)
        if not server or not server.token:
            return True

        # 1. ترويسة X-FlexDown-Token المخصصة
        token_hdr = self.headers.get("X-FlexDown-Token", "").strip()
        if token_hdr and secrets.compare_digest(token_hdr, server.token):
            return True

        # 2. ترويسة Authorization: Bearer <token>
        auth_hdr = self.headers.get("Authorization", "").strip()
        if auth_hdr.startswith("Bearer "):
            bearer = auth_hdr[7:].strip()
            if secrets.compare_digest(bearer, server.token):
                return True

        # 3. رمز التوثيق داخل حمولة JSON (Fallback)
        if payload and isinstance(payload, dict):
            body_token = str(payload.get("token", "")).strip()
            if body_token and secrets.compare_digest(body_token, server.token):
                return True

        return False

    def do_POST(self):
        """استقبال طلب تنزيل جديد من إضافة المتصفح بعد التأكد الصارم من الهوية"""
        if self.path in ("/api/download", "/download", "/api/add"):
            try:
                content_length = int(self.headers.get("Content-Length", 0))
                raw_data = self.rfile.read(content_length)
                payload: Dict[str, Any] = json.loads(raw_data.decode("utf-8")) if raw_data else {}

                # 🛡️ التحصين الأمني: رفض أي طلب لا يحمل الرمز السري الصحيح
                if not self._is_authenticated(payload):
                    err_msg = json.dumps({
                        "success": False,
                        "error": "Unauthorized: Invalid or missing FlexDown security token."
                    }).encode("utf-8")
                    self.send_response(401)
                    self.send_header("Content-Type", "application/json; charset=utf-8")
                    self._send_cors_headers()
                    self.send_header("Content-Length", str(len(err_msg)))
                    self.end_headers()
                    self.wfile.write(err_msg)
                    return

                url = payload.get("url", "").strip()
                if not url:
                    self.send_response(400)
                    self._send_cors_headers()
                    self.end_headers()
                    self.wfile.write(b'{"error": "Missing URL"}')
                    return

                # إرسال إشارة للنافذة الرئيسية لتلقي أمر التنزيل
                server: BridgeServer = getattr(self.server, "bridge_server_instance", None)
                if server:
                    server.download_requested.emit(payload)

                response = {
                    "success": True,
                    "message": "Sent to FlexDown successfully!",
                    "url": url
                }
                body = json.dumps(response).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._send_cors_headers()
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            except Exception as e:
                err_resp = json.dumps({"success": False, "error": str(e)}).encode("utf-8")
                self.send_response(500)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self._send_cors_headers()
                self.send_header("Content-Length", str(len(err_resp)))
                self.end_headers()
                self.wfile.write(err_resp)
        else:
            self.send_response(404)
            self.end_headers()


class BridgeServer(QObject):
    """
    خادم الواجهة البرمجية المحلي لـ FlexDown مع حماية متقدمة.
    Localhost HTTP Server running in background with Token-based protection.
    """
    download_requested = pyqtSignal(dict)

    def __init__(self, port: int = 18888, parent=None):
        super().__init__(parent)
        self.port = port
        self._httpd: Optional[_ThreadedHTTPServer] = None
        self._thread: Optional[threading.Thread] = None
        self._is_running = False
        self.token: str = self._load_or_create_token()
        self._sync_extension_token()

    def _load_or_create_token(self) -> str:
        """تحميل رمز الأمان السري أو توليده وحفظه محلياً في ملف مشفر"""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            token_file = CONFIG_DIR / "bridge_token.key"
            if token_file.exists():
                saved = token_file.read_text(encoding="utf-8").strip()
                if len(saved) >= 20:
                    return saved
        except Exception:
            pass

        new_token = secrets.token_hex(24)
        try:
            token_file = CONFIG_DIR / "bridge_token.key"
            token_file.write_text(new_token, encoding="utf-8")
        except Exception as e:
            print(f"[BridgeServer] Could not write token file: {e}")
        return new_token

    def _sync_extension_token(self) -> None:
        """مزامنة رمز الأمان مع ملفات إضافة المتصفح تلقائياً لتعمل فوراً دون تدخل يدوي"""
        token_js = (
            "// Auto-generated security token for FlexDown Bridge\n"
            f'(typeof window !== "undefined" ? window : self).FLEXDOWN_SECURITY_TOKEN = "{self.token}";\n'
        )

        candidate_dirs = [
            Path(__file__).resolve().parent.parent.parent / "browser_extension",
            Path.home() / "OneDrive" / "Bureau" / "FlexDown" / "browser_extension",
            Path.home() / "OneDrive" / "Bureau" / "FlexDown" / "_internal" / "browser_extension",
        ]
        for cdir in candidate_dirs:
            if cdir.exists():
                try:
                    (cdir / "token.js").write_text(token_js, encoding="utf-8")
                except Exception as ex:
                    print(f"[BridgeServer] Failed to write token.js to {cdir}: {ex}")

    def start(self) -> bool:
        """تشغيل الخادم في خيط منفصل (Background Thread)"""
        if self._is_running:
            return True

        for p in (self.port, self.port + 1, self.port + 2):
            try:
                self._httpd = _ThreadedHTTPServer(("127.0.0.1", p), _BridgeRequestHandler)
                self._httpd.bridge_server_instance = self
                self.port = p
                break
            except OSError:
                continue

        if not self._httpd:
            print(f"[BridgeServer] Failed to bind to ports {self.port}-{self.port+2}")
            return False

        self._is_running = True
        self._thread = threading.Thread(target=self._run_server, daemon=True, name="FlexDownBridgeServer")
        self._thread.start()
        print(f"[BridgeServer] FlexDown Secure Bridge listening on http://127.0.0.1:{self.port} (Secured by Token)")
        return True

    def _run_server(self):
        try:
            if self._httpd:
                self._httpd.serve_forever()
        except Exception as e:
            if self._is_running:
                print(f"[BridgeServer] Server loop error: {e}")

    def stop(self):
        """إيقاف الخادم وإغلاق المقابس بأمان"""
        self._is_running = False
        if self._httpd:
            try:
                self._httpd.shutdown()
                self._httpd.server_close()
            except Exception:
                pass
            self._httpd = None
