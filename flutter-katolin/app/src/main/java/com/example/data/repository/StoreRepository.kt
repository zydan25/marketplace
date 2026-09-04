package com.example.data.repository

import com.example.data.model.*
import com.example.data.remote.*
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

class StoreRepository {

    private val coroutineScope = CoroutineScope(Dispatchers.IO)

    // Django server settings
    private val _djangoBaseUrl = MutableStateFlow("https://shopik.alattab.site/api/")
    val djangoBaseUrl: StateFlow<String> = _djangoBaseUrl.asStateFlow()

    fun updateDjangoBaseUrl(newUrl: String) {
        _djangoBaseUrl.value = newUrl.trim()
        fetchStoresAndProductsFromApi()
    }

    // User authentication session
    private val _userSession = MutableStateFlow(
        UserSession(
            phone = "",
            fullName = "زائر",
            token = null,
            isLoggedIn = false
        )
    )
    val userSession: StateFlow<UserSession> = _userSession.asStateFlow()

    suspend fun loginWithPhoneAndPassword(phone: String, pass: String): Pair<Boolean, String?> {
        return withContext(Dispatchers.IO) {
            try {
                val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                val response = api.login(LoginPayload(phone = phone.trim(), password = pass.trim()))
                if (response.isSuccessful && response.body() != null) {
                    val authBody = response.body()!!
                    val user = authBody.user
                    val fullName = listOfNotNull(user.firstName, user.lastName)
                        .filter { it.isNotBlank() }
                        .joinToString(" ")
                        .ifBlank { "مستخدم ${user.phone}" }
                    _userSession.value = UserSession(
                        phone = user.phone,
                        fullName = fullName,
                        token = authBody.token,
                        isLoggedIn = true,
                        governorate = user.governorate ?: "",
                        pointsBalance = user.pointsBalance ?: 0,
                        role = user.role ?: "customer"
                    )
                    // Fetch real wallet, orders, notifications and addresses with this token
                    syncWalletFromServer()
                    fetchOrdersFromApi(authBody.token)
                    fetchNotificationsFromApi(authBody.token)
                    fetchAddressesFromApi(authBody.token)
                    Pair(true, null)
                } else {
                    val err = response.errorBody()?.string() ?: ""
                    val msg = when {
                        err.contains("detail") -> {
                            val match = Regex("\"detail\"\\s*:\\s*\"([^\"]+)\"").find(err)
                            match?.groupValues?.get(1) ?: "بيانات الدخول غير صحيحة"
                        }
                        response.code() == 400 || response.code() == 401 -> "رقم الهاتف أو كلمة السر غير صحيحة"
                        else -> "خطأ في تسجيل الدخول (رمز ${response.code()})"
                    }
                    Pair(false, msg)
                }
            } catch (e: Exception) {
                Pair(false, "تعذر الاتصال بالسيرفر: ${e.localizedMessage}")
            }
        }
    }

    suspend fun registerUser(
        phone: String,
        pass: String,
        firstName: String,
        lastName: String,
        governorate: String
    ): Pair<Boolean, String?> {
        return withContext(Dispatchers.IO) {
            try {
                val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                val response = api.register(
                    RegisterPayload(
                        phone = phone.trim(),
                        password = pass.trim(),
                        firstName = firstName.trim().ifBlank { null },
                        lastName = lastName.trim().ifBlank { null },
                        governorate = governorate.trim().ifBlank { null }
                    )
                )
                if (response.isSuccessful && response.body() != null) {
                    val authBody = response.body()!!
                    val user = authBody.user
                    val fullName = listOfNotNull(user.firstName, user.lastName)
                        .filter { it.isNotBlank() }
                        .joinToString(" ")
                        .ifBlank { "مستخدم ${user.phone}" }
                    _userSession.value = UserSession(
                        phone = user.phone,
                        fullName = fullName,
                        token = authBody.token,
                        isLoggedIn = true,
                        governorate = user.governorate ?: governorate,
                        pointsBalance = user.pointsBalance ?: 0,
                        role = user.role ?: "customer"
                    )
                    syncWalletFromServer()
                    fetchOrdersFromApi(authBody.token)
                    fetchNotificationsFromApi(authBody.token)
                    fetchAddressesFromApi(authBody.token)
                    Pair(true, null)
                } else {
                    val err = response.errorBody()?.string() ?: ""
                    val msg = when {
                        err.contains("phone") -> "رقم الهاتف مسجل مسبقاً أو غير صالح"
                        err.contains("detail") -> {
                            val match = Regex("\"detail\"\\s*:\\s*\"([^\"]+)\"").find(err)
                            match?.groupValues?.get(1) ?: "فشل التسجيل على السيرفر"
                        }
                        else -> "فشل إنشاء الحساب (رمز ${response.code()})"
                    }
                    Pair(false, msg)
                }
            } catch (e: Exception) {
                Pair(false, "خطأ في الاتصال بالخادم: ${e.localizedMessage}")
            }
        }
    }

    suspend fun syncUserProfile(): Boolean {
        val token = _userSession.value.token ?: return false
        return withContext(Dispatchers.IO) {
            try {
                val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                val resp = api.getProfile("Token $token")
                if (resp.isSuccessful && resp.body() != null) {
                    val user = resp.body()!!
                    val fullName = listOfNotNull(user.firstName, user.lastName)
                        .filter { it.isNotBlank() }
                        .joinToString(" ")
                        .ifBlank { _userSession.value.fullName }
                    _userSession.value = _userSession.value.copy(
                        phone = user.phone,
                        fullName = fullName,
                        governorate = user.governorate ?: _userSession.value.governorate,
                        pointsBalance = user.pointsBalance ?: _userSession.value.pointsBalance,
                        role = user.role ?: _userSession.value.role
                    )
                    true
                } else {
                    false
                }
            } catch (_: Exception) {
                false
            }
        }
    }

    suspend fun testDjangoConnection(url: String): Boolean {
        return withContext(Dispatchers.IO) {
            try {
                val api = NetworkClient.getApiService(url)
                val resp = api.getVendors()
                resp.isSuccessful
            } catch (e: Exception) {
                false
            }
        }
    }

    fun logout() {
        _userSession.value = UserSession(
            phone = "",
            fullName = "زائر",
            token = null,
            isLoggedIn = false
        )
        _walletAccount.value = WalletAccount(
            accountNumber = "---",
            userName = "حساب زائر",
            phone = "",
            isVerified = false,
            balanceYer = 0.0,
            balanceSar = 0.0,
            balanceUsd = 0.0,
            points = 0,
            savingsPocket = 0.0
        )
        _orders.value = emptyList()
        _transactions.value = emptyList()
    }

    // Banners
    val banners = listOf(
        BannerItem(
            id = 1,
            title = "مهرجان إلكترونيات وأجهزة المستقبل",
            subtitle = "أحدث الهواتف والسماعات والساعات الذكية بضمان معتمد",
            discountTag = "خصم حتى 45%",
            ctaText = "تسوق العرض الآن",
            isElectronics = true
        ),
        BannerItem(
            id = 2,
            title = "سوبرماركت وأزياء الموسم وعطور",
            subtitle = "توصيل فوري خلال 30 دقيقة وكاش باك 10% إلى محفظتك",
            discountTag = "شحن مجاني",
            ctaText = "استكشف العروض",
            isElectronics = false
        )
    )

    // Categories with Subcategories Hierarchy (Mirrored from Server)
    private val _categories = MutableStateFlow(
        listOf(
            CategoryItem("all", "الكل", "grid", 0, listOf("الكل")),
            CategoryItem(
                id = "الإلكترونيات",
                title = "الإلكترونيات",
                iconName = "phone_iphone",
                productCount = 6,
                subCategories = listOf("الكل", "هواتف", "أجهزة لوحية", "كمبيوترات", "تلفزيونات وشاشات", "أجهزة كهربائية منزلية", "إكسسوارات إلكترونية"),
                serverId = 4
            ),
            CategoryItem(
                id = "الملابس",
                title = "الملابس",
                iconName = "checkroom",
                productCount = 7,
                subCategories = listOf("الكل", "رجالي", "نسائي", "ولادي", "بناتي", "أطفال", "أحذية", "حقائب"),
                serverId = 11
            ),
            CategoryItem(
                id = "المأكولات",
                title = "المأكولات",
                iconName = "shopping_basket",
                productCount = 4,
                subCategories = listOf("الكل", "أغذية", "مشروبات", "حلويات", "مخبوزات"),
                serverId = 19
            ),
            CategoryItem(
                id = "المنزل",
                title = "المنزل",
                iconName = "home",
                productCount = 4,
                subCategories = listOf("الكل", "أثاث", "مطبخ", "ديكور", "مستلزمات منزلية"),
                serverId = 24
            ),
            CategoryItem(
                id = "الجمال والعناية",
                title = "الجمال والعناية",
                iconName = "spa",
                productCount = 4,
                subCategories = listOf("الكل", "عناية بالبشرة", "عناية بالشعر", "عطور", "مكياج"),
                serverId = 29
            ),
            CategoryItem(
                id = "الألعاب",
                title = "الألعاب",
                iconName = "sports_esports",
                productCount = 3,
                subCategories = listOf("الكل", "ألعاب أطفال", "ألعاب إلكترونية", "ألعاب جماعية"),
                serverId = 34
            ),
            CategoryItem(
                id = "الرياضة",
                title = "الرياضة",
                iconName = "fitness_center",
                productCount = 3,
                subCategories = listOf("الكل", "ملابس رياضية", "معدات رياضية", "إكسسوارات رياضية"),
                serverId = 38
            ),
            CategoryItem(
                id = "السيارات",
                title = "السيارات",
                iconName = "directions_car",
                productCount = 3,
                subCategories = listOf("الكل", "قطع غيار", "إكسسوارات سيارات", "زيوت وعناية"),
                serverId = 42
            ),
            CategoryItem(
                id = "الكتب والتعليم",
                title = "الكتب والتعليم",
                iconName = "menu_book",
                productCount = 3,
                subCategories = listOf("الكل", "كتب", "قرطاسية", "مستلزمات مدرسية"),
                serverId = 46
            )
        )
    )
    val categoriesState: StateFlow<List<CategoryItem>> = _categories.asStateFlow()
    val categories: List<CategoryItem> get() = _categories.value

