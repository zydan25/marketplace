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
        action = request.POST.get("action", "save")
        try:
            if action in {"archive", "activate", "delete"}:
                provider = get_object_or_404(ProviderConnection, pk=request.POST.get("provider"))
                with transaction.atomic():
                    if action == "archive":
                        ServiceDistribution.objects.filter(provider_link__provider=provider).update(is_active=False)
                        provider.links.update(is_active=False)
                        provider.is_active = False
                        provider.save(update_fields=["is_active", "updated_at"])
                        messages.success(request, f"تم إيقاف الربطية {provider.name} بأمان؛ لم تُحذف العمليات التاريخية.")
                    elif action == "activate":
                        provider.is_active = True
                        provider.links.update(is_active=True)
                        provider.save(update_fields=["is_active", "updated_at"])
                        messages.success(request, f"تم تفعيل الربطية {provider.name}. تم فتح مساراتها ويمكنك إعادة تخصيص التوزيع.")
                    else:
                        has_transactions = provider.links.filter(transactions__isnull=False).exists()
                        if has_transactions:
                            ServiceDistribution.objects.filter(provider_link__provider=provider).update(is_active=False)
                            provider.links.update(is_active=False)
                            provider.is_active = False
                            provider.save(update_fields=["is_active", "updated_at"])
                            messages.warning(request, f"للربطية {provider.name} عمليات تاريخية؛ لذلك تم أرشفتها بدل حذفها.")
                        else:
                            provider.delete()
                            messages.success(request, "تم حذف الربطية نهائيًا لأنها بلا عمليات تاريخية.")
            else:
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
                    note=(request.POST.get("note") or "").strip(),
                    base_url=(request.POST.get("base_url") or "https://sanaacash.yrbso.net/api/yr/").strip(),
                )
                messages.success(request, f"تم حفظ الربطية {provider.name} وتهيئة مسارات API القياسية تلقائيًا.")
        except Exception as exc:
            messages.error(request, f"تعذر تنفيذ العملية: {exc}")
        return redirect("admin-services-provider-setup")
    return render(request, "services/provider_setup.html", {"providers": ProviderConnection.objects.all(), "links": ProviderLink.objects.select_related("provider").all()})


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def distribution_matrix_view(request):
    if request.method == "POST":
        try:
            with transaction.atomic():
                provider = get_object_or_404(ProviderConnection, pk=request.POST.get("provider"), is_active=True)
                selected_services = {int(value) for value in request.POST.getlist("services") if value.isdigit()}
                route_entries = request.POST.getlist("route")
                priority_entries = request.POST.getlist("priority")
                route_map = {}
                for entry in route_entries:
                    if ":" not in entry:
                        continue
                    service_id, link_id = entry.split(":", 1)
                    if service_id.isdigit() and link_id.isdigit():
                        route_map[int(service_id)] = int(link_id)
                priority_map = {}
                for entry in priority_entries:
                    if ":" not in entry:
                        continue
                    service_id, value = entry.split(":", 1)
                    if service_id.isdigit() and value.isdigit():
                        priority_map[int(service_id)] = int(value)
                valid_links = set(provider.links.filter(is_active=True).values_list("id", flat=True))
                ServiceDistribution.objects.filter(provider_link__provider=provider).update(is_active=False)
                for service in Service.objects.filter(id__in=selected_services, is_active=True):
                    link_id = route_map.get(service.id)
                    if link_id not in valid_links:
                        raise ValueError(f"يجب اختيار مسار صالح للخدمة: {service.name}.")
                    ServiceDistribution.objects.update_or_create(service=service, provider_link_id=link_id, defaults={"priority": priority_map.get(service.id, 100), "is_active": True})
            messages.success(request, "تم تحديث توزيع الخدمات والمسارات والأولويات لهذه الربطية.")
        except Exception as exc:
            messages.error(request, f"تعذر تحديث التوزيع: {exc}")
        return redirect("admin-services-distribution")
    services, providers, distribution, links_by_provider = distribution_matrix()
    return render(request, "services/distribution_matrix.html", {"services": services, "providers": providers, "distribution": distribution, "links_by_provider": links_by_provider})
