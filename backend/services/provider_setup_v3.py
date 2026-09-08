from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.text import slugify

from .models import ProviderConnection, ServiceDistribution, ServiceRequestReference, ServiceTask
from .provider import ProviderClient
from .provider_setup import create_or_update_sanaacash_provider


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) == "admin"))


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def provider_setup(request):
    if request.method == "POST":
        action = request.POST.get("action", "save")
        provider_id = request.POST.get("provider") or ""
        try:
            provider = get_object_or_404(ProviderConnection, pk=provider_id) if provider_id else None
            with transaction.atomic():
                if action == "save":
                    name = (request.POST.get("name") or "").strip()
                    if not name:
                        raise ValueError("اسم الربطية مطلوب.")
                    code = (provider.code if provider else (request.POST.get("code") or slugify(name, allow_unicode=True))).strip()
                    provider = create_or_update_sanaacash_provider(
                        code=code,
                        name=name,
                        userid=(request.POST.get("userid") or "").strip(),
                        username=(request.POST.get("username") or "").strip(),
                        password=request.POST.get("password") or "",
                        note=(request.POST.get("note") or "").strip(),
                        base_url=(request.POST.get("base_url") or "").strip(),
                        domain_name="",
                    )
                    messages.success(request, "تم حفظ الربطية وإعادة تهيئة مسارات API القياسية.")
                elif action == "balance":
                    result = ProviderClient(provider).check_balance()
                    if result.success:
                        messages.success(request, f"الرصيد الحالي لدى المزود: {result.response.get('balance')}")
                    else:
                        messages.error(request, result.description or "تعذر فحص الرصيد.")
                elif action == "activate":
                    provider.is_active = True
                    provider.links.update(is_active=True)
                    provider.save(update_fields=["is_active", "updated_at"])
                    messages.success(request, "تم تفعيل الربطية ومساراتها القياسية.")
                elif action == "archive":
                    ServiceDistribution.objects.filter(provider_link__provider=provider).update(is_active=False)
                    provider.links.update(is_active=False)
                    provider.is_active = False
                    provider.save(update_fields=["is_active", "updated_at"])
                    messages.success(request, "تم إيقاف الربطية مع الحفاظ على السجل التاريخي.")
                elif action == "delete":
                    has_history = (
                        provider.links.filter(transactions__isnull=False).exists()
                        or provider.links.filter(tasks__isnull=False).exists()
                        or ServiceRequestReference.objects.filter(provider=provider).exists()
                    )
                    if has_history:
                        ServiceDistribution.objects.filter(provider_link__provider=provider).update(is_active=False)
                        provider.links.update(is_active=False)
                        provider.is_active = False
                        provider.save(update_fields=["is_active", "updated_at"])
                        messages.warning(request, "للربطية سجل عمليات؛ تم أرشفتها بدل حذفها.")
                    else:
                        ServiceDistribution.objects.filter(provider_link__provider=provider).delete()
                        provider.links.all().delete()
                        provider.delete()
                        messages.success(request, "تم حذف الربطية بأمان.")
                else:
                    raise ValueError("عملية غير معروفة.")
        except Exception as exc:
            messages.error(request, f"تعذر تنفيذ العملية: {exc}")
        return redirect(request.path + (f"?edit={provider_id}" if provider_id and action == "save" else ""))

    edit_id = request.GET.get("edit")
    editing_provider = ProviderConnection.objects.prefetch_related("links").filter(pk=edit_id).first() if edit_id else None
    providers = ProviderConnection.objects.prefetch_related("links").order_by("name")
    return render(request, "services/provider_setup_v3.html", {
        "providers": providers,
        "editing_provider": editing_provider,
        "show_form": bool(editing_provider or request.GET.get("add")),
    })
