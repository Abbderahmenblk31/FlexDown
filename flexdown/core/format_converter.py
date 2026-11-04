"""
FlexDown - Format Converter Module
وحدة تحويل صيغ الوسائط المتعددة (فيديو وصوت) باستخدام FFmpeg مع تتبع نسبة التقدم واكتشاف المسارات تلقائياً.
"""

import os
import re
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional, List
from PyQt6.QtCore import QThread, pyqtSignal


class FormatConverter(QThread):
    """
    خيط تحويل صيغ الوسائط (فيديو وصوت) باستخدام أداة FFmpeg.
    يدعم استخراج الصوت، وضغط الفيديو، وتغيير التنسيقات، وحساب نسبة التقدم المئوية في الوقت الفعلي.
    """
    SUPPORTED_VIDEO: List[str] = ['mp4', 'mkv', 'avi', 'webm', 'mov', 'flv']
    SUPPORTED_AUDIO: List[str] = ['mp3', 'wav', 'flac', 'aac', 'ogg', 'm4a']

    # إشارات الخيط
    progress = pyqtSignal(int)      # نسبة التقدم المئوية من 0 إلى 100
    finished = pyqtSignal(str)      # مسار الملف النهائي بعد التحويل
    error = pyqtSignal(str)         # رسالة الخطأ عند فشل العملية

    def __init__(
        self,
        input_path: str,
        output_format: str,
        output_dir: Optional[str] = None,
        custom_args: Optional[List[str]] = None,
        parent=None
    ):
        super().__init__(parent)
        self.input_path = os.path.abspath(input_path)
        self.output_format = output_format.lower().lstrip('.')
        self.output_dir = output_dir or os.path.dirname(self.input_path)
        self.custom_args = custom_args or []
        self._is_cancelled = False
        self._proc: Optional[subprocess.Popen] = None

    def cancel(self) -> None:
        """إلغاء عملية التحويل الجارية وإنهاء العملية الفرعية."""
        self._is_cancelled = True
        if self._proc and self._proc.poll() is None:
            try:
                self._proc.kill()
            except Exception:
                pass

    @classmethod
    def get_ffmpeg_path(cls) -> str:
        """
        اكتشاف مسار أداة FFmpeg المدمجة مع التطبيق أو المتوفرة في نظام التشغيل.
        Detect bundled or system FFmpeg binary path.
        """
        # مسار بيئة PyInstaller المؤقتة إن وُجدت
        if hasattr(sys, '_MEIPASS'):
            bundle_ffmpeg = os.path.join(sys._MEIPASS, 'bin', 'ffmpeg.exe' if sys.platform == 'win32' else 'ffmpeg')
            if os.path.exists(bundle_ffmpeg):
                return bundle_ffmpeg

        # التحقق من مجلد bin الخاص بالتطبيق
        base_dir = Path(__file__).resolve().parent.parent.parent
        possible_paths = [
            base_dir / "bin" / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"),
            base_dir / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"),
            Path.cwd() / "bin" / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"),
            Path.cwd() / ("ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"),
        ]

        for p in possible_paths:
            if p.exists() and p.is_file():
                return str(p)

        # البحث في متغيرات البيئة PATH لنظام التشغيل
        system_path = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
        if system_path:
            return system_path

        # التحقق من مكتبة imageio_ffmpeg المدمجة إن وُجدت
        try:
            import imageio_ffmpeg
            imageio_bin = imageio_ffmpeg.get_ffmpeg_exe()
            if imageio_bin and os.path.exists(imageio_bin):
                return imageio_bin
        except Exception:
            pass

        # الاسم الافتراضي كخيار أخير
        return "ffmpeg"

    @classmethod
    def is_ffmpeg_available(cls) -> bool:
        """التحقق من توفر أداة FFmpeg وجاهزيتها للعمل."""
        ffmpeg_bin = cls.get_ffmpeg_path()
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            res = subprocess.run(
                [ffmpeg_bin, "-version"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=creationflags,
                timeout=5
            )
            return res.returncode == 0
        except Exception:
            return False

    def get_duration(self, file_path: str) -> float:
        """
        الحصول على مدة الملف الزمني بالثواني عبر تشغيل فحص أولي بـ FFmpeg.
        Extract total media duration in seconds.
        """
        ffmpeg_bin = self.get_ffmpeg_path()
        try:
            creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
            cmd = [ffmpeg_bin, "-i", file_path]
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=creationflags,
                encoding="utf-8",
                errors="ignore",
                timeout=15
            )
            # استخراج المدة من مخرجات stderr
            pattern = re.compile(r'Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)')
            match = pattern.search(proc.stderr)
            if match:
                hours = float(match.group(1))
                minutes = float(match.group(2))
                seconds = float(match.group(3))
                return hours * 3600.0 + minutes * 60.0 + seconds
        except Exception:
            pass
        return 0.0

    def run(self) -> None:
        """تنفيذ أمر التحويل وقراءة مخرجات FFmpeg في الوقت الفعلي لحساب التقدم."""
        if not os.path.exists(self.input_path):
            self.error.emit(f"Input file not found: {self.input_path}")
            return

        ffmpeg_bin = self.get_ffmpeg_path()
        os.makedirs(self.output_dir, exist_ok=True)

        # استخراج مدة الملف لحساب النسبة المئوية
        total_duration = self.get_duration(self.input_path)

        # تجهيز مسار الملف الهدف
        base_name = os.path.splitext(os.path.basename(self.input_path))[0]
        output_filename = f"{base_name}.{self.output_format}"
        output_file = os.path.join(self.output_dir, output_filename)

        # تفادي الكتابة فوق نفس الملف إذا كانت الصيغة مطابقة
        if os.path.abspath(output_file) == os.path.abspath(self.input_path):
            output_file = os.path.join(self.output_dir, f"{base_name}_converted.{self.output_format}")

        # بناء أمر التحويل الأساسي
        cmd = [ffmpeg_bin, "-y", "-i", self.input_path]

        # تخصيص إعدادات الترميز بحسب الصيغة المختارة
        if self.custom_args:
            cmd.extend(self.custom_args)
        elif self.output_format in self.SUPPORTED_AUDIO:
            # تحويل أو استخراج صوتي
            cmd.append("-vn")  # تعطيل مسار الفيديو
            if self.output_format == 'mp3':
                cmd.extend(["-c:a", "libmp3lame", "-b:a", "192k"])
            elif self.output_format == 'aac':
                cmd.extend(["-c:a", "aac", "-b:a", "192k"])
            elif self.output_format == 'wav':
                cmd.extend(["-c:a", "pcm_s16le"])
            elif self.output_format == 'flac':
                cmd.extend(["-c:a", "flac"])
            elif self.output_format == 'ogg':
                cmd.extend(["-c:a", "libvorbis", "-q:a", "5"])
            elif self.output_format == 'm4a':
                cmd.extend(["-c:a", "aac", "-b:a", "192k"])
        elif self.output_format in self.SUPPORTED_VIDEO:
            # تحويل فيديو
            if self.output_format == 'mp4':
                cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "22", "-c:a", "aac", "-b:a", "192k"])
            elif self.output_format == 'mkv':
                cmd.extend(["-c:v", "libx264", "-preset", "fast", "-crf", "22", "-c:a", "aac"])
            elif self.output_format == 'webm':
                cmd.extend(["-c:v", "libvpx-vp9", "-crf", "30", "-b:v", "0", "-c:a", "libopus"])
            elif self.output_format in ('avi', 'mov', 'flv'):
                cmd.extend(["-c:v", "libx264", "-c:a", "aac"])

        cmd.append(output_file)

        # بدء تنفيذ الأمر كعملية فرعية
        creationflags = subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                universal_newlines=True,
                creationflags=creationflags,
                encoding="utf-8",
                errors="ignore"
            )

            # نمط قراءة الوقت المنقضي من مخرجات ffmpeg (time=HH:MM:SS.ms)
            time_regex = re.compile(r'time=(\d+):(\d+):(\d+(?:\.\d+)?)')
            last_percent = -1
            line_buf = ""

            # قراءة المخرجات حرفاً بحرف لمعالجة أسطر \r التي ينتجها FFmpeg
            while True:
                if self._is_cancelled:
                    if self._proc.poll() is None:
                        self._proc.kill()
                    return

                char = self._proc.stderr.read(1)
                if not char and self._proc.poll() is not None:
                    break

                if char in ('\r', '\n'):
                    line = line_buf.strip()
                    line_buf = ""
                    if line:
                        match = time_regex.search(line)
                        if match and total_duration > 0:
                            h = float(match.group(1))
                            m = float(match.group(2))
                            s = float(match.group(3))
                            curr_time = h * 3600.0 + m * 60.0 + s
                            pct = int(min(100, max(0, (curr_time / total_duration) * 100)))
                            if pct != last_percent:
                                last_percent = pct
                                self.progress.emit(pct)
                else:
                    line_buf += char

            return_code = self._proc.wait()

            if self._is_cancelled:
                return

            if return_code == 0 and os.path.exists(output_file):
                self.progress.emit(100)
                self.finished.emit(output_file)
            else:
                self.error.emit(f"FFmpeg conversion failed with return code {return_code}")

        except Exception as e:
            if not self._is_cancelled:
                self.error.emit(str(e))
