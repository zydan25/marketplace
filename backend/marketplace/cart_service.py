from decimal import Decimal
from .models import Product, City
from .services import PricingEngine

class CartService:
    @staticmethod
    def calculate_cart(items_data, city_id=None):
        city = City.objects.filter(id=city_id).first() if city_id else None
        
        subtotal = Decimal("0")
        validated_items = []
        errors = []
        
        for item in items_data:
            try:
                product = Product.objects.get(pk=item.get("product_id"), is_published=True)
                quantity = int(item.get("quantity", 1))
                
                if quantity < 1:
                    errors.append(f"الكمية غير صالحة للمنتج {product.name}")
                    continue
                    
                if product.stock < quantity:
                    errors.append(f"الكمية المطلوبة ({quantity}) غير متوفرة للمنتج {product.name}. المتوفر: {product.stock}")
                    continue
                    
                pricing = PricingEngine.calculate(product, city, quantity)
                
                validated_items.append({
                    "product_id": product.id,
                    "name": product.name,
                    "sku": product.sku,
                    "quantity": quantity,
                    "unit_price": pricing["unit_final_price"],
                    "line_total": pricing["total_price"],
                    "color": item.get("color", ""),
                    "size": item.get("size", "")
                })
                
                subtotal += pricing["total_price"]
                
            except Product.DoesNotExist:
                errors.append(f"المنتج رقم {item.get('product_id')} غير موجود أو غير متاح")
                
        shipping_fee = city.shipping_fee if city else Decimal("0")
        total = subtotal + shipping_fee
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "items": validated_items,
            "subtotal": subtotal,
            "shipping_fee": shipping_fee,
            "total": total
        }
