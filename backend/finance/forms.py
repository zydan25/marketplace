from decimal import Decimal

from django import forms

from .models import CurrencyRate, VendorCityShipping
from marketplace.models import VendorProfile


class CurrencyRateForm(forms.ModelForm):
    class Meta:
        model = CurrencyRate
        fields = ("base_currency", "target_currency", "rate", "is_active")

    def clean(self):
        cleaned = super().clean()
        base = (cleaned.get("base_currency") or "").upper()
        target = (cleaned.get("target_currency") or "").upper()
        rate = cleaned.get("rate")
        if base == target:
            self.add_error("target_currency", "لا يمكن أن تكون العملتان متطابقتين.")
        if rate is not None and rate <= Decimal("0"):
            self.add_error("rate", "سعر الصرف يجب أن يكون أكبر من صفر.")
        cleaned["base_currency"] = base
        cleaned["target_currency"] = target
        return cleaned


class VendorCityShippingForm(forms.ModelForm):
    class Meta:
        model = VendorCityShipping
        fields = ("vendor", "city", "fee", "is_active")

    def __init__(self, *args, vendor_required=True, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["vendor"].queryset = VendorProfile.objects.filter(status="active").order_by("store_name")
        if not vendor_required:
            self.fields["vendor"].required = False
            self.fields["vendor"].disabled = True

    def clean_fee(self):
        value = self.cleaned_data["fee"]
        if value < 0:
            raise forms.ValidationError("رسوم الشحن لا يمكن أن تكون سالبة.")
        return value


class WalletTopUpForm(forms.Form):
    amount = forms.DecimalField(min_value=Decimal("0.01"), max_digits=14, decimal_places=2, label="المبلغ")
    note = forms.CharField(required=False, max_length=255, label="ملاحظة")
