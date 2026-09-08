import re


_DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")


def normalize_yemen_phone(value):
    raw = str(value or "").translate(_DIGITS)
    digits = re.sub(r"\D+", "", raw)
    if digits.startswith("00967"):
        digits = digits[5:]
    elif digits.startswith("967") and len(digits) >= 12:
        digits = digits[3:]
    return digits