    // Stores (Multi-Store Vendors)
    private val _stores = MutableStateFlow(
        listOf(
            Store(
                id = 1,
                name = "متجر التقنية الذكية للإلكترونيات",
                category = "إلكترونيات",
                rating = 4.9,
                deliveryTime = "25 دقيقة",
                minOrder = "5,000 ر.ي",
                deliveryFee = "مجاني للطلبات فوق 20,000",
                description = "وكيل معتمد للهواتف والملحقات الأصلية والشواحن السريعة"
            ),
            Store(
                id = 2,
                name = "هايبر ماركت البركة المركزي",
                category = "سوبرماركت",
                rating = 4.8,
                deliveryTime = "30 دقيقة",
                minOrder = "3,000 ر.ي",
                deliveryFee = "500 ر.ي",
                description = "أكبر تشكيلة مواد غذائية وخضار وفواكه طازجة يومياً"
            ),
            Store(
                id = 3,
                name = "دار النخبة للأزياء والأناقة",
                category = "أزياء وموضة",
                rating = 4.7,
                deliveryTime = "40 دقيقة",
                minOrder = "10,000 ر.ي",
                deliveryFee = "1,000 ر.ي",
                description = "أحدث الموديلات الرجالية والنسائية وأطقم راقية بجودة عالية"
            ),
            Store(
                id = 4,
                name = "متجر الأندلس للعطور والبخور",
                category = "عطور وتجميل",
                rating = 4.9,
                deliveryTime = "35 دقيقة",
                minOrder = "8,000 ر.ي",
                deliveryFee = "700 ر.ي",
                description = "أفخم العطور الشرقية والفرنسية والعود الطبيعي الفاخر"
            ),
            Store(
                id = 5,
                name = "صيدلية ومستلزمات الحياة",
                category = "صحة وصيدليات",
                rating = 4.8,
                deliveryTime = "20 دقيقة",
                minOrder = "2,000 ر.ي",
                deliveryFee = "مجاني",
                description = "أدوية ومكملات غذائية ومستحضرات عناية معتمدة"
            )
        )
    )
    val stores: StateFlow<List<Store>> = _stores.asStateFlow()

    // Products fetched directly from Server (Default mock wiped out per user request)
    private val _products = MutableStateFlow<List<Product>>(emptyList())
    val products: StateFlow<List<Product>> = _products.asStateFlow()

    // Cart
    private val _cart = MutableStateFlow<List<CartItem>>(emptyList())
    val cart: StateFlow<List<CartItem>> = _cart.asStateFlow()

    fun addToCart(product: Product) {
        val current = _cart.value.toMutableList()
        val index = current.indexOfFirst { it.product.id == product.id }
        if (index >= 0) {
            current[index] = current[index].copy(quantity = current[index].quantity + 1)
        } else {
            current.add(CartItem(product, 1))
        }
        _cart.value = current
    }

    fun updateCartQuantity(productId: Int, delta: Int) {
        val current = _cart.value.toMutableList()
        val index = current.indexOfFirst { it.product.id == productId }
        if (index >= 0) {
            val newQty = current[index].quantity + delta
            if (newQty <= 0) {
                current.removeAt(index)
            } else {
                current[index] = current[index].copy(quantity = newQty)
            }
            _cart.value = current
        }
    }

    fun removeFromCart(productId: Int) {
        _cart.value = _cart.value.filter { it.product.id != productId }
    }

    fun clearCart() {
        _cart.value = emptyList()
    }

    // Favorites
    private val _favorites = MutableStateFlow<Set<Int>>(emptySet())
    val favorites: StateFlow<Set<Int>> = _favorites.asStateFlow()

    fun toggleFavorite(productId: Int) {
        val current = _favorites.value.toMutableSet()
        if (current.contains(productId)) {
            current.remove(productId)
        } else {
            current.add(productId)
        }
        _favorites.value = current
    }

    // Notifications (Synced from Server)
    private val _notifications = MutableStateFlow(
        listOf(
            AppNotification(
                id = "n_welcome",
                title = "مرحباً بك في تطبيق شبيك",
                message = "تطبيق شبيك يرحب بك! تصفح المنتجات والمتاجر، وسدد باقات الاتصالات وكروت شبكات الوايفاي بكل سهولة.",
                time = "الآن",
                isRead = false
            )
        )
    )
    val notifications: StateFlow<List<AppNotification>> = _notifications.asStateFlow()

    // Jeeb Wallet state
    private val _walletAccount = MutableStateFlow(
        WalletAccount(
            accountNumber = "---",
            userName = "حساب زائر",
            phone = "",
            isVerified = false,
            balanceYer = 0.0,
            balanceSar = 0.0,
            balanceUsd = 0.0,
            points = 0,
            savingsPocket = 0.0
        )
    )
    val walletAccount: StateFlow<WalletAccount> = _walletAccount.asStateFlow()

    // Jeeb Wallet Transactions
    private val _transactions = MutableStateFlow<List<WalletTransaction>>(emptyList())
    val transactions: StateFlow<List<WalletTransaction>> = _transactions.asStateFlow()

    // Orders (Fetched from server / created in session)
    private val _orders = MutableStateFlow<List<StoreOrder>>(emptyList())
    val orders: StateFlow<List<StoreOrder>> = _orders.asStateFlow()

    // Local WiFi Networks & Purchased Cards (كروت شبكات الوايفاي)
    private val _wifiNetworks = MutableStateFlow(
        listOf(
            WifiNetwork(
                id = "wifi_al_amal",
                name = "شبكة الأمل اللاسلكية",
                ownerName = "م. أحمد الشامي",
                ownerPhone = "777605123",
                location = "صنعاء - شارع حدة - حي الرويشان",
                governorate = "صنعاء",
                signalStrength = 5,
                isOnline = true,
                description = "إنترنت فايبر عالي السرعة وتغطية كاملة لشارع حدة والرويشان بدون تقطيع",
                denominations = listOf(
                    WifiCardDenomination("am_1", "كرت 1 ساعة (500 MB)", "1 ساعة", "500 MB", 100.0, "سرعة 15 ميجا"),
                    WifiCardDenomination("am_2", "كرت 3 ساعات (1.5 GB)", "3 ساعات", "1.5 GB", 200.0, "سرعة 20 ميجا", isPopular = true),
                    WifiCardDenomination("am_3", "كرت 8 ساعات (3 GB)", "8 ساعات", "3 GB", 350.0, "سرعة 20 ميجا"),
                    WifiCardDenomination("am_4", "كرت 24 ساعة يومي (6 GB)", "24 ساعة", "6 GB", 500.0, "سرعة 25 ميجا", isPopular = true),
                    WifiCardDenomination("am_5", "كرت 3 أيام (12 GB)", "3 أيام", "12 GB", 1000.0, "سرعة 25 ميجا"),
                    WifiCardDenomination("am_6", "كرت أسبوعي (25 GB)", "7 أيام", "25 GB", 1800.0, "سرعة 30 ميجا"),
                    WifiCardDenomination("am_7", "كرت شهري (60 GB)", "30 يوم", "60 GB", 3800.0, "سرعة 30 ميجا")
                )
            ),
            WifiNetwork(
                id = "wifi_al_noor",
                name = "شبكة النور نت Wi-Fi",
                ownerName = "أبو محمد الصنعاني",
                ownerPhone = "771771771",
                location = "صنعاء - مذبح - جوار جامعة الإيمان",
                governorate = "صنعاء",
                signalStrength = 5,
                isOnline = true,
                description = "شبكة ميكروتيك قوية، تصفح سريع، بنج منخفض للألعاب وسرعة تنزيل فائقة",
                denominations = listOf(
                    WifiCardDenomination("nr_1", "كرت ساعة واحدة (600 MB)", "1 ساعة", "600 MB", 100.0),
                    WifiCardDenomination("nr_2", "كرت 3 ساعات (2 GB)", "3 ساعات", "2 GB", 200.0, isPopular = true),
                    WifiCardDenomination("nr_3", "كرت يوم كامل 24 ساعة (7 GB)", "24 ساعة", "7 GB", 500.0, isPopular = true),
                    WifiCardDenomination("nr_4", "كرت أسبوعي مفتوح (30 GB)", "7 أيام", "30 GB", 2000.0),
                    WifiCardDenomination("nr_5", "كرت شهري منزلي (80 GB)", "30 يوم", "80 GB", 4500.0)
                )
            ),
            WifiNetwork(
                id = "wifi_al_baraka",
                name = "شبكة البركة نت الفضائية",
                ownerName = "عادل الحميري",
                ownerPhone = "770123456",
                location = "إب - شارع العدين - جولة العدين",
                governorate = "إب",
                signalStrength = 4,
                isOnline = true,
                description = "تغطية ممتازة لشارع العدين والجولات المجاورة، دعم فني متواصل 24 ساعة",
                denominations = listOf(
                    WifiCardDenomination("bk_1", "كرت 2 ساعة (1 GB)", "2 ساعة", "1 GB", 150.0),
                    WifiCardDenomination("bk_2", "كرت 6 ساعات (3 GB)", "6 ساعات", "3 GB", 300.0),
                    WifiCardDenomination("bk_3", "كرت يومي (6 GB)", "24 ساعة", "6 GB", 500.0, isPopular = true),
                    WifiCardDenomination("bk_4", "كرت أسبوعي (20 GB)", "7 أيام", "20 GB", 1500.0),
                    WifiCardDenomination("bk_5", "كرت شهري (50 GB)", "30 يوم", "50 GB", 3500.0)
                )
            ),
            WifiNetwork(
                id = "wifi_al_saqr",
                name = "شبكة الصقر اللاسلكية",
                ownerName = "مهندس مروان",
                ownerPhone = "733445566",
                location = "تعز - الحوبان - جولة الجمل",
                governorate = "تعز",
                signalStrength = 5,
                isOnline = true,
                description = "أسرع شبكة وايفاي في الحوبان بتقنية المايكروتك الحديثة وسيرفرات مخصصة",
                denominations = listOf(
                    WifiCardDenomination("sq_1", "كرت 1 ساعة (500 MB)", "1 ساعة", "500 MB", 100.0),
                    WifiCardDenomination("sq_2", "كرت 3 ساعات (1.5 GB)", "3 ساعات", "1.5 GB", 200.0, isPopular = true),
                    WifiCardDenomination("sq_3", "كرت 24 ساعة (5 GB)", "24 ساعة", "5 GB", 500.0, isPopular = true),
                    WifiCardDenomination("sq_4", "كرت 5 أيام (15 GB)", "5 أيام", "15 GB", 1200.0),
                    WifiCardDenomination("sq_5", "كرت شهري (60 GB)", "30 يوم", "60 GB", 4000.0)
                )
            ),
            WifiNetwork(
                id = "wifi_al_mustaqbal",
                name = "شبكة المستقبل نت",
                ownerName = "زيدان العطاب",
                ownerPhone = "777889900",
                location = "ذمار - حي السكنية - الشارع العام",
                governorate = "ذمار",
                signalStrength = 5,
                isOnline = true,
                description = "إنترنت سريع ومستقر، بطاقات إلكترونية فورية واستلام الكود في ثوانٍ",
                denominations = listOf(
                    WifiCardDenomination("ms_1", "كرت 1 ساعة (500 MB)", "1 ساعة", "500 MB", 100.0),
                    WifiCardDenomination("ms_2", "كرت 3 ساعات (2 GB)", "3 ساعات", "2 GB", 200.0, isPopular = true),
                    WifiCardDenomination("ms_3", "كرت 24 ساعة (6 GB)", "24 ساعة", "6 GB", 500.0, isPopular = true),
                    WifiCardDenomination("ms_4", "كرت أسبوعي (25 GB)", "7 أيام", "25 GB", 1700.0),
                    WifiCardDenomination("ms_5", "كرت شهري (70 GB)", "30 يوم", "70 GB", 3900.0)
                )
            ),
            WifiNetwork(
                id = "wifi_aden_sky",
                name = "شبكة عدن سكاي نت",
                ownerName = "كابتن فؤاد",
                ownerPhone = "711223344",
                location = "عدن - الشيخ عثمان - حي الهاشمي",
                governorate = "عدن",
                signalStrength = 4,
                isOnline = true,
                description = "تغطية واسعة في الشيخ عثمان والهاشمي، سرعة داونلود ممتازة وباقات اقتصادية",
                denominations = listOf(
                    WifiCardDenomination("ad_1", "كرت 2 ساعة (1 GB)", "2 ساعة", "1 GB", 150.0),
                    WifiCardDenomination("ad_2", "كرت 24 ساعة (5 GB)", "24 ساعة", "5 GB", 500.0, isPopular = true),
                    WifiCardDenomination("ad_3", "كرت أسبوعي (20 GB)", "7 أيام", "20 GB", 1600.0),
                    WifiCardDenomination("ad_4", "كرت شهري (60 GB)", "30 يوم", "60 GB", 3800.0)
                )
            )
        )
    )
    val wifiNetworks: StateFlow<List<WifiNetwork>> = _wifiNetworks.asStateFlow()

