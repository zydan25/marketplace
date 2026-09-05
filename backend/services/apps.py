from django.apps import AppConfig


class ServicesConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "services"
    verbose_name = "الخدمات"

    def ready(self):
        # The services dashboard template owns its responsive shell and drawer.
        # The legacy response-injection helper in views.py must not inject a second
        # mobile bar/drawer, which caused the clipped/duplicated mobile UI.
        from . import views
        from django.shortcuts import render

        def render_services_page(request, ctx):
            return render(request, "services/dashboard.html", ctx)

        views._render_services_page = render_services_page
