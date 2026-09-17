import json

from django import forms

from marketplace.models import User

from .models import VendorApplication, VendorBranch, VendorCategory, VendorProfile


class VendorProfileForm(forms.ModelForm):
    class Meta:
        model = VendorProfile
        fields = ["owner", "store_name", "slug", "description", "logo", "cover", "phone", "address", "status", "commission_percent", "settings"]
        widgets = {
            "owner": forms.Select(attrs={"dir": "ltr"}),
            "slug": forms.TextInput(attrs={"dir": "ltr", "placeholder": "يُنشأ تلقائيًا"}),
            "description": forms.Textarea(attrs={"rows": 4}),
            "address": forms.TextInput(),
            "commission_percent": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}),
            "settings": forms.Textarea(attrs={"rows": 7, "dir": "ltr", "placeholder": "{}"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        owner_qs = User.objects.filter(is_staff=False).order_by("phone", "email", "id")
        if self.instance.pk and self.instance.owner_id:
            owner_qs = User.objects.filter(is_staff=False).filter(pk=self.instance.owner_id) | owner_qs
            owner_qs = owner_qs.distinct().order_by("phone", "email", "id")
        else:
            owner_qs = owner_qs.filter(role__in=[User.Roles.CUSTOMER, User.Roles.VENDOR])
        self.fields["owner"].queryset = owner_qs
        self.fields["owner"].disabled = False
        if self.instance.pk:
            self.initial["settings"] = json.dumps(self.instance.settings or {}, ensure_ascii=False, indent=2)

    def clean_owner(self):
        owner = self.cleaned_data["owner"]
        if owner.is_staff:
            raise forms.ValidationError("لا يمكن تعيين مستخدم إداري كمالك متجر.")
        return owner

    def clean_commission_percent(self):
        value = self.cleaned_data["commission_percent"]
        if value < 0 or value > 100:
            raise forms.ValidationError("العمولة يجب أن تكون بين 0 و100٪.")
        return value

    def clean_settings(self):
        value = self.cleaned_data.get("settings")
        if isinstance(value, dict):
            return value
        if value in (None, ""):
            return {}
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            raise forms.ValidationError("إعدادات المتجر يجب أن تكون JSON صالحًا.")
        if not isinstance(parsed, dict):
            raise forms.ValidationError("إعدادات المتجر يجب أن تكون كائن JSON.")
        return parsed


class VendorCategoryForm(forms.ModelForm):
    class Meta:
        model = VendorCategory
        fields = ["vendor", "name", "slug", "description", "image", "parent", "is_active", "sort_order"]
        widgets = {
            "vendor": forms.Select(),
            "slug": forms.TextInput(attrs={"dir": "ltr", "placeholder": "يُنشأ تلقائيًا"}),
            "description": forms.Textarea(attrs={"rows": 3}),
            "sort_order": forms.NumberInput(attrs={"min": 0}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        vendor = self.instance.vendor if self.instance.pk else None
        if vendor:
            self.fields["parent"].queryset = VendorCategory.objects.filter(vendor=vendor).exclude(pk=self.instance.pk).order_by("sort_order", "name")
        else:
            self.fields["parent"].queryset = VendorCategory.objects.all().order_by("vendor__store_name", "sort_order", "name")

    def clean(self):
        cleaned = super().clean()
        vendor = cleaned.get("vendor")
        parent = cleaned.get("parent")
        if parent and vendor and parent.vendor_id != vendor.pk:
            self.add_error("parent", "الفئة الأب يجب أن تنتمي إلى المتجر نفسه.")
        if self.instance.pk and parent:
            current = parent
            while current:
                if current.pk == self.instance.pk:
                    self.add_error("parent", "لا يمكن وضع الفئة داخل نفسها أو أحد أبنائها.")
                    break
                current = current.parent
        return cleaned


class VendorBranchForm(forms.ModelForm):
    class Meta:
        model = VendorBranch
        fields = [
            "vendor", "name", "code", "manager_name", "phone", "governorate", "address",
            "latitude", "longitude", "opening_hours", "is_main", "is_active",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"dir": "ltr"}),
            "opening_hours": forms.Textarea(attrs={"rows": 5, "dir": "ltr", "placeholder": "{\"sat\": \"09:00-22:00\"}"}),
            "latitude": forms.NumberInput(attrs={"step": "0.000001"}),
            "longitude": forms.NumberInput(attrs={"step": "0.000001"}),
        }

    def clean_opening_hours(self):
        value = self.cleaned_data.get("opening_hours")
        if isinstance(value, dict):
            return value
        if not value:
            return {}
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            raise forms.ValidationError("ساعات الدوام يجب أن تكون JSON صالحًا.")
        if not isinstance(parsed, dict):
            raise forms.ValidationError("ساعات الدوام يجب أن تكون كائن JSON.")
        return parsed


class VendorApplicationReviewForm(forms.ModelForm):
    class Meta:
        model = VendorApplication
        fields = ["review_note"]
        widgets = {"review_note": forms.Textarea(attrs={"rows": 4, "placeholder": "ملاحظة المراجعة (اختيارية)"})}
