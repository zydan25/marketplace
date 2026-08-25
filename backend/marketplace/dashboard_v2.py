from django.shortcuts import render

from .dashboard import dashboard_access_required, _dashboard_context


@dashboard_access_required
def dashboard_v2(request):
    return render(request, "admin/dashboard_v2.html", _dashboard_context())
