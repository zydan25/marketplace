from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import redirect, render

from .views import _context, _post_action, staff_only


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def catalog_manager(request):
    if request.method == "POST":
        try:
            with transaction.atomic():
                _post_action(request)
            messages.success(request, "تم حفظ التغييرات بنجاح.")
        except Exception as exc:  # noqa: BLE001 - admin UI must return safely
            messages.error(request, str(exc) if request.user.is_staff else "تعذر حفظ التغييرات.")
        return redirect("admin-services-catalog-manager")
    context = _context()
    context["section"] = "catalog-manager"
    return render(request, "services/catalog_manager.html", context)
