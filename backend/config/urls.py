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
from marketplace.control_pages import (
    control_placeholder,
    control_product_delete,
    control_product_report,
    control_store_delete,
    control_store_report,
    control_store_status,
)
from marketplace.control_v5 import order_chat_message, order_chat_open, order_status
from marketplace.control_v6 import (
    control_categories,
    control_orders,
    order_customer_message,
    order_detail,
    store_branch_delete,
    store_branch_save,
    store_category_delete,
    store_category_save,
    store_detail,
    control_stores,
)
from marketplace.control_v7 import control_products, product_detail
from marketplace.dashboard import dashboard_icon, dashboard_login, dashboard_logout, dashboard_manifest, dashboard_worker
from marketplace.dashboard_crud import resource_create, resource_delete, resource_list, resource_update
from marketplace.dashboard_legacy_redirects import legacy_resource_redirect
from marketplace.dashboard_v2 import dashboard_v2
from marketplace.erp_style_dashboard import erp_style_dashboard
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
    path("admin/dashboard/control/", erp_style_dashboard, name="admin-erp-style-dashboard"),

    # Integrated multi-vendor control workspaces.
    path("admin/dashboard/control/categories/", control_categories, name="admin-control-categories-v6"),
    path("admin/dashboard/control/stores/new/", control_stores, name="admin-control-stores-v6-new"),
    path("admin/dashboard/control/stores/<int:vendor_id>/detail/", store_detail, name="admin-control-store-v6-detail"),
    path("admin/dashboard/control/stores/<int:vendor_id>/categories/save/", store_category_save, name="admin-control-store-category-save"),
    path("admin/dashboard/control/stores/<int:vendor_id>/categories/<int:category_id>/delete/", store_category_delete, name="admin-control-store-category-delete"),
    path("admin/dashboard/control/stores/<int:vendor_id>/branches/save/", store_branch_save, name="admin-control-store-branch-save"),
    path("admin/dashboard/control/stores/<int:vendor_id>/branches/<int:branch_id>/delete/", store_branch_delete, name="admin-control-store-branch-delete"),
    path("admin/dashboard/control/stores/", control_stores, name="admin-control-stores-v6"),
    path("admin/dashboard/control/products/new/", control_products, name="admin-control-products-v7-new"),
    path("admin/dashboard/control/products/<int:product_id>/detail/", product_detail, name="admin-control-product-v7-detail"),
    path("admin/dashboard/control/products/", control_products, name="admin-control-products-v7"),
    path("admin/dashboard/control/orders/<int:order_id>/detail/", order_detail, name="admin-control-order-v6-detail"),
    path("admin/dashboard/control/orders/<int:order_id>/status/", order_status, name="admin-control-order-v6-status"),
    path("admin/dashboard/control/orders/<int:order_id>/chat/open/<int:vendor_order_id>/", order_chat_open, name="admin-control-order-v6-chat-open"),
    path("admin/dashboard/control/orders/<int:order_id>/chat/message/", order_chat_message, name="admin-control-order-v6-chat-message"),
    path("admin/dashboard/control/orders/<int:order_id>/customer-chat/message/", order_customer_message, name="admin-control-order-v6-customer-chat-message"),
    path("admin/dashboard/control/orders/", control_orders, name="admin-control-orders-v6"),

    # Legacy endpoints retained for reports/status actions and not-yet-migrated sections.
    path("admin/dashboard/control/stores/<int:vendor_id>/status/<str:status>/", control_store_status, name="admin-control-store-status"),
    path("admin/dashboard/control/stores/<int:vendor_id>/delete/", control_store_delete, name="admin-control-store-delete"),
    path("admin/dashboard/control/stores/<int:vendor_id>/report/", control_store_report, name="admin-control-store-report"),
    path("admin/dashboard/control/products/<int:product_id>/delete/", control_product_delete, name="admin-control-product-delete"),
    path("admin/dashboard/control/products/<int:product_id>/report/", control_product_report, name="admin-control-product-report"),
    path("admin/dashboard/control/<slug:section>/", control_placeholder, name="admin-control-placeholder"),
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
    path("admin/dashboard/accounting/<slug:section>/", accounting_dashboard, name="admin-dashboard-accounting-section"),
    path("admin/dashboard/services/", include("services.dashboard_urls")),
    path("admin/dashboard/communication/", communication_dashboard, name="admin-dashboard-communication"),
    path("admin/dashboard/communication/notifications/new/", notification_form, name="admin-communication-notification-new"),
    path("admin/dashboard/communication/notifications/<int:pk>/edit/", notification_form, name="admin-communication-notification-edit"),
    path("admin/dashboard/promotions/", promotions_dashboard, name="admin-dashboard-promotions"),
    path("admin/dashboard/promotions/coupons/new/", coupon_form, name="admin-promotions-coupon-new"),
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
