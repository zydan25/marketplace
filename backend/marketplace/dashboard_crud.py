from django import forms
from django.db import IntegrityError
from django.db.models import Q
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render

from .dashboard import dashboard_access_required
from .models import Category, Coupon, DesignTheme, Notification, Order, Product, StorefrontSection, User, VendorProfile
from .models_extended import City, PriceGroup, ProductVariant
from .marketplace_models import Payment, Shipment, VendorApplication, VendorLedgerEntry, VendorPayout


class JsonTextarea(forms.Textarea):
    def __init__(self, *args, **kwargs):
        attrs = {"rows": 6, "dir": "ltr"}
        attrs.update(kwargs.pop("attrs", {}) or {})
        super().__init__(*args, attrs=attrs, **kwargs)


class DashboardForm(forms.ModelForm):
    class Meta:
        widgets = {"config": JsonTextarea(), "settings": JsonTextarea(), "tokens": JsonTextarea(), "layout": JsonTextarea(), "sections": JsonTextarea(), "details": JsonTextarea(), "shipping_address": JsonTextarea(), "metadata": JsonTextarea(), "audience": JsonTextarea()}


class ProductForm(DashboardForm):
    class Meta:
        model = Product
        fields = ["vendor", "categories", "sku", "name", "slug", "description", "brand", "material", "shipping_note", "return_policy", "price", "sale_price", "currency", "stock", "colors", "sizes", "hashtags", "details", "main_image", "is_published", "is_trending"]
        widgets = DashboardForm.Meta.widgets


class VendorForm(DashboardForm):
    class Meta:
        model = VendorProfile
        fields = ["owner", "store_name", "description", "logo", "cover", "phone", "address", "status", "commission_percent", "settings"]
        widgets = DashboardForm.Meta.widgets


class UserForm(DashboardForm):
    password = forms.CharField(required=False, widget=forms.PasswordInput(render_value=False), help_text="اتركه فارغًا عند التعديل.")
    class Meta:
        model = User
        fields = ["phone", "email", "first_name", "middle_name", "third_name", "last_name", "governorate", "role", "is_active", "is_staff", "is_phone_verified", "points_balance", "password"]
    def save(self, commit=True):
        obj = super().save(commit=False)
        password = self.cleaned_data.get("password")
        if password:
            obj.set_password(password)
        if commit:
            obj.save()
        return obj


class OrderForm(DashboardForm):
    class Meta:
        model = Order
        fields = ["customer", "order_number", "status", "subtotal", "shipping_fee", "discount", "total", "currency", "shipping_address", "payment_method", "payment_status", "metadata"]
        widgets = DashboardForm.Meta.widgets


RESOURCE = {
    "users": (User, UserForm, ["phone", "first_name", "last_name", "role", "is_active"], "المستخدمون"),
    "vendors": (VendorProfile, VendorForm, ["store_name", "owner", "status", "commission_percent"], "التجار"),
    "products": (Product, ProductForm, ["name", "sku", "vendor", "price", "stock", "is_published", "is_trending"], "المنتجات"),
    "categories": (Category, None, ["name", "slug", "parent", "is_active", "sort_order"], "الفئات"),
    "orders": (Order, OrderForm, ["order_number", "customer", "status", "total", "payment_status", "created_at"], "الطلبات"),
    "coupons": (Coupon, None, ["code", "discount_percent", "discount_amount", "minimum_order", "is_active"], "الكوبونات"),
    "storefront": (StorefrontSection, None, ["title", "section_type", "vendor", "sort_order", "is_visible"], "أقسام الواجهة"),
    "themes": (DesignTheme, None, ["name", "vendor", "is_global", "is_active"], "الثيمات"),
    "notifications": (Notification, None, ["title", "recipient", "product", "is_read", "created_at"], "الإشعارات"),
    "payments": (Payment, None, ["order", "provider", "method", "amount", "status", "paid_at"], "المدفوعات"),
    "shipments": (Shipment, None, ["vendor_order", "carrier", "tracking_number", "status", "shipped_at", "delivered_at"], "الشحن"),
    "payouts": (VendorPayout, None, ["vendor", "amount", "currency", "status", "reference"], "مستحقات التجار"),
    "cities": (City, None, ["name", "price_group", "shipping_fee", "is_active"], "المدن"),
    "price-groups": (PriceGroup, None, ["name", "code", "adjustment_type", "percentage", "fixed_amount", "is_active"], "مجموعات الأسعار"),
    "variants": (ProductVariant, None, ["product", "sku", "color", "size", "price_override", "stock", "reserved_stock", "is_active"], "الأصناف والمخزون"),
    "applications": (VendorApplication, None, ["store_name", "applicant", "phone", "status", "created_at"], "طلبات التجار"),
    "ledger": (VendorLedgerEntry, None, ["vendor", "entry_type", "amount", "balance_after", "reference", "created_at"], "دفتر التجار"),
}


