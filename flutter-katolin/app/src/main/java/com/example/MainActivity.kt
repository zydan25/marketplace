package com.example

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.BackHandler
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawing
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.ShoppingCart
import androidx.compose.material.icons.filled.Storefront
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Badge
import androidx.compose.material3.BadgedBox
import androidx.compose.material3.Button
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalLayoutDirection
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.lifecycle.viewmodel.compose.viewModel
import kotlinx.coroutines.launch
import com.example.ui.AddressesScreen
import com.example.ui.AdminPortalScreen
import com.example.ui.CartScreen
import com.example.ui.CategoriesScreen
import com.example.ui.CategoryTabsBar
import com.example.ui.DepositDialog
import com.example.ui.DjangoSettingsDialog
import com.example.ui.FavoritesScreen
import com.example.ui.FeaturedStoresSection
import com.example.ui.FullLoginScreen
import com.example.ui.GamesScreen
import com.example.ui.HeroBannersSlider
import com.example.ui.JeebAccountScreen
import com.example.ui.LoginWithPhoneDialog
import com.example.ui.MainViewModel
import com.example.ui.NetworkCardsScreen
import com.example.ui.NotificationsDialog
import com.example.ui.OrderChatScreen
import com.example.ui.OrderDetailScreen
import com.example.ui.OrdersListScreen
import com.example.ui.PaddingHeader
import com.example.ui.PaymentNetworkScreen
import com.example.ui.ProductCard
import com.example.ui.ProductDetailScreen
import com.example.ui.ProgramsScreen
import com.example.ui.RegisterScreen
import com.example.ui.ScreenTab
import com.example.ui.ServicesScreen
import com.example.ui.SplashScreen
import com.example.ui.StoreChatDialog
import com.example.ui.StoresScreen
import com.example.ui.TopBarWithSearch
import com.example.ui.TransferDialog
import com.example.ui.TransferScreen
import com.example.ui.VendorPortalScreen
import com.example.ui.VisualCategoryCircles
import com.example.ui.theme.MyApplicationTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            MyApplicationTheme {
                // Ensure RTL layout direction for pristine Arabic typography and design
                CompositionLocalProvider(LocalLayoutDirection provides LayoutDirection.Rtl) {
                    MainAppScreen()
                }
            }
        }
    }
}

