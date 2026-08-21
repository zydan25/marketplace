from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from marketplace.root_views import landing_page

urlpatterns = [
    path("", landing_page, name="landing-page"),
    path("admin/", admin.site.urls),
    path("api/", include("marketplace.urls")),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
