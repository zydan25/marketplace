MAIN = {
    "payments": ("التسديدات", "payments", "receipt"),
    "games": ("الألعاب", "games", "gamepad"),
    "digital": ("البرامج والبطاقات", "software", "apps"),
}

CATEGORIES = [
    ("payments", "يمن موبايل", "yemen-mobile"),
    ("payments", "سبأفون", "sabafon"),
    ("payments", "يو", "you"),
    ("payments", "واي", "why"),
    ("payments", "يمن فورجي", "yemen-4g"),
    ("payments", "يمن نت", "yemen-net"),
    ("payments", "عدن نت", "adenet"),
    ("payments", "الكهرباء", "electricity"),
    ("payments", "الماء", "water"),
    ("payments", "الخدمات الجماعية", "wholesale"),
    ("games", "الألعاب", "games"),
    ("digital", "البطاقات الرقمية", "digital-cards"),
]

# code, name, category, kind, pricing, link_key, requires_balance
SERVICES = [
    ("yem-balance", "Yemen Mobile - رصيد", "yemen-mobile", "purchase", "amount", "yem_bill_balance", True),
    ("yem-denomination", "Yemen Mobile - فئات", "yemen-mobile", "purchase", "item", "yem_denomination", True),
    ("yem-offer", "Yemen Mobile - الباقات", "yemen-mobile", "catalog", "item", "yem_offer_catalog", False),
    ("yem-bill-offer", "Yemen Mobile - تفعيل باقة", "yemen-mobile", "purchase", "item", "yem_bill_offer", True),
    ("yem-offer-bill", "Yemen Mobile - تسديد وتفعيل", "yemen-mobile", "purchase", "item", "yem_offer_bill", True),
    ("yem-query-balance", "Yemen Mobile - استعلام الرصيد", "yemen-mobile", "query", "fixed", "yem_query", False),
    ("yem-query-offers", "Yemen Mobile - استعلام الباقات", "yemen-mobile", "query", "fixed", "yem_offer_query", False),

    ("saba-denomination", "سبأفون - فئات", "sabafon", "purchase", "item", "saba_denomination", True),
    ("saba-offer", "سبأفون - باقات", "sabafon", "purchase", "item", "saba_offer", True),
    ("sbay-offer", "سبأفون الجنوب - باقات", "sabafon", "purchase", "item", "sbay_offer", True),
    ("sbay-denomination", "سبأفون الجنوب - شحن", "sabafon", "purchase", "item", "sbay_denominations", True),
    ("saba-units", "سبأفون - وحدات", "sabafon", "purchase", "amount", "saba_units", True),

    ("you-balance", "يو - رصيد مفتوح", "you", "purchase", "amount", "you_balance", True),
    ("you-denomination", "يو - فئات شحن", "you", "purchase", "item", "you_denominations", True),
    ("you-offer", "يو - باقات", "you", "purchase", "item", "you_offer", True),

    ("why-bill", "واي - تسديد", "why", "purchase", "item", "why_bill", True),
    ("why-balance", "واي - رصيد", "why", "purchase", "amount", "why_balance", True),
    ("why-package", "واي - باقات", "why", "purchase", "item", "why_package", True),

    ("yem4g-package", "يمن فورجي - باقة", "yemen-4g", "purchase", "amount", "yem4g_package", True),
    ("yem4g-balance", "يمن فورجي - رصيد", "yemen-4g", "purchase", "amount", "yem4g_balance", True),
    ("yem4g-change", "يمن فورجي - تغيير باقة", "yemen-4g", "purchase", "amount", "yem4g_change", True),
    ("yem4g-query", "يمن فورجي - استعلام", "yemen-4g", "query", "fixed", "yem4g_query", False),

    ("post-adsl", "يمن نت - ADSL", "yemen-net", "purchase", "amount", "post_bill_adsl", True),
    ("post-line", "يمن نت - خط", "yemen-net", "purchase", "amount", "post_bill_line", True),
    ("post-query", "يمن نت - استعلام", "yemen-net", "query", "fixed", "post_query", False),

    ("adenet-bill", "عدن نت - تسديد", "adenet", "purchase", "item", "adenet_bill", True),
    ("adenet-query", "عدن نت - استعلام", "adenet", "query", "fixed", "adenet_query", False),

    ("electric-query", "الكهرباء - استعلام", "electricity", "query", "fixed", "electric_query", False),
    ("electric-bill", "الكهرباء - تسديد", "electricity", "purchase", "amount", "electric_bill", True),
    ("water-query", "الماء - استعلام", "water", "query", "fixed", "water_query", False),
    ("water-bill", "الماء - تسديد", "water", "purchase", "amount", "water_bill", True),

    ("saba-gomla", "سبأفون جملة", "wholesale", "purchase", "amount", "saba_gomla", True),
    ("mtn-gomla", "MTN جملة", "wholesale", "purchase", "amount", "mtn_gomla", True),
    ("mobile-gomla", "يمن موبايل جملة", "wholesale", "purchase", "amount", "mobile_gomla", True),

    ("pubg", "بوبجي PUBG Mobile", "games", "purchase", "item", "games_cards", True),
    ("freefire", "فري فاير Free Fire", "games", "purchase", "item", "games_cards", True),
    ("legends", "Mobile Legends", "games", "purchase", "item", "games_cards", True),
    ("loardstelmble", "لوردز موبايل", "games", "purchase", "item", "games_cards", True),
    ("clashroial", "كلاش رويال", "games", "purchase", "item", "games_cards", True),
    ("genshmbacket", "جنش امباكت", "games", "purchase", "item", "games_cards", True),
    ("clashofclanz", "كالش أوف كالنز", "games", "purchase", "item", "games_cards", True),
    ("newstatepobg", "PUBG: NEW STATE", "games", "purchase", "item", "games_cards", True),
    ("praolstars", "براول ستار", "games", "purchase", "item", "games_cards", True),
    ("hidadijwaher", "هاي داي جواهر", "games", "purchase", "item", "games_cards", True),
    ("ddihadi", "هاي دي عمله ذهبيه", "games", "purchase", "item", "games_cards", True),
    ("calloffdyoty", "كول أوف ديوتي", "games", "purchase", "item", "games_cards", True),
    ("pompitch", "بوم بيتش", "games", "purchase", "item", "games_cards", True),

    ("googleplayusa", "Google Play أمريكي", "digital-cards", "purchase", "item", "games_cards", True),
    ("googleplaykorea", "Google Play كوري", "digital-cards", "purchase", "item", "games_cards", True),
    ("appstore", "Apple Store Gift", "digital-cards", "purchase", "item", "games_cards", True),
    ("beinconnect", "beIN Connect", "digital-cards", "purchase", "item", "games_cards", True),
    ("razergold", "Razer Gold Gift", "digital-cards", "purchase", "item", "games_cards", True),
    ("crossfire", "CrossFire Gift", "digital-cards", "purchase", "item", "games_cards", True),
    ("plastationusa", "PlayStation أمريكي", "digital-cards", "purchase", "item", "games_cards", True),
    ("plastationsar", "PlayStation سعودي", "digital-cards", "purchase", "item", "games_cards", True),
    ("visacard", "Visa Card", "digital-cards", "purchase", "item", "games_cards", True),
    ("mastercard", "MasterCard", "digital-cards", "purchase", "item", "games_cards", True),
    ("likee", "Likee", "digital-cards", "purchase", "item", "games_cards", True),
    ("bigolive", "BIGO LIVE", "digital-cards", "purchase", "item", "games_cards", True),
]