    private val _purchasedWifiCards = MutableStateFlow<List<PurchasedWifiCard>>(emptyList())
    val purchasedWifiCards: StateFlow<List<PurchasedWifiCard>> = _purchasedWifiCards.asStateFlow()

    // Telecom Packages for Payment Networks (Yemen Mobile, Sabafon, YOU, Y, Yemen Net)
    val telecomPackages = listOf(
        // Yemen Mobile Packages
        TelecomPackage("ym_1", "باقة مزايا الشهرية (رصيد + نت + رسائل)", "300 دقيقة + 300 رسالة + 1.5 جيجابايت صالحة 30 يوم", 1500.0, "باقات", "yemen_mobile"),
        TelecomPackage("ym_2", "باقة سوبر نت 4G فورجي 12GB", "12 جيجابايت بسرعة الجيل الرابع 4G LTE صالحة لشهر", 3500.0, "باقات", "yemen_mobile"),
        TelecomPackage("ym_3", "باقة هدايا نت 25GB التوفيرية", "25 جيجابايت نت فائق السرعة + استخدام مجاني فيسبوك وواتساب", 6500.0, "باقات", "yemen_mobile"),
        TelecomPackage("ym_4", "رصيد فوري يمن موبايل 1000 ريال", "تغذية رصيد مكالمات وخدمات يمن موبايل", 1000.0, "رصيد", "yemen_mobile"),
        TelecomPackage("ym_5", "رصيد فوري يمن موبايل 3000 ريال", "شحن رصيد مباشر لأي رقم يمن موبايل", 3000.0, "رصيد", "yemen_mobile"),
        TelecomPackage("ym_6", "شحن جملة وكلاء 10,000 ريال", "شحن فئات الجملة المعتمدة بخصم فوري", 9800.0, "جملة", "yemen_mobile"),
        TelecomPackage("ym_7", "باقة ريال موبايل (مكالمات مخفضة)", "رصيد ريال للدفع حسب الاستخدام مع تعرفة منخفضة", 2000.0, "ريال", "yemen_mobile"),

        // Sabafon Packages
        TelecomPackage("sb_1", "باقة شباب سبأفون الشهرية 10GB", "10 جيجابايت إنترنت سريع + 500 دقيقة سبأفون", 3200.0, "باقات", "sabafon"),
        TelecomPackage("sb_2", "باقة ميكس الأسبوعية 3GB", "3 جيجابايت + 150 دقيقة اتصال داخل وخارج الشبكة", 1200.0, "باقات", "sabafon"),
        TelecomPackage("sb_3", "رصيد فوري سبأفون 1000 ريال", "شحن رصيد مباشر فوري لسبأفون شمال وجنوب", 1000.0, "رصيد", "sabafon"),
        TelecomPackage("sb_4", "رصيد فوري سبأفون 2500 ريال", "تغذية رصيد أساسي لجميع باقات سبأفون", 2500.0, "فوري", "sabafon"),
        TelecomPackage("sb_5", "باقات جملة سبأفون المعتمدة", "سداد رصيد جملة وتفعيل باقات للمحلات والوكلاء", 5000.0, "جملة", "sabafon"),

        // YOU Packages
        TelecomPackage("you_1", "باقة يو مكس التوفيرية 15GB", "15 جيجابايت إنترنت الجيل الرابع 4G + 400 دقيقة", 3800.0, "باقات", "you"),
        TelecomPackage("you_2", "باقة يو سمارت اليومية 2GB", "2 جيجابايت إنترنت سريع للاستخدام اليومي", 600.0, "باقات", "you"),
        TelecomPackage("you_3", "رصيد فوري يو 1500 ريال", "شحن رصيد مباشر لخطوط YOU", 1500.0, "رصيد", "you"),
        TelecomPackage("you_4", "شحن جملة يو 10,000 ريال", "شحن رصيد الجملة لخطوط يو بأفضل خصم", 9800.0, "جملة", "you"),

        // Y Telecom
        TelecomPackage("y_1", "باقة واي إنترنت شهرية 8GB", "8 جيجابايت صالحة 30 يوم لشبكة واي Y", 2600.0, "باقات", "y"),
        TelecomPackage("y_2", "رصيد فوري واي 1000 ريال", "تغذية رصيد مباشر لخط واي", 1000.0, "رصيد", "y"),

        // Yemen Net & Fixed
        TelecomPackage("yn_1", "تجديد اشتراك يمن نت ADSL باقة 50GB", "شحن وتجديد رصيد الإنترنت المنزلي فائق السرعة", 4200.0, "باقات", "fixed"),
        TelecomPackage("yn_2", "تجديد يمن نت ADSL فئة 120GB", "باقة الإنترنت العائلي المنزلي بلا حدود", 9600.0, "باقات", "fixed"),
        TelecomPackage("yn_3", "سداد فاتورة الهاتف الثابت المنزلي", "سداد فواتير الهاتف الأرضي والنداء الآلي", 1500.0, "رصيد", "fixed")
    )

    // Sync wallet balance
    fun syncWalletBalance(): Double {
        val current = _walletAccount.value
        return current.balanceYer
    }

    suspend fun syncWalletFromServer(): Pair<Boolean, String> {
        return withContext(Dispatchers.IO) {
            val token = _userSession.value.token
            try {
                val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                if (!token.isNullOrBlank()) {
                    val profResp = api.getProfile("Token $token")
                    if (profResp.isSuccessful && profResp.body() != null) {
                        val u = profResp.body()!!
                        val fullName = listOfNotNull(u.firstName, u.lastName)
                            .filter { it.isNotBlank() }
                            .joinToString(" ")
                            .ifBlank { u.phone }
                        _userSession.value = _userSession.value.copy(
                            phone = u.phone,
                            fullName = fullName,
                            governorate = u.governorate ?: _userSession.value.governorate,
                            pointsBalance = u.pointsBalance ?: _userSession.value.pointsBalance,
                            role = u.role ?: "customer"
                        )
                    }

                    var fetchedYer: Double? = null
                    var fetchedSar: Double? = null
                    var fetchedUsd: Double? = null
                    var fetchedPoints: Int? = null
                    var fetchedAccNum: String? = null

                    // 1. Try GET wallets/
                    try {
                        val walletsResp = api.getWallets("Token $token")
                        if (walletsResp.isSuccessful && walletsResp.body() != null) {
                            val body = walletsResp.body()
                            val walletMap: Map<String, Any?>? = when (body) {
                                is List<*> -> (body.firstOrNull() as? Map<String, Any?>)
                                is Map<*, *> -> {
                                    val results = body["results"] as? List<*>
                                    (results?.firstOrNull() as? Map<String, Any?>) ?: (body as? Map<String, Any?>)
                                }
                                else -> null
                            }
                            if (walletMap != null) {
                                fetchedYer = (walletMap["balance_yer"] ?: walletMap["balance"])?.toString()?.toDoubleOrNull()
                                fetchedSar = walletMap["balance_sar"]?.toString()?.toDoubleOrNull()
                                fetchedUsd = walletMap["balance_usd"]?.toString()?.toDoubleOrNull()
                                fetchedPoints = walletMap["points"]?.toString()?.toIntOrNull()
                                fetchedAccNum = (walletMap["account_number"] ?: walletMap["id"])?.toString()
                            }
                        }
                    } catch (_: Exception) {}

                    // 2. Try GET wallet/
                    if (fetchedYer == null) {
                        try {
                            val wResp = api.getWallet("Token $token")
                            if (wResp.isSuccessful && wResp.body() != null) {
                                val wData = wResp.body()!!
                                fetchedYer = (wData["balance_yer"] ?: wData["balance"])?.toString()?.toDoubleOrNull()
                                fetchedSar = wData["balance_sar"]?.toString()?.toDoubleOrNull()
                                fetchedUsd = wData["balance_usd"]?.toString()?.toDoubleOrNull()
                                fetchedPoints = wData["points"]?.toString()?.toIntOrNull()
                            }
                        } catch (_: Exception) {}
                    }

                    val finalYer = fetchedYer ?: _walletAccount.value.balanceYer
                    val finalSar = fetchedSar ?: _walletAccount.value.balanceSar
                    val finalUsd = fetchedUsd ?: _walletAccount.value.balanceUsd
                    val finalPoints = fetchedPoints ?: _userSession.value.pointsBalance
                    val finalAcc = if (fetchedAccNum.isNullOrBlank()) _userSession.value.phone.ifBlank { _walletAccount.value.accountNumber } else fetchedAccNum

                    _walletAccount.value = _walletAccount.value.copy(
                        accountNumber = finalAcc,
                        userName = _userSession.value.fullName.ifBlank { "عميل شبيك" },
                        phone = _userSession.value.phone.ifBlank { _walletAccount.value.phone },
                        balanceYer = finalYer,
                        balanceSar = finalSar,
                        balanceUsd = finalUsd,
                        points = finalPoints,
                        isVerified = true
                    )

                    fetchOrdersFromApi(token)
                    fetchNotificationsFromApi(token)
                    fetchAddressesFromApi(token)
                    Pair(true, "تمت مزامنة رصيد الحساب بنجاح من الخادم! رصيدك الحالي: ${finalYer.toInt()} ر.ي")
                } else {
                    Pair(true, "تم تحديث الرصيد المحلي: ${_walletAccount.value.balanceYer.toInt()} ر.ي")
                }
            } catch (e: Exception) {
                Pair(false, "تعذر الاتصال بالخادم لمزامنة الرصيد: ${e.localizedMessage}")
            }
        }
    }

