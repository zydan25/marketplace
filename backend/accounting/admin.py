from django.contrib import admin
from django.core.exceptions import PermissionDenied

from .models import Account, JournalEntry, JournalLine, Voucher, Wallet, WithdrawalRequest


@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "account_type", "normal_side", "parent", "is_group", "is_active", "party_user")
    list_filter = ("account_type", "is_group", "is_active", "normal_side")
    search_fields = ("code", "name", "party_user__phone", "party_user__first_name", "party_user__last_name")
    list_select_related = ("parent", "party_user")
    readonly_fields = ("code",)

    def has_delete_permission(self, request, obj=None):
        if obj and (obj.children.exists() or obj.journal_lines.exists() or Wallet.objects.filter(account=obj).exists()):
            return False
        return super().has_delete_permission(request, obj)


class JournalLineInline(admin.TabularInline):
    model = JournalLine
    extra = 0
    can_delete = False
    readonly_fields = ("account", "description", "debit", "credit")


@admin.register(JournalEntry)
class JournalEntryAdmin(admin.ModelAdmin):
    list_display = ("number", "entry_date", "description", "status", "source_type", "source_id", "created_by")
    list_filter = ("status", "entry_date", "source_type")
    search_fields = ("number", "description", "source_id")
    readonly_fields = tuple(field.name for field in JournalEntry._meta.fields)
    inlines = [JournalLineInline]

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def save_model(self, request, obj, form, change):
        raise PermissionDenied("القيود المرحّلة لا تعدل من لوحة الإدارة؛ أنشئ قيد تصحيح جديدًا.")


@admin.register(JournalLine)
class JournalLineAdmin(admin.ModelAdmin):
    list_display = ("entry", "account", "debit", "credit", "description")
    list_filter = ("account__account_type",)
    search_fields = ("entry__number", "account__code", "account__name")
    readonly_fields = tuple(field.name for field in JournalLine._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Wallet)
class WalletAdmin(admin.ModelAdmin):
    list_display = ("owner", "kind", "currency", "account", "is_active", "created_at")
    list_filter = ("kind", "currency", "is_active")
    search_fields = ("owner__phone", "owner__first_name", "owner__last_name")
    readonly_fields = tuple(field.name for field in Wallet._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Voucher)
class VoucherAdmin(admin.ModelAdmin):
    list_display = ("number", "voucher_type", "voucher_date", "amount", "currency", "cash_account", "party_account", "journal_entry")
    list_filter = ("voucher_type", "currency", "voucher_date")
    search_fields = ("number", "description", "source_id")
    readonly_fields = tuple(field.name for field in Voucher._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(WithdrawalRequest)
class WithdrawalRequestAdmin(admin.ModelAdmin):
    list_display = ("number", "requester", "amount", "currency", "status", "created_at", "updated_at")
    list_filter = ("status", "currency")
    search_fields = ("number", "requester__phone", "requester__first_name", "requester__last_name")
    readonly_fields = tuple(field.name for field in WithdrawalRequest._meta.fields)

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