def _form_for(model, explicit=None):
    if explicit:
        return explicit
    Meta = type("Meta", (), {"model": model, "fields": "__all__"})
    return type(f"{model.__name__}DashboardForm", (DashboardForm,), {"Meta": Meta})


def _model_queryset(resource):
    model = RESOURCE[resource][0]
    qs = model.objects.all()
    if resource == "products":
        qs = qs.select_related("vendor", "vendor__owner")
    elif resource == "vendors":
        qs = qs.select_related("owner")
    elif resource == "orders":
        qs = qs.select_related("customer")
    return qs


def _display_value(obj, field_name):
    value = getattr(obj, field_name, None)
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "نعم" if value else "لا"
    return str(value)


@dashboard_access_required
def resource_list(request, resource):
    if resource not in RESOURCE:
        raise Http404
    model, _, columns, label = RESOURCE[resource]
    qs = _model_queryset(resource)
    q = request.GET.get("q", "").strip()
    if q:
        conditions = [Q(**{f"{field.name}__icontains": q}) for field in model._meta.fields if field.get_internal_type() in {"CharField", "TextField", "EmailField", "SlugField"}]
        if conditions:
            query = conditions[0]
            for condition in conditions[1:]:
                query |= condition
            qs = qs.filter(query)
    rows = [{"object": obj, "values": [_display_value(obj, col) for col in columns]} for obj in qs.order_by("-pk")[:100]]
    return render(request, "admin/crud_list.html", {"resource": resource, "label": label, "columns": columns, "rows": rows, "q": q})


@dashboard_access_required
def resource_create(request, resource):
    if resource not in RESOURCE:
        raise Http404
    model, form_class, _, label = RESOURCE[resource]
    Form = _form_for(model, form_class)
    if request.method == "POST":
        form = Form(request.POST, request.FILES)
        if form.is_valid():
            try:
                form.save()
            except IntegrityError as exc:
                form.add_error(None, f"تعذر الحفظ بسبب تعارض بيانات فريدة: {exc}")
            else:
                return redirect("admin-crud-list", resource=resource)
    else:
        form = Form()
    return render(request, "admin/crud_form.html", {"resource": resource, "label": label, "form": form, "mode": "create"})


@dashboard_access_required
def resource_update(request, resource, pk):
    if resource not in RESOURCE:
        raise Http404
    model, form_class, _, label = RESOURCE[resource]
    obj = get_object_or_404(model, pk=pk)
    Form = _form_for(model, form_class)
    if request.method == "POST":
        form = Form(request.POST, request.FILES, instance=obj)
        if form.is_valid():
            try:
                form.save()
            except IntegrityError as exc:
                form.add_error(None, f"تعذر التحديث بسبب تعارض بيانات فريدة: {exc}")
            else:
                return redirect("admin-crud-list", resource=resource)
    else:
        form = Form(instance=obj)
    return render(request, "admin/crud_form.html", {"resource": resource, "label": label, "form": form, "mode": "edit", "object": obj})


@dashboard_access_required
def resource_delete(request, resource, pk):
    if resource not in RESOURCE:
        raise Http404
    model, _, _, label = RESOURCE[resource]
    obj = get_object_or_404(model, pk=pk)
    if request.method == "POST":
        obj.delete()
        return redirect("admin-crud-list", resource=resource)
    return render(request, "admin/crud_delete.html", {"resource": resource, "label": label, "object": obj})