    suspend fun checkTransferEligibility(recipientPhone: String, amount: Double, message: String = ""): TransferCheckResult {
        val current = _walletAccount.value
        val cleanPhone = recipientPhone.trim()
        if (cleanPhone.isBlank()) {
            return TransferCheckResult(
                isAllowed = false,
                recipientPhone = cleanPhone,
                amount = amount,
                message = "يرجى إدخال رقم هاتف المشترك المستلم أولاً"
            )
        }
        if (amount <= 0) {
            return TransferCheckResult(
                isAllowed = false,
                recipientPhone = cleanPhone,
                amount = amount,
                message = "يرجى تحديد مبلغ تحويل صحيح أكبر من 0 ر.ي"
            )
        }
        if (current.balanceYer < amount) {
            return TransferCheckResult(
                isAllowed = false,
                recipientPhone = cleanPhone,
                amount = amount,
                message = "عفواً، رصيدك الحالي (${current.balanceYer.toInt()} ر.ي) غير كافٍ لإتمام التحويل بمبلغ ${amount.toInt()} ر.ي"
            )
        }

        return withContext(Dispatchers.IO) {
            var foundName: String? = null
            var giftId: Int? = null
            val token = _userSession.value.token
            if (!token.isNullOrBlank()) {
                try {
                    val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                    val giftPayload = mapOf(
                        "receiver_phone" to cleanPhone,
                        "amount" to amount,
                        "message" to message.ifBlank { "تحويل مالي إلى مشترك" }
                    )
                    val giftResp = api.createGift("Token $token", giftPayload)
                    if (giftResp.isSuccessful && giftResp.body() != null) {
                        val body = giftResp.body()!!
                        giftId = (body["id"] as? Number)?.toInt() ?: body["id"]?.toString()?.toIntOrNull()
                        foundName = body["receiver_name"]?.toString() ?: body["recipient_name"]?.toString() ?: body["receiver_phone"]?.toString()
                    } else if (giftResp.code() == 404 || giftResp.code() == 400) {
                        val errStr = giftResp.errorBody()?.string() ?: ""
                        if (errStr.contains("المحفظة") || errStr.contains("غير موجود") || errStr.contains("not found", ignoreCase = true)) {
                            return@withContext TransferCheckResult(
                                isAllowed = false,
                                recipientPhone = cleanPhone,
                                amount = amount,
                                message = "المشترك المطلوب غير موجود في النظام؛ يرجى التأكد من صحة رقم الهاتف."
                            )
                        } else if (errStr.contains("الرصيد") || errStr.contains("insufficient", ignoreCase = true)) {
                            return@withContext TransferCheckResult(
                                isAllowed = false,
                                recipientPhone = cleanPhone,
                                amount = amount,
                                message = "عفواً، رصيدك في الخادم غير كافٍ لإتمام التحويل."
                            )
                        }
                    }
                } catch (_: Exception) {}
            }

            if (foundName.isNullOrBlank()) {
                foundName = when {
                    cleanPhone.endsWith("456") -> "زيدان العطاب"
                    cleanPhone.endsWith("789") -> "أحمد مصلح الشامي"
                    cleanPhone.endsWith("111") -> "محمد عبدالملك اليماني"
                    cleanPhone.endsWith("222") -> "عبدالرحمن سنان"
                    cleanPhone.endsWith("333") -> "خالد الورداني"
                    cleanPhone.endsWith("444") -> "ياسر القدسي"
                    cleanPhone.endsWith("555") -> "سامي الصلوي"
                    cleanPhone.length in 9..12 -> "مشترك معتمد (${cleanPhone})"
                    else -> null
                }
            }

            if (foundName == null) {
                return@withContext TransferCheckResult(
                    isAllowed = false,
                    recipientPhone = cleanPhone,
                    amount = amount,
                    message = "المشترك غير مسجل في النظام، يرجى التأكد من صحة رقم الهاتف المدخل."
                )
            }

            TransferCheckResult(
                isAllowed = true,
                recipientName = foundName,
                recipientPhone = cleanPhone,
                amount = amount,
                fee = 0.0,
                giftId = giftId,
                message = "تم العثور على المشترك ورصيدك كافٍ. يرجى مراجعة التفاصيل أدناه وتأكيد العملية أو التراجع."
            )
        }
    }

    suspend fun confirmTransfer(
        giftId: Int?,
        recipientPhone: String,
        recipientName: String,
        amount: Double
    ): Pair<Boolean, WalletTransaction?> {
        val current = _walletAccount.value
        if (current.balanceYer < amount) return Pair(false, null)

        _walletAccount.value = current.copy(balanceYer = current.balanceYer - amount)
        val txId = "TR-${(100000..999999).random()}"
        val sdf = SimpleDateFormat("yyyy/MM/dd hh:mm a", Locale.forLanguageTag("ar"))
        val dateStr = sdf.format(Date())

        val newTx = WalletTransaction(
            id = txId,
            title = "تحويل مالي إلى $recipientName",
            type = "TRANSFER",
            amount = amount,
            currency = "ر.ي",
            date = dateStr,
            isPositive = false,
            recipientName = recipientName,
            recipientPhone = recipientPhone,
            referenceCode = "TXN-$txId",
            status = "ناجحة ومكتملة ✅",
            fee = 0.0,
            notes = "تم تأكيد التحويل المالي الفوري للمشترك بنجاح"
        )
        _transactions.value = listOf(newTx) + _transactions.value

        val token = _userSession.value.token
        if (!token.isNullOrBlank()) {
            withContext(Dispatchers.IO) {
                try {
                    val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                    if (giftId != null) {
                        api.confirmGift("Token $token", giftId)
                    } else {
                        api.transfer("Token $token", mapOf("phone" to recipientPhone, "amount" to amount))
                    }
                } catch (_: Exception) {}
            }
        }

        val notif = AppNotification(
            id = "n_${System.currentTimeMillis()}",
            title = "حوالة مالية صادرة بنجاح",
            message = "تم خصم ${amount.toInt()} ر.ي وتحويلها إلى $recipientName ($recipientPhone). رقم المرجع: $txId",
            time = "الآن",
            isRead = false
        )
        _notifications.value = listOf(notif) + _notifications.value

        return Pair(true, newTx)
    }

    suspend fun cancelTransfer(giftId: Int?): Boolean {
        if (giftId == null) return true
        val token = _userSession.value.token
        if (!token.isNullOrBlank()) {
            withContext(Dispatchers.IO) {
                try {
                    val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                    api.cancelGift("Token $token", giftId)
                } catch (_: Exception) {}
            }
        }
        return true
    }

    suspend fun executeTransfer(
        recipientPhone: String,
        recipientName: String,
        amount: Double
    ): Pair<Boolean, WalletTransaction?> {
        return confirmTransfer(null, recipientPhone, recipientName, amount)
    }

    suspend fun feedWalletViaServer(
        phone: String,
        amount: Double,
        code: String,
        method: String = "floosak",
        reference: String = ""
    ): Pair<Boolean, String> {
        return withContext(Dispatchers.IO) {
            val token = _userSession.value.token
            val methodNameArabic = when (method.lowercase()) {
                "floosak" -> "محفظة فلوسك (CAC Bank)"
                "jeeb" -> "محفظة جيب (بنك الكريمي)"
                "jawali" -> "محفظة جوالي (YKB)"
                "cash" -> "محفظة ون كاش / كاش"
                "direct" -> "كرت شحن رصيد فوري"
                else -> method
            }

            var serverSuccess = false
            var serverMessage = ""
            try {
                val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                val resp = api.feedAccount(
                    token = if (token != null) "Token $token" else null,
                    request = mapOf(
                        "phone" to phone.trim(),
                        "amount" to amount,
                        "code" to code.trim(),
                        "method" to method,
                        "reference" to reference.trim()
                    )
                )
                if (resp.isSuccessful && resp.body() != null) {
                    serverSuccess = true
                    serverMessage = resp.body()!!["message"]?.toString() ?: "تمت تغذية الحساب بنجاح عبر $methodNameArabic"
                }
            } catch (_: Exception) {}

            // Update balance locally and record transaction
            val current = _walletAccount.value
            _walletAccount.value = current.copy(balanceYer = current.balanceYer + amount)
            val newTx = WalletTransaction(
                id = "DEP-${(100000..999999).random()}",
                title = "تغذية عبر $methodNameArabic",
                type = "DEPOSIT",
                amount = amount,
                currency = "ر.ي",
                date = SimpleDateFormat("yyyy/MM/dd hh:mm a", Locale.forLanguageTag("ar")).format(Date()),
                isPositive = true,
                status = "ناجحة ومكتملة ✅",
                referenceCode = if (reference.isNotBlank()) reference else "REF-${(10000..99999).random()}",
                notes = "تم إيداع الرصيد بنجاح من حساب $phone"
            )
            _transactions.value = listOf(newTx) + _transactions.value

            val notif = AppNotification(
                id = "n_dep_${System.currentTimeMillis()}",
                title = "تم إيداع رصيد في المحفظة 💰",
                message = "تمت إضافة ${amount.toInt()} ر.ي إلى محفظتك بنجاح عبر $methodNameArabic.",
                time = "الآن",
                isRead = false
            )
            _notifications.value = listOf(notif) + _notifications.value

            Pair(true, if (serverSuccess) serverMessage else "تمت التغذية الذاتية بنجاح! رصيدك الجديد: ${_walletAccount.value.balanceYer.toInt()} ر.ي")
        }
    }

    fun markNotificationAsRead(id: String) {
        _notifications.value = _notifications.value.map {
            if (it.id == id) it.copy(isRead = true) else it
        }
        val token = _userSession.value.token
        if (!token.isNullOrBlank()) {
            val serverId = id.removePrefix("srv_")
            coroutineScope.launch {
                try {
                    val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                    api.markNotificationRead("Token $token", serverId)
                } catch (_: Exception) {}
            }
        }
    }

    fun markAllNotificationsAsRead() {
        _notifications.value = _notifications.value.map { it.copy(isRead = true) }
    }

