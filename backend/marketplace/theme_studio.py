import copy
import json

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.db import transaction
from django.shortcuts import redirect, render

from .models import Category, DesignTheme, Product


BUILTIN_THEMES = {
    "original-1": {
        "name": "الرئيسية الأصلية 1",
        "tokens": {"primary": "#E60023", "secondary": "#111111", "background": "#FFFFFF", "surface": "#FFFFFF", "text": "#111111", "muted": "#6B7280", "radius": 12},
        "layout": {"family": "fashion", "page_padding": 0, "section_gap": 8, "hero_height": 300, "hero_radius": 0, "header_overlay": False, "category_size": 70, "category_gap": 12, "product_gap": 10, "product_columns_desktop": 4, "product_image_height": 190, "product_card": "rounded"},
        "sections": [
            {"key": "header", "type": "header", "title": "الرأس", "sort_order": 10, "enabled": True, "config": {"category_chip_limit": 7, "show_category_chips": True, "show_favorites": True, "show_camera": True}},
            {"key": "hero", "type": "hero", "title": "البانر الرئيسي", "sort_order": 20, "enabled": True, "config": {"height": 300, "radius": 0, "overlay": True, "overlay_opacity": 25, "image_fit": "cover", "show_dots": True, "slides": []}},
            {"key": "categories", "type": "category_grid", "title": "الفئات", "sort_order": 30, "enabled": True, "config": {"rows": 2, "columns": 5, "size": 70, "gap": 12, "category_ids": [], "show_title": True, "label_lines": 2, "label_size": 10}},
            {"key": "trending", "type": "product_grid", "title": "الأكثر رواجًا", "sort_order": 40, "enabled": True, "config": {"source": "trending", "rows": 2, "columns_mobile": 2, "columns_tablet": 3, "columns_desktop": 4, "limit": 8, "gap": 10, "card_style": "rounded", "image_height": 190, "show_images": True, "show_names": True, "show_prices": True, "show_discount": True, "show_rating": True}},
            {"key": "offers", "type": "product_grid", "title": "عروض مميزة", "sort_order": 50, "enabled": True, "config": {"source": "discounts", "rows": 1, "columns_mobile": 2, "columns_tablet": 3, "columns_desktop": 4, "limit": 8, "gap": 10, "card_style": "rounded", "image_height": 190, "show_images": True, "show_names": True, "show_prices": True, "show_discount": True}},
            {"key": "bottom", "type": "bottom_nav", "title": "التنقل السفلي", "sort_order": 100, "enabled": True, "config": {"style": "standard", "active_index": 4, "items": []}},
        ],
    },
    "original-2": {
        "name": "الرئيسية الأصلية 2",
        "tokens": {"primary": "#0D47A1", "secondary": "#1565C0", "background": "#F6F8FB", "surface": "#FFFFFF", "text": "#111827", "muted": "#64748B", "radius": 10},
        "layout": {"family": "electronics", "page_padding": 0, "section_gap": 6, "hero_height": 220, "hero_radius": 0, "header_overlay": False, "category_size": 68, "category_gap": 10, "product_gap": 9, "product_columns_desktop": 4, "product_image_height": 180, "product_card": "square"},
        "sections": [
            {"key": "header", "type": "header", "title": "الرأس", "sort_order": 10, "enabled": True, "config": {"category_chip_limit": 8, "show_category_nav": True, "search_placeholder": "ابحث عن منتج أو متجر"}},
            {"key": "hero", "type": "hero", "title": "البانر الرئيسي", "sort_order": 20, "enabled": True, "config": {"height": 220, "radius": 0, "overlay": False, "overlay_opacity": 0, "image_fit": "cover", "show_dots": True, "slides": []}},
            {"key": "notice", "type": "notice", "title": "تنبيه", "sort_order": 30, "enabled": True, "config": {"text": "توصيل سريع وعروض يومية", "background": "#FFF8E1"}},
            {"key": "categories", "type": "category_grid", "title": "تسوق حسب الفئة", "sort_order": 40, "enabled": True, "config": {"rows": 2, "columns": 4, "size": 68, "gap": 10, "category_ids": [], "show_title": True, "label_lines": 2, "label_size": 10}},
            {"key": "brands", "type": "brand_grid", "title": "تسوق حسب الماركة", "sort_order": 50, "enabled": True, "config": {"rows": 1, "columns": 5, "size": 72, "gap": 12, "limit": 5, "show_title": True}},
            {"key": "latest", "type": "product_grid", "title": "وصل حديثًا", "sort_order": 60, "enabled": True, "config": {"source": "latest", "rows": 2, "columns_mobile": 2, "columns_tablet": 3, "columns_desktop": 4, "limit": 8, "gap": 9, "card_style": "square", "image_height": 180, "show_images": True, "show_names": True, "show_prices": True, "show_discount": True, "show_rating": True}},
            {"key": "bottom", "type": "bottom_nav", "title": "التنقل السفلي", "sort_order": 100, "enabled": True, "config": {"style": "standard", "active_index": 4, "items": []}},
        ],
    },
}


