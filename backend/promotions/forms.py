from django import forms

from .models import Coupon, GiftTransfer, Loan


class CouponForm(forms.ModelForm):
    class Meta:
        model = Coupon
        fields = (
            "code", "discount_percent", "discount_amount", "minimum_order",
            "usage_limit", "starts_at", "ends_at", "is_active", "assigned_to",
        )
        widgets = {
            "starts_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
            "ends_at": forms.DateTimeInput(attrs={"type": "datetime-local"}),
        }

    def clean(self):
        cleaned = super().clean()
        percent = cleaned.get("discount_percent") or 0
        amount = cleaned.get("discount_amount") or 0
        if percent and amount:
            raise forms.ValidationError("حدد نسبة الخصم أو مبلغ الخصم، وليس الاثنين معًا.")
        starts = cleaned.get("starts_at")
        ends = cleaned.get("ends_at")
        if starts and ends and ends <= starts:
            self.add_error("ends_at", "تاريخ الانتهاء يجب أن يكون بعد تاريخ البداية.")
        return cleaned


class LoanReviewForm(forms.ModelForm):
    class Meta:
        model = Loan
        fields = ("status", "reason")

    def clean_status(self):
        status = self.cleaned_data["status"]
        if status not in {Loan.Status.APPROVED, Loan.Status.REJECTED, Loan.Status.PAID}:
            raise forms.ValidationError("هذه الصفحة مخصصة لمراجعة طلبات التمويل.")
        return status


class GiftTransferForm(forms.ModelForm):
    class Meta:
        model = GiftTransfer
        fields = ("receiver", "amount", "points", "message")
