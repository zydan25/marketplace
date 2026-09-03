from django.urls import include, path
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.schemas import get_schema_view


schema_view = get_schema_view(title="Shabik Marketplace API", version="2.0", public=True)


@api_view(["GET"])
def api_v2_root(request):
    return Response({
        "name": "Shabik Marketplace API",
        "version": "2",
        "status": "stable-domain-boundaries",
        "domains": {
            "accounts": "/api/v2/accounts/",
            "catalog": "/api/v2/catalog/",
            "vendors": "/api/v2/vendors/",
            "storefront": "/api/v2/storefront/",
            "orders": "/api/v2/orders/",
            "finance": "/api/v2/finance/",
            "communication": "/api/v2/communication/",
            "promotions": "/api/v2/promotions/",
        },
        "schema": "/api/v2/schema/",
    })


urlpatterns = [
    path("", api_v2_root, name="api-v2-root"),
    path("schema/", schema_view, name="api-v2-schema"),
    path("accounts/", include(("accounts.urls", "accounts-v2"), namespace="accounts-v2")),
    path("catalog/", include(("catalog.api_v2_urls", "catalog-v2"), namespace="catalog-v2")),
    path("vendors/", include(("vendors.urls", "vendors-v2"), namespace="vendors-v2")),
    path("storefront/", include(("storefront.urls", "storefront-v2"), namespace="storefront-v2")),
    path("orders/", include(("orders.urls", "orders-v2"), namespace="orders-v2")),
    path("finance/", include(("finance.urls", "finance-v2"), namespace="finance-v2")),
    path("communication/", include(("communication.urls", "communication-v2"), namespace="communication-v2")),
    path("promotions/", include(("promotions.urls", "promotions-v2"), namespace="promotions-v2")),
]