    // Feed wallet via Jeeb or any payment gateway
    fun feedWalletViaGateway(sourceName: String, phone: String, amount: Double, code: String): Boolean {
        if (amount <= 0) return false
        val current = _walletAccount.value
        _walletAccount.value = current.copy(balanceYer = current.balanceYer + amount)
        val newTx = WalletTransaction(
            id = "tx_${System.currentTimeMillis()}",
            title = "تغذية حسابي عبر $sourceName",
            type = "DEPOSIT",
            amount = amount,
            currency = "ر.ي",
            date = "الآن",
            isPositive = true
        )
        _transactions.value = listOf(newTx) + _transactions.value
        return true
    }

    // Pay telecom bill or recharge package
    fun payTelecomRecharge(
        phone: String,
        operatorName: String,
        category: String,
        packageName: String,
        amount: Double
    ): Pair<Boolean, String> {
        val current = _walletAccount.value
        if (current.balanceYer < amount) {
            return Pair(false, "عذراً، رصيد حسابك (${current.balanceYer.toInt()} ر.ي) غير كافٍ لسداد هذا المبلغ ($amount ر.ي). يرجى تغذية حسابك أولاً.")
        }

        _walletAccount.value = current.copy(
            balanceYer = current.balanceYer - amount,
            points = current.points + (amount / 200).toInt()
        )

        val txId = "TEL-${(100000..999999).random()}"
        val newTx = WalletTransaction(
            id = txId,
            title = "سداد $operatorName ($packageName) للرقم $phone",
            type = "BILL",
            amount = amount,
            currency = "ر.ي",
            date = "الآن",
            isPositive = false
        )
        _transactions.value = listOf(newTx) + _transactions.value

        val successMsg = "تمت عملية السداد بنجاح!\nالشبكة: $operatorName\nالرقم: $phone\nالخدمة: $packageName\nالمبلغ: $amount ر.ي\nرقم السند: $txId"
        return Pair(true, successMsg)
    }

    // Add message to order chat
    fun addOrderChatMessage(orderId: String, text: String) {
        val currentOrders = _orders.value.toMutableList()
        val index = currentOrders.indexOfFirst { it.id == orderId }
        if (index >= 0) {
            val order = currentOrders[index]
            val sdf = SimpleDateFormat("hh:mm a", Locale.getDefault())
            val currentTime = sdf.format(Date())

            val userMsg = OrderChatMessage(
                id = "msg_${System.currentTimeMillis()}",
                senderName = "أنت",
                message = text,
                time = currentTime,
                isFromUser = true
            )

            // Context-aware auto-reply from the store or courier
            val replyMsg = OrderChatMessage(
                id = "reply_${System.currentTimeMillis() + 1}",
                senderName = if (order.statusStep >= 2) order.deliveryDriver else order.storeName,
                message = when {
                    text.contains("أين") || text.contains("وين") -> "الطلب في الطريق إليك مع الكابتن وسأصل قريباً جداً، يمكنك متابعة موقعي!"
                    text.contains("باب") || text.contains("وصلت") -> "حاضر، أنا أمام الباب الآن ونازل لعندك!"
                    text.contains("شكرا") || text.contains("يعطيك") -> "العفو على الرحب والسعة! في خدمتك دائماً في شبيك 🌟"
                    else -> "أهلاً بك! تم استلام رسالتك وجاري المتابعة معك فوراً لخدمتك بأفضل شكل."
                },
                time = currentTime,
                isFromUser = false
            )

            val updatedOrder = order.copy(
                chatMessages = order.chatMessages + listOf(userMsg, replyMsg)
            )
            currentOrders[index] = updatedOrder
            _orders.value = currentOrders
        }
    }

    // Rate an order
    fun rateOrder(orderId: String, rating: Float, comment: String) {
        val currentOrders = _orders.value.toMutableList()
        val index = currentOrders.indexOfFirst { it.id == orderId }
        if (index >= 0) {
            val order = currentOrders[index]
            val sdf = SimpleDateFormat("dd MMMM yyyy", Locale.forLanguageTag("ar"))
            val currentDate = sdf.format(Date())

            val newReview = OrderReview(
                id = "rev_${System.currentTimeMillis()}",
                userName = _userSession.value.fullName.ifBlank { "مستخدم شبيك" },
                rating = rating,
                comment = comment,
                date = currentDate
            )

            val updatedOrder = order.copy(
                rating = rating,
                userReview = comment,
                reviews = listOf(newReview) + order.reviews
            )
            currentOrders[index] = updatedOrder
            _orders.value = currentOrders
        }
    }

    // Wallet actions (Deposit, Transfer, Pay from Cart)
    fun depositToWallet(amount: Double) {
        val current = _walletAccount.value
        _walletAccount.value = current.copy(balanceYer = current.balanceYer + amount)
        val newTx = WalletTransaction(
            id = "tx_${System.currentTimeMillis()}",
            title = "تغذية المحفظة (إيداع سريع)",
            type = "DEPOSIT",
            amount = amount,
            currency = "ر.ي",
            date = "الآن",
            isPositive = true
        )
        _transactions.value = listOf(newTx) + _transactions.value
    }

    fun transferFromWallet(recipient: String, amount: Double): Boolean {
        val current = _walletAccount.value
        if (current.balanceYer >= amount) {
            _walletAccount.value = current.copy(balanceYer = current.balanceYer - amount)
            val newTx = WalletTransaction(
                id = "tx_${System.currentTimeMillis()}",
                title = "تحويل إلى $recipient",
                type = "TRANSFER",
                amount = amount,
                currency = "ر.ي",
                date = "الآن",
                isPositive = false
            )
            _transactions.value = listOf(newTx) + _transactions.value
            return true
        }
        return false
    }

    fun payOrderWithWallet(
        total: Double,
        storeName: String,
        deliveryAddress: String = "",
        orderNotes: String = ""
    ): Boolean {
        val current = _walletAccount.value
        if (current.balanceYer >= total) {
            _walletAccount.value = current.copy(
                balanceYer = current.balanceYer - total,
                points = current.points + (total / 500).toInt()
            )
            val newTx = WalletTransaction(
                id = "tx_${System.currentTimeMillis()}",
                title = "دفع مشتريات: $storeName",
                type = "PURCHASE",
                amount = total,
                currency = "ر.ي",
                date = "الآن",
                isPositive = false
            )
            _transactions.value = listOf(newTx) + _transactions.value

            val cartItems = _cart.value
            val orderItems = cartItems.map {
                OrderItemDetail(
                    productId = it.product.id,
                    productName = it.product.name,
                    quantity = it.quantity,
                    priceYer = it.product.priceYer,
                    category = it.product.category,
                    subCategory = it.product.subCategory,
                    storeName = it.product.storeName
                )
            }

            val finalAddress = deliveryAddress.ifBlank {
                _addresses.value.firstOrNull { it.isDefault }?.fullAddress
                    ?: "صنعاء - شارع حدة - تقاطع الرويشان"
            }

            val newOrder = StoreOrder(
                id = "ORD-${(1000..9999).random()}",
                storeName = storeName,
                totalAmount = total,
                currency = "ر.ي",
                date = "الآن",
                status = "قيد التجهيز",
                itemsCount = cartItems.sumOf { it.quantity },
                items = orderItems,
                deliveryAddress = finalAddress,
                deliveryDriver = "الكابتن محمد اليماني",
                driverPhone = "771998877",
                paymentMethod = "محفظة جيب الإلكترونية (مدفوع بالكامل من الرصيد)",
                statusStep = 1,
                orderNotes = orderNotes,
                chatMessages = listOf(
                    OrderChatMessage(
                        id = "msg_init_1",
                        senderName = storeName,
                        message = "مرحباً بك في تطبيق شبيك! تم استلام طلبك وبدأ المتجر في التجهيز فوراً. شبيك لبيّك طلبك بين يديك 🌟",
                        time = "الآن",
                        isFromUser = false
                    )
                )
            )
            _orders.value = listOf(newOrder) + _orders.value

            // Also attempt to push order to Django backend if logged in
            val token = _userSession.value.token
            if (!token.isNullOrBlank() && !token.startsWith("local_")) {
                coroutineScope.launch {
                    try {
                        val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                        val itemsPayload = cartItems.map {
                            CreateOrderItemRequest(productId = it.product.id, quantity = it.quantity)
                        }
                        api.createOrder(
                            token = "Token $token",
                            request = CreateOrderRequest(
                                paymentMethod = "wallet",
                                items = itemsPayload
                            )
                        )
                    } catch (_: Exception) {}
                }
            }

            clearCart()
            return true
        }
        return false
    }

    fun checkoutCashOnDelivery(
        total: Double,
        storeName: String,
        deliveryAddress: String = "",
        orderNotes: String = ""
    ) {
        val cartItems = _cart.value
        val orderItems = cartItems.map {
            OrderItemDetail(
                productId = it.product.id,
                productName = it.product.name,
                quantity = it.quantity,
                priceYer = it.product.priceYer,
                category = it.product.category,
                subCategory = it.product.subCategory,
                storeName = it.product.storeName
            )
        }

        val finalAddress = deliveryAddress.ifBlank {
            _addresses.value.firstOrNull { it.isDefault }?.fullAddress
                ?: "صنعاء - شارع حدة - تقاطع الرويشان"
        }

        val newOrder = StoreOrder(
            id = "ORD-${(1000..9999).random()}",
            storeName = storeName,
            totalAmount = total,
            currency = "ر.ي",
            date = "الآن",
            status = "قيد التجهيز",
            itemsCount = cartItems.sumOf { it.quantity },
            items = orderItems,
            deliveryAddress = finalAddress,
            deliveryDriver = "الكابتن محمد اليماني",
            driverPhone = "771998877",
            paymentMethod = "الدفع نقداً عند الاستلام (COD)",
            statusStep = 1,
            orderNotes = orderNotes,
            chatMessages = listOf(
                OrderChatMessage(
                    id = "msg_init_1",
                    senderName = storeName,
                    message = "مرحباً بك! تم تأكيد طلبك بنجاح وسيكون الدفع نقداً عند الاستلام. نسعد بخدمتك دائماً 🌟",
                    time = "الآن",
                    isFromUser = false
                )
            )
        )
        _orders.value = listOf(newOrder) + _orders.value

        val token = _userSession.value.token
        if (!token.isNullOrBlank() && !token.startsWith("local_")) {
            coroutineScope.launch {
                try {
                    val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                    val itemsPayload = cartItems.map {
                        CreateOrderItemRequest(productId = it.product.id, quantity = it.quantity)
                    }
                    api.createOrder(
                        token = "Token $token",
                        request = CreateOrderRequest(
                            paymentMethod = "cod",
                            items = itemsPayload
                        )
                    )
                } catch (_: Exception) {}
            }
        }

        clearCart()
    }

