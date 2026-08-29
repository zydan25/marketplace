from django import forms
from django.contrib.auth import password_validation

from .models import User, UserPreference


class UserCreateForm(forms.ModelForm):
    password1 = forms.CharField(label="كلمة المرور", widget=forms.PasswordInput, required=True)
    password2 = forms.CharField(label="تأكيد كلمة المرور", widget=forms.PasswordInput, required=True)

    class Meta:
        model = User
        fields = (
            "username",
            "phone",
            "first_name",
            "middle_name",
            "third_name",
            "last_name",
            "email",
            "governorate",
            "role",
            "points_balance",
            "is_active",
            "is_staff",
            "is_phone_verified",
        )
        labels = {
            "username": "اسم المستخدم",
            "phone": "رقم الهاتف",
            "first_name": "الاسم الأول",
            "middle_name": "الاسم الأوسط",
            "third_name": "الاسم الثالث",
            "last_name": "اسم العائلة",
            "email": "البريد الإلكتروني",
            "governorate": "المحافظة",
            "role": "الدور",
            "points_balance": "رصيد النقاط",
            "is_active": "الحساب نشط",
            "is_staff": "صلاحية الإدارة",
            "is_phone_verified": "الهاتف موثق",
        }

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise forms.ValidationError("اسم المستخدم مطلوب.")
        qs = User.objects.filter(username__iexact=username)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("اسم المستخدم مستخدم مسبقًا.")
        return username

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            raise forms.ValidationError("رقم الهاتف مطلوب.")
        qs = User.objects.filter(phone=phone)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("رقم الهاتف مستخدم مسبقًا.")
        return phone

    def clean_points_balance(self):
        value = self.cleaned_data.get("points_balance")
        if value is not None and value < 0:
            raise forms.ValidationError("رصيد النقاط لا يمكن أن يكون سالبًا.")
        return value

    def clean(self):
        cleaned = super().clean()
        password1 = cleaned.get("password1")
        password2 = cleaned.get("password2")
        if password1 or password2:
            if password1 != password2:
                self.add_error("password2", "كلمتا المرور غير متطابقتين.")
            elif password1:
                try:
                    password_validation.validate_password(password1, user=self.instance)
                except forms.ValidationError as exc:
                    self.add_error("password1", exc)
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        password = self.cleaned_data.get("password1")
        if password:
            user.set_password(password)
        if commit:
            user.save()
        return user


class UserEditForm(forms.ModelForm):
    class Meta:
        model = User
        fields = (
            "username",
            "phone",
            "first_name",
            "middle_name",
            "third_name",
            "last_name",
            "email",
            "governorate",
            "role",
            "points_balance",
            "is_active",
            "is_staff",
            "is_phone_verified",
        )
        labels = {
            "username": "اسم المستخدم",
            "phone": "رقم الهاتف",
            "first_name": "الاسم الأول",
            "middle_name": "الاسم الأوسط",
            "third_name": "الاسم الثالث",
            "last_name": "اسم العائلة",
            "email": "البريد الإلكتروني",
            "governorate": "المحافظة",
            "role": "الدور",
            "points_balance": "رصيد النقاط",
            "is_active": "الحساب نشط",
            "is_staff": "صلاحية الإدارة",
            "is_phone_verified": "الهاتف موثق",
        }

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if not username:
            raise forms.ValidationError("اسم المستخدم مطلوب.")
        qs = User.objects.filter(username__iexact=username).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("اسم المستخدم مستخدم مسبقًا.")
        return username

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            raise forms.ValidationError("رقم الهاتف مطلوب.")
        qs = User.objects.filter(phone=phone).exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError("رقم الهاتف مستخدم مسبقًا.")
        return phone


class PreferenceForm(forms.ModelForm):
    class Meta:
        model = UserPreference
        fields = ("currency", "notifications_enabled")
        labels = {
            "currency": "العملة المفضلة",
            "notifications_enabled": "تفعيل الإشعارات",
        }
        widgets = {
            "currency": forms.Select(choices=(("YER", "ريال يمني (YER)"), ("SAR", "ريال سعودي (SAR)"), ("USD", "دولار أمريكي (USD)"))),
        }
