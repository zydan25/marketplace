from django.contrib import admin, messages
from django.utils import timezone

from .models import VendorApplication, VendorProfile
from .services import approve_application, reject_application, set_vendor_status


@admin.register(VendorProfile)
class VendorProfileAdmin(admin.ModelAdmin):
    list_display = ("store_name", "owner", "status", "commission_percent", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("store_name", "slug", "owner__phone", "owner__email")
    readonly_fields = ("created_at", "updated_at")
    actions = ("activate_selected", "suspend_selected")

    @admin.action(description="تفعيل المتاجر المحددة")
    def activate_selected(self, request, queryset):
        queryset.update(status="active", updated_at=timezone.now())

    @admin.action(description="تعليق المتاجر المحددة")
    def suspend_selected(self, request, queryset):
        queryset.update(status="suspended", updated_at=timezone.now())


@admin.register(VendorApplication)
class VendorApplicationAdmin(admin.ModelAdmin):
    list_display = ("store_name", "applicant", "phone", "status", "created_at", "reviewed_by", "reviewed_at")
    list_filter = ("status", "created_at")
    search_fields = ("store_name", "phone", "applicant__phone", "applicant__email")
    readonly_fields = ("applicant", "created_at", "updated_at", "reviewed_by", "reviewed_at")
    actions = ("approve_selected", "reject_selected")

    @admin.action(description="اعتماد طلبات التجار المحددة")
    def approve_selected(self, request, queryset):
        for application in queryset.filter(status=VendorApplication.Status.PENDING):
            try:
                approve_application(application, request.user)
            except Exception as exc:
                self.message_user(request, f"تعذر اعتماد {application.store_name}: {exc}", level=messages.ERROR)
        self.message_user(request, "تمت معالجة الطلبات القابلة للاعتماد.", level=messages.SUCCESS)

    @admin.action(description="رفض طلبات التجار المحددة")
    def reject_selected(self, request, queryset):
        count = 0
        for application in queryset.filter(status=VendorApplication.Status.PENDING):
            reject_application(application, request.user, "رُفض من الإدارة عبر Django Admin")
            count += 1
        self.message_user(request, f"تم رفض {count} طلب.", level=messages.SUCCESS)
