import csv
from functools import wraps
from urllib.parse import urlencode

from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.core.paginator import Paginator
from django.db import transaction
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from rest_framework.authtoken.models import Token

from .forms import PreferenceForm, UserCreateForm, UserEditForm
from .models import User, UserPreference
from .services import ensure_preference, set_account_action


ACCOUNTS_HOME = "/admin/dashboard/accounts/"
BULK_ACTIONS = {
    "activate": "تفعيل الحسابات المحددة",
    "deactivate": "إيقاف الحسابات المحددة",
    "verify-phone": "توثيق الهواتف المحددة",
    "unverify-phone": "إلغاء توثيق الهواتف المحددة",
    "grant-staff": "منح صلاحية الإدارة للحسابات المحددة",
    "revoke-staff": "سحب صلاحية الإدارة من الحسابات المحددة",
    "revoke-api-token": "إلغاء جلسات API للحسابات المحددة",
}


def accounts_dashboard_access_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"/admin/dashboard/login/?next={request.get_full_path()}")
        if not (request.user.is_staff or getattr(request.user, "role", None) == "admin"):
            return HttpResponse("ليس لديك صلاحية الوصول إلى مركز الحسابات.", status=403)
        return view(request, *args, **kwargs)

    return wrapped


def _display_name(user):
    return user.get_full_name() or user.phone or user.username or f"مستخدم #{user.pk}"


def _user_list_queryset(request):
    qs = User.objects.all().order_by("-date_joined", "-pk")
    query = request.GET.get("q", "").strip()
    role = request.GET.get("role", "").strip()
    status = request.GET.get("status", "").strip()
    verified = request.GET.get("verified", "").strip()
    if query:
        from django.db.models import Q

        qs = qs.filter(
            Q(username__icontains=query)
            | Q(phone__icontains=query)
            | Q(email__icontains=query)
            | Q(first_name__icontains=query)
            | Q(middle_name__icontains=query)
            | Q(third_name__icontains=query)
            | Q(last_name__icontains=query)
        )
    if role in {choice.value for choice in User.Roles}:
        qs = qs.filter(role=role)
    if status == "active":
        qs = qs.filter(is_active=True)
    elif status == "inactive":
        qs = qs.filter(is_active=False)
    if verified == "yes":
        qs = qs.filter(is_phone_verified=True)
    elif verified == "no":
        qs = qs.filter(is_phone_verified=False)
    return qs


@accounts_dashboard_access_required
def accounts_dashboard(request):
    now = timezone.now()
    qs = User.objects.all()
    total = qs.count()
    customers = qs.filter(role=User.Roles.CUSTOMER).count()
    vendors = qs.filter(role=User.Roles.VENDOR).count()
    admins = qs.filter(role=User.Roles.ADMIN).count()
    active = qs.filter(is_active=True).count()
    inactive = qs.filter(is_active=False).count()
    verified = qs.filter(is_phone_verified=True).count()
    unverified = total - verified
    recent = qs.order_by("-date_joined", "-pk")[:8]
    return render(request, "accounts/dashboard/overview.html", {"now": now, "stats": {"total": total, "customers": customers, "vendors": vendors, "admins": admins, "active": active, "inactive": inactive, "verified": verified, "unverified": unverified}, "recent_users": recent})


@accounts_dashboard_access_required
def users_list(request):
    if request.method == "POST":
        action = request.POST.get("bulk_action", "")
        selected_ids = [value for value in request.POST.getlist("selected_users") if str(value).isdigit()]
        if action not in BULK_ACTIONS:
            messages.error(request, "إجراء جماعي غير صالح.")
        elif not selected_ids:
            messages.warning(request, "حدد حسابًا واحدًا على الأقل أولًا.")
        else:
            selected = list(User.objects.filter(pk__in=selected_ids))
            changed = 0
            skipped_self = False
            for user in selected:
                if user.pk == request.user.pk and action in {"deactivate", "revoke-staff", "revoke-api-token"}:
                    skipped_self = True
                    continue
                try:
                    set_account_action(user, action)
                except ValueError:
                    continue
                changed += 1
            messages.success(request, f"تم تنفيذ: {BULK_ACTIONS[action]} على {changed} حسابًا.")
            if skipped_self:
                messages.warning(request, "تم تجاهل حسابك الحالي لحمايتك من فقدان وصول الإدارة أو جلسة API.")
        query = request.GET.copy()
        return redirect(f"{reverse('accounts-dashboard:users')}?{urlencode(query, doseq=True)}" if query else reverse("accounts-dashboard:users"))

    qs = _user_list_queryset(request)
    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page"))
    query = request.GET.copy()
    query.pop("page", None)
    return render(request, "accounts/dashboard/users.html", {"page_obj": page_obj, "query_string": urlencode(query), "filters": {"q": request.GET.get("q", ""), "role": request.GET.get("role", ""), "status": request.GET.get("status", ""), "verified": request.GET.get("verified", "")}, "role_choices": User.Roles.choices, "bulk_actions": BULK_ACTIONS})