    suspend fun updateOrderDetails(orderId: String, newAddress: String, newNotes: String): Boolean {
        val currentOrders = _orders.value.toMutableList()
        val index = currentOrders.indexOfFirst { it.id == orderId }
        if (index >= 0) {
            val updated = currentOrders[index].copy(
                deliveryAddress = newAddress.ifBlank { currentOrders[index].deliveryAddress },
                orderNotes = newNotes
            )
            currentOrders[index] = updated
            _orders.value = currentOrders

            val token = _userSession.value.token
            val numId = orderId.removePrefix("ORD-").toIntOrNull()
            if (!token.isNullOrBlank() && numId != null) {
                withContext(Dispatchers.IO) {
                    try {
                        val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                        api.updateOrderDetails(
                            token = "Token $token",
                            id = orderId,
                            payload = mapOf(
                                "delivery_address" to newAddress,
                                "notes" to newNotes
                            )
                        )
                    } catch (_: Exception) {}
                }
            }
            return true
        }
        return false
    }

    suspend fun cancelOrder(orderId: String, reason: String = "إلغاء بناء على رغبة العميل"): Boolean {
        val currentOrders = _orders.value.toMutableList()
        val index = currentOrders.indexOfFirst { it.id == orderId }
        if (index >= 0) {
            val existing = currentOrders[index]
            val updated = existing.copy(
                status = "ملغي",
                isCancelled = true,
                orderNotes = if (existing.orderNotes.isNotBlank()) "${existing.orderNotes} (سبب الإلغاء: $reason)" else "سبب الإلغاء: $reason"
            )
            currentOrders[index] = updated
            _orders.value = currentOrders

            // If it was paid from wallet, refund the user!
            if (existing.paymentMethod.contains("محفظة") || existing.paymentMethod.contains("رصيد")) {
                depositToWallet(existing.totalAmount)
                val notif = AppNotification(
                    id = "n_refund_${System.currentTimeMillis()}",
                    title = "استرجاع مبلغ طلب ملغي 🔄",
                    message = "تم استرجاع مبلغ ${existing.totalAmount.toInt()} ر.ي إلى محفظتك للطلب ${existing.id}",
                    time = "الآن",
                    isRead = false
                )
                _notifications.value = listOf(notif) + _notifications.value
            }

            val token = _userSession.value.token
            val numId = orderId.removePrefix("ORD-").toIntOrNull()
            if (!token.isNullOrBlank() && numId != null) {
                withContext(Dispatchers.IO) {
                    try {
                        val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                        api.cancelOrder(
                            token = "Token $token",
                            id = orderId
                        )
                    } catch (_: Exception) {}
                }
            }
            return true
        }
        return false
    }

    fun fetchStoresAndProductsFromApi() {
        coroutineScope.launch {
            try {
                val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                val baseUrl = _djangoBaseUrl.value.removeSuffix("/api/").removeSuffix("/")
                
                // 1. Fetch Categories & Subcategories from Server (All pages)
                try {
                    val allCatDtos = mutableListOf<CategoryDto>()
                    var catPage = 1
                    var catHasMore = true
                    while (catHasMore && catPage <= 10) {
                        try {
                            val catResp = api.getCategories(page = catPage)
                            if (catResp.isSuccessful && catResp.body() != null) {
                                val body = catResp.body()!!
                                allCatDtos.addAll(body.results)
                                catHasMore = body.next != null
                                catPage++
                            } else {
                                catHasMore = false
                            }
                        } catch (e: Exception) {
                            catHasMore = false
                        }
                    }

                    if (allCatDtos.isNotEmpty()) {
                        val mainCats = allCatDtos.filter { it.parent == null }
                        val mappedCats = mutableListOf<CategoryItem>()
                        // "All" item
                        mappedCats.add(CategoryItem("all", "الكل", "grid", _products.value.size, listOf("الكل")))

                        mainCats.forEach { main ->
                            val children = allCatDtos.filter { it.parent == main.id }
                            val subTitles = mutableListOf("الكل")
                            subTitles.addAll(children.map { it.name })

                            val iconName = when (main.name.trim()) {
                                "الإلكترونيات" -> "phone_iphone"
                                "الملابس" -> "checkroom"
                                "المأكولات" -> "shopping_basket"
                                "المنزل" -> "home"
                                "الجمال والعناية" -> "spa"
                                "الألعاب" -> "sports_esports"
                                "الرياضة" -> "fitness_center"
                                "السيارات" -> "directions_car"
                                "الكتب والتعليم" -> "menu_book"
                                else -> "category"
                            }

                            mappedCats.add(
                                CategoryItem(
                                    id = main.name,
                                    title = main.name,
                                    iconName = iconName,
                                    productCount = main.productsCount ?: children.size,
                                    subCategories = subTitles,
                                    serverId = main.id,
                                    parentId = null
                                )
                            )
                        }
                        _categories.value = mappedCats
                    }
                } catch (e: Exception) {}

                // 2. Fetch Vendors/Stores
                val vendorResp = api.getVendors()
                if (vendorResp.isSuccessful && vendorResp.body() != null) {
                    val vendorResults = vendorResp.body()!!.results
                    if (vendorResults.isNotEmpty()) {
                        val mappedStores = vendorResults.map { v ->
                            Store(
                                id = v.id,
                                name = v.storeName,
                                category = v.address ?: "عام",
                                rating = 4.8,
                                deliveryTime = "30 دقيقة",
                                minOrder = "2,000 ر.ي",
                                deliveryFee = "مجاني",
                                description = v.description ?: "متجر معتمد على منصة شبيك",
                                phone = v.phone ?: "771234567",
                                logoUrl = resolveMediaUrl(v.logoUrl, baseUrl, "https://images.unsplash.com/photo-1441986300917-64674bd600d8?w=300"),
                                coverUrl = resolveMediaUrl(v.coverUrl, baseUrl, "https://images.unsplash.com/photo-1472851294608-062f824d29cc?w=800")
                            )
                        }
                        _stores.value = mappedStores
                    }
                }

                // 3. Fetch Products with Full Server Details
                val prodResp = api.getProducts()
                if (prodResp.isSuccessful && prodResp.body() != null) {
                    val productResults = prodResp.body()!!.results
                    if (productResults.isNotEmpty()) {
                        val mappedProducts = productResults.map { p ->
                            val effectivePrice = p.effectivePrice?.toDoubleOrNull() 
                                ?: p.salePrice?.toDoubleOrNull()
                                ?: p.price?.toDoubleOrNull() 
                                ?: 1000.0
                            val origPrice = p.price?.toDoubleOrNull()
                            val storeId = p.vendor?.id ?: 1
                            val storeName = p.vendor?.storeName ?: "شبيك ستور"

                            // Exact category & subcategory parsing
                            val rootCat = p.categories.firstOrNull { it.parent == null }
                            val subCat = p.categories.firstOrNull { it.parent != null }
                            val catName = rootCat?.name ?: p.categories.firstOrNull()?.name ?: "الإلكترونيات"
                            val subCatName = subCat?.name ?: ""

                            // Image URLs
                            val imgList = mutableListOf<String>()
                            p.mainImageUrl?.let {
                                val full = resolveMediaUrl(it, baseUrl, "")
                                if (full.isNotBlank()) imgList.add(full)
                            }
                            p.gallery.forEach { g ->
                                val full = resolveMediaUrl(g.url, baseUrl, "")
                                if (full.isNotBlank() && !imgList.contains(full)) imgList.add(full)
                            }
                            val defaultFallback = getCategoryFallbackImageUrl(catName, p.name)
                            if (imgList.isEmpty()) {
                                imgList.add(defaultFallback)
                            }

                            // Colors & Sizes
                            val colorList = p.colors?.mapNotNull { it.name }?.filter { it.isNotBlank() }
                                ?.ifEmpty { null } ?: listOf("أسود ملكي", "أزرق تيتانيوم")
                            val sizeList = p.sizes?.mapNotNull { it.label }?.filter { it.isNotBlank() }
                                ?.ifEmpty { null } ?: listOf("النسخة القياسية")

                            // Specifications & Warranty
                            val specsMap = mutableMapOf<String, String>()
                            if (!p.brand.isNullOrBlank()) specsMap["الماركة"] = p.brand
                            if (!p.material.isNullOrBlank()) specsMap["الخامة / المواصفات"] = p.material
                            if (subCatName.isNotBlank()) specsMap["القسم الفرعي"] = subCatName
                            if (!p.shippingNote.isNullOrBlank()) specsMap["الشحن والتوصيل"] = p.shippingNote
                            if (!p.returnPolicy.isNullOrBlank()) specsMap["سياسة الإرجاع"] = p.returnPolicy

                            var warrantyText = "ضمان فحص واستبدال معتمد"
                            var hasWarranty = true

                            if (p.details != null) {
                                if (p.details is Map<*, *>) {
                                    (p.details as Map<*, *>).forEach { (k, v) ->
                                        val key = k?.toString() ?: ""
                                        val value = v?.toString() ?: ""
                                        if (value.isNotBlank()) {
                                            when (key) {
                                                "condition" -> specsMap["حالة المنتج"] = value
                                                "warranty" -> {
                                                    hasWarranty = (value == "نعم" || value.contains("نعم"))
                                                    specsMap["الضمان"] = value
                                                }
                                                "warranty_duration" -> {
                                                    warrantyText = "ضمان رسمي معتمد: $value"
                                                    specsMap["مدة الضمان"] = value
                                                }
                                                "category_name" -> if (specsMap["القسم الفرعي"] == null) specsMap["القسم الفرعي"] = value
                                                else -> if (!key.contains("_id")) specsMap[key] = value
                                            }
                                        }
                                    }
                                } else {
                                    specsMap["بيانات إضافية"] = p.details.toString()
                                }
                            }

                            Product(
                                id = p.id,
                                storeId = storeId,
                                storeName = storeName,
                                name = p.name,
                                description = p.description?.ifBlank { null } ?: "منتج أصلي معتمد متوفر من $storeName بضمان وجودة عالية وتوصيل سريع.",
                                priceYer = effectivePrice,
                                originalPriceYer = if (origPrice != null && origPrice > effectivePrice) origPrice else null,
                                category = catName,
                                subCategory = subCatName,
                                brand = p.brand ?: "",
                                specs = specsMap,
                                rating = p.rating?.toDoubleOrNull() ?: 4.8,
                                inStock = (p.availableStock ?: p.stock ?: 1) > 0,
                                badge = if (p.isTrending == true) "الأكثر طلباً" else if ((p.discountPercent ?: 0) > 0) "خصم ${p.discountPercent}%" else null,
                                images = if (imgList.isNotEmpty()) imgList else listOf("https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600"),
                                colors = colorList,
                                sizes = sizeList,
                                warranty = warrantyText,
                                hasWarranty = hasWarranty,
                                reviewsCount = p.reviewsCount ?: 12
                            )
                        }
                        _products.value = mappedProducts
                    }
                }
            } catch (e: Exception) {
                // Keep default seed data on failure
            }
        }
    }

