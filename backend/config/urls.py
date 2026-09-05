from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.shortcuts import redirect
from django.urls import include, path
from accounting.views import dashboard as accounting_dashboard
from communication.views import dashboard as communication_dashboard, notification_form
from finance.views import currency_rate_form, dashboard as finance_dashboard, vendor_shipping_form
from orders.views import dashboard as orders_dashboard, shipment_form
from promotions.views import coupon_form, dashboard as promotions_dashboard, loan_review
from storefront.views import dashboard as storefront_dashboard, media_form, section_form, theme_form
from marketplace.dashboard import dashboard_icon, dashboard_login, dashboard_logout, dashboard_manifest, dashboard_worker
from marketplace.dashboard_crud import resource_create, resource_delete, resource_list, resource_update
from marketplace.dashboard_legacy_redirects import legacy_resource_redirect
from marketplace.dashboard_v2 import dashboard_v2
from marketplace.root_views import landing_page
from marketplace.theme_studio import theme_studio
from marketplace.visual_storefront_v8 import create_section, reorder_sections, update_section, upload_storefront_image, visual_editor
from marketplace.visual_storefront_v9 import visual_editor_v9


def legacy_user_admin_redirect(request, rest=""):
    target = "/admin/accounts/user/"
    if rest:
        target = f"{target}{rest}"
    return redirect(target)


urlpatterns = [
    path("", landing_page, name="landing-page"),
    path("admin/dashboard/login/", dashboard_login, name="admin-dashboard-login"),
    path("admin/dashboard/logout/", dashboard_logout, name="admin-dashboard-logout"),
    path("admin/dashboard/", dashboard_v2, name="admin-dashboard"),
    path("admin/dashboard/theme-studio/", theme_studio, name="admin-theme-studio"),
    path("admin/dashboard/accounts/", include("accounts.dashboard_urls")),
    path("admin/dashboard/catalog/", include("catalog.dashboard_urls")),
    path("admin/dashboard/vendors/", include("vendors.dashboard_urls")),
    path("admin/dashboard/storefront/", storefront_dashboard, name="admin-dashboard-storefront"),
    path("admin/dashboard/storefront/themes/new/", theme_form, name="admin-storefront-theme-new"),
    path("admin/dashboard/storefront/themes/<int:pk>/edit/", theme_form, name="admin-storefront-theme-edit"),
    path("admin/dashboard/storefront/sections/new/", section_form, name="admin-storefront-section-new"),
    path("admin/dashboard/storefront/sections/<int:pk>/edit/", section_form, name="admin-storefront-section-edit"),
    path("admin/dashboard/storefront/media/new/", media_form, name="admin-storefront-media-new"),
    path("admin/dashboard/storefront/media/<int:pk>/edit/", media_form, name="admin-storefront-media-edit"),
    path("admin/dashboard/orders/", orders_dashboard, name="admin-dashboard-orders"),
    path("admin/dashboard/orders/shipments/<int:pk>/edit/", shipment_form, name="admin-order-shipment-edit"),
    path("admin/dashboard/finance/", finance_dashboard, name="admin-dashboard-finance"),
    path("admin/dashboard/finance/currency-rates/new/", currency_rate_form, name="admin-finance-currency-rate-new"),
    path("admin/dashboard/finance/currency-rates/<int:pk>/edit/", currency_rate_form, name="admin-finance-currency-rate-edit"),
    path("admin/dashboard/finance/shipping/new/", vendor_shipping_form, name="admin-finance-shipping-new"),
    path("admin/dashboard/finance/shipping/<int:pk>/edit/", vendor_shipping_form, name="admin-finance-shipping-edit"),
    path("admin/dashboard/accounting/", accounting_dashboard, name="admin-dashboard-accounting"),
    path("admin/dashboard/communication/", communication_dashboard, name="admin-dashboard-communication"),
    path("admin/dashboard/communication/notifications/new/", notification_form, name="admin-communication-notification-new"),
    path("admin/dashboard/communication/notifications/<int:pk>/edit/", notification_form, name="admin-communication-notification-edit"),
    path("admin/dashboard/promotions/", promotions_dashboard, name="admin-dashboard-promotions"),
    path("admin/dashboard/promotions/coupons/new/", coupon_form, name="admin-promotions-coupon-new"),
    path("admin/dashboard/promotions/coupons/<int:pk>/edit/", coupon_form, name="admin-promotions-coupon-edit"),
    path("admin/dashboard/promotions/loans/<int:pk>/review/", loan_review, name="admin-promotions-loan-review"),
    path("admin/dashboard/manifest.json", dashboard_manifest, name="admin-dashboard-manifest"),
    path("admin/dashboard/sw.js", dashboard_worker, name="admin-dashboard-sw"),
    path("admin/dashboard/icon.svg", dashboard_icon, name="admin-dashboard-icon"),
    path("admin/dashboard/resource/<slug:resource>/", resource_list, name="admin-crud-list"),
    path("admin/dashboard/resource/<slug:resource>/add/", resource_create, name="admin-crud-create"),
    path("admin/dashboard/resource/<slug:resource>/<int:pk>/edit/", resource_update, name="admin-crud-edit"),
    path("admin/dashboard/resource/<slug:resource>/<int:pk>/delete/", resource_delete, name="admin-crud-delete"),
    path("admin/marketplace/user/", legacy_user_admin_redirect, name="legacy-marketplace-user-admin"),
    path("admin/marketplace/user/<path:rest>", legacy_user_admin_redirect, name="legacy-marketplace-user-admin-rest"),
    path("admin/marketplace/storefront-editor/", visual_editor_v9, name="admin-storefront-editor"),
    path("admin/marketplace/storefront-editor-legacy/", visual_editor, name="admin-storefront-editor-legacy"),
    path("admin/marketplace/storefront-editor/section/create/", create_section, name="admin-storefront-section-create"),
    path("admin/marketplace/storefront-editor/section/<int:pk>/", update_section, name="admin-storefront-section-update"),
    path("admin/marketplace/storefront-editor/upload-image/", upload_storefront_image, name="admin-storefront-image-upload"),
    path("admin/marketplace/storefront-editor/reorder/", reorder_sections, name="admin-storefront-section-reorder"),
    path("admin/marketplace/storefront-builder/", visual_editor_v9, name="admin-storefront-builder"),
    path("admin/marketplace/storefront-builder/create/", create_section, name="admin-storefront-builder-create"),
    path("admin/marketplace/storefront-builder/<int:pk>/save/", update_section, name="admin-storefront-builder-save"),
    path("admin/marketplace/storefront-builder/<int:pk>/delete/", update_section, name="admin-storefront-builder-delete"),
    path("admin/marketplace/storefront-builder/<int:pk>/duplicate/", update_section, name="admin-storefront-builder-duplicate"),
    path("admin/marketplace/storefront-builder/<int:pk>/publish/", update_section, name="admin-storefront-builder-publish"),
    path("admin/marketplace/storefront-builder/upload/", upload_storefront_image, name="admin-storefront-builder-upload"),
    path("admin/marketplace/storefront-builder/reorder/", reorder_sections, name="admin-storefront-builder-reorder"),
    path("admin/marketplace/storefront-builder/reorder-by-numbers/", reorder_sections, name="admin-storefront-builder-reorder-by-numbers"),
    path("admin/marketplace/<slug:resource>/", legacy_resource_redirect, name="admin-legacy-resource"),
    path("admin/", admin.site.urls),
    path("api/", include("marketplace.urls")),
    path("api/v2/", include("config.api_v2_urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
