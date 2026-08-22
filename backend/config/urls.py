from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from marketplace.root_views import landing_page
from marketplace.visual_storefront import create_section, update_section, visual_editor

urlpatterns = [
    path("", landing_page, name="landing-page"),
    path("admin/", admin.site.urls),
    path("admin/marketplace/storefront-editor/", visual_editor, name="admin-storefront-editor"),
    path("admin/marketplace/storefront-editor/section/create/", create_section, name="admin-storefront-section-create"),
    path("admin/marketplace/storefront-editor/section/<int:pk>/", update_section, name="admin-storefront-section-update"),
    path("api/", include("marketplace.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