    fun fetchOrdersFromApi(token: String) {
        coroutineScope.launch {
            try {
                val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                val resp = api.getOrders("Token $token")
                if (resp.isSuccessful && resp.body() != null) {
                    val ordersList = resp.body()!!.results
                    if (ordersList.isNotEmpty()) {
                        val mappedOrders = ordersList.map { o ->
                            val items = o.items?.map { item ->
                                OrderItemDetail(
                                    productName = item.productName ?: "منتج",
                                    quantity = item.quantity,
                                    priceYer = item.unitPrice?.toDoubleOrNull() ?: 0.0,
                                    category = "عام"
                                )
                            } ?: emptyList()

                            StoreOrder(
                                id = o.orderNumber ?: "ORD-${o.id}",
                                storeName = o.items?.firstOrNull()?.vendorName ?: "شبيك ستور",
                                totalAmount = o.total?.toDoubleOrNull() ?: 0.0,
                                currency = o.currency ?: "ر.ي",
                                date = o.createdAt?.take(10) ?: "الآن",
                                status = when (o.status) {
                                    "pending" -> "قيد المراجعة"
                                    "processing" -> "قيد التجهيز"
                                    "shipped" -> "في الطريق إليك"
                                    "delivered" -> "تم التوصيل"
                                    "cancelled" -> "ملغي"
                                    else -> o.status ?: "قيد التجهيز"
                                },
                                itemsCount = items.sumOf { it.quantity },
                                items = items,
                                deliveryAddress = "صنعاء - العنوان المسجل",
                                deliveryDriver = "مندوب التوصيل",
                                driverPhone = "771234567",
                                paymentMethod = o.paymentMethod ?: "الدفع الإلكتروني",
                                statusStep = when (o.status) {
                                    "pending" -> 0
                                    "processing" -> 1
                                    "shipped" -> 2
                                    "delivered" -> 3
                                    else -> 1
                                }
                            )
                        }
                        _orders.value = mappedOrders
                    }
                }
            } catch (_: Exception) {}
        }
    }

    fun fetchNotificationsFromApi(token: String) {
        coroutineScope.launch {
            try {
                val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                val resp = api.getNotifications("Token $token")
                if (resp.isSuccessful && resp.body() != null) {
                    val notifList = resp.body()!!.results
                    if (notifList.isNotEmpty()) {
                        val mapped = notifList.map { n ->
                            AppNotification(
                                id = "srv_${n.id}",
                                title = n.title ?: "إشعار من شبيك",
                                message = n.message ?: "",
                                time = n.createdAt?.take(10) ?: "مؤخراً",
                                isRead = n.isRead ?: false
                            )
                        }
                        _notifications.value = mapped
                    }
                }
            } catch (e: Exception) {}
        }
    }

    fun purchaseWifiCard(
        network: WifiNetwork,
        denomination: WifiCardDenomination,
        userPhone: String
    ): PurchasedWifiCard {
        val randomPin = (100000000000L..999999999999L).random().toString()
        val randomSerial = "SN-${(10000000..99999999).random()}"

        val purchased = PurchasedWifiCard(
            id = "wifi_card_${System.currentTimeMillis()}",
            networkName = network.name,
            denominationTitle = denomination.title,
            priceYer = denomination.priceYer,
            pinCode = randomPin,
            serialNumber = randomSerial,
            targetPhone = userPhone,
            purchaseDate = "الآن",
            duration = denomination.duration,
            dataQuota = denomination.dataQuota,
            ownerPhone = network.ownerPhone
        )

        // Deduct from wallet if user has balance
        val currentBalance = _walletAccount.value.balanceYer
        if (currentBalance >= denomination.priceYer) {
            _walletAccount.value = _walletAccount.value.copy(
                balanceYer = currentBalance - denomination.priceYer
            )
            // Add wallet transaction
            val newTx = WalletTransaction(
                id = "tx_wifi_${System.currentTimeMillis()}",
                title = "شراء كرت وايفاي - ${network.name}",
                type = "WIFI_CARD",
                amount = denomination.priceYer,
                currency = "ر.ي",
                date = "اليوم",
                isPositive = false
            )
            _transactions.value = listOf(newTx) + _transactions.value
        }

        // Add to notifications
        val notif = AppNotification(
            id = "notif_wifi_${System.currentTimeMillis()}",
            title = "تم شراء كرت وايفاي بنجاح 📶",
            message = "تم شراء ${denomination.title} لشبكة ${network.name}. كود الكرت: $randomPin",
            time = "الآن",
            isRead = false
        )
        _notifications.value = listOf(notif) + _notifications.value

        _purchasedWifiCards.value = listOf(purchased) + _purchasedWifiCards.value

        // Try remote endpoint asynchronously
        coroutineScope.launch {
            try {
                val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                val token = _userSession.value.token
                if (!token.isNullOrBlank() && !token.startsWith("local_")) {
                    api.buyWifiCard(
                        "Token $token",
                        mapOf(
                            "network_id" to network.id,
                            "network_name" to network.name,
                            "denomination_id" to denomination.id,
                            "denomination_title" to denomination.title,
                            "phone" to userPhone,
                            "price" to denomination.priceYer
                        )
                    )
                }
            } catch (e: Exception) {}
        }

        return purchased
    }

    fun setUserRole(newRole: String) {
        _userSession.value = _userSession.value.copy(role = newRole)
    }

    // User Addresses Book
    private val _addresses = MutableStateFlow<List<UserAddress>>(
        listOf(
            UserAddress(
                id = 1,
                title = "المنزل",
                city = "صنعاء",
                district = "حدة - الحي الدبلوماسي",
                street = "شارع طوكيو، عمارة الأمل، شقة 4",
                building = "عمارة 12",
                phone = "770123456",
                isDefault = true
            ),
            UserAddress(
                id = 2,
                title = "العمل / المتجر",
                city = "صنعاء",
                district = "شارع الزبيري",
                street = "برج سبأ، الدور الثالث، مكتب 304",
                building = "برج سبأ",
                phone = "771234567",
                isDefault = false
            )
        )
    )
    val addresses: StateFlow<List<UserAddress>> = _addresses.asStateFlow()

    fun fetchAddressesFromApi(token: String? = null) {
        val userToken = token ?: _userSession.value.token
        if (userToken.isNullOrBlank()) return
        coroutineScope.launch(Dispatchers.IO) {
            try {
                val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                val resp = api.getAddresses("Token $userToken")
                if (resp.isSuccessful && resp.body() != null) {
                    val rawBody = resp.body()
                    val list = when (rawBody) {
                        is List<*> -> rawBody.filterIsInstance<Map<String, Any?>>()
                        is Map<*, *> -> (rawBody["results"] as? List<*>)?.filterIsInstance<Map<String, Any?>>() ?: emptyList()
                        else -> emptyList()
                    }
                    if (list.isNotEmpty()) {
                        val mapped = list.map { a ->
                            UserAddress(
                                id = (a["id"] as? Number)?.toInt() ?: a["id"]?.toString()?.toIntOrNull() ?: (1000..9999).random(),
                                title = a["title"]?.toString() ?: a["name"]?.toString() ?: "العنوان",
                                city = a["city"]?.toString() ?: "صنعاء",
                                district = a["district"]?.toString() ?: a["area"]?.toString() ?: "",
                                street = a["street"]?.toString() ?: a["address"]?.toString() ?: "",
                                building = a["building"]?.toString() ?: "",
                                phone = a["phone"]?.toString() ?: _userSession.value.phone,
                                isDefault = (a["is_default"] as? Boolean) ?: false
                            )
                        }
                        _addresses.value = mapped
                    }
                }
            } catch (_: Exception) {}
        }
    }

    fun addAddress(address: UserAddress) {
        val updated = if (address.isDefault) {
            _addresses.value.map { it.copy(isDefault = false) } + address
        } else {
            _addresses.value + address
        }
        _addresses.value = updated

        val token = _userSession.value.token
        if (!token.isNullOrBlank()) {
            coroutineScope.launch(Dispatchers.IO) {
                try {
                    val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                    val payload = mapOf(
                        "title" to address.title,
                        "city" to address.city,
                        "district" to address.district,
                        "street" to address.street,
                        "building" to address.building,
                        "phone" to address.phone,
                        "is_default" to address.isDefault
                    )
                    val resp = api.createAddress("Token $token", payload)
                    if (resp.isSuccessful && resp.body() != null) {
                        val serverId = (resp.body()!!["id"] as? Number)?.toInt()
                        if (serverId != null) {
                            _addresses.value = _addresses.value.map {
                                if (it.id == address.id) it.copy(id = serverId) else it
                            }
                        }
                    }
                } catch (_: Exception) {}
            }
        }
    }

    fun updateAddress(address: UserAddress) {
        _addresses.value = _addresses.value.map {
            if (it.id == address.id) address else if (address.isDefault) it.copy(isDefault = false) else it
        }

        val token = _userSession.value.token
        if (!token.isNullOrBlank()) {
            coroutineScope.launch(Dispatchers.IO) {
                try {
                    val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                    val payload = mapOf(
                        "title" to address.title,
                        "city" to address.city,
                        "district" to address.district,
                        "street" to address.street,
                        "building" to address.building,
                        "phone" to address.phone,
                        "is_default" to address.isDefault
                    )
                    api.updateAddress("Token $token", address.id, payload)
                } catch (_: Exception) {}
            }
        }
    }

    fun setDefaultAddress(id: Int) {
        _addresses.value = _addresses.value.map {
            it.copy(isDefault = (it.id == id))
        }
        val token = _userSession.value.token
        if (!token.isNullOrBlank()) {
            coroutineScope.launch(Dispatchers.IO) {
                try {
                    val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                    api.setDefaultAddress("Token $token", id)
                } catch (_: Exception) {}
            }
        }
    }

    fun deleteAddress(id: Int) {
        _addresses.value = _addresses.value.filter { it.id != id }
        val token = _userSession.value.token
        if (!token.isNullOrBlank()) {
            coroutineScope.launch(Dispatchers.IO) {
                try {
                    val api = NetworkClient.getApiService(_djangoBaseUrl.value)
                    api.deleteAddress("Token $token", id)
                } catch (_: Exception) {}
            }
        }
    }

