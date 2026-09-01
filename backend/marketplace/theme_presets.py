from copy import deepcopy


FASHION_PRESET = {
    "name": "شبيك Fashion — التصميم الجاهز 1",
    "description": "قالب الأزياء المرجعي: هيدر عائم فوق الصورة، بانر رئيسي، عروض، اكتشاف الإطلالات، أقسام دائرية، تبويبات وشبكة منتجات.",
    "tokens": {
        "primary": "#E60023",
        "secondary": "#111111",
        "background": "#FFFFFF",
        "surface": "#FFFFFF",
        "muted": "#F7F7F7",
        "text": "#171717",
        "text_muted": "#777777",
        "border": "#EEEEEE",
        "radius": 18,
    },
    "layout": {
        "family": "fashion",
        "header": "fashion-floating",
        "header_height": 64,
        "header_overlay": True,
        "hero": "large-carousel",
        "hero_height": 310,
        "hero_radius": 0,
        "page_padding": 0,
        "section_gap": 8,
        "category_size": 68,
        "category_gap": 12,
        "product_card": "rounded",
        "product_columns_mobile": 2,
        "product_columns_desktop": 4,
        "product_gap": 10,
        "product_image_height": 190,
        "show_bottom_nav": True,
        "bottom_nav_style": "pill",
        "bottom_nav_height": 68,
    },
    "sections": [
        {"key": "header", "type": "header", "title": "الهيدر", "sort_order": 1, "enabled": True, "config": {
            "variant": "fashion-floating", "overlay": True, "show_notifications": True, "show_calendar": True,
            "show_camera": True, "show_favorites": True, "show_mail": True, "show_category_chips": True,
            "category_chip_limit": 7, "search_placeholder": "ابحث عن منتج أو متجر", "favorite_badge": "3",
        }},
        {"key": "hero", "type": "hero", "title": "بنايل وتيشرتات صيفية رجالية", "sort_order": 2, "enabled": True, "config": {
            "height": 310, "overlay": True, "overlay_opacity": 0.30, "image_fit": "cover", "text_align": "right",
            "show_dots": True, "autoplay": True, "interval_ms": 4500, "slides": [],
        }},
        {"key": "promo_strip", "type": "promo_strip", "title": "العروض السريعة", "sort_order": 3, "enabled": True, "config": {
            "columns": 3, "background": "#FFF7F8", "items": [
                {"title": "للمستخدمين الجدد فقط", "value": "خصم 30%", "note": "أكثر من SR149"},
                {"title": "للمستخدمين الجدد فقط", "value": "خصم 25%", "note": "أكثر من SR79"},
                {"title": "قسائم حصرية", "value": "عروض جديدة", "note": "استخدم القسيمة"},
            ],
        }},
        {"key": "discovery", "type": "category_grid", "title": "إطلالات وتصنيفات لكل", "sort_order": 4, "enabled": True, "config": {
            "rows": 1, "columns": 5, "size": 72, "gap": 13, "horizontal": True, "label_lines": 1,
            "show_title": True, "title_note": "اختر إطلالتك لتصفح الأصناف", "category_ids": [],
        }},
        {"key": "categories", "type": "category_grid", "title": "الأقسام والتصنيفات", "sort_order": 5, "enabled": True, "config": {
            "rows": 3, "columns": 5, "size": 62, "gap": 12, "horizontal": False, "label_lines": 1,
            "show_title": True, "category_ids": [],
        }},
        {"key": "tabs", "type": "tabs", "title": "", "sort_order": 6, "enabled": True, "config": {
            "active_index": 3, "items": [
                {"id": "for-you", "title": "من أجلك", "url": "/collection"},
                {"id": "new", "title": "مقترحات جديدة", "url": "/collection?sort=new"},
                {"id": "discounts", "title": "خصومات", "url": "/collection?sort=discounts"},
                {"id": "best", "title": "الأكثر مبيعًا", "url": "/collection?sort=best"},
            ],
        }},
        {"key": "toolbar", "type": "catalog_toolbar", "title": "المعروضات والتخفيضات", "sort_order": 7, "enabled": True, "config": {
            "show_count": True, "show_sort": True, "show_filter": True,
        }},
        {"key": "products", "type": "product_grid", "title": "المعروضات والتخفيضات", "sort_order": 8, "enabled": True, "config": {
            "source": "discounts", "rows": 3, "columns_mobile": 2, "columns_desktop": 4, "limit": 12,
            "gap": 10, "card_style": "rounded", "show_see_all": False,
        }},
        {"key": "bottom_nav", "type": "bottom_nav", "title": "التنقل السفلي", "sort_order": 99, "enabled": True, "config": {
            "items": [
                {"label": "حسابي", "icon": "person-outline", "url": "/profile"},
                {"label": "المفضلة", "icon": "favorite-border", "url": "/favorites"},
                {"label": "السلة", "icon": "shopping-cart", "url": "/bag"},
                {"label": "المنتجات", "icon": "inventory-2", "url": "/collection"},
                {"label": "الرئيسية", "icon": "home", "url": "/"},
            ],
        }},
    ],
}


