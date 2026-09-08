from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render

from .admin_v4 import service_context, staff_only


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def modern_home(request):
    context = service_context()
    return render(request, "services/service_dashboard_home.html", context)