def _is_admin(user):
    return user.is_staff or getattr(user, "role", None) == "admin"


def _merge(default, current):
    result = copy.deepcopy(default)
    if isinstance(current, dict):
        result.update(current)
    return result


def _ensure_builtins():
    names = {preset["name"] for preset in BUILTIN_THEMES.values()}
    for preset in BUILTIN_THEMES.values():
        theme = DesignTheme.objects.filter(is_global=True, name=preset["name"]).first()
        if not theme:
            theme = DesignTheme.objects.create(name=preset["name"], is_global=True, is_active=False, tokens=copy.deepcopy(preset["tokens"]), layout=copy.deepcopy(preset["layout"]), sections=copy.deepcopy(preset["sections"]))
        else:
            theme.tokens = _merge(preset["tokens"], theme.tokens)
            theme.layout = _merge(preset["layout"], theme.layout)
            if not isinstance(theme.sections, list) or not theme.sections:
                theme.sections = copy.deepcopy(preset["sections"])
            theme.save(update_fields=["tokens", "layout", "sections", "updated_at"])
    # Backfill legacy global themes into the two canonical names when safe.
    for theme in DesignTheme.objects.filter(is_global=True).exclude(name__in=names).order_by("id"):
        family = str((theme.layout or {}).get("family", "")).lower()
        target = "الرئيسية الأصلية 1" if family == "fashion" else "الرئيسية الأصلية 2" if family == "electronics" else None
        if target and not DesignTheme.objects.filter(is_global=True, name=target).exclude(pk=theme.pk).exists():
            theme.name = target
            theme.save(update_fields=["name", "updated_at"])
    # Never leave the public storefront without an active global theme.
    if not DesignTheme.objects.filter(is_global=True, is_active=True).exists():
        fallback = DesignTheme.objects.filter(is_global=True, name="الرئيسية الأصلية 1").first() or DesignTheme.objects.filter(is_global=True).order_by("id").first()
        if fallback:
            DesignTheme.objects.filter(is_global=True).exclude(pk=fallback.pk).update(is_active=False)
            fallback.is_active = True
            fallback.save(update_fields=["is_active", "updated_at"])


def _catalog_context():
    return {"categories": list(Category.objects.filter(is_active=True).order_by("sort_order", "name").values("id", "name", "slug")), "products": list(Product.objects.filter(is_published=True, vendor__status="active").select_related("vendor").order_by("name")[:500].values("id", "name", "brand", "vendor__store_name"))}


