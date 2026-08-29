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
        self.fields["owner"].queryset = User.objects.filter(is_staff=False).order_by("phone", "email")
        if self.instance.pk:
            self.fields["owner"].disabled = True

    def clean_commission_percent(self):
        value = self.cleaned_data["commission_percent"]
        if value < 0 or value > 100:
            raise forms.ValidationError("العمولة يجب أن تكون بين 0 و100٪.")
        return value


class VendorApplicationReviewForm(forms.ModelForm):
    class Meta:
        model = VendorApplication
        fields = ["review_note"]
        widgets = {"review_note": forms.Textarea(attrs={"rows": 4, "placeholder": "ملاحظة المراجعة (اختيارية)"})}
