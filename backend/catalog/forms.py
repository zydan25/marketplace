import json

from django import forms
from django.core.exceptions import ValidationError
from django.utils.text import slugify

from marketplace.models import VendorProfile

from .models import Category, CatalogOption, PriceGroup, Product, ProductImage, ProductVariant


class CatalogFormMixin(forms.ModelForm):
    class Meta:
        widgets = {
            "description": forms.Textarea(attrs={"rows": 5}),
            "shipping_note": forms.Textarea(attrs={"rows": 2}),
            "return_policy": forms.Textarea(attrs={"rows": 2}),
            "details": forms.Textarea(attrs={"rows": 5, "dir": "ltr"}),
            "colors": forms.Textarea(attrs={"rows": 2, "dir": "ltr"}),
            "sizes": forms.Textarea(attrs={"rows": 2, "dir": "ltr"}),
            "hashtags": forms.Textarea(attrs={"rows": 2, "dir": "ltr"}),
        }


class CategoryForm(CatalogFormMixin):
    class Meta:
        model = Category
        fields = ["name", "slug", "parent", "image", "is_active", "sort_order"]
        widgets = {"name": forms.TextInput(), "slug": forms.TextInput(attrs={"dir": "ltr"}), "sort_order": forms.NumberInput(min=0)}

    def clean(self):
        cleaned = super().clean()
        parent = cleaned.get("parent")
        if self.instance.pk and parent and (parent.pk == self.instance.pk or self._is_descendant(parent)):
            raise ValidationError("لا يمكن وضع الفئة داخل نفسها أو أحد أبنائها.")
        return cleaned

    def _is_descendant(self, candidate):
        current = candidate
        while current is not None:
            if current.pk == self.instance.pk:
                return True
            current = current.parent
        return False


class ProductForm(CatalogFormMixin):
    vendor = forms.ModelChoiceField(queryset=VendorProfile.objects.select_related("owner").order_by("store_name"), label="المتجر")
    categories = forms.ModelMultipleChoiceField(queryset=Category.objects.filter(is_active=True).order_by("sort_order", "name"), required=False, label="الفئات", widget=forms.SelectMultiple(attrs={"size": 7}))

    class Meta:
        model = Product
        fields = [
            "vendor", "categories", "sku", "name", "slug", "description", "brand", "material",
            "shipping_note", "return_policy", "price", "sale_price", "currency", "stock",
            "colors", "sizes", "hashtags", "details", "main_image", "is_published", "is_trending",
        ]
        widgets = {
            "sku": forms.TextInput(attrs={"dir": "ltr", "placeholder": "يُنشأ تلقائيًا عند تركه فارغًا"}),
            "name": forms.TextInput(),
            "slug": forms.TextInput(attrs={"dir": "ltr", "placeholder": "يُنشأ تلقائيًا"}),
            "price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "sale_price": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "stock": forms.NumberInput(attrs={"min": "0"}),
            "currency": forms.Select(choices=[("YER", "ريال يمني"), ("SAR", "ريال سعودي"), ("USD", "دولار")]),
            "colors": forms.Textarea(attrs={"rows": 2, "dir": "ltr", "placeholder": '["أسود", "أبيض"]'}),
            "sizes": forms.Textarea(attrs={"rows": 2, "dir": "ltr", "placeholder": '["S", "M", "L"]'}),
            "hashtags": forms.Textarea(attrs={"rows": 2, "dir": "ltr", "placeholder": '["جديد", "مميز"]'}),
            "details": forms.Textarea(attrs={"rows": 5, "dir": "ltr", "placeholder": '{"material": "..."}'}),
            "description": forms.Textarea(attrs={"rows": 5}),
            "shipping_note": forms.Textarea(attrs={"rows": 2}),
            "return_policy": forms.Textarea(attrs={"rows": 2}),
        }

    def _clean_json(self, name, allow_list=False):
        value = self.cleaned_data.get(name)
        if value in (None, ""):
            return [] if allow_list else {}
        if isinstance(value, (list, dict)):
            return value
        try:
            parsed = json.loads(value)
        except (TypeError, ValueError):
            raise ValidationError({name: "أدخل JSON صالحًا أو اترك الحقل فارغًا."})
        if allow_list and not isinstance(parsed, list):
            raise ValidationError({name: "هذا الحقل يجب أن يكون قائمة JSON."})
        if not allow_list and not isinstance(parsed, dict):
            raise ValidationError({name: "هذا الحقل يجب أن يكون كائن JSON."})
        return parsed

    def clean_colors(self):
        return self._clean_json("colors", allow_list=True)

    def clean_sizes(self):
        return self._clean_json("sizes", allow_list=True)

    def clean_hashtags(self):
        return self._clean_json("hashtags", allow_list=True)

    def clean_details(self):
        return self._clean_json("details", allow_list=False)

    def clean(self):
        cleaned = super().clean()
        sale = cleaned.get("sale_price")
        price = cleaned.get("price")
        if sale is not None and price is not None and sale > price:
            self.add_error("sale_price", "سعر التخفيض لا يمكن أن يكون أكبر من السعر الأصلي.")
        return cleaned


