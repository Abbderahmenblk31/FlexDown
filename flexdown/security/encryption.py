"""
FlexDown - وحدة تشفير وفك تشفير الملفات (File Encryption Module)
توفر فئة FileEncryptor لتشفير الملفات المحملة وفك تشفيرها لحماية البيانات الشخصية للمستخدم.
تستخدم معيار التشفير المتقدم (AES-256) عبر مكتبة Cryptography وواجهة Fernet مع اشتقاق المفاتيح بواسطة PBKDF2HMAC.
"""

import os
import base64
from typing import Tuple, Optional, Callable
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend
from cryptography.fernet import Fernet, InvalidToken


class FileEncryptor:
    """
    فئة تشفير الملفات وحمايتها بكلمة مرور.
    FileEncryptor provides secure file-level encryption and decryption
    using AES (Fernet) with PBKDF2 key derivation.
    """

    CHUNK_SIZE: int = 64 * 1024       # 64 KB لكل مقطع أثناء التشفير
    SALT_SIZE: int = 16               # حجم الملح العشوائي (16 بايت)
    ITERATIONS: int = 480_000         # 480 ألف دورة اشتقاق مفاتيح لضمان الأمان العالي
    MAGIC_HEADER: bytes = b"FLXENC01"  # ترويسة تعريفية للملف المشفر للتحقق من سلامته

    @staticmethod
    def derive_key(password: str, salt: Optional[bytes] = None) -> Tuple[bytes, bytes]:
        """
        اشتقاق مفتاح التشفير من كلمة المرور والملح (Salt).
        Derives a URL-safe Fernet encryption key using PBKDF2HMAC with SHA-256.

        :param password: كلمة المرور كنص
        :param salt: ملح التشفير (إذا لم يتم تمريره يتم توليد ملح عشوائي جديد)
        :return: زوج يتكون من (مفتاح التشفير المشتق Fernet key, الملح salt)
        """
        if not password:
            raise ValueError("لا يمكن أن تكون كلمة المرور فارغة (Password cannot be empty).")

        if salt is None:
            salt = os.urandom(FileEncryptor.SALT_SIZE)
        elif isinstance(salt, str):
            salt = salt.encode("latin1")

        password_bytes = password.encode("utf-8") if isinstance(password, str) else password

        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=FileEncryptor.ITERATIONS,
            backend=default_backend(),
        )

        derived = kdf.derive(password_bytes)
        # تشفير الناتج بنظام URL-safe Base64 ليتوافق مع متطلبات Fernet
        fernet_key = base64.urlsafe_b64encode(derived)
        return fernet_key, salt

    @classmethod
    def encrypt_file(
        cls,
        file_path: str,
        password: str,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """
        تشفير ملف مجزأً إلى كتل بحجم 64 كيلوبايت وحفظه كملف مشفر، ثم حذف الملف الأصلي.
        Encrypts a file in 64KB chunks, prepends salt, and deletes the original file.

        :param file_path: مسار الملف الأصلي المراد تشفيره
        :param password: كلمة مرور التشفير
        :param progress_callback: دالة اختيارية لإشعار واجهة المستخدم بالتقدم (تمت معالجته, الإجمالي)
        :return: مسار الملف المشفر الجديد (.enc)
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"الملف غير موجود: {file_path}")

        if not os.path.isfile(file_path):
            raise ValueError(f"المسار المحدد ليس ملفاً صالحاً: {file_path}")

        if not password:
            raise ValueError("كلمة المرور مطلوبة لإتمام عملية التشفير.")

        total_size = os.path.getsize(file_path)
        encrypted_path = file_path + ".enc"
        temp_encrypted_path = encrypted_path + ".tmp"

        # توليد ملح عشوائي واشتقاق مفتاح التشفير
        salt = os.urandom(cls.SALT_SIZE)
        key, _ = cls.derive_key(password, salt)
        fernet = Fernet(key)

        bytes_processed = 0

        try:
            with open(file_path, "rb") as f_in, open(temp_encrypted_path, "wb") as f_out:
                # كتابة الترويسة التعريفية والملح في بداية الملف
                f_out.write(cls.MAGIC_HEADER)
                f_out.write(salt)

                # قراءة وتشفير الملف كتلة بكتلة (64 كيلوبايت)
                while True:
                    chunk = f_in.read(cls.CHUNK_SIZE)
                    if not chunk:
                        break

                    encrypted_chunk = fernet.encrypt(chunk)
                    chunk_len = len(encrypted_chunk)

                    # كتابة طول الكتلة المشفرة (4 بايت بنظام Big-Endian) متبوعة بالكتلة المشفرة
                    f_out.write(chunk_len.to_bytes(4, byteorder="big"))
                    f_out.write(encrypted_chunk)

                    bytes_processed += len(chunk)
                    if progress_callback:
                        progress_callback(bytes_processed, total_size)

            # استبدال المسار النهائي بالملف المؤقت بعد اكتمال التشفير بنجاح
            if os.path.exists(encrypted_path):
                os.remove(encrypted_path)
            os.rename(temp_encrypted_path, encrypted_path)

            # حذف الملف الأصلي بعد نجاح عملية التشفير لحماية الخصوصية
            os.remove(file_path)

            return encrypted_path

        except Exception as e:
            # تنظيف الملف المؤقت في حال حدوث أي خطأ
            if os.path.exists(temp_encrypted_path):
                try:
                    os.remove(temp_encrypted_path)
                except OSError:
                    pass
            raise RuntimeError(f"فشلت عملية تشفير الملف: {str(e)}") from e

    @classmethod
    def decrypt_file(
        cls,
        encrypted_path: str,
        password: str,
        output_path: Optional[str] = None,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> str:
        """
        فك تشفير الملف المشفر باستخراج الملح وفك تشفير كل كتلة، وكتابة الملف الأصلي.
        Decrypts an encrypted file chunk-by-chunk and writes the original file.

        :param encrypted_path: مسار الملف المشفر
        :param password: كلمة مرور فك التشفير
        :param output_path: مسار الملف الناتج الاختياري (إذا ترك فارغاً يحذف امتداد .enc تلقائياً)
        :param progress_callback: دالة اختيارية لإشعار واجهة المستخدم بالتقدم
        :return: مسار الملف الأصلي المفكوك
        """
        if not os.path.exists(encrypted_path):
            raise FileNotFoundError(f"الملف المشفر غير موجود: {encrypted_path}")

        if not password:
            raise ValueError("كلمة المرور مطلوبة لفك التشفير.")

        # تحديد مسار الملف الناتج بعد فك التشفير
        if output_path:
            target_path = output_path
        elif encrypted_path.endswith(".enc"):
            target_path = encrypted_path[:-4]
        else:
            target_path = encrypted_path + ".dec"

        temp_target_path = target_path + ".tmp"
        file_size = os.path.getsize(encrypted_path)
        bytes_read = 0

        try:
            with open(encrypted_path, "rb") as f_in, open(temp_target_path, "wb") as f_out:
                # التحقق من الترويسة التعريفية إذا كانت موجودة
                header = f_in.read(len(cls.MAGIC_HEADER))
                if header == cls.MAGIC_HEADER:
                    salt = f_in.read(cls.SALT_SIZE)
                    bytes_read = len(cls.MAGIC_HEADER) + cls.SALT_SIZE
                else:
                    # توافقية في حال الملف لا يحتوي على magic header وبدأ مباشرة بالملح
                    f_in.seek(0)
                    salt = f_in.read(cls.SALT_SIZE)
                    bytes_read = cls.SALT_SIZE

                if len(salt) < cls.SALT_SIZE:
                    raise ValueError("الملف المشفر تالف أو غير صالح (حجم الملح غير مكتمل).")

                # اشتقاق مفتاح فك التشفير
                key, _ = cls.derive_key(password, salt)
                fernet = Fernet(key)

                # قراءة الكتل المشفرة وفك تشفيرها
                while True:
                    len_bytes = f_in.read(4)
                    if not len_bytes:
                        break  # الوصول إلى نهاية الملف
                    bytes_read += 4

                    chunk_len = int.from_bytes(len_bytes, byteorder="big")
                    encrypted_chunk = f_in.read(chunk_len)
                    bytes_read += len(encrypted_chunk)

                    if len(encrypted_chunk) != chunk_len:
                        raise ValueError("الملف المشفر غير مكتمل أو مقطوع.")

                    try:
                        decrypted_chunk = fernet.decrypt(encrypted_chunk)
                    except InvalidToken:
                        raise ValueError("كلمة المرور غير صحيحة أو تم التلاعب بمحتوى الملف.")

                    f_out.write(decrypted_chunk)

                    if progress_callback:
                        progress_callback(bytes_read, file_size)

            # نقل الملف المؤقت المفكوك إلى المسار النهائي
            if os.path.exists(target_path):
                os.remove(target_path)
            os.rename(temp_target_path, target_path)

            return target_path

        except Exception as e:
            # تنظيف الملف غير المكتمل
            if os.path.exists(temp_target_path):
                try:
                    os.remove(temp_target_path)
                except OSError:
                    pass
            raise e