ELECTRONICS_PRESET = {
    "name": "شبيك Electronics — التصميم الجاهز 2",
    "description": "قالب الإلكترونيات المرجعي: رأس أزرق، بحث وأقسام، بانر عريض، شريط تنبيه، فئات دائرية، ماركات، منتجات وتنقل سفلي.",
    "tokens": {
        "primary": "#0D47A1",
        "secondary": "#123B72",
        "background": "#FFFFFF",
        "surface": "#FFFFFF",
        "muted": "#EEF5FF",
        "text": "#151A22",
        "text_muted": "#667085",
        "border": "#E4EAF2",
        "radius": 10,
    },
    "layout": {
        "family": "electronics",
        "header": "electronics-blue",
        "header_height": 112,
        "header_overlay": False,
        "hero": "wide-banner",
        "hero_height": 220,
        "hero_radius": 0,
        "page_padding": 0,
        "section_gap": 0,
        "category_size": 74,
        "category_gap": 14,
        "product_card": "square",
        "product_columns_mobile": 2,
        "product_columns_desktop": 5,
        "product_gap": 9,
        "product_image_height": 190,
        "show_bottom_nav": True,
        "bottom_nav_style": "classic",
        "bottom_nav_height": 68,
    },
    "sections": [
        {"key": "header", "type": "header", "title": "الهيدر الأزرق", "sort_order": 1, "enabled": True, "config": {
            "variant": "electronics-blue", "show_notifications": True, "show_search": True, "show_menu": True,
            "show_account": True, "show_category_nav": True, "category_nav_limit": 6,
            "search_placeholder": "ابحث عن منتج أو متجر",
        }},
        {"key": "hero", "type": "hero", "title": "البانر الرئيسي", "sort_order": 2, "enabled": True, "config": {
            "height": 220, "overlay": False, "image_fit": "cover", "show_dots": True,
            "autoplay": True, "interval_ms": 5000, "slides": [],
        }},
        {"key": "notice", "type": "notice", "title": "تنبيه", "sort_order": 3, "enabled": True, "config": {
            "text": "نغطي احتياجاتكم على المحافظ التالية (جوي - جيب - فلوسك) وذلك", "show_icon": False,
            "background": "#FFFDF4",
        }},
        {"key": "categories", "type": "category_grid", "title": "", "sort_order": 4, "enabled": True, "config": {
            "rows": 3, "columns": 4, "size": 74, "gap": 14, "label_lines": 2, "show_title": False,
            "category_ids": [],
        }},
        {"key": "brands", "type": "brand_grid", "title": "تسوق حسب الماركة", "sort_order": 5, "enabled": True, "config": {
            "rows": 1, "columns": 4, "size": 84, "limit": 8, "gap": 16,
        }},
        {"key": "products", "type": "product_grid", "title": "المنتجات الأكثر طلبًا", "sort_order": 6, "enabled": True, "config": {
            "source": "best_selling", "rows": 2, "columns_mobile": 2, "columns_desktop": 5, "limit": 10,
            "gap": 9, "card_style": "square", "show_see_all": True,
        }},
        {"key": "bottom_nav", "type": "bottom_nav", "title": "التنقل السفلي", "sort_order": 99, "enabled": True, "config": {
            "items": [
                {"label": "حسابي", "icon": "person-outline", "url": "/profile"},
                {"label": "المفضلة", "icon": "favorite-border", "url": "/favorites"},
                {"label": "السلة", "icon": "shopping-cart", "url": "/bag"},
                {"label": "المنتجات", "icon": "inventory-2", "url": "/collection"},
                {"label": "الرئيسية", "icon": "home", "url": "/"},
            ],
        }},
    ],
}


def presets():
    return {"fashion": deepcopy(FASHION_PRESET), "electronics": deepcopy(ELECTRONICS_PRESET)}