def _normalise_sections(value):
    output = []
    for i, item in enumerate(value if isinstance(value, list) else []):
        if not isinstance(item, dict):
            continue
        row = copy.deepcopy(item)
        row["key"] = str(row.get("key") or f"section-{i + 1}")
        row["type"] = str(row.get("type") or "product_grid")
        row["title"] = str(row.get("title") or "")
        try:
            row["sort_order"] = int(row.get("sort_order", row.get("sortOrder", i + 1)) or i + 1)
        except (TypeError, ValueError):
            row["sort_order"] = i + 1
        row["enabled"] = bool(row.get("enabled", row.get("is_visible", True)))
        row["config"] = row.get("config") if isinstance(row.get("config"), dict) else {}
        output.append(row)
    return sorted(output, key=lambda x: (x["sort_order"], x["key"]))


@staff_member_required
def theme_studio(request):
    if not _is_admin(request.user):
        messages.error(request, "لا تملك صلاحية إدارة التصميم.")
        return redirect("admin-dashboard")
    _ensure_builtins()
    themes = list(DesignTheme.objects.filter(is_global=True).order_by("-is_active", "id"))
    selected_id = request.GET.get("theme") or request.POST.get("theme_id")
    selected = next((x for x in themes if str(x.id) == str(selected_id)), None) or next((x for x in themes if x.name == "الرئيسية الأصلية 1"), themes[0] if themes else None)
    if request.method == "POST" and selected:
        action = request.POST.get("action", "save")
        try:
            with transaction.atomic():
                if action == "activate":
                    DesignTheme.objects.filter(is_global=True).exclude(pk=selected.pk).update(is_active=False)
                    selected.is_active = True
                    selected.save(update_fields=["is_active", "updated_at"])
                    messages.success(request, f"تم تفعيل {selected.name} وهي الآن الواجهة الرئيسية العامة.")
                elif action == "save":
                    selected.name = request.POST.get("name", selected.name).strip()[:120] or selected.name
                    selected.tokens = json.loads(request.POST.get("tokens_json", "{}"))
                    selected.layout = json.loads(request.POST.get("layout_json", "{}"))
                    selected.sections = _normalise_sections(json.loads(request.POST.get("sections_json", "[]")))
                    selected.save(update_fields=["name", "tokens", "layout", "sections", "updated_at"])
                    messages.success(request, "تم حفظ تصميم الواجهة بالكامل.")
                elif action == "reset":
                    preset = next((p for p in BUILTIN_THEMES.values() if p["name"] == selected.name), None)
                    if not preset:
                        raise ValueError("إعادة الأصل متاحة للقالبين الأصليين فقط.")
                    selected.tokens = copy.deepcopy(preset["tokens"])
                    selected.layout = copy.deepcopy(preset["layout"])
                    selected.sections = copy.deepcopy(preset["sections"])
                    selected.save(update_fields=["tokens", "layout", "sections", "updated_at"])
                    messages.success(request, "تمت إعادة القالب إلى حالته الأصلية.")
                elif action == "clone":
                    selected = DesignTheme.objects.create(owner=request.user, name=f"{selected.name} — نسخة", is_global=True, is_active=False, tokens=copy.deepcopy(selected.tokens or {}), layout=copy.deepcopy(selected.layout or {}), sections=copy.deepcopy(selected.sections or []))
                    messages.success(request, "تم إنشاء تصميم جديد مستقل.")
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            messages.error(request, f"تعذر حفظ التصميم: {exc}")
        return redirect(f"admin-theme-studio?theme={selected.id}" if selected else "admin-theme-studio")

    sections = _normalise_sections(selected.sections if selected else [])
    return render(request, "admin/marketplace/theme_studio.html", {"themes": themes, "selected": selected, "sections_json": json.dumps(sections, ensure_ascii=False, indent=2), "tokens_json": json.dumps(selected.tokens if selected else {}, ensure_ascii=False, indent=2), "layout_json": json.dumps(selected.layout if selected else {}, ensure_ascii=False, indent=2), "catalog_json": json.dumps(_catalog_context(), ensure_ascii=False), "published_sections": sum(1 for x in sections if x.get("enabled")), "active_theme": next((x for x in themes if x.is_active), None)})
