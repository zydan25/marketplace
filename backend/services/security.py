from cryptography.fernet import Fernet, InvalidToken
from django.conf import settings


def _fernet():
    key = getattr(settings, "SERVICES_CREDENTIALS_KEY", "")
    if not key:
        raise RuntimeError("SERVICES_CREDENTIALS_KEY غير مضبوط؛ لا يمكن حفظ بيانات الربط الحساسة بأمان.")
    return Fernet(key.encode() if isinstance(key, str) else key)


def encrypt_secret(value):
    if not value:
        return ""
    return _fernet().encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_secret(value):
    if not value:
        return ""
    try:
        return _fernet().decrypt(value.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise RuntimeError("تعذر فك بيانات اعتماد الربط؛ تحقق من SERVIC​ES_CREDENTIALS_KEY.") from exc
