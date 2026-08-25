from django.shortcuts import redirect


LEGACY_RESOURCE_MAP = {
    "product": "products",
    "category": "categories",
    "productvariant": "variants",
    "vendorprofile": "vendors",
    "vendorapplication": "applications",
    "order": "orders",
    "vendororder": "vendor-orders",
    "payment": "payments",
    "shipment": "shipments",
    "vendorpayout": "payouts",
    "vendorledgerentry": "ledger",
    "wallet": "wallets",
    "storefrontsection": "storefront",
    "designtheme": "themes",
    "notification": "notifications",
    "conversation": "conversations",
    "user": "users",
    "coupon": "coupons",
    "city": "cities",
    "pricegroup": "price-groups",
}


def legacy_resource_redirect(request, resource):
    target = LEGACY_RESOURCE_MAP.get(resource)
    if not target:
        return redirect("admin-dashboard")
    return redirect("admin-crud-list", resource=target)