@accounts_dashboard_access_required
def user_create(request):
    if request.method == "POST":
        form = UserCreateForm(request.POST, request.FILES)
        if form.is_valid():
            with transaction.atomic():
                user = form.save()
                ensure_preference(user)
            messages.success(request, "تم إنشاء الحساب بنجاح.")
            return redirect("accounts-dashboard:user-detail", user_id=user.pk)
    else:
        form = UserCreateForm(initial={"role": User.Roles.CUSTOMER, "is_active": True, "is_phone_verified": False, "is_staff": False})
    return render(request, "accounts/dashboard/user_form.html", {"form": form, "mode": "create"})


@accounts_dashboard_access_required
def user_detail(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    preference = ensure_preference(user)
    return render(request, "accounts/dashboard/user_detail.html", {"user_obj": user, "display_name": _display_name(user), "edit_form": UserEditForm(instance=user), "preference_form": PreferenceForm(instance=preference), "password_form": SetPasswordForm(user), "preference": preference, "has_api_token": Token.objects.filter(user=user).exists()})


@accounts_dashboard_access_required
@transaction.atomic
def user_save(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method != "POST":
        return redirect("accounts-dashboard:user-detail", user_id=user.pk)
    form = UserEditForm(request.POST, request.FILES, instance=user)
    if not form.is_valid():
        preference = ensure_preference(user)
        return render(request, "accounts/dashboard/user_detail.html", {"user_obj": user, "display_name": _display_name(user), "edit_form": form, "preference_form": PreferenceForm(instance=preference), "password_form": SetPasswordForm(user), "preference": preference, "has_api_token": Token.objects.filter(user=user).exists()}, status=400)
    if user.pk == request.user.pk:
        form.instance.is_active = True
        form.instance.is_staff = True
        form.instance.role = User.Roles.ADMIN
        messages.warning(request, "تم إبقاء حسابك الحالي مديرًا ونشطًا لتجنب فقدان الوصول إلى الإدارة.")
    form.save()
    messages.success(request, "تم حفظ بيانات الحساب.")
    return redirect("accounts-dashboard:user-detail", user_id=user.pk)


@accounts_dashboard_access_required
def user_action(request, user_id, action):
    user = get_object_or_404(User, pk=user_id)
    if request.method != "POST":
        return redirect("accounts-dashboard:user-detail", user_id=user.pk)
    if user.pk == request.user.pk and action in {"deactivate", "revoke-staff", "revoke-api-token"}:
        messages.error(request, "لا يمكنك إلغاء وصول حسابك الحالي إلى الإدارة أو جلسة API أثناء استخدامها.")
        return redirect("accounts-dashboard:user-detail", user_id=user.pk)
    try:
        set_account_action(user, action)
    except ValueError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, "تم تنفيذ الإجراء على الحساب.")
    return redirect("accounts-dashboard:user-detail", user_id=user.pk)


@accounts_dashboard_access_required
def user_password(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method != "POST":
        return redirect("accounts-dashboard:user-detail", user_id=user.pk)
    form = SetPasswordForm(user, request.POST)
    if form.is_valid():
        form.save()
        if user.pk == request.user.pk:
            update_session_auth_hash(request, user)
        messages.success(request, "تم تغيير كلمة المرور بنجاح.")
    else:
        messages.error(request, "لم يتم تغيير كلمة المرور. راجع متطلبات كلمة المرور.")
    return redirect("accounts-dashboard:user-detail", user_id=user.pk)


@accounts_dashboard_access_required
def user_preferences_save(request, user_id):
    user = get_object_or_404(User, pk=user_id)
    if request.method != "POST":
        return redirect("accounts-dashboard:user-detail", user_id=user.pk)
    preference = ensure_preference(user)
    form = PreferenceForm(request.POST, instance=preference)
    if form.is_valid():
        form.save()
        messages.success(request, "تم حفظ تفضيلات الحساب.")
    else:
        messages.error(request, "تعذر حفظ التفضيلات. تحقق من البيانات.")
    return redirect("accounts-dashboard:user-detail", user_id=user.pk)


@accounts_dashboard_access_required
def users_export_csv(request):
    qs = _user_list_queryset(request)
    response = HttpResponse(content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = 'attachment; filename="accounts-users.csv"'
    response.write("\ufeff")
    writer = csv.writer(response)
    writer.writerow(["المعرف", "اسم المستخدم", "الهاتف", "الاسم الكامل", "البريد", "الدور", "نشط", "الهاتف موثق", "موظف إدارة", "النقاط", "تاريخ التسجيل", "آخر دخول"])
    for user in qs.iterator():
        writer.writerow([user.pk, user.username or "", user.phone or "", _display_name(user), user.email or "", user.get_role_display(), "نعم" if user.is_active else "لا", "نعم" if user.is_phone_verified else "لا", "نعم" if user.is_staff else "لا", user.points_balance, timezone.localtime(user.date_joined).strftime("%Y-%m-%d %H:%M") if user.date_joined else "", timezone.localtime(user.last_login).strftime("%Y-%m-%d %H:%M") if user.last_login else ""])
    return response
