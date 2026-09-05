from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .models import ProviderConnection, ProviderLink, Service, ServiceDistribution
from .provider_setup import create_or_update_sanaacash_provider, distribution_matrix


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def provider_setup(request):
    if request.method == "POST":
        try:
            code = (request.POST.get("code") or "").strip()
            name = (request.POST.get("name") or "").strip()
            if not code or not name:
                raise ValueError("كود واسم الربطية مطلوبان.")
            provider = create_or_update_sanaacash_provider(
                code=code,
                name=name,
                userid=(request.POST.get("userid") or "").strip(),
                domain_name=(request.POST.get("domain_name") or "").strip(),
                username=(request.POST.get("username") or "").strip(),
                password=request.POST.get("password") or "",
                base_url=(request.POST.get("base_url") or "https://sanaacash.yrbso.net/api/yr/").strip(),
            )
            messages.success(request, f"تم حفظ الربطية {provider.name} وتهيئة مسارات Sanaacash تلقائيًا.")
        except Exception as exc:
            messages.error(request, f"تعذر حفظ الربطية: {exc}")
        return redirect("admin-services-provider-setup")
    return render(request, "services/provider_setup.html", {"providers": ProviderConnection.objects.all(), "links": ProviderLink.objects.select_related("provider").all()})


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def distribution_matrix_view(request):
    if request.method == "POST":
        try:
            with transaction.atomic():
                provider = get_object_or_404(ProviderConnection, pk=request.POST.get("provider"))
                service_ids = {int(value) for value in request.POST.getlist("services") if value.isdigit()}
                priorities = request.POST.getlist("priority")
                links = list(provider.links.filter(is_active=True).order_by("priority", "id"))
                if not links:
                    raise ValueError("لا توجد مسارات فعالة لهذه الربطية.")
                link = links[0]
                ServiceDistribution.objects.filter(provider_link__provider=provider).update(is_active=False)
                priority_map = {}
                for entry in priorities:
                    if ":" in entry:
                        service_id, value = entry.split(":", 1)
                        if service_id.isdigit() and value.isdigit():
                            priority_map[int(service_id)] = int(value)
                for service in Service.objects.filter(id__in=service_ids, is_active=True):
                    ServiceDistribution.objects.update_or_create(
                        service=service,
                        provider_link=link,
                        defaults={"priority": priority_map.get(service.id, 100), "is_active": True},
                    )
            messages.success(request, "تم تحديث توزيع الخدمات لهذه الربطية.")
        except Exception as exc:
            messages.error(request, f"تعذر تحديث التوزيع: {exc}")
        return redirect("admin-services-distribution")
    services, providers, distribution, links = distribution_matrix()
    return render(request, "services/distribution_matrix.html", {"services": services, "providers": providers, "distribution": distribution, "links": links})
