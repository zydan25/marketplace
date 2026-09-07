"""Compatibility normalization for Yemen Mobile catalog codes.

The supplied Sanaacash contract contains two historical code conventions:
regular offers are written as ``<digits>A`` while activation/service entries
such as ``A83001`` keep the leading ``A``.  The existing seed file used the
leading form for both, which would send the wrong offerid/offerkey upstream.
"""

import re

from .catalog_yemen import YEMEN_MOBILE_OFFERS as _RAW_YEMEN_MOBILE_OFFERS

# These are explicitly written with a leading A in the provider contract.
_LEADING_A_CODES = {
    "83001", "300007", "96004", "300009", "300067", "300068",
    "115887147", "101045",
}


def canonical_yemen_mobile_offer_code(code: str) -> str:
    value = str(code or "").strip()
    if not value:
        return value
    match = re.fullmatch(r"A(\d+)", value, re.IGNORECASE)
    if not match:
        return value
    digits = match.group(1)
    if digits in _LEADING_A_CODES:
        return "A" + digits
    return digits + "A"


YEMEN_MOBILE_OFFERS = [
    (canonical_yemen_mobile_offer_code(code), price, name, payment_type, line_type)
    for code, price, name, payment_type, line_type in _RAW_YEMEN_MOBILE_OFFERS
]

__all__ = ["YEMEN_MOBILE_OFFERS", "canonical_yemen_mobile_offer_code"]
