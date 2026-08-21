import os
import sys

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
import django

django.setup()

from marketplace.models import StorefrontSection, User

admin = User.objects.filter(role="admin").order_by("id").first()
if admin is None:
    raise SystemExit("لا يوجد حساب مدير لتهيئة CMS")

section, created = StorefrontSection.objects.get_or_create(
    owner=admin,
    title="الكل",
    section_type="tab",
    defaults={
        "sort_order": 0,
        "is_visible": True,
        "config": {
            "searchPlaceholder": "ابحثي عن منتج أو متجر",
            "slides": [],
            "circles": [],
            "promo": {
                "flashTitle": "تخفيضات سريعة",
                "flashSubtitle": "عرض المزيد",
                "flashMode": "flash",
                "freeShippingTitle": "شحن مجاني",
                "freeShippingSubtitle": "أضيفي المزيد للحصول عليه",
                "freeShippingCategory": "",
            },
        },
    },
)
if not created:
    config = section.config or {}
    config.setdefault("promo", {
        "flashTitle": "تخفيضات سريعة",
        "flashSubtitle": "عرض المزيد",
        "flashMode": "flash",
        "freeShippingTitle": "شحن مجاني",
        "freeShippingSubtitle": "أضيفي المزيد للحصول عليه",
        "freeShippingCategory": "",
    })
    section.config = config
    section.is_visible = True
    section.save(update_fields=["config", "is_visible", "updated_at"])
print(f"default storefront section {'created' if created else 'updated'}: {section.id}")
