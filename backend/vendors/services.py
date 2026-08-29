from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from marketplace.models import User as MarketplaceUser

from .models import VendorApplication, VendorProfile


@transaction.atomic
def approve_application(application, reviewer):
    if application.status != VendorApplication.Status.PENDING:
        raise ValidationError("الطلب ليس بانتظار المراجعة")

    user = MarketplaceUser.objects.select_for_update().get(pk=application.applicant_id)
    vendor = VendorProfile.objects.filter(owner=user).first()
    if vendor is None:
        user.role = MarketplaceUser.Roles.VENDOR
        user.save(update_fields=["role"])
        vendor = VendorProfile.objects.create(
            owner=user,
            store_name=application.store_name,
            description=application.description,
            phone=application.phone,
            address=application.address,
            status="active",
        )
    else:
        if vendor.status == "suspended":
            vendor.status = "active"
            vendor.save(update_fields=["status", "updated_at"])

    application.status = VendorApplication.Status.APPROVED
    application.reviewed_by = reviewer
    application.reviewed_at = timezone.now()
    application.save(update_fields=["status", "reviewed_by", "reviewed_at", "updated_at"])
    return vendor, application


@transaction.atomic
def reject_application(application, reviewer, review_note=""):
    if application.status != VendorApplication.Status.PENDING:
        raise ValidationError("الطلب ليس بانتظار المراجعة")
    application.status = VendorApplication.Status.REJECTED
    application.reviewed_by = reviewer
    application.reviewed_at = timezone.now()
    application.review_note = (review_note or "").strip()
    application.save(update_fields=["status", "reviewed_by", "reviewed_at", "review_note", "updated_at"])
    return application


@transaction.atomic
def set_vendor_status(vendor, status):
    valid = {"active", "suspended", "pending"}
    if status not in valid:
        raise ValidationError("حالة التاجر غير صالحة")
    vendor.status = status
    vendor.save(update_fields=["status", "updated_at"])
    return vendor
