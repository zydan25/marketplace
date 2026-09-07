package com.example.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.SessionStore
import com.example.data.model.*
import com.example.data.remote.NetworkClient
import com.example.data.remote.ServiceRequestPayload
import com.example.data.repository.StoreRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.text.DecimalFormat
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale
import java.util.UUID

enum class ScreenTab {
    HOME, STORES, CART, FAVORITES, ACCOUNT, ORDERS, CATEGORIES, PAYMENT_NETWORK,
    PRODUCT_DETAIL, TRENDS, SEARCH, ADDRESSES, INVITE, SUPPORT, SETTINGS,
    VENDOR_PORTAL, ADMIN_PORTAL, SERVICES, NETWORK_CARDS, GAMES_CARDS,
    PROGRAMS_CARDS, REGISTER, LOGIN, TRANSFER
}

class MainViewModel(
    private val repository: StoreRepository = StoreRepository.instance
) : ViewModel() {

    private val numberFormat = DecimalFormat("#,###")

    fun formatMoney(amount: Double): String = numberFormat.format(amount)

    private val _selectedTab = MutableStateFlow(ScreenTab.HOME)
    val selectedTab: StateFlow<ScreenTab> = _selectedTab.asStateFlow()
    fun selectTab(tab: ScreenTab) { _selectedTab.value = tab }

    private val _selectedProduct = MutableStateFlow<Product?>(null)
    val selectedProduct: StateFlow<Product?> = _selectedProduct.asStateFlow()
    val selectedProductDetail: StateFlow<Product?> = _selectedProduct.asStateFlow()
    fun openProductDetail(product: Product) { _selectedProduct.value = product; _selectedTab.value = ScreenTab.PRODUCT_DETAIL }
    fun closeProductDetail() { _selectedProduct.value = null; if (_selectedTab.value == ScreenTab.PRODUCT_DETAIL) _selectedTab.value = ScreenTab.HOME }

    private val _activeStoreChat = MutableStateFlow<Store?>(null)
    val activeStoreChat: StateFlow<Store?> = _activeStoreChat.asStateFlow()
    private val _storeChatMessages = MutableStateFlow<Map<Int, List<OrderChatMessage>>>(emptyMap())
    val storeChatMessages: StateFlow<Map<Int, List<OrderChatMessage>>> = _storeChatMessages.asStateFlow()
    fun openStoreChat(store: Store) {
        _activeStoreChat.value = store
        if (!_storeChatMessages.value.containsKey(store.id)) {
            _storeChatMessages.value = _storeChatMessages.value + (store.id to listOf(OrderChatMessage("init_st_${store.id}", store.name, "أهلاً بك في متجرنا! يسعدنا الرد على أي استفسار حول المنتجات أو الأسعار والضمان 💬", "الآن", false)))
        }
    }
    fun closeStoreChat() { _activeStoreChat.value = null }
    fun sendStoreChatMessage(storeId: Int, text: String) {
        if (text.isBlank()) return
        val now = SimpleDateFormat("hh:mm a", Locale.getDefault()).format(Date())
        val userMsg = OrderChatMessage("user_st_${System.currentTimeMillis()}", "أنت", text.trim(), now, true)
        val current = _storeChatMessages.value[storeId].orEmpty()
        _storeChatMessages.value = _storeChatMessages.value + (storeId to (current + userMsg))
        viewModelScope.launch {
            delay(1000)
            val reply = OrderChatMessage("reply_st_${System.currentTimeMillis()}", _activeStoreChat.value?.name ?: "خدمة العملاء", when {
                text.contains("ضمان") -> "نعم، جميع منتجاتنا معتمدة بضمان الوكيل الرسمي والاستبدال الفوري!"
                text.contains("سعر") || text.contains("تخفيض") -> "الأسعار المعروضة شاملة الضريبة وأفضل عروض الخصم متوفرة في التطبيق!"
                text.contains("توصيل") -> "التوصيل يتم خلال نصف ساعة بطلبك عبر تطبيق شبيك!"
                else -> "شكراً لتواصلك! مندوب خدمة المتجر معك وسيقوم بخدمتك فوراً."
            }, now, false)
            _storeChatMessages.value = _storeChatMessages.value + (storeId to (_storeChatMessages.value[storeId].orEmpty() + reply))
        }
    }

    private val _isSyncing = MutableStateFlow(false)
    val isSyncing: StateFlow<Boolean> = _isSyncing.asStateFlow()
    fun syncBalance(onSynced: (Boolean, String) -> Unit = { _, _ -> }) {
        viewModelScope.launch {
            _isSyncing.value = true
            val result = repository.syncWalletFromServer()
            _isSyncing.value = false
            onSynced(result.first, result.second)
        }
    }
    fun syncWalletBalance(onSynced: (Boolean, String) -> Unit = { _, _ -> }) = syncBalance(onSynced)

    /** Server-authoritative recipient lookup. No synthetic recipient is ever created on-device. */
    suspend fun checkTransferEligibility(phone: String, amount: Double): TransferCheckResult {
        val cleanPhone = phone.trim()
        val token = userSession.value.token
        if (cleanPhone.isBlank()) return TransferCheckResult(false, recipientPhone = cleanPhone, amount = amount, message = "رقم المستلم مطلوب")
        if (amount <= 0) return TransferCheckResult(false, recipientPhone = cleanPhone, amount = amount, message = "المبلغ يجب أن يكون أكبر من صفر")
        if (token.isNullOrBlank()) return TransferCheckResult(false, recipientPhone = cleanPhone, amount = amount, message = "سجل الدخول أولاً")
        return withContext(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val response = NetworkClient.getApiService(djangoBaseUrl.value).lookupRecipient("Token $token", mapOf("receiver_phone" to cleanPhone))
                if (!response.isSuccessful || response.body() == null) return@withContext TransferCheckResult(false, recipientPhone = cleanPhone, amount = amount, message = "المشترك المستلم غير موجود")
                val body = response.body()!!
                val available = body["available_balance"]?.toString()?.toDoubleOrNull()
                if (available != null && available < amount) return@withContext TransferCheckResult(false, recipientPhone = cleanPhone, amount = amount, message = "الرصيد المحاسبي غير كافٍ")
                TransferCheckResult(true, body["receiver_name"]?.toString(), cleanPhone, amount, 0.0, null, "تم التحقق من المشترك. راجع البيانات ثم أكد التحويل.")
            } catch (e: Exception) {
                TransferCheckResult(false, recipientPhone = cleanPhone, amount = amount, message = "تعذر التحقق من المشترك: ${e.localizedMessage}")
            }
        }
    }

    suspend fun executeTransfer(phone: String, name: String, amount: Double): Pair<Boolean, WalletTransaction?> {
        val check = checkTransferEligibility(phone, amount)
        if (!check.isAllowed) return Pair(false, null)
        return confirmTransfer(check.giftId, phone, name, amount)
    }

    /** Transfer is committed on Django/accounting first; local UI changes only after a confirmed response. */
    suspend fun confirmTransfer(giftId: Int?, recipientPhone: String, recipientName: String, amount: Double): Pair<Boolean, WalletTransaction?> {
        val token = userSession.value.token ?: return Pair(false, null)
        return withContext(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val api = NetworkClient.getApiService(djangoBaseUrl.value)
                val id = giftId ?: run {
                    val created = api.createGift("Token $token", mapOf("receiver_phone" to recipientPhone.trim(), "amount" to amount, "message" to "تحويل مالي إلى مشترك"))
                    if (!created.isSuccessful || created.body() == null) return@withContext Pair(false, null)
                    created.body()!!["id"]?.toString()?.toIntOrNull() ?: return@withContext Pair(false, null)
                }
                val response = api.confirmGift("Token $token", id)
                if (!response.isSuccessful || response.body() == null) return@withContext Pair(false, null)
                repository.syncWalletFromServer()
                val ref = response.body()!!["journal"]?.toString() ?: "GIFT-$id"
                val tx = WalletTransaction(ref, "تحويل مالي إلى $recipientName", "TRANSFER", amount, "ر.ي", "الآن", false, recipientName, recipientPhone, ref, "ناجحة ومكتملة ✅", 0.0, "تم تأكيد التحويل محاسبياً من الخادم")
                _transactions.value = listOf(tx) + _transactions.value
                showTransferDialog.value = false
                Pair(true, tx)
            } catch (_: Exception) {
                Pair(false, null)
            }
        }
    }

    suspend fun cancelTransfer(giftId: Int?): Boolean {
        val token = userSession.value.token ?: return false
        val id = giftId ?: return false
        return withContext(kotlinx.coroutines.Dispatchers.IO) {
            runCatching { NetworkClient.getApiService(djangoBaseUrl.value).cancelGift("Token $token", id).isSuccessful }.getOrDefault(false)
        }
    }

    suspend fun feedWalletViaServer(phone: String, amount: Double, code: String): Pair<Boolean, String> {
        val result = repository.feedWalletViaServer(phone, amount, code)
        if (result.first) showDepositDialog.value = false
        return result
    }

    fun markNotificationAsRead(id: String) = repository.markNotificationAsRead(id)
    fun markAllNotificationsAsRead() = repository.markAllNotificationsAsRead()

    fun feedAccount(sourceName: String, phone: String, amount: Double, code: String): Boolean {
        val success = repository.feedWalletViaGateway(sourceName, phone, amount, code)
        if (success) showOrderSuccessDialog.value = "تمت تغذية حسابك بنجاح بمبلغ ${formatMoney(amount)} ر.ي عبر $sourceName!"
        return success
    }

    val telecomPackages = repository.telecomPackages

    fun payTelecom(phone: String, operatorName: String, category: String, packageName: String, amount: Double): Pair<Boolean, String> {
        // Keep the legacy callback API for old telecom screens. The primary customer flow is DynamicServicesScreen,
        // which always submits the selected service/item to /api/v2/services/requests/ using the server catalog.
        val result = repository.payTelecomRecharge(phone, operatorName, category, packageName, amount)
        if (result.first) showOrderSuccessDialog.value = result.second
        return result
    }

    suspend fun feedWalletAccount(phone: String, amount: Double, code: String): Pair<Boolean, String> = repository.feedWalletViaServer(phone, amount, code)
    fun executeTelecomPayment(phone: String, operatorName: String, category: String, packageName: String, amount: Double): Pair<Boolean, String> = payTelecom(phone, operatorName, category, packageName, amount)

    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()
    fun updateSearchQuery(query: String) { _searchQuery.value = query }
    private val _selectedCategory = MutableStateFlow("all")
    val selectedCategory: StateFlow<String> = _selectedCategory.asStateFlow()
    private val _selectedSubCategory = MutableStateFlow("الكل")
    val selectedSubCategory: StateFlow<String> = _selectedSubCategory.asStateFlow()
    fun selectCategory(categoryId: String) { _selectedCategory.value = categoryId; _selectedSubCategory.value = "الكل" }
    fun selectSubCategory(subCategory: String) { _selectedSubCategory.value = subCategory }
    fun openCategories(initialCategory: String = "all", initialSubCategory: String = "الكل") { selectCategory(initialCategory); selectSubCategory(initialSubCategory); _selectedTab.value = ScreenTab.CATEGORIES }

    private val _selectedStoreId = MutableStateFlow<Int?>(null)
    val selectedStoreId: StateFlow<Int?> = _selectedStoreId.asStateFlow()
    fun selectStore(storeId: Int?) { _selectedStoreId.value = storeId }

    fun openProductById(productId: Int) { repository.products.value.firstOrNull { it.id == productId }?.let(::openProductDetail) }
    fun openProductForOrderItem(item: OrderItemDetail) {
        val product = item.productId?.let { id -> repository.products.value.firstOrNull { it.id == id } }
            ?: repository.products.value.firstOrNull { it.name.trim() == item.productName.trim() }
            ?: repository.products.value.firstOrNull { it.category == item.category }
        if (product != null) openProductDetail(product)
    }
    fun reorderItem(item: OrderItemDetail) { repository.products.value.firstOrNull { it.id == item.productId }?.let { repository.addToCart(it); showOrderSuccessDialog.value = "تمت إضافة '${it.name}' إلى السلة بنجاح!" } }
    fun getRelatedProducts(product: Product): List<Product> = repository.products.value.filter { it.id != product.id && (it.category == product.category || (it.subCategory.isNotBlank() && it.subCategory == product.subCategory)) }.take(6)
    fun getCategoryTitle(catId: String): String = repository.categories.firstOrNull { it.id == catId }?.title ?: catId

    private val _selectedOrderId = MutableStateFlow<String?>(null)
    val selectedOrderId: StateFlow<String?> = _selectedOrderId.asStateFlow()
    private val _selectedChatOrderId = MutableStateFlow<String?>(null)
    val selectedChatOrderId: StateFlow<String?> = _selectedChatOrderId.asStateFlow()
    fun openOrderDetails(orderId: String) { _selectedOrderId.value = orderId }
    fun closeOrderDetails() { _selectedOrderId.value = null }
    fun openOrderChat(orderId: String) { _selectedChatOrderId.value = orderId }
    fun closeOrderChat() { _selectedChatOrderId.value = null }
    fun openPaymentNetwork() { _selectedTab.value = ScreenTab.PAYMENT_NETWORK }

    val showNotificationsDialog = MutableStateFlow(false)
    val showLoginDialog = MutableStateFlow(false)
    val showDepositDialog = MutableStateFlow(false)
    val showTransferDialog = MutableStateFlow(false)
    val showDjangoSettingsDialog = MutableStateFlow(false)
    val showOrderSuccessDialog = MutableStateFlow<String?>(null)

    val banners = repository.banners
    val categoriesState: StateFlow<List<CategoryItem>> = repository.categoriesState
    val categories = repository.categories
    val stores: StateFlow<List<Store>> = repository.stores
    val products: StateFlow<List<Product>> = repository.products
    val cart: StateFlow<List<CartItem>> = repository.cart
    val favorites: StateFlow<Set<Int>> = repository.favorites
    val notifications: StateFlow<List<AppNotification>> = repository.notifications
    val walletAccount: StateFlow<WalletAccount> = repository.walletAccount
    private val _transactions = MutableStateFlow<List<WalletTransaction>>(emptyList())
    val transactions: StateFlow<List<WalletTransaction>> = combine(_transactions, repository.transactions) { local, remote -> (local + remote).distinctBy { it.id } }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), repository.transactions.value)
    val orders: StateFlow<List<StoreOrder>> = repository.orders
    val userSession: StateFlow<UserSession> = repository.userSession
    private val _wifiNetworks = MutableStateFlow<List<WifiNetwork>>(emptyList())
    val wifiNetworks: StateFlow<List<WifiNetwork>> = _wifiNetworks.asStateFlow()
    private val _purchasedWifiCards = MutableStateFlow<List<PurchasedWifiCard>>(emptyList())
    val purchasedWifiCards: StateFlow<List<PurchasedWifiCard>> = _purchasedWifiCards.asStateFlow()
    val djangoBaseUrl: StateFlow<String> = repository.djangoBaseUrl
    val addresses = repository.addresses
    val supportTickets = repository.supportTickets
    val supportChatMessages = repository.supportChatMessages
    val referralCode = repository.referralCode
    val invitedCount = repository.invitedCount
    val referralRewardYer = repository.referralRewardYer
    val selectedCurrency = repository.selectedCurrency
    val notificationsEnabled = repository.notificationsEnabled
    val currencyRates = repository.currencyRates
    val vendorFinance = repository.vendorFinance
    val vendorPayouts = repository.vendorPayouts

    fun addAddress(address: UserAddress) = repository.addAddress(address)
    fun setDefaultAddress(id: Int) = repository.setDefaultAddress(id)
    fun deleteAddress(id: Int) = repository.deleteAddress(id)
    fun sendSupportMessage(msg: String) = repository.sendSupportMessage(msg)
    fun createSupportTicket(subject: String, category: String, details: String) = repository.createSupportTicket(subject, category, details)
    fun setSelectedCurrency(curr: String) = repository.setSelectedCurrency(curr)
    fun setNotificationsEnabled(enabled: Boolean) = repository.setNotificationsEnabled(enabled)
    fun requestVendorPayout(amount: Double, ref: String) = repository.requestVendorPayout(amount, ref)
    fun addVendorProduct(name: String, desc: String, price: Double, category: String, stock: Int, badge: String?) = repository.addVendorProduct(name, desc, price, category, stock, badge)
    fun updateOrderStatus(orderId: String, status: String, step: Int) = repository.updateOrderStatus(orderId, status, step)

    val filteredProducts: StateFlow<List<Product>> = combine(repository.products, _searchQuery, _selectedCategory, _selectedSubCategory, _selectedStoreId) { all, query, category, subCategory, storeId ->
        all.filter { product ->
            val q = query.isBlank() || product.name.contains(query, true) || product.description.contains(query, true) || product.brand.contains(query, true) || product.subCategory.contains(query, true) || product.storeName.contains(query, true)
            val c = category == "all" || product.category == category
            val s = subCategory == "الكل" || product.subCategory.isBlank() || product.subCategory == subCategory
            val st = storeId == null || product.storeId == storeId
            q && c && s && st
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val cartTotalYer: StateFlow<Double> = combine(repository.cart) { items -> items.first().sumOf { it.product.priceYer * it.quantity } }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), 0.0)
    val cartItemCount: StateFlow<Int> = combine(repository.cart) { items -> items.first().sumOf { it.quantity } }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), 0)
    fun addToCart(product: Product) = repository.addToCart(product)
    fun updateCartQuantity(productId: Int, delta: Int) = repository.updateCartQuantity(productId, delta)
    fun removeFromCart(productId: Int) = repository.removeFromCart(productId)
    fun toggleFavorite(productId: Int) = repository.toggleFavorite(productId)
    fun depositWallet(amount: Double) { repository.depositToWallet(amount); showDepositDialog.value = false }
    fun transferWallet(recipient: String, amount: Double): Boolean = repository.transferFromWallet(recipient, amount).also { if (it) showTransferDialog.value = false }
    fun checkoutWithWallet(storeName: String, deliveryAddress: String = "", orderNotes: String = ""): Boolean = repository.payOrderWithWallet(cartTotalYer.value, storeName, deliveryAddress, orderNotes).also { if (it) showOrderSuccessDialog.value = "تم دفع الطلب بنجاح وخصم ${formatMoney(cartTotalYer.value)} ر.ي من محفظة جيب!" }
    fun checkoutCash(storeName: String, deliveryAddress: String = "", orderNotes: String = "") { repository.checkoutCashOnDelivery(cartTotalYer.value, storeName, deliveryAddress, orderNotes); showOrderSuccessDialog.value = "تم تأكيد طلبك بنجاح! الدفع نقداً عند الاستلام لمندوب التوصيل." }
    fun checkoutCartWithDetails(storeName: String, deliveryAddress: String, orderNotes: String, isWallet: Boolean): Boolean = if (isWallet) checkoutWithWallet(storeName, deliveryAddress, orderNotes) else { checkoutCash(storeName, deliveryAddress, orderNotes); true }

    suspend fun updateOrderDetails(orderId: String, newAddress: String, newNotes: String): Boolean = repository.updateOrderDetails(orderId, newAddress, newNotes)
    suspend fun cancelOrder(orderId: String, reason: String = "إلغاء بناء على رغبة العميل"): Boolean = repository.cancelOrder(orderId, reason)
    fun syncWalletBalance() { viewModelScope.launch { repository.syncWalletFromServer() } }
    fun sendOrderChatMessage(orderId: String, text: String) { if (text.isNotBlank()) repository.addOrderChatMessage(orderId, text.trim()) }
    fun submitOrderReview(orderId: String, rating: Float, comment: String) { if (rating > 0 && comment.isNotBlank()) { repository.rateOrder(orderId, rating, comment.trim()); showOrderSuccessDialog.value = "شكراً لتقييمك! تم حفظ تقييمك ورأيك في الطلب بنجاح." } }

    suspend fun login(phone: String, pass: String): Pair<Boolean, String?> {
        val result = repository.loginWithPhoneAndPassword(phone, pass)
        if (result.first) {
            SessionStore.saveCredentials(phone, pass)
            showLoginDialog.value = false
            loadWifiData()
        }
        return result
    }

    suspend fun register(phone: String, pass: String, firstName: String, lastName: String, governorate: String): Pair<Boolean, String?> {
        val result = repository.registerUser(phone, pass, firstName, lastName, governorate)
        if (result.first) {
            SessionStore.saveCredentials(phone, pass)
            showLoginDialog.value = false
            loadWifiData()
        }
        return result
    }

    fun logout() { SessionStore.clear(); repository.logout() }
    fun setUserRole(role: String) = repository.setUserRole(role)
    fun updateDjangoUrl(url: String) { repository.updateDjangoBaseUrl(url); showDjangoSettingsDialog.value = false }

    private fun serviceApiUrl(): String {
        val base = djangoBaseUrl.value.trim().trimEnd('/')
        return when {
            base.endsWith("/api/v2") -> "$base/"
            base.endsWith("/api") -> "$base/v2/"
            else -> "$base/api/v2/"
        }
    }

    private fun loadWifiData() {
        viewModelScope.launch {
            try {
                val token = userSession.value.token ?: return@launch
                val api = NetworkClient.getApiService(serviceApiUrl())
                val networkResponse = api.getWifiNetworksV2()
                if (networkResponse.isSuccessful && networkResponse.body() != null) {
                    val rows = networkResponse.body()!!["networks"] as? List<*> ?: emptyList<Any>()
                    _wifiNetworks.value = rows.mapNotNull { raw ->
                        val n = raw as? Map<*, *> ?: return@mapNotNull null
                        val denoms = (n["denominations"] as? List<*>)?.mapNotNull { rawD ->
                            val d = rawD as? Map<*, *> ?: return@mapNotNull null
                            WifiCardDenomination(d["id"]?.toString().orEmpty(), d["name"]?.toString().orEmpty(), d["duration"]?.toString().orEmpty(), d["data_quota"]?.toString().orEmpty(), d["sale_price"]?.toString()?.toDoubleOrNull() ?: 0.0)
                        }.orEmpty()
                        WifiNetwork(n["id"]?.toString().orEmpty(), n["name"]?.toString().orEmpty(), n["owner_name"]?.toString().orEmpty(), n["owner_phone"]?.toString().orEmpty(), n["location"]?.toString().orEmpty(), n["governorate"]?.toString().orEmpty(), isOnline = true, description = n["description"]?.toString().orEmpty(), denominations = denoms)
                    }
                }
                val cardResponse = api.getMyWifiCardsV2("Token $token")
                if (cardResponse.isSuccessful && cardResponse.body() != null) {
                    val rows = cardResponse.body()!!["cards"] as? List<*> ?: emptyList<Any>()
                    _purchasedWifiCards.value = rows.mapNotNull { raw ->
                        val c = raw as? Map<*, *> ?: return@mapNotNull null
                        PurchasedWifiCard(c["id"]?.toString().orEmpty(), c["network_name"]?.toString().orEmpty(), c["denomination_title"]?.toString().orEmpty(), c["price"]?.toString()?.toDoubleOrNull() ?: 0.0, c["pin_code"]?.toString().orEmpty(), c["serial_number"]?.toString().orEmpty(), userSession.value.phone, c["purchase_date"]?.toString().orEmpty(), c["duration"]?.toString().orEmpty(), c["data_quota"]?.toString().orEmpty(), c["owner_phone"]?.toString().orEmpty())
                    }
                }
            } catch (_: Exception) {}
        }
    }

    suspend fun purchaseWifiCard(network: WifiNetwork, denomination: WifiCardDenomination, userPhone: String): PurchasedWifiCard? {
        val token = userSession.value.token ?: return null
        val denominationId = denomination.id.toIntOrNull() ?: return null
        return withContext(kotlinx.coroutines.Dispatchers.IO) {
            try {
                val response = NetworkClient.getApiService(serviceApiUrl()).purchaseWifiCardV2("Token $token", mapOf("denomination_id" to denominationId, "amount" to denomination.priceYer, "phone" to userPhone.trim()))
                if (!response.isSuccessful || response.body() == null) return@withContext null
                val c = response.body()!!
                val card = PurchasedWifiCard(c["id"]?.toString().orEmpty(), c["network_name"]?.toString() ?: network.name, c["denomination"]?.toString() ?: denomination.title, c["price"]?.toString()?.toDoubleOrNull() ?: denomination.priceYer, c["pin"]?.toString().orEmpty(), c["card_number"]?.toString().orEmpty(), userPhone.trim(), c["sold_at"]?.toString().orEmpty(), denomination.duration, denomination.dataQuota, network.ownerPhone)
                _purchasedWifiCards.value = listOf(card) + _purchasedWifiCards.value
                repository.syncWalletFromServer()
                showOrderSuccessDialog.value = "تم شراء كرت وايفاي بنجاح! كود الكرت: ${card.pinCode}"
                card
            } catch (_: Exception) { null }
        }
    }

    init {
        val saved = runCatching { SessionStore.loadCredentials() }.getOrNull()
        if (saved != null) {
            viewModelScope.launch {
                val result = repository.loginWithPhoneAndPassword(saved.phone, saved.password)
                if (!result.first) SessionStore.clear() else loadWifiData()
            }
        }
        loadWifiData()
    }
}