@Composable
fun MainAppScreen(
    viewModel: MainViewModel = viewModel()
) {
    var showSplash by rememberSaveable { mutableStateOf(true) }

    if (showSplash) {
        SplashScreen(
            onSplashFinished = { showSplash = false }
        )
        return
    }

    val selectedTab by viewModel.selectedTab.collectAsState()
    val searchQuery by viewModel.searchQuery.collectAsState()
    val selectedCategory by viewModel.selectedCategory.collectAsState()
    val selectedStoreId by viewModel.selectedStoreId.collectAsState()

    val cartItems by viewModel.cart.collectAsState()
    val cartCount by viewModel.cartItemCount.collectAsState()
    val cartTotalYer by viewModel.cartTotalYer.collectAsState()

    val favorites by viewModel.favorites.collectAsState()
    val notifications by viewModel.notifications.collectAsState()
    val stores by viewModel.stores.collectAsState()
    val filteredProducts by viewModel.filteredProducts.collectAsState()
    val allProducts by viewModel.products.collectAsState()
    val walletAccount by viewModel.walletAccount.collectAsState()
    val transactions by viewModel.transactions.collectAsState()
    val orders by viewModel.orders.collectAsState()
    val userSession by viewModel.userSession.collectAsState()
    val djangoBaseUrl by viewModel.djangoBaseUrl.collectAsState()

    val selectedOrderId by viewModel.selectedOrderId.collectAsState()
    val selectedChatOrderId by viewModel.selectedChatOrderId.collectAsState()
    val selectedProductDetail by viewModel.selectedProductDetail.collectAsState()
    val selectedSubCategory by viewModel.selectedSubCategory.collectAsState()
    val activeStoreChat by viewModel.activeStoreChat.collectAsState()
    val storeChatMessages by viewModel.storeChatMessages.collectAsState()

    // Dialog state collectors
    val showNotifications by viewModel.showNotificationsDialog.collectAsState()
    val showLogin by viewModel.showLoginDialog.collectAsState()
    val showDeposit by viewModel.showDepositDialog.collectAsState()
    val showTransfer by viewModel.showTransferDialog.collectAsState()
    val showDjangoSettings by viewModel.showDjangoSettingsDialog.collectAsState()
    val orderSuccessMessage by viewModel.showOrderSuccessDialog.collectAsState()

    val coroutineScope = rememberCoroutineScope()

    // Smart Back Button handling
    BackHandler(
        enabled = activeStoreChat != null ||
            selectedChatOrderId != null ||
            selectedOrderId != null ||
            selectedProductDetail != null ||
            selectedTab != ScreenTab.HOME
    ) {
        when {
            activeStoreChat != null -> viewModel.closeStoreChat()
            selectedChatOrderId != null -> viewModel.closeOrderChat()
            selectedOrderId != null -> viewModel.closeOrderDetails()
            selectedProductDetail != null -> viewModel.closeProductDetail()
            selectedTab == ScreenTab.PAYMENT_NETWORK -> viewModel.selectTab(ScreenTab.ACCOUNT)
            selectedTab == ScreenTab.SERVICES -> viewModel.selectTab(ScreenTab.ACCOUNT)
            selectedTab == ScreenTab.NETWORK_CARDS -> viewModel.selectTab(ScreenTab.SERVICES)
            selectedTab == ScreenTab.GAMES_CARDS -> viewModel.selectTab(ScreenTab.SERVICES)
            selectedTab == ScreenTab.PROGRAMS_CARDS -> viewModel.selectTab(ScreenTab.SERVICES)
            selectedTab == ScreenTab.LOGIN || selectedTab == ScreenTab.REGISTER -> viewModel.selectTab(ScreenTab.ACCOUNT)
            selectedTab == ScreenTab.PRODUCT_DETAIL -> viewModel.closeProductDetail()
            selectedTab == ScreenTab.CATEGORIES -> viewModel.selectTab(ScreenTab.HOME)
            selectedTab == ScreenTab.ORDERS -> viewModel.selectTab(ScreenTab.ACCOUNT)
            selectedTab == ScreenTab.TRANSFER -> viewModel.selectTab(ScreenTab.ACCOUNT)
            selectedTab == ScreenTab.ADDRESSES -> viewModel.selectTab(ScreenTab.ACCOUNT)
            selectedTab != ScreenTab.HOME -> viewModel.selectTab(ScreenTab.HOME)
        }
    }

    Scaffold(
        modifier = Modifier
            .fillMaxSize()
            .windowInsetsPadding(WindowInsets.safeDrawing),
        topBar = {
            // Search bar only visible on Home and Stores tabs; search field compact & exclusive to Home tab
            if (selectedTab == ScreenTab.HOME || selectedTab == ScreenTab.STORES) {
                TopBarWithSearch(
                    searchQuery = searchQuery,
                    onSearchQueryChange = { viewModel.updateSearchQuery(it) },
                    cartCount = cartCount,
                    favoritesCount = favorites.size,
                    notificationsCount = notifications.size,
                    onCartClick = { viewModel.selectTab(ScreenTab.CART) },
                    onFavoritesClick = { viewModel.selectTab(ScreenTab.FAVORITES) },
                    onNotificationsClick = { viewModel.showNotificationsDialog.value = true },
                    showSearchField = (selectedTab == ScreenTab.HOME)
                )
            }
        },
        bottomBar = {
            // Don't show bottom bar if in active order chat, payment network, login/register, or product detail
            if (selectedChatOrderId == null &&
                selectedTab != ScreenTab.PAYMENT_NETWORK &&
                selectedTab != ScreenTab.LOGIN &&
                selectedTab != ScreenTab.REGISTER &&
                selectedTab != ScreenTab.PRODUCT_DETAIL &&
                selectedProductDetail == null
            ) {
                NavigationBar(
                    modifier = Modifier
                        .windowInsetsPadding(WindowInsets.navigationBars)
                        .testTag("bottom_nav_bar"),
                    containerColor = MaterialTheme.colorScheme.surface,
                    tonalElevation = 8.dp
                ) {
                    // 1. Home
                    NavigationBarItem(
                        selected = selectedTab == ScreenTab.HOME,
                        onClick = {
                            viewModel.selectTab(ScreenTab.HOME)
                            viewModel.selectStore(null)
                        },
                        icon = {
                            Icon(
                                imageVector = Icons.Default.Home,
                                contentDescription = "الرئيسية"
                            )
                        },
                        label = { Text("الرئيسية", fontWeight = FontWeight.Bold) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            indicatorColor = MaterialTheme.colorScheme.primaryContainer
                        )
                    )

                    // 2. Stores
                    NavigationBarItem(
                        selected = selectedTab == ScreenTab.STORES,
                        onClick = { viewModel.selectTab(ScreenTab.STORES) },
                        icon = {
                            Icon(
                                imageVector = Icons.Default.Storefront,
                                contentDescription = "المتاجر"
                            )
                        },
                        label = { Text("المتاجر", fontWeight = FontWeight.Bold) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            indicatorColor = MaterialTheme.colorScheme.primaryContainer
                        )
                    )

                    // 3. Cart
                    NavigationBarItem(
                        selected = selectedTab == ScreenTab.CART,
                        onClick = { viewModel.selectTab(ScreenTab.CART) },
                        icon = {
                            BadgedBox(
                                badge = {
                                    if (cartCount > 0) {
                                        Badge(containerColor = MaterialTheme.colorScheme.primary) {
                                            Text("$cartCount")
                                        }
                                    }
                                }
                            ) {
                                Icon(
                                    imageVector = Icons.Default.ShoppingCart,
                                    contentDescription = "السلة"
                                )
                            }
                        },
                        label = { Text("السلة", fontWeight = FontWeight.Bold) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            indicatorColor = MaterialTheme.colorScheme.primaryContainer
                        )
                    )

                    // 4. Favorites
                    NavigationBarItem(
                        selected = selectedTab == ScreenTab.FAVORITES,
                        onClick = { viewModel.selectTab(ScreenTab.FAVORITES) },
                        icon = {
                            BadgedBox(
                                badge = {
                                    if (favorites.isNotEmpty()) {
                                        Badge(containerColor = MaterialTheme.colorScheme.tertiary) {
                                            Text("${favorites.size}")
                                        }
                                    }
                                }
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Favorite,
                                    contentDescription = "المفضلة"
                                )
                            }
                        },
                        label = { Text("المفضلة", fontWeight = FontWeight.Bold) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            indicatorColor = MaterialTheme.colorScheme.primaryContainer
                        )
                    )

                    // 5. Jeeb Wallet / Account
                    NavigationBarItem(
                        selected = selectedTab == ScreenTab.ACCOUNT || selectedTab == ScreenTab.ORDERS,
                        onClick = { viewModel.selectTab(ScreenTab.ACCOUNT) },
                        icon = {
                            Icon(
                                imageVector = Icons.Default.AccountBalanceWallet,
                                contentDescription = "حسابي"
                            )
                        },
                        label = { Text("حسابي", fontWeight = FontWeight.Bold) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            indicatorColor = MaterialTheme.colorScheme.primaryContainer
                        )
                    )
                }
            }
        }
    ) { innerPadding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            when (selectedTab) {
                ScreenTab.HOME -> {
                    HomeScreenBody(
                        viewModel = viewModel,
                        selectedCategory = selectedCategory,
                        stores = stores,
                        filteredProducts = filteredProducts,
                        favorites = favorites
                    )
                }

                ScreenTab.STORES -> {
                    StoresScreen(
                        stores = stores,
                        selectedStoreId = selectedStoreId,
                        products = filteredProducts,
                        favorites = favorites,
                        onSelectStore = { viewModel.selectStore(it) },
                        onProductClick = { viewModel.openProductDetail(it) },
                        onAddToCart = { viewModel.addToCart(it) },
                        onToggleFavorite = { viewModel.toggleFavorite(it) },
                        onOpenChatWithStore = { viewModel.openStoreChat(it) },
                        formatMoney = { viewModel.formatMoney(it) }
                    )
                }

                ScreenTab.CART -> {
                    val addressesList by viewModel.addresses.collectAsState()
                    CartScreen(
                        cartItems = cartItems,
                        walletAccount = walletAccount,
                        totalYer = cartTotalYer,
                        addresses = addressesList,
                        onUpdateQuantity = { id, delta -> viewModel.updateCartQuantity(id, delta) },
                        onRemoveItem = { id -> viewModel.removeFromCart(id) },
                        onCheckoutWithWallet = { storeName -> viewModel.checkoutWithWallet(storeName) },
                        onCheckoutCash = { storeName -> viewModel.checkoutCash(storeName) },
                        onCheckoutWithDetails = { storeName, addr, notes, isWallet ->
                            viewModel.checkoutCartWithDetails(storeName, addr, notes, isWallet)
                        },
                        onOpenAddresses = { viewModel.selectTab(ScreenTab.ADDRESSES) },
                        onDepositClick = { viewModel.showDepositDialog.value = true },
                        onExploreStores = { viewModel.selectTab(ScreenTab.STORES) },
                        formatMoney = { viewModel.formatMoney(it) }
                    )
                }

                ScreenTab.FAVORITES -> {
                    val favoriteProducts = filteredProducts.filter { favorites.contains(it.id) }
                    FavoritesScreen(
                        favoriteProducts = favoriteProducts,
                        onToggleFavorite = { viewModel.toggleFavorite(it) },
                        onAddToCart = { viewModel.addToCart(it) },
                        onExploreProducts = { viewModel.selectTab(ScreenTab.HOME) },
                        formatMoney = { viewModel.formatMoney(it) }
                    )
                }

                ScreenTab.ACCOUNT -> {
                    JeebAccountScreen(
                        userSession = userSession,
                        wallet = walletAccount,
                        transactions = transactions,
                        orders = orders,
                        djangoUrl = djangoBaseUrl,
                        formatMoney = { viewModel.formatMoney(it) },
                        onLoginClick = { viewModel.selectTab(ScreenTab.LOGIN) },
                        onRegisterClick = { viewModel.selectTab(ScreenTab.REGISTER) },
                        onLogoutClick = { viewModel.logout() },
                        onDepositClick = { viewModel.showDepositDialog.value = true },
                        onTransferClick = { viewModel.selectTab(ScreenTab.TRANSFER) },
                        onOrdersClick = { viewModel.selectTab(ScreenTab.ORDERS) },
                        onDjangoSettingsClick = { viewModel.showDjangoSettingsDialog.value = true },
                        onOpenPaymentNetwork = { viewModel.openPaymentNetwork() },
                        onSyncBalance = { viewModel.syncWalletBalance() },
                        onFeedAccountSubmit = { phone, amount, code ->
                            viewModel.feedWalletAccount(phone, amount, code)
                        },
                        onOpenServices = { viewModel.selectTab(ScreenTab.SERVICES) },
                        onOpenAddresses = { viewModel.selectTab(ScreenTab.ADDRESSES) },
                        onOpenNetworkCards = { viewModel.selectTab(ScreenTab.NETWORK_CARDS) },
                        onOpenGames = { viewModel.selectTab(ScreenTab.GAMES_CARDS) },
                        onOpenPrograms = { viewModel.selectTab(ScreenTab.PROGRAMS_CARDS) },
                        onOpenVendorPortal = { viewModel.selectTab(ScreenTab.VENDOR_PORTAL) },
                        onOpenAdminPortal = { viewModel.selectTab(ScreenTab.ADMIN_PORTAL) }
                    )
                }

                ScreenTab.SERVICES -> {
                    ServicesScreen(
                        userSession = userSession,
                        onBackClick = { viewModel.selectTab(ScreenTab.ACCOUNT) },
                        onNavigateToNetworkCards = { viewModel.selectTab(ScreenTab.NETWORK_CARDS) },
                        onNavigateToGames = { viewModel.selectTab(ScreenTab.GAMES_CARDS) },
                        onNavigateToPrograms = { viewModel.selectTab(ScreenTab.PROGRAMS_CARDS) },
                        formatMoney = { viewModel.formatMoney(it) },
                        onPayBill = { billName, amount, accountNo ->
                            viewModel.executeTelecomPayment(accountNo, "سداد خدمات", billName, "سداد فاتورة $billName", amount)
                        }
                    )
                }

                ScreenTab.NETWORK_CARDS -> {
                    val wifiNetworks by viewModel.wifiNetworks.collectAsState()
                    val purchasedWifiCards by viewModel.purchasedWifiCards.collectAsState()
                    NetworkCardsScreen(
                        userSession = userSession,
                        wifiNetworks = wifiNetworks,
                        purchasedWifiCards = purchasedWifiCards,
                        onBackClick = { viewModel.selectTab(ScreenTab.SERVICES) },
                        formatMoney = { viewModel.formatMoney(it) },
                        onPurchaseWifiCard = { network, denomination, targetPhone ->
                            viewModel.purchaseWifiCard(network, denomination, targetPhone)
                        }
                    )
                }

                ScreenTab.GAMES_CARDS -> {
                    GamesScreen(
                        userSession = userSession,
                        onBackClick = { viewModel.selectTab(ScreenTab.SERVICES) },
                        formatMoney = { viewModel.formatMoney(it) },
                        onRechargeGame = { gameName, packName, price, playerId ->
                            viewModel.executeTelecomPayment(playerId, gameName, "شحن ألعاب", packName, price)
                        }
                    )
                }

                ScreenTab.PROGRAMS_CARDS -> {
                    ProgramsScreen(
                        userSession = userSession,
                        onBackClick = { viewModel.selectTab(ScreenTab.SERVICES) },
                        formatMoney = { viewModel.formatMoney(it) },
                        onPurchaseProgram = { progName, planName, price, emailOrPhone ->
                            viewModel.executeTelecomPayment(emailOrPhone, progName, "اشتراكات وبرامج", planName, price)
                        }
                    )
                }

                ScreenTab.LOGIN -> {
                    FullLoginScreen(
                        onBackClick = { viewModel.selectTab(ScreenTab.ACCOUNT) },
                        onNavigateToRegister = { viewModel.selectTab(ScreenTab.REGISTER) },
                        onLoginSuccess = { viewModel.selectTab(ScreenTab.ACCOUNT) },
                        onLoginSubmit = { phone, password ->
                            viewModel.login(phone, password)
                        }
                    )
                }

                ScreenTab.REGISTER -> {
                    RegisterScreen(
                        onBackClick = { viewModel.selectTab(ScreenTab.ACCOUNT) },
                        onNavigateToLogin = { viewModel.selectTab(ScreenTab.LOGIN) },
                        onRegisterSuccess = { viewModel.selectTab(ScreenTab.ACCOUNT) },
                        onRegisterSubmit = { phone, pass, firstName, lastName, governorate ->
                            viewModel.register(phone, pass, firstName, lastName, governorate)
                        }
                    )
                }

                ScreenTab.CATEGORIES -> {
                    CategoriesScreen(
                        categories = viewModel.categories,
                        selectedCategory = selectedCategory,
                        products = allProducts,
                        favorites = favorites,
                        onSelectCategory = { viewModel.selectCategory(it) },
                        selectedSubCategory = selectedSubCategory,
                        onSelectSubCategory = { viewModel.selectSubCategory(it) },
                        onProductClick = { viewModel.openProductDetail(it) },
                        onAddToCart = { viewModel.addToCart(it) },
                        onToggleFavorite = { viewModel.toggleFavorite(it) },
                        onBackClick = { viewModel.selectTab(ScreenTab.HOME) },
                        formatMoney = { viewModel.formatMoney(it) }
                    )
                }

                ScreenTab.PAYMENT_NETWORK -> {
                    PaymentNetworkScreen(
                        wallet = walletAccount,
                        packages = viewModel.telecomPackages,
                        formatMoney = { viewModel.formatMoney(it) },
                        onBackClick = { viewModel.selectTab(ScreenTab.ACCOUNT) },
                        onSyncBalance = { viewModel.syncWalletBalance() },
                        onRechargeSubmit = { phone, operatorName, category, packageName, amount ->
                            viewModel.executeTelecomPayment(phone, operatorName, category, packageName, amount)
                        }
                    )
                }

                ScreenTab.PRODUCT_DETAIL -> {
                    val currentProduct = selectedProductDetail
                    if (currentProduct != null) {
                        ProductDetailScreen(
                            product = currentProduct,
                            isFavorite = favorites.contains(currentProduct.id),
                            onBackClick = { viewModel.closeProductDetail() },
                            onToggleFavorite = { viewModel.toggleFavorite(currentProduct.id) },
                            onAddToCart = { prod, qty ->
                                repeat(qty) { viewModel.addToCart(prod) }
                            },
                            onBuyNow = { prod, qty ->
                                repeat(qty) { viewModel.addToCart(prod) }
                                viewModel.closeProductDetail()
                                viewModel.selectTab(ScreenTab.CART)
                            },
                            onVisitStore = { storeId ->
                                viewModel.closeProductDetail()
                                viewModel.selectStore(storeId)
                                viewModel.selectTab(ScreenTab.STORES)
                            },
                            onChatWithStore = {
                                val st = stores.find { it.id == currentProduct.storeId }
                                if (st != null) {
                                    viewModel.openStoreChat(st)
                                }
                            },
                            relatedProducts = viewModel.getRelatedProducts(currentProduct),
                            onCategoryClick = { catId ->
                                viewModel.closeProductDetail()
                                viewModel.openCategories(catId)
                            },
                            onRelatedProductClick = { prod ->
                                viewModel.openProductDetail(prod)
                            },
                            formatMoney = { viewModel.formatMoney(it) }
                        )
                    } else {
                        viewModel.closeProductDetail()
                    }
                }

                ScreenTab.ORDERS -> {
                    when {
                        selectedChatOrderId != null -> {
                            val activeOrder = orders.find { it.id == selectedChatOrderId }
                            if (activeOrder != null) {
                                OrderChatScreen(
                                    order = activeOrder,
                                    onBackClick = { viewModel.closeOrderChat() },
                                    onSendMessage = { text ->
                                        viewModel.sendOrderChatMessage(activeOrder.id, text)
                                    }
                                )
                            } else {
                                viewModel.closeOrderChat()
                            }
                        }

                        selectedOrderId != null -> {
                            val activeOrder = orders.find { it.id == selectedOrderId }
                            if (activeOrder != null) {
                                OrderDetailScreen(
                                    order = activeOrder,
                                    onBackClick = { viewModel.closeOrderDetails() },
                                    onOpenChat = { viewModel.openOrderChat(activeOrder.id) },
                                    onSubmitReview = { rating, comment ->
                                        viewModel.submitOrderReview(activeOrder.id, rating, comment)
                                    },
                                    onOrderItemClick = { item ->
                                        viewModel.openProductForOrderItem(item)
                                    },
                                    onReorderItem = { item ->
                                        viewModel.reorderItem(item)
                                    },
                                    onUpdateOrder = { orderId, newAddr, newNotes ->
                                        coroutineScope.launch {
                                            viewModel.updateOrderDetails(orderId, newAddr, newNotes)
                                        }
                                    },
                                    onCancelOrder = { orderId, reason ->
                                        coroutineScope.launch {
                                            viewModel.cancelOrder(orderId, reason)
                                        }
                                    },
                                    formatMoney = { viewModel.formatMoney(it) }
                                )
                            } else {
                                viewModel.closeOrderDetails()
                            }
                        }

                        else -> {
                            OrdersListScreen(
                                orders = orders,
                                onOrderClick = { orderId -> viewModel.openOrderDetails(orderId) },
                                onChatClick = { orderId -> viewModel.openOrderChat(orderId) },
                                onBackClick = { viewModel.selectTab(ScreenTab.ACCOUNT) },
                                formatMoney = { viewModel.formatMoney(it) }
                            )
                        }
                    }
                }

                ScreenTab.VENDOR_PORTAL -> {
                    val vendorFinance by viewModel.vendorFinance.collectAsState()
                    val vendorPayouts by viewModel.vendorPayouts.collectAsState()
                    VendorPortalScreen(
                        finance = vendorFinance,
                        payouts = vendorPayouts,
                        products = allProducts,
                        orders = orders,
                        onBackClick = { viewModel.selectTab(ScreenTab.ACCOUNT) },
                        onRequestPayout = { amount, ref -> viewModel.requestVendorPayout(amount, ref) },
                        onAddProduct = { name, desc, price, cat, stock, badge ->
                            viewModel.addVendorProduct(name, desc, price, cat, stock, badge)
                        },
                        onUpdateOrderStatus = { orderId, status, step ->
                            viewModel.updateOrderStatus(orderId, status, step)
                        },
                        formatMoney = { viewModel.formatMoney(it) }
                    )
                }

                ScreenTab.ADMIN_PORTAL -> {
                    AdminPortalScreen(
                        stores = stores,
                        products = allProducts,
                        orders = orders,
                        djangoUrl = djangoBaseUrl,
                        onBackClick = { viewModel.selectTab(ScreenTab.ACCOUNT) },
                        onOpenDjangoSettings = { viewModel.showDjangoSettingsDialog.value = true },
                        formatMoney = { viewModel.formatMoney(it) }
                    )
                }

                ScreenTab.ADDRESSES -> {
                    val addressesList by viewModel.addresses.collectAsState()
                    AddressesScreen(
                        addresses = addressesList,
                        onBackClick = { viewModel.selectTab(ScreenTab.ACCOUNT) },
                        onAddAddress = { viewModel.addAddress(it) },
                        onSetDefault = { viewModel.setDefaultAddress(it) },
                        onDeleteAddress = { viewModel.deleteAddress(it) }
                    )
                }

                ScreenTab.TRANSFER -> {
                    TransferScreen(
                        wallet = walletAccount,
                        userSession = userSession,
                        onBackClick = { viewModel.selectTab(ScreenTab.ACCOUNT) },
                        formatMoney = { viewModel.formatMoney(it) },
                        onCheckEligibility = { phone, amount, message ->
                            viewModel.checkTransferEligibility(phone, amount, message)
                        },
                        onConfirmTransfer = { giftId, phone, name, amount ->
                            viewModel.confirmTransfer(giftId, phone, name, amount)
                        },
                        onCancelTransfer = { giftId ->
                            viewModel.cancelTransfer(giftId)
                        }
                    )
                }

                else -> {
                    HomeScreenBody(
                        viewModel = viewModel,
                        selectedCategory = selectedCategory,
                        stores = stores,
                        filteredProducts = filteredProducts,
                        favorites = favorites
                    )
                }
            }
        }
    }

    // Dialogs Management
    if (activeStoreChat != null) {
        val activeStore = activeStoreChat
        if (activeStore != null) {
            StoreChatDialog(
                store = activeStore,
                messages = storeChatMessages[activeStore.id] ?: emptyList(),
                onSendMessage = { text -> viewModel.sendStoreChatMessage(activeStore.id, text) },
                onDismiss = { viewModel.closeStoreChat() }
            )
        }
    }

    if (showNotifications) {
        NotificationsDialog(
            notifications = notifications,
            onDismiss = { viewModel.showNotificationsDialog.value = false },
            onNotificationClick = { notification ->
                viewModel.markNotificationAsRead(notification.id)
            },
            onMarkAllAsRead = {
                viewModel.markAllNotificationsAsRead()
            }
        )
    }

    if (showLogin) {
        LoginWithPhoneDialog(
            onDismiss = { viewModel.showLoginDialog.value = false },
            onLogin = { phone, pass -> viewModel.login(phone, pass) }
        )
    }

    if (showDeposit) {
        DepositDialog(
            onDismiss = { viewModel.showDepositDialog.value = false },
            onFeedViaServer = { phone, amount, code ->
                viewModel.feedWalletViaServer(phone, amount, code)
            }
        )
    }

    if (showTransfer) {
        TransferDialog(
            onDismiss = { viewModel.showTransferDialog.value = false },
            onCheckEligibility = { recipient, amount ->
                viewModel.checkTransferEligibility(recipient, amount)
            },
            onConfirmTransfer = { recipient, recipientName, amount ->
                viewModel.executeTransfer(recipient, recipientName, amount).first
            }
        )
    }

    if (showDjangoSettings) {
        DjangoSettingsDialog(
            currentUrl = djangoBaseUrl,
            onDismiss = { viewModel.showDjangoSettingsDialog.value = false },
            onSaveUrl = { viewModel.updateDjangoUrl(it) }
        )
    }

    if (orderSuccessMessage != null) {
        AlertDialog(
            onDismissRequest = { viewModel.showOrderSuccessDialog.value = null },
            title = {
                Text(text = "نجاح العملية", fontWeight = FontWeight.Bold)
            },
            text = {
                Text(text = orderSuccessMessage ?: "")
            },
            confirmButton = {
                Button(onClick = {
                    viewModel.showOrderSuccessDialog.value = null
                    viewModel.selectTab(ScreenTab.ORDERS)
                }) {
                    Text("عرض في طلباتي")
                }
            },
            dismissButton = {
                TextButton(onClick = { viewModel.showOrderSuccessDialog.value = null }) {
                    Text("إغلاق")
                }
            }
        )
    }
}

