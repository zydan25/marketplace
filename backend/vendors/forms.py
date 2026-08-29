import json

from django import forms

from marketplace.models import User

from .models import VendorApplication, VendorProfile


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
            "settings": forms.Textarea(attrs={"rows": 5, "dir": "ltr", "placeholder": "{}"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields["owner"].queryset = User.objects.filter(pk=self.instance.owner_id)
            self.fields["owner"].disabled = True
        else:
            self.fields["owner"].queryset = User.objects.filter(is_staff=False, role="customer").order_by("phone", "email")

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


class VendorApplicationReviewForm(forms.ModelForm):
    class Meta:
        model = VendorApplication
        fields = ["review_note"]
        widgets = {"review_note": forms.Textarea(attrs={"rows": 4, "placeholder": "ملاحظة المراجعة (اختيارية)"})}
