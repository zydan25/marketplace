from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from marketplace.dashboard import dashboard, dashboard_icon, dashboard_login, dashboard_logout, dashboard_manifest, dashboard_worker
from marketplace.dashboard_crud import resource_create, resource_delete, resource_list, resource_update
from marketplace.root_views import landing_page
from marketplace.visual_storefront import create_section, update_section, visual_editor

urlpatterns = [
    path("", landing_page, name="landing-page"),
    path("admin/", admin.site.urls),
    path("admin/dashboard/login/", dashboard_login, name="admin-dashboard-login"),
    path("admin/dashboard/logout/", dashboard_logout, name="admin-dashboard-logout"),
    path("admin/dashboard/", dashboard, name="admin-dashboard"),
    path("admin/dashboard/manifest.json", dashboard_manifest, name="admin-dashboard-manifest"),
    path("admin/dashboard/sw.js", dashboard_worker, name="admin-dashboard-sw"),
    path("admin/dashboard/icon.svg", dashboard_icon, name="admin-dashboard-icon"),
    path("admin/dashboard/resource/<slug:resource>/", resource_list, name="admin-crud-list"),
    path("admin/dashboard/resource/<slug:resource>/add/", resource_create, name="admin-crud-create"),
    path("admin/dashboard/resource/<slug:resource>/<int:pk>/edit/", resource_update, name="admin-crud-edit"),
    path("admin/dashboard/resource/<slug:resource>/<int:pk>/delete/", resource_delete, name="admin-crud-delete"),
    path("admin/marketplace/storefront-editor/", visual_editor, name="admin-storefront-editor"),
    path("admin/marketplace/storefront-editor/section/create/", create_section, name="admin-storefront-section-create"),
    path("admin/marketplace/storefront-editor/section/<int:pk>/", update_section, name="admin-storefront-section-update"),
    path("api/", include("marketplace.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
