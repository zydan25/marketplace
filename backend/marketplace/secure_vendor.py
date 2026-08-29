"""Compatibility exports for the vendor domain.

Canonical vendor APIs now live in ``vendors.api``. This module remains importable
so legacy integrations do not break during the modularization migration.
"""

from vendors.api import VendorApplicationViewSet, VendorViewSet

SecureVendorViewSet = VendorViewSet
