from decimal import Decimal
from django.test import TestCase
from .models import Product, City, PriceGroup, VendorProfile, User
from .services import PricingEngine
from .cart_service import CartService

class PricingAndCartTests(TestCase):
    def setUp(self):
        self.vendor_user = User.objects.create_user(username="710000000", phone="710000000", password="123", role="vendor")
        self.vendor = VendorProfile.objects.create(owner=self.vendor_user, store_name="متجر التسعير", status="active")
        self.product = Product.objects.create(vendor=self.vendor, sku="P1", name="منتج 1", price=Decimal("1000.00"), stock=10, is_published=True)
        
        self.pg_increase = PriceGroup.objects.create(name="زيادة 10%", code="INC10", adjustment_type="percentage", percentage=Decimal("10.00"))
        self.pg_fixed = PriceGroup.objects.create(name="خصم ثابت", code="FIX50", adjustment_type="fixed", fixed_amount=Decimal("-50.00"))
        
        self.city_sanaa = City.objects.create(name="صنعاء", price_group=self.pg_increase, shipping_fee=Decimal("500.00"))
        self.city_aden = City.objects.create(name="عدن", price_group=self.pg_fixed, shipping_fee=Decimal("1000.00"))

    def test_pricing_engine_percentage_increase(self):
        result = PricingEngine.calculate(self.product, self.city_sanaa, quantity=2)
        self.assertEqual(result["base_price"], Decimal("1000.00"))
        self.assertEqual(result["city_adjustment"], Decimal("100.00"))  # 10% of 1000
        self.assertEqual(result["unit_final_price"], Decimal("1100.00"))
        self.assertEqual(result["total_price"], Decimal("2200.00"))

    def test_pricing_engine_fixed_discount(self):
        result = PricingEngine.calculate(self.product, self.city_aden, quantity=1)
        self.assertEqual(result["city_adjustment"], Decimal("-50.00"))
        self.assertEqual(result["unit_final_price"], Decimal("950.00"))

    def test_cart_service_validation(self):
        items = [{"product_id": self.product.id, "quantity": 2}]
        result = CartService.calculate_cart(items, city_id=self.city_sanaa.id)
        
        self.assertTrue(result["valid"])
        self.assertEqual(result["subtotal"], Decimal("2200.00"))  # 2 * 1100
        self.assertEqual(result["shipping_fee"], Decimal("500.00"))
        self.assertEqual(result["total"], Decimal("2700.00"))
        
    def test_cart_service_out_of_stock(self):
        items = [{"product_id": self.product.id, "quantity": 15}]
        result = CartService.calculate_cart(items, city_id=self.city_sanaa.id)
        
        self.assertFalse(result["valid"])
        self.assertIn("الكمية المطلوبة (15) غير متوفرة", result["errors"][0])
