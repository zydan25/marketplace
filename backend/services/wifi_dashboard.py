from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import user_passes_test
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render

from .wifi_cards import WifiCard
from .wifi_denominations import WifiDenomination
from .wifi_networks import WifiNetwork


def staff_only(user):
    return bool(user.is_authenticated and (user.is_staff or getattr(user, "role", None) in {"admin", "manager", "staff"}))


@user_passes_test(staff_only, login_url="/admin/dashboard/login/")
def wifi_management(request):
    if request.method == "POST":
        action = request.POST.get("action")
        try:
            with transaction.atomic():
                if action == "network":
                    owner = get_object_or_404(get_user_model(), pk=request.POST.get("owner"), is_active=True)
                    obj = WifiNetwork.objects.filter(pk=request.POST.get("pk") or 0).first() or WifiNetwork()
                    obj.owner = owner
                    obj.name = request.POST.get("name", "").strip()
                    obj.location = request.POST.get("location", "").strip()
                    obj.management_percent = request.POST.get("management_percent", "0") or 0
                    obj.latitude = request.POST.get("latitude") or None
                    obj.longitude = request.POST.get("longitude") or None
                    obj.description = request.POST.get("description", "").strip()
                    obj.is_active = True
                    if not obj.name or not obj.location:
                        raise ValueError("اسم الشبكة والموقع مطلوبان.")
                    obj.save()
                    messages.success(request, "تم حفظ شبكة الوايفاي وربطها بالعميل.")
                elif action == "denomination":
                    network = get_object_or_404(WifiNetwork, pk=request.POST.get("network"), is_active=True)
                    obj = WifiDenomination.objects.filter(pk=request.POST.get("pk") or 0).first() or WifiDenomination()
                    obj.network = network
                    obj.name = request.POST.get("name", "").strip()
                    # Server-side generated identifier; operators do not enter it.
                    obj.denomination_number = ""
                    obj.face_value = request.POST.get("face_value", "0") or 0
                    obj.sale_price = request.POST.get("sale_price", "0") or 0
                    obj.is_active = True
                    if not obj.name or float(obj.face_value) <= 0 or float(obj.sale_price) <= 0:
                        raise ValueError("اسم الفئة والقيمة الاسمية وسعر البيع مطلوبة.")
                    obj.save()
                    messages.success(request, f"تم حفظ فئة الوايفاي برقم {obj.denomination_number}.")
                elif action == "card":
                    denomination = get_object_or_404(WifiDenomination, pk=request.POST.get("denomination"), is_active=True, network__is_active=True)
                    obj = WifiCard.objects.filter(pk=request.POST.get("pk") or 0).first() or WifiCard()
                    obj.denomination = denomination
                    obj.card_number = request.POST.get("card_number", "").strip()
                    obj.pin = request.POST.get("pin", "").strip()
                    obj.status = request.POST.get("status", WifiCard.Status.AVAILABLE)
                    if not obj.card_number:
                        raise ValueError("اسم المستخدم / رقم الكرت مطلوب.")
                    obj.save()
                    messages.success(request, "تم حفظ الكرت؛ كلمة المرور اختيارية.")
                elif action == "bulk_cards":
                    denomination = get_object_or_404(WifiDenomination, pk=request.POST.get("denomination"), is_active=True)
                    created = 0
                    for line in request.POST.get("cards", "").splitlines():
                        raw = [x.strip() for x in line.split(",", 1)]
                        username = raw[0] if raw else ""
                        password = raw[1] if len(raw) == 2 else ""
                        if not username:
                            continue
                        WifiCard.objects.get_or_create(
                            denomination=denomination,
                            card_number=username,
                            defaults={"pin": password, "status": WifiCard.Status.AVAILABLE},
                        )
                        created += 1
                    messages.success(request, f"تمت معالجة {created} كرت رقمي.")
                elif action == "toggle_network":
                    network = get_object_or_404(WifiNetwork, pk=request.POST.get("pk"))
                    network.is_active = not network.is_active
                    network.save(update_fields=["is_active", "updated_at"])
                    messages.success(request, "تم تحديث حالة الشبكة.")
                elif action == "toggle_denomination":
                    denomination = get_object_or_404(WifiDenomination, pk=request.POST.get("pk"))
                    denomination.is_active = not denomination.is_active
                    denomination.save(update_fields=["is_active", "updated_at"])
                    messages.success(request, "تم تحديث حالة فئة الوايفاي.")
                elif action == "toggle_card":
                    card = get_object_or_404(WifiCard, pk=request.POST.get("pk"))
                    if card.status == WifiCard.Status.AVAILABLE:
                        card.status = WifiCard.Status.BLOCKED
                    elif card.status == WifiCard.Status.BLOCKED:
                        card.status = WifiCard.Status.AVAILABLE
                    card.save(update_fields=["status", "updated_at"])
                    messages.success(request, "تم تحديث حالة الكرت.")
        except Exception as exc:
            messages.error(request, f"تعذر الحفظ: {exc}")
        return redirect(request.path)

    owners = get_user_model().objects.filter(is_active=True).order_by("first_name", "last_name", "phone")
    networks = WifiNetwork.objects.select_related("owner").prefetch_related("denominations__cards").order_by("name")
    denominations = WifiDenomination.objects.select_related("network", "network__owner").prefetch_related("cards").order_by("network__name", "face_value")
    cards = WifiCard.objects.select_related("denomination__network", "sold_to").order_by("status", "denomination__network__name", "id")[:500]

    edit_network = WifiNetwork.objects.select_related("owner").filter(pk=request.GET.get("edit_network") or 0).first()
    edit_denomination = WifiDenomination.objects.select_related("network").filter(pk=request.GET.get("edit_denomination") or 0).first()
    edit_card = WifiCard.objects.select_related("denomination__network").filter(pk=request.GET.get("edit_card") or 0).first()

    return render(request, "services/wifi_management.html", {
        "owners": owners,
        "networks": networks,
        "denominations": denominations,
        "cards": cards,
        "edit_network": edit_network,
        "edit_denomination": edit_denomination,
        "edit_card": edit_card,
    })
