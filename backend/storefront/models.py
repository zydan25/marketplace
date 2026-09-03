from marketplace.models import DesignTheme as LegacyDesignTheme, StorefrontSection as LegacyStorefrontSection
from marketplace.storefront_models import StorefrontMedia as LegacyStorefrontMedia


class DesignTheme(LegacyDesignTheme):
    class Meta:
        proxy = True
        verbose_name = "ثيم واجهة"
        verbose_name_plural = "ثيمات الواجهات"


class StorefrontSection(LegacyStorefrontSection):
    class Meta:
        proxy = True
        verbose_name = "قسم واجهة"
        verbose_name_plural = "أقسام الواجهة"


class StorefrontMedia(LegacyStorefrontMedia):
    class Meta:
        proxy = True
        verbose_name = "وسائط واجهة"
        verbose_name_plural = "وسائط الواجهة"
