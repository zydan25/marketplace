from decimal import Decimal
import os
import secrets
from django.core.management.base import BaseCommand
from marketplace.models import User, VendorProfile, Product, Category, Wallet
from marketplace.models_extended import PriceGroup, City

class Command(BaseCommand):
    help = "Create demo users and marketplace data"

    def upsert_user(self, phone, password, role, first_name):
        user, created = User.objects.get_or_create(phone=phone, defaults={"username": phone, "role": role, "first_name": first_name})
        user.username = phone
        user.role = role
        user.first_name = first_name
        user.set_password(password)
        user.is_active = True
        user.is_staff = role == "admin"
        user.is_superuser = role == "admin"
        user.save()
        Wallet.objects.get_or_create(user=user, defaults={"currency": "YER"})
        return user, created

    def handle(self, *args, **options):
        passwords = {
            "admin": os.getenv("DEMO_ADMIN_PASSWORD") or secrets.token_urlsafe(12),
            "vendor": os.getenv("DEMO_VENDOR_PASSWORD") or secrets.token_urlsafe(12),
            "customer": os.getenv("DEMO_CUSTOMER_PASSWORD") or secrets.token_urlsafe(12),
        }
        admin, _ = self.upsert_user("777000001", passwords["admin"], "admin", "مدير المنصة")
        vendor_user, _ = self.upsert_user("777000002", passwords["vendor"], "vendor", "تاجر تجريبي")
        customer, _ = self.upsert_user("777000003", passwords["customer"], "customer", "عميل تجريبي")

        vendor, _ = VendorProfile.objects.get_or_create(
            owner=vendor_user,
            defaults={"store_name": "متجر الأناقة", "slug": "elegance-store", "status": "active", "commission_percent": Decimal("10.00")},
        )
        vendor.status = "active"
        vendor.save()

        category, _ = Category.objects.get_or_create(name="أزياء", slug="fashion")
        Product.objects.get_or_create(
            sku="DEMO-001",
            defaults={
                "vendor": vendor,
                "name": "فستان تجريبي",
                "slug": "demo-dress",
                "description": "منتج تجريبي لاختبار الكتالوج والطلب.",
                "price": Decimal("15000.00"),
                "sale_price": Decimal("12000.00"),
                "currency": "YER",
                "stock": 20,
                "is_published": True,
                "is_trending": True,
            },
        )[0].categories.add(category)

        price_group, _ = PriceGroup.objects.get_or_create(code="DEMO-YER", defaults={"name": "تجربة بدون تعديل", "adjustment_type": "percentage", "percentage": 0})
        City.objects.get_or_create(name="إب", defaults={"price_group": price_group, "shipping_fee": Decimal("1000.00")})
        City.objects.get_or_create(name="صنعاء", defaults={"price_group": price_group, "shipping_fee": Decimal("1500.00")})

        self.stdout.write(self.style.SUCCESS("Demo data created/updated successfully."))
        self.stdout.write(f"Admin: 777000001 / {passwords['admin']}")
        self.stdout.write(f"Vendor: 777000002 / {passwords['vendor']}")
        self.stdout.write(f"Customer: 777000003 / {passwords['customer']}")
