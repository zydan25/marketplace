from copy import deepcopy


FASHION_PRESET = {
    "name": "شبيك Fashion — التصميم العام 1",
    "tokens": {
        "primary": "#E60023",
        "secondary": "#111111",
        "background": "#FFFFFF",
        "surface": "#FFFFFF",
        "muted": "#F7F7F7",
        "text": "#171717",
        "text_muted": "#777777",
        "radius": 18,
        "header_mode": "floating",
    },
    "layout": {
        "family": "fashion",
        "header": "search-floating-icons",
        "hero": "large-carousel",
        "category_bar": "chips",
        "category_shape": "circle",
        "section_style": "clean",
        "product_card": "rounded",
        "product_columns_mobile": 2,
        "product_columns_desktop": 4,
        "show_bottom_nav": True,
    },
    "sections": [
        {"type": "hero", "title": "عروض الموسم", "sort_order": 1},
        {"type": "category_bar", "title": "تسوّق حسب التصنيف", "sort_order": 2},
        {"type": "category", "title": "الأقسام والتصنيفات", "sort_order": 3},
        {"type": "promo", "title": "عروض حصرية", "sort_order": 4},
        {"type": "trend", "title": "الأكثر رواجًا", "sort_order": 5},
        {"type": "product_grid", "title": "المعروضات والتخفيضات", "sort_order": 6},
    ],
}


ELECTRONICS_PRESET = {
    "name": "شبيك Electronics — التصميم العام 2",
    "tokens": {
        "primary": "#0D47A1",
        "secondary": "#123B72",
        "background": "#FFFFFF",
        "surface": "#FFFFFF",
        "muted": "#EEF5FF",
        "text": "#151A22",
        "text_muted": "#667085",
        "radius": 12,
        "header_mode": "solid",
    },
    "layout": {
        "family": "electronics",
        "header": "blue-navigation",
        "hero": "wide-banner",
        "category_bar": "grid",
        "category_shape": "circle",
        "section_style": "boxed",
        "product_card": "square",
        "product_columns_mobile": 2,
        "product_columns_desktop": 5,
        "show_bottom_nav": True,
    },
    "sections": [
        {"type": "hero", "title": "أحدث الأجهزة والعروض", "sort_order": 1},
        {"type": "category_bar", "title": "كل الأقسام", "sort_order": 2},
        {"type": "category", "title": "تسوق حسب القسم", "sort_order": 3},
        {"type": "promo", "title": "عروض وخصومات", "sort_order": 4},
        {"type": "product_grid", "title": "الأجهزة الأكثر طلبًا", "sort_order": 5},
        {"type": "trend", "title": "الأكثر مبيعًا", "sort_order": 6},
    ],
}


def presets():
    return {"fashion": deepcopy(FASHION_PRESET), "electronics": deepcopy(ELECTRONICS_PRESET)}
