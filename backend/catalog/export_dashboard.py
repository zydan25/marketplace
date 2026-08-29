import csv

from django.http import HttpResponse

from .dashboard import _product_queryset, catalog_access_required


@catalog_access_required
def products_export_csv(request):
    qs = _product_queryset(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="catalog-products.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["المعرف", "الاسم", "SKU", "المتجر", "السعر", "سعر التخفيض", "العملة", "المخزون", "المحجوز", "متاح", "منشور", "ترند", "التقييم", "المبيعات", "آخر تحديث"])
    for product in qs.iterator(chunk_size=1000):
        writer.writerow([
            product.pk, product.name, product.sku, product.vendor.store_name, product.price, product.sale_price or "",
            product.currency, product.stock, product.reserved_stock, product.available_stock, "نعم" if product.is_published else "لا",
            "نعم" if product.is_trending else "لا", product.rating, product.sold_count, product.updated_at.isoformat(),
        ])
    return response