/**
 * المحتوى التفاعلي للواجهة الرئيسية (Home)
 */
@Composable
fun HomeScreenBody(
    viewModel: MainViewModel,
    selectedCategory: String,
    stores: List<com.example.data.model.Store>,
    filteredProducts: List<com.example.data.model.Product>,
    favorites: Set<Int>
) {
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(bottom = 24.dp)
    ) {
        // 1. Category Tabs Bar directly underneath Search Bar
        item {
            CategoryTabsBar(
                categories = viewModel.categories,
                selectedCategory = selectedCategory,
                onCategorySelected = { viewModel.selectCategory(it) }
            )
        }

        // 2. Hero Banners Slider with CTA Button
        item {
            Spacer(modifier = Modifier.height(6.dp))
            HeroBannersSlider(
                banners = viewModel.banners,
                onCtaClick = {
                    viewModel.selectTab(ScreenTab.STORES)
                }
            )
        }

        // 3. Category Circles with Titles Underneath
        item {
            Spacer(modifier = Modifier.height(10.dp))
            VisualCategoryCircles(
                categories = viewModel.categories,
                selectedCategory = selectedCategory,
                onCategorySelected = { viewModel.selectCategory(it) },
                onViewAllCategoriesClick = { viewModel.selectTab(ScreenTab.CATEGORIES) }
            )
        }

        // 4. Featured Partner Stores
        item {
            Spacer(modifier = Modifier.height(10.dp))
            FeaturedStoresSection(
                stores = stores,
                onStoreClick = { store ->
                    viewModel.selectStore(store.id)
                    viewModel.selectTab(ScreenTab.STORES)
                }
            )
        }

        // 5. Featured Products Grid Header
        item {
            Spacer(modifier = Modifier.height(10.dp))
            PaddingHeader(
                title = "أحدث العروض والمنتجات المميزة",
                actionText = "جميع الأقسام"
            ) {
                viewModel.selectTab(ScreenTab.CATEGORIES)
            }
        }

        // 6. Products
        items(filteredProducts) { product ->
            ProductCard(
                product = product,
                isFavorite = favorites.contains(product.id),
                onFavoriteToggle = { viewModel.toggleFavorite(product.id) },
                onAddToCart = { viewModel.addToCart(product) },
                onProductClick = { viewModel.openProductDetail(product) },
                formatMoney = { viewModel.formatMoney(it) },
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp)
            )
        }
    }
}

@Composable
fun Greeting(name: String, modifier: Modifier = Modifier) {
    Text(text = "مرحباً $name في سوق بلس!", modifier = modifier)
}
