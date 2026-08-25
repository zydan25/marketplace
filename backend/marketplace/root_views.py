from django.shortcuts import redirect


def landing_page(request):
    # The web root is the administration portal in this deployment. The customer
    # and vendor experiences remain separate Expo applications and use /api/.
    # Use the concrete URL instead of a shared URL name because the API also has
    # an `admin-dashboard` route and URL-name collisions can resolve to /api/.
    return redirect("/admin/dashboard/") if request.user.is_authenticated and (request.user.is_staff or getattr(request.user, "role", None) == "admin") else redirect("/admin/dashboard/login/")
