from django import forms

from .models import Order, Shipment


class OrderStatusForm(forms.Form):
    status = forms.ChoiceField(choices=Order.Status.choices, label="حالة الطلب")
    note = forms.CharField(required=False, widget=forms.Textarea(attrs={"rows": 4}), label="ملاحظة")


class ShipmentForm(forms.ModelForm):
    class Meta:
        model = Shipment
        fields = ("carrier", "tracking_number", "status")

    def clean(self):
        cleaned = super().clean()
        status = cleaned.get("status")
        if status in {Shipment.Status.SHIPPED, Shipment.Status.IN_TRANSIT} and not cleaned.get("carrier"):
            self.add_error("carrier", "اسم شركة الشحن مطلوب عند بدء الشحن.")
        return cleaned