class ProductImageForm(forms.ModelForm):
    class Meta:
        model = ProductImage
        fields = ["image", "alt_text", "sort_order", "is_primary"]
        widgets = {"sort_order": forms.NumberInput(min=0)}


class ProductVariantForm(forms.ModelForm):
    class Meta:
        model = ProductVariant
        fields = ["sku", "color", "size", "price_override", "stock", "is_active"]
        widgets = {
            "sku": forms.TextInput(attrs={"dir": "ltr", "placeholder": "يُنشأ تلقائيًا"}),
            "price_override": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
            "stock": forms.NumberInput(attrs={"min": "0"}),
        }

    def clean_stock(self):
        stock = self.cleaned_data["stock"]
        if self.instance.pk and stock < self.instance.reserved_stock:
            raise ValidationError("لا يمكن خفض المخزون عن الكمية المحجوزة.")
        return stock


class CatalogOptionForm(forms.ModelForm):
    class Meta:
        model = CatalogOption
        fields = ["group", "name", "slug", "category", "sort_order", "is_active"]
        widgets = {
            "group": forms.TextInput(attrs={"placeholder": "color / size / material", "dir": "ltr"}),
            "slug": forms.TextInput(attrs={"dir": "ltr", "placeholder": "يُنشأ تلقائيًا"}),
            "sort_order": forms.NumberInput(min=0),
        }

    def clean_slug(self):
        return self.cleaned_data.get("slug") or slugify(self.cleaned_data.get("name", ""), allow_unicode=True)

    def clean(self):
        cleaned = super().clean()
        group = str(cleaned.get("group", "")).strip().lower()
        name = str(cleaned.get("name", "")).strip()
        if not group or not name:
            raise ValidationError("نوع الخيار واسم الخيار مطلوبان.")
        cleaned["group"] = group
        return cleaned


class PriceGroupForm(forms.ModelForm):
    class Meta:
        model = PriceGroup
        fields = ["name", "code", "adjustment_type", "percentage", "fixed_amount", "is_active"]
        widgets = {
            "code": forms.TextInput(attrs={"dir": "ltr"}),
            "percentage": forms.NumberInput(attrs={"step": "0.01", "min": "0", "max": "100"}),
            "fixed_amount": forms.NumberInput(attrs={"step": "0.01", "min": "0"}),
        }

    def clean(self):
        cleaned = super().clean()
        adjustment_type = cleaned.get("adjustment_type")
        if adjustment_type == "percentage" and (cleaned.get("percentage") is None or cleaned.get("percentage") < 0):
            raise ValidationError("النسبة المئوية مطلوبة عند اختيار نوع النسبة.")
        if adjustment_type == "fixed" and (cleaned.get("fixed_amount") is None or cleaned.get("fixed_amount") < 0):
            raise ValidationError("المبلغ الثابت مطلوب عند اختيار النوع الثابت.")
        return cleaned