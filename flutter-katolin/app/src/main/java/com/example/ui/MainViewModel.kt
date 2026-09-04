package com.example.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.example.data.model.*
import com.example.data.repository.StoreRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.text.DecimalFormat
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

enum class ScreenTab {
    HOME,
    STORES,
    CART,
    FAVORITES,
    ACCOUNT,
    ORDERS,
    CATEGORIES,
    PAYMENT_NETWORK,
    PRODUCT_DETAIL,
    TRENDS,
    SEARCH,
    ADDRESSES,
    INVITE,
    SUPPORT,
    SETTINGS,
    VENDOR_PORTAL,
    ADMIN_PORTAL,
    SERVICES,
    NETWORK_CARDS,
    GAMES_CARDS,
    PROGRAMS_CARDS,
    REGISTER,
    LOGIN,
    TRANSFER
}

class MainViewModel(
    private val repository: StoreRepository = StoreRepository.instance
) : ViewModel() {

    private val numberFormat = DecimalFormat("#,###")

    fun formatMoney(amount: Double): String {
        return numberFormat.format(amount)
    }

    // Active bottom navigation tab
    private val _selectedTab = MutableStateFlow(ScreenTab.HOME)
    val selectedTab: StateFlow<ScreenTab> = _selectedTab.asStateFlow()

    fun selectTab(tab: ScreenTab) {
        _selectedTab.value = tab
    }

    // Selected product for ProductDetailScreen
    private val _selectedProduct = MutableStateFlow<Product?>(null)
    val selectedProduct: StateFlow<Product?> = _selectedProduct.asStateFlow()
    val selectedProductDetail: StateFlow<Product?> = _selectedProduct.asStateFlow()

    fun openProductDetail(product: Product) {
        _selectedProduct.value = product
        _selectedTab.value = ScreenTab.PRODUCT_DETAIL
    }

    fun closeProductDetail() {
        _selectedProduct.value = null
        if (_selectedTab.value == ScreenTab.PRODUCT_DETAIL) {
            _selectedTab.value = ScreenTab.HOME
        }
    }

    // Categories screen navigation
    fun openCategories(initialCategory: String = "all", initialSubCategory: String = "الكل") {
        _selectedCategory.value = initialCategory
        _selectedSubCategory.value = initialSubCategory
        _selectedTab.value = ScreenTab.CATEGORIES
    }

    // Payment network navigation
    fun openPaymentNetwork() {
        _selectedTab.value = ScreenTab.PAYMENT_NETWORK
    }

    // Store Chat
    private val _activeStoreChat = MutableStateFlow<Store?>(null)
    val activeStoreChat: StateFlow<Store?> = _activeStoreChat.asStateFlow()

    private val _storeChatMessages = MutableStateFlow<Map<Int, List<OrderChatMessage>>>(emptyMap())
    val storeChatMessages: StateFlow<Map<Int, List<OrderChatMessage>>> = _storeChatMessages.asStateFlow()

    fun openStoreChat(store: Store) {
        _activeStoreChat.value = store
        if (!_storeChatMessages.value.containsKey(store.id)) {
            val initial = listOf(
                OrderChatMessage(
                    id = "init_st_${store.id}",
                    senderName = store.name,
                    message = "أهلاً بك في متجرنا! يسعدنا الرد على أي استفسار حول المنتجات أو الأسعار والضمان 💬",
                    time = "الآن",
                    isFromUser = false
                )
            )
            _storeChatMessages.value = _storeChatMessages.value + (store.id to initial)
        }
    }

    fun closeStoreChat() {
        _activeStoreChat.value = null
    }

    fun sendStoreChatMessage(storeId: Int, text: String) {
        if (text.isBlank()) return
        val sdf = SimpleDateFormat("hh:mm a", Locale.getDefault())
        val timeNow = sdf.format(Date())
        val userMsg = OrderChatMessage(
            id = "user_st_${System.currentTimeMillis()}",
            senderName = "أنت",
            message = text.trim(),
            time = timeNow,
            isFromUser = true
        )
        val currentList = _storeChatMessages.value[storeId] ?: emptyList()
        val updated = currentList + userMsg
        _storeChatMessages.value = _storeChatMessages.value + (storeId to updated)

        // Store automated reply
        viewModelScope.launch {
            delay(1000)
            val replyMsg = OrderChatMessage(
                id = "reply_st_${System.currentTimeMillis()}",
                senderName = _activeStoreChat.value?.name ?: "خدمة العملاء",
                message = when {
                    text.contains("ضمان") -> "نعم، جميع منتجاتنا معتمدة بضمان الوكيل الرسمي والاستبدال الفوري!"
                    text.contains("سعر") || text.contains("تخفيض") -> "الأسعار المعروضة شاملة الضريبة وأفضل عروض الخصم متوفرة في التطبيق!"
                    text.contains("توصيل") -> "التوصيل يتم خلال نصف ساعة بطلبك عبر تطبيق شبيك!"
                    else -> "شكراً لتواصلك! مندوب خدمة المتجر معك وسيقوم بخدمتك فوراً."
                },
                time = timeNow,
                isFromUser = false
            )
            val withReply = (_storeChatMessages.value[storeId] ?: emptyList()) + replyMsg
            _storeChatMessages.value = _storeChatMessages.value + (storeId to withReply)
        }
    }

    // Sync wallet balance
    private val _isSyncing = MutableStateFlow(false)
    val isSyncing: StateFlow<Boolean> = _isSyncing.asStateFlow()

    fun syncBalance(onSynced: (Boolean, String) -> Unit = { _, _ -> }) {
        viewModelScope.launch {
            _isSyncing.value = true
            val (success, msg) = repository.syncWalletFromServer()
            _isSyncing.value = false
            onSynced(success, msg)
        }
    }

    fun syncWalletBalance(onSynced: (Boolean, String) -> Unit = { _, _ -> }) {
        syncBalance(onSynced)
    }

    suspend fun checkTransferEligibility(phone: String, amount: Double): TransferCheckResult {
        return repository.checkTransferEligibility(phone, amount)
    }

    suspend fun executeTransfer(phone: String, name: String, amount: Double): Pair<Boolean, WalletTransaction?> {
        val result = repository.executeTransfer(phone, name, amount)
        if (result.first) {
            showTransferDialog.value = false
        }
        return result
    }

    suspend fun feedWalletViaServer(phone: String, amount: Double, code: String): Pair<Boolean, String> {
        val result = repository.feedWalletViaServer(phone, amount, code)
        if (result.first) {
            showDepositDialog.value = false
        }
        return result
    }

    fun markNotificationAsRead(id: String) {
        repository.markNotificationAsRead(id)
    }

    fun markAllNotificationsAsRead() {
        repository.markAllNotificationsAsRead()
    }

    // Feed account via gateway
    fun feedAccount(sourceName: String, phone: String, amount: Double, code: String): Boolean {
        val success = repository.feedWalletViaGateway(sourceName, phone, amount, code)
        if (success) {
            showOrderSuccessDialog.value = "تمت تغذية حسابك بنجاح بمبلغ ${formatMoney(amount)} ر.ي عبر $sourceName!"
        }
        return success
    }

    // Telecom payment
    val telecomPackages = repository.telecomPackages

    fun payTelecom(
        phone: String,
        operatorName: String,
        category: String,
        packageName: String,
        amount: Double
    ): Pair<Boolean, String> {
        val result = repository.payTelecomRecharge(phone, operatorName, category, packageName, amount)
        if (result.first) {
            showOrderSuccessDialog.value = result.second
        }
        return result
    }

    suspend fun feedWalletAccount(phone: String, amount: Double, code: String): Pair<Boolean, String> {
        return repository.feedWalletViaServer(phone, amount, code)
    }

    fun executeTelecomPayment(
        phone: String,
        operatorName: String,
        category: String,
        packageName: String,
        amount: Double
    ): Pair<Boolean, String> {
        return payTelecom(phone, operatorName, category, packageName, amount)
    }

    // Search query
    private val _searchQuery = MutableStateFlow("")
    val searchQuery: StateFlow<String> = _searchQuery.asStateFlow()

    fun updateSearchQuery(query: String) {
        _searchQuery.value = query
    }

    // Selected category filter
    private val _selectedCategory = MutableStateFlow("all")
    val selectedCategory: StateFlow<String> = _selectedCategory.asStateFlow()

    // Selected subcategory filter
    private val _selectedSubCategory = MutableStateFlow("الكل")
    val selectedSubCategory: StateFlow<String> = _selectedSubCategory.asStateFlow()

    fun selectCategory(categoryId: String) {
        _selectedCategory.value = categoryId
        _selectedSubCategory.value = "الكل"
    }

    fun selectSubCategory(subCategory: String) {
        _selectedSubCategory.value = subCategory
    }

    // Selected store filter for Store Detail view
    private val _selectedStoreId = MutableStateFlow<Int?>(null)
    val selectedStoreId: StateFlow<Int?> = _selectedStoreId.asStateFlow()

    fun selectStore(storeId: Int?) {
        _selectedStoreId.value = storeId
    }

    // Matching and navigating to Product from Order or Category
    fun openProductById(productId: Int) {
        val prod = repository.products.value.firstOrNull { it.id == productId }
        if (prod != null) {
            openProductDetail(prod)
        }
    }

    fun openProductForOrderItem(item: OrderItemDetail) {
        val prod = if (item.productId != null) {
            repository.products.value.firstOrNull { it.id == item.productId }
        } else {
            repository.products.value.firstOrNull { it.name.trim() == item.productName.trim() }
                ?: repository.products.value.firstOrNull { it.name.contains(item.productName.take(10)) }
                ?: repository.products.value.firstOrNull { it.category == item.category }
        }
        if (prod != null) {
            openProductDetail(prod)
        }
    }

    fun reorderItem(item: OrderItemDetail) {
        val prod = if (item.productId != null) {
            repository.products.value.firstOrNull { it.id == item.productId }
        } else {
            repository.products.value.firstOrNull { it.name.trim() == item.productName.trim() }
        }
        if (prod != null) {
            repository.addToCart(prod)
            showOrderSuccessDialog.value = "تمت إضافة '${prod.name}' إلى السلة بنجاح!"
        } else {
            val fallback = Product(
                id = item.productId ?: (9000..9999).random(),
                storeId = 1,
                storeName = item.storeName.ifBlank { "متجر شبيك" },
                name = item.productName,
                description = "صنف معاد طلبه من طلباتك السابقة",
                priceYer = item.priceYer,
                category = item.category.ifBlank { "all" },
                subCategory = item.subCategory
            )
            repository.addToCart(fallback)
            showOrderSuccessDialog.value = "تمت إضافة '${fallback.name}' إلى السلة بنجاح!"
        }
    }

    fun getRelatedProducts(product: Product): List<Product> {
        return repository.products.value.filter {
            it.id != product.id && (it.category == product.category || (it.subCategory.isNotBlank() && it.subCategory == product.subCategory))
        }.take(6)
    }

    fun getCategoryTitle(catId: String): String {
        return repository.categories.firstOrNull { it.id == catId }?.title ?: catId
    }

    // Active order selected for Details View
    private val _selectedOrderId = MutableStateFlow<String?>(null)
    val selectedOrderId: StateFlow<String?> = _selectedOrderId.asStateFlow()

    // Active order selected for Chat View
    private val _selectedChatOrderId = MutableStateFlow<String?>(null)
    val selectedChatOrderId: StateFlow<String?> = _selectedChatOrderId.asStateFlow()

    fun openOrderDetails(orderId: String) {
        _selectedOrderId.value = orderId
    }

    fun closeOrderDetails() {
        _selectedOrderId.value = null
    }

    fun openOrderChat(orderId: String) {
        _selectedChatOrderId.value = orderId
    }

    fun closeOrderChat() {
        _selectedChatOrderId.value = null
    }

    // UI Dialogs
    val showNotificationsDialog = MutableStateFlow(false)
    val showLoginDialog = MutableStateFlow(false)
    val showDepositDialog = MutableStateFlow(false)
    val showTransferDialog = MutableStateFlow(false)
    val showDjangoSettingsDialog = MutableStateFlow(false)
    val showOrderSuccessDialog = MutableStateFlow<String?>(null)

    // Data streams from repository
    val banners = repository.banners
    val categoriesState: StateFlow<List<CategoryItem>> = repository.categoriesState
    val categories = repository.categories
    val stores: StateFlow<List<Store>> = repository.stores
    val products: StateFlow<List<Product>> = repository.products
    val cart: StateFlow<List<CartItem>> = repository.cart
    val favorites: StateFlow<Set<Int>> = repository.favorites
    val notifications: StateFlow<List<AppNotification>> = repository.notifications
    val walletAccount: StateFlow<WalletAccount> = repository.walletAccount
    val transactions: StateFlow<List<WalletTransaction>> = repository.transactions
    val orders: StateFlow<List<StoreOrder>> = repository.orders
    val userSession: StateFlow<UserSession> = repository.userSession
    val wifiNetworks: StateFlow<List<WifiNetwork>> = repository.wifiNetworks
    val purchasedWifiCards: StateFlow<List<PurchasedWifiCard>> = repository.purchasedWifiCards
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

    fun addAddress(address: com.example.data.model.UserAddress) = repository.addAddress(address)
    fun setDefaultAddress(id: Int) = repository.setDefaultAddress(id)
    fun deleteAddress(id: Int) = repository.deleteAddress(id)
    fun sendSupportMessage(msg: String) = repository.sendSupportMessage(msg)
    fun createSupportTicket(subject: String, category: String, details: String) = repository.createSupportTicket(subject, category, details)
    fun setSelectedCurrency(curr: String) = repository.setSelectedCurrency(curr)
    fun setNotificationsEnabled(enabled: Boolean) = repository.setNotificationsEnabled(enabled)
    fun requestVendorPayout(amount: Double, ref: String) = repository.requestVendorPayout(amount, ref)
    fun addVendorProduct(name: String, desc: String, price: Double, category: String, stock: Int, badge: String?) = repository.addVendorProduct(name, desc, price, category, stock, badge)
    fun updateOrderStatus(orderId: String, status: String, step: Int) = repository.updateOrderStatus(orderId, status, step)

    // Filtered Products based on search query, category, subcategory, and store filter
    val filteredProducts: StateFlow<List<Product>> = combine(
        repository.products,
        _searchQuery,
        _selectedCategory,
        _selectedSubCategory,
        _selectedStoreId
    ) { products, query, category, subCategory, storeId ->
        products.filter { product ->
            val matchesQuery = query.isBlank() ||
                    product.name.contains(query, ignoreCase = true) ||
                    product.description.contains(query, ignoreCase = true) ||
                    product.brand.contains(query, ignoreCase = true) ||
                    product.subCategory.contains(query, ignoreCase = true) ||
                    product.storeName.contains(query, ignoreCase = true)

            val matchesCategory = category == "all" || product.category == category
            val matchesSubCategory = subCategory == "الكل" || product.subCategory.isBlank() || product.subCategory == subCategory
            val matchesStore = storeId == null || product.storeId == storeId

            matchesQuery && matchesCategory && matchesSubCategory && matchesStore
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    // Cart calculations
    val cartTotalYer: StateFlow<Double> = combine(repository.cart) { cartList ->
        cartList.first().sumOf { it.product.priceYer * it.quantity }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), 0.0)

    val cartItemCount: StateFlow<Int> = combine(repository.cart) { cartList ->
        cartList.first().sumOf { it.quantity }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), 0)

    // Actions
    fun addToCart(product: Product) {
        repository.addToCart(product)
    }

    fun updateCartQuantity(productId: Int, delta: Int) {
        repository.updateCartQuantity(productId, delta)
    }

    fun removeFromCart(productId: Int) {
        repository.removeFromCart(productId)
    }

    fun toggleFavorite(productId: Int) {
        repository.toggleFavorite(productId)
    }

    fun depositWallet(amount: Double) {
        repository.depositToWallet(amount)
        showDepositDialog.value = false
    }

    fun transferWallet(recipient: String, amount: Double): Boolean {
        val success = repository.transferFromWallet(recipient, amount)
        if (success) {
            showTransferDialog.value = false
        }
        return success
    }

    fun checkoutWithWallet(storeName: String, deliveryAddress: String = "", orderNotes: String = ""): Boolean {
        val total = cartTotalYer.value
        val success = repository.payOrderWithWallet(total, storeName, deliveryAddress, orderNotes)
        if (success) {
            showOrderSuccessDialog.value = "تم دفع الطلب بنجاح وخصم ${formatMoney(total)} ر.ي من محفظة جيب!"
        }
        return success
    }

    fun checkoutCash(storeName: String, deliveryAddress: String = "", orderNotes: String = "") {
        val total = cartTotalYer.value
        repository.checkoutCashOnDelivery(total, storeName, deliveryAddress, orderNotes)
        showOrderSuccessDialog.value = "تم تأكيد طلبك بنجاح! الدفع نقداً عند الاستلام لمندوب التوصيل."
    }

    fun checkoutCartWithDetails(storeName: String, deliveryAddress: String, orderNotes: String, isWallet: Boolean): Boolean {
        return if (isWallet) {
            checkoutWithWallet(storeName, deliveryAddress, orderNotes)
        } else {
            checkoutCash(storeName, deliveryAddress, orderNotes)
            true
        }
    }

    suspend fun checkTransferEligibility(recipientPhone: String, amount: Double, message: String = ""): TransferCheckResult {
        return repository.checkTransferEligibility(recipientPhone, amount, message)
    }

    suspend fun confirmTransfer(giftId: Int?, recipientPhone: String, recipientName: String, amount: Double): Pair<Boolean, WalletTransaction?> {
        return repository.confirmTransfer(giftId, recipientPhone, recipientName, amount)
    }

    suspend fun cancelTransfer(giftId: Int?): Boolean {
        return repository.cancelTransfer(giftId)
    }

    suspend fun feedWalletAccount(phone: String, amount: Double, code: String, method: String = "floosak", reference: String = ""): Pair<Boolean, String> {
        return repository.feedWalletViaServer(phone, amount, code, method, reference)
    }

    suspend fun updateOrderDetails(orderId: String, newAddress: String, newNotes: String): Boolean {
        return repository.updateOrderDetails(orderId, newAddress, newNotes)
    }

    suspend fun cancelOrder(orderId: String, reason: String = "إلغاء بناء على رغبة العميل"): Boolean {
        return repository.cancelOrder(orderId, reason)
    }

    fun syncWalletBalance() {
        viewModelScope.launch {
            repository.syncWalletFromServer()
        }
    }

    fun sendOrderChatMessage(orderId: String, text: String) {
        if (text.isNotBlank()) {
            repository.addOrderChatMessage(orderId, text.trim())
        }
    }

    fun submitOrderReview(orderId: String, rating: Float, comment: String) {
        if (comment.isNotBlank() && rating > 0) {
            repository.rateOrder(orderId, rating, comment.trim())
            showOrderSuccessDialog.value = "شكراً لتقييمك! تم حفظ تقييمك ورأيك في الطلب بنجاح."
        }
    }

    suspend fun login(phone: String, pass: String): Pair<Boolean, String?> {
        val (success, errorMsg) = repository.loginWithPhoneAndPassword(phone, pass)
        if (success) {
            showLoginDialog.value = false
        }
        return Pair(success, errorMsg)
    }

    suspend fun register(phone: String, pass: String, firstName: String, lastName: String, governorate: String): Pair<Boolean, String?> {
        val (success, errorMsg) = repository.registerUser(phone, pass, firstName, lastName, governorate)
        if (success) {
            showLoginDialog.value = false
        }
        return Pair(success, errorMsg)
    }

    suspend fun syncUserProfile(): Boolean {
        val res = repository.syncUserProfile()
        val token = userSession.value.token
        if (!token.isNullOrBlank()) {
            repository.fetchOrdersFromApi(token)
            repository.fetchNotificationsFromApi(token)
        }
        return res
    }

    fun purchaseWifiCard(
        network: WifiNetwork,
        denomination: WifiCardDenomination,
        userPhone: String
    ): PurchasedWifiCard {
        val card = repository.purchaseWifiCard(network, denomination, userPhone)
        showOrderSuccessDialog.value = "تم شراء كرت وايفاي بنجاح! كود الكرت: ${card.pinCode}"
        return card
    }

    fun setUserRole(role: String) {
        repository.setUserRole(role)
    }

    fun logout() {
        repository.logout()
    }

    fun updateDjangoUrl(url: String) {
        repository.updateDjangoBaseUrl(url)
        showDjangoSettingsDialog.value = false
    }
}
