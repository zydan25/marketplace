from marketplace.marketplace_models import VendorApplication as LegacyVendorApplication
from marketplace.models import VendorProfile as LegacyVendorProfile


class VendorProfile(LegacyVendorProfile):
    class Meta:
        proxy = True
        verbose_name = "التاجر"
        verbose_name_plural = "التجار"
        ordering = ["-created_at"]


class VendorApplication(LegacyVendorApplication):
    class Meta:
        proxy = True
        verbose_name = "طلب تاجر"
        verbose_name_plural = "طلبات التجار"
        ordering = ["-created_at"]
