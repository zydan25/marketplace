from django.contrib import admin

from .models import DesignTheme, StorefrontMedia, StorefrontSection


@admin.register(DesignTheme)
class DesignThemeAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "is_global", "is_active", "updated_at")
    list_filter = ("is_global", "is_active")
    search_fields = ("name", "vendor__store_name")
    ordering = ("-is_global", "-updated_at")


@admin.register(StorefrontSection)
class StorefrontSectionAdmin(admin.ModelAdmin):
    list_display = ("title", "section_type", "vendor", "sort_order", "is_visible", "updated_at")
    list_filter = ("section_type", "is_visible")
    search_fields = ("title", "vendor__store_name")
    list_editable = ("sort_order", "is_visible")


@admin.register(StorefrontMedia)
class StorefrontMediaAdmin(admin.ModelAdmin):
    list_display = ("name", "vendor", "is_active", "sort_order", "updated_at")
    list_filter = ("is_active",)
    search_fields = ("name", "alt_text", "vendor__store_name")
    list_editable = ("sort_order", "is_active")
