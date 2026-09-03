from django import forms

from .models import DesignTheme, StorefrontMedia, StorefrontSection


class DesignThemeForm(forms.ModelForm):
    class Meta:
        model = DesignTheme
        fields = ("name", "is_global", "is_active", "tokens", "layout", "sections")
        widgets = {
            "tokens": forms.Textarea(attrs={"rows": 8, "dir": "ltr"}),
            "layout": forms.Textarea(attrs={"rows": 8, "dir": "ltr"}),
            "sections": forms.Textarea(attrs={"rows": 8, "dir": "ltr"}),
        }

    def clean(self):
        cleaned = super().clean()
        if cleaned.get("is_global") and self.instance.vendor_id:
            raise forms.ValidationError("الثيم العام لا يمكن ربطه بمتجر محدد.")
        return cleaned


class StorefrontSectionForm(forms.ModelForm):
    class Meta:
        model = StorefrontSection
        fields = ("title", "section_type", "config", "sort_order", "is_visible")
        widgets = {"config": forms.Textarea(attrs={"rows": 8, "dir": "ltr"})}


class StorefrontMediaForm(forms.ModelForm):
    class Meta:
        model = StorefrontMedia
        fields = ("name", "image", "alt_text", "target_url", "is_active", "sort_order")
