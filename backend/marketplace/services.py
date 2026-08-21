from decimal import Decimal
from .models import Product, City

class PricingEngine:
    @staticmethod
    def calculate(product: Product, city: City = None, quantity: int = 1, variant=None):
        base_price = variant.price_override if variant and variant.price_override is not None else product.price
        discount_amount = Decimal("0")
        if product.sale_price and product.sale_price < product.price:
            discount_amount = product.price - product.sale_price
            base_price = product.sale_price

        city_adjustment = Decimal("0")
        if city and city.price_group and city.price_group.is_active:
            pg = city.price_group
            if pg.adjustment_type == "percentage":
                city_adjustment = (base_price * pg.percentage / Decimal("100")).quantize(Decimal("0.01"))
            elif pg.adjustment_type == "fixed":
                city_adjustment = pg.fixed_amount

        unit_final_price = max(Decimal("0"), base_price + city_adjustment)
        total_price = unit_final_price * quantity
        
        return {
            "base_price": base_price,
            "discount_amount": discount_amount,
            "city_adjustment": city_adjustment,
            "unit_final_price": unit_final_price,
            "total_price": total_price
        }
