"""Legacy import path kept for backwards compatibility.

Business logic now lives in ``finance.services``.
"""

from finance.services import VendorFinanceViewSet

__all__ = ["VendorFinanceViewSet"]
