from pathlib import Path
import shutil
import os
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from marketplace.models import Product, ProductImage

source_dir = Path("/home/ubuntu/upload")
target_dir = Path("/home/ubuntu/work/backend/media/products/demo")
target_dir.mkdir(parents=True, exist_ok=True)
assignments = {1: "1000324500.jpg", 2: "1000324494.jpg"}
for product_id, filename in assignments.items():
    source = source_dir / filename
    if not source.exists():
        continue
    target = target_dir / filename
    shutil.copy2(source, target)
    product = Product.objects.get(pk=product_id)
    relative = f"products/demo/{filename}"
    product.main_image.name = relative
    product.save(update_fields=["main_image", "updated_at"])
    ProductImage.objects.filter(product=product).delete()
    ProductImage.objects.create(product=product, image=relative, sort_order=0, is_primary=True, alt_text=product.name)
print("attached", assignments)
