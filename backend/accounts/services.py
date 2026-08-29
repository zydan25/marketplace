from django.contrib.auth import password_validation
from django.db import transaction
from rest_framework.authtoken.models import Token

from .models import User, UserPreference


@transaction.atomic
def set_account_action(user, action):
    """Apply safe account lifecycle actions; destructive deletion is intentionally unsupported."""
    if action == "activate":
        user.is_active = True
    elif action == "deactivate":
        user.is_active = False
    elif action == "verify-phone":
        user.is_phone_verified = True
    elif action == "unverify-phone":
        user.is_phone_verified = False
    elif action == "grant-staff":
        user.is_staff = True
    elif action == "revoke-staff":
        user.is_staff = False
    elif action == "revoke-api-token":
        Token.objects.filter(user=user).delete()
        return user
    else:
        raise ValueError("إجراء الحساب غير معروف.")
    update_fields = ["is_active", "is_phone_verified", "is_staff"]
    if hasattr(user, "updated_at"):
        update_fields.append("updated_at")
    user.save(update_fields=update_fields)
    return user


@transaction.atomic
def set_account_password(user, password):
    password_validation.validate_password(password, user=user)
    user.set_password(password)
    user.save(update_fields=["password"])


@transaction.atomic
def ensure_preference(user):
    preference, _ = UserPreference.objects.get_or_create(user=user)
    return preference
