from django import forms

from .models import Message, Notification
from marketplace.models import Product


class NotificationForm(forms.ModelForm):
    class Meta:
        model = Notification
        fields = ("title", "body", "image", "product", "audience")
        widgets = {"body": forms.Textarea(attrs={"rows": 6}), "audience": forms.Textarea(attrs={"rows": 4, "dir": "ltr"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["product"].queryset = Product.objects.filter(is_published=True).order_by("name")


class MessageForm(forms.ModelForm):
    class Meta:
        model = Message
        fields = ("body", "attachment")
        widgets = {"body": forms.Textarea(attrs={"rows": 5})}