    // Support Tickets & Inquiries
    private val _supportTickets = MutableStateFlow<List<SupportTicket>>(
        listOf(
            SupportTicket(
                id = "TCK-1082",
                subject = "استفسار بخصوص موعد شحن الطلب",
                category = "شحن وتوصيل",
                status = "تم الرد",
                date = "اليوم 02:15 م",
                lastMessage = "تم تسليم الشحنة لمندوب التوصيل في أمانة العاصمة."
            ),
            SupportTicket(
                id = "TCK-1049",
                subject = "تأكيد تغذية المحفظة عبر الكريمي",
                category = "مشكلة دفع",
                status = "مغلقة",
                date = "أمس 09:30 ص",
                lastMessage = "تم قيد المبلغ بنجاح في رصيد محفظتك المتاح."
            )
        )
    )
    val supportTickets: StateFlow<List<SupportTicket>> = _supportTickets.asStateFlow()

    private val _supportChatMessages = MutableStateFlow<List<SupportChatMessage>>(
        listOf(
            SupportChatMessage("1", "خدمة العملاء", "مرحباً بك في خدمة عملاء متجر شبيك وسوق بلس. كيف يمكننا مساعدتك اليوم؟", "02:10 م", false),
            SupportChatMessage("2", "أنت", "أريد الاستفسار عن كود الخصم وطريقة تفعيله عند الطلب.", "02:12 م", true),
            SupportChatMessage("3", "خدمة العملاء", "أهلاً بك يا أخي! يتم إدراج كود الخصم تلقائياً عند الشراء عبر المحفظة أو من صفحة الترندات والعروض الخاصة.", "02:14 م", false)
        )
    )
    val supportChatMessages: StateFlow<List<SupportChatMessage>> = _supportChatMessages.asStateFlow()

    fun sendSupportMessage(msg: String) {
        val newMsg = SupportChatMessage(
            id = System.currentTimeMillis().toString(),
            sender = "أنت",
            message = msg,
            time = SimpleDateFormat("hh:mm a", Locale("ar")).format(Date()),
            isFromUser = true
        )
        _supportChatMessages.value = _supportChatMessages.value + newMsg

        // Auto reply after delay
        coroutineScope.launch {
            kotlinx.coroutines.delay(1200)
            val reply = SupportChatMessage(
                id = (System.currentTimeMillis() + 1).toString(),
                sender = "خدمة العملاء",
                message = "شكراً لتواصلك معنا، استلمنا رسالتك: '$msg'. الموظف المختص يتابع طلبك الآن.",
                time = SimpleDateFormat("hh:mm a", Locale("ar")).format(Date()),
                isFromUser = false
            )
            _supportChatMessages.value = _supportChatMessages.value + reply
        }
    }

    fun createSupportTicket(subject: String, category: String, details: String) {
        val newTicket = SupportTicket(
            id = "TCK-${(1000..9999).random()}",
            subject = subject,
            category = category,
            status = "قيد المعالجة",
            date = "الآن",
            lastMessage = details
        )
        _supportTickets.value = listOf(newTicket) + _supportTickets.value
        sendSupportMessage("تم فتح تذكرة جديدة [$category]: $subject - $details")
    }

    // Referral Program
    private val _referralCode = MutableStateFlow("SHOP-770123")
    val referralCode: StateFlow<String> = _referralCode.asStateFlow()

    private val _invitedCount = MutableStateFlow(14)
    val invitedCount: StateFlow<Int> = _invitedCount.asStateFlow()

    private val _referralRewardYer = MutableStateFlow(35000.0)
    val referralRewardYer: StateFlow<Double> = _referralRewardYer.asStateFlow()

    // Preferences & Settings
    private val _selectedCurrency = MutableStateFlow("YER")
    val selectedCurrency: StateFlow<String> = _selectedCurrency.asStateFlow()

    private val _notificationsEnabled = MutableStateFlow(true)
    val notificationsEnabled: StateFlow<Boolean> = _notificationsEnabled.asStateFlow()

    val currencyRates: List<CurrencyRate> = listOf(
        CurrencyRate("USD", "YER", "535.00 ر.ي (صنعاء) / 1,900.00 ر.ي (عدن)"),
        CurrencyRate("SAR", "YER", "140.50 ر.ي (صنعاء) / 500.00 ر.ي (عدن)"),
        CurrencyRate("USD", "SAR", "3.75 ر.س")
    )

    fun setSelectedCurrency(curr: String) {
        _selectedCurrency.value = curr
    }

    fun setNotificationsEnabled(enabled: Boolean) {
        _notificationsEnabled.value = enabled
    }

    // Vendor Portal & Store Management
    private val _vendorFinance = MutableStateFlow(
        VendorFinance(
            vendorName = "روائع العود والعطور",
            walletBalance = 385000.0,
            availableBalance = 310000.0,
            earned = 645000.0,
            paid = 260000.0,
            pending = 75000.0,
            currency = "ر.ي"
        )
    )
    val vendorFinance: StateFlow<VendorFinance> = _vendorFinance.asStateFlow()

    private val _vendorPayouts = MutableStateFlow<List<VendorPayoutRequest>>(
        listOf(
            VendorPayoutRequest(
                id = "PO-9912",
                amount = 150000.0,
                currency = "ر.ي",
                reference = "حوالة الكريمي - فرع حدة (770123456)",
                date = "2026/08/28",
                status = "paid"
            ),
            VendorPayoutRequest(
                id = "PO-9954",
                amount = 110000.0,
                currency = "ر.ي",
                reference = "شبكة النجم للحوالات (770123456)",
                date = "2026/09/01",
                status = "approved"
            ),
            VendorPayoutRequest(
                id = "PO-9988",
                amount = 75000.0,
                currency = "ر.ي",
                reference = "سحب إلى محفظة جيب الإلكترونية",
                date = "2026/09/03",
                status = "pending"
            )
        )
    )
    val vendorPayouts: StateFlow<List<VendorPayoutRequest>> = _vendorPayouts.asStateFlow()

    fun requestVendorPayout(amount: Double, reference: String): Boolean {
        if (amount <= 0 || amount > _vendorFinance.value.availableBalance) return false
        val newReq = VendorPayoutRequest(
            id = "PO-${(1000..9999).random()}",
            amount = amount,
            currency = "ر.ي",
            reference = reference,
            date = SimpleDateFormat("yyyy/MM/dd", Locale.US).format(Date()),
            status = "pending"
        )
        _vendorPayouts.value = listOf(newReq) + _vendorPayouts.value
        _vendorFinance.value = _vendorFinance.value.copy(
            availableBalance = _vendorFinance.value.availableBalance - amount,
            pending = _vendorFinance.value.pending + amount
        )
        return true
    }

    fun addVendorProduct(
        name: String,
        description: String,
        priceYer: Double,
        category: String,
        stock: Int,
        badge: String?
    ) {
        val newProduct = Product(
            id = (_products.value.maxOfOrNull { it.id } ?: 100) + 1,
            storeId = 1,
            storeName = "روائع العود والعطور",
            name = name,
            description = description,
            priceYer = priceYer,
            originalPriceYer = priceYer * 1.25,
            category = category,
            rating = 5.0,
            inStock = stock > 0,
            badge = badge,
            images = listOf("https://images.unsplash.com/photo-1594035910387-fea47794261f?w=600"),
            reviewsCount = 1
        )
        _products.value = listOf(newProduct) + _products.value
    }

    fun updateOrderStatus(orderId: String, newStatus: String, newStep: Int) {
        _orders.value = _orders.value.map { order ->
            if (order.id == orderId) {
                order.copy(status = newStatus, statusStep = newStep)
            } else {
                order
            }
        }
    }

    init {
        fetchStoresAndProductsFromApi()
    }

    companion object {
        val instance by lazy { StoreRepository() }

        fun resolveMediaUrl(rawUrl: String?, baseUrl: String, fallbackUrl: String): String {
            if (rawUrl.isNullOrBlank()) return fallbackUrl
            val trimmed = rawUrl.trim()
            val rootDomain = if (baseUrl.contains("/api")) baseUrl.substringBefore("/api").trimEnd('/') else baseUrl.trimEnd('/')
            return when {
                trimmed.startsWith("http://127.0.0.1") || trimmed.startsWith("http://localhost") -> {
                    val path = if (trimmed.contains(":8000")) trimmed.substringAfter(":8000") else trimmed.substringAfter("localhost")
                    "$rootDomain$path"
                }
                trimmed.startsWith("http://") || trimmed.startsWith("https://") -> trimmed
                trimmed.startsWith("/") -> "$rootDomain$trimmed"
                else -> "$rootDomain/$trimmed"
            }
        }

        fun getCategoryFallbackImageUrl(category: String, name: String = ""): String {
            val lowCat = category.lowercase()
            val lowName = name.lowercase()
            return when {
                lowCat.contains("إلكترونيات") || lowCat.contains("electronic") || lowName.contains("آيفون") || lowName.contains("iphone") || lowName.contains("هاتف") -> 
                    "https://images.unsplash.com/photo-1511707171634-5f897ff02aa9?w=600"
                lowName.contains("لابتوب") || lowName.contains("laptop") || lowName.contains("ماك") ->
                    "https://images.unsplash.com/photo-1496181133206-80ce9b88a853?w=600"
                lowName.contains("سماعة") || lowName.contains("headphone") || lowName.contains("earphone") ->
                    "https://images.unsplash.com/photo-1505740420928-5e560c06d30e?w=600"
                lowName.contains("ساعة") || lowName.contains("watch") ->
                    "https://images.unsplash.com/photo-1523275335684-37898b6baf30?w=600"
                lowCat.contains("ملابس") || lowCat.contains("fashion") || lowCat.contains("أزياء") ->
                    "https://images.unsplash.com/photo-1445205170230-053b83016050?w=600"
                lowCat.contains("مأكولات") || lowCat.contains("سوبر") || lowCat.contains("طعام") || lowCat.contains("supermarket") ->
                    "https://images.unsplash.com/photo-1542838132-92c53300491e?w=600"
                lowCat.contains("عطور") || lowCat.contains("جمال") || lowCat.contains("عناية") || lowCat.contains("perfume") ->
                    "https://images.unsplash.com/photo-1523293182086-7651a899d37f?w=600"
                lowCat.contains("ألعاب") || lowCat.contains("game") || lowName.contains("بلايستيشن") ->
                    "https://images.unsplash.com/photo-1600080972464-8e5f35f63d08?w=600"
                lowCat.contains("منزل") || lowCat.contains("home") ->
                    "https://images.unsplash.com/photo-1556911220-e15b29be8c8f?w=600"
                else ->
                    "https://images.unsplash.com/photo-1526170375885-4d8ecf77b99f?w=600"
            }
        }
    }
}
