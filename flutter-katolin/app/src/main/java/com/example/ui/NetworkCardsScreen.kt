package com.example.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalClipboardManager
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.PurchasedWifiCard
import com.example.data.model.UserSession
import com.example.data.model.WifiCardDenomination
import com.example.data.model.WifiNetwork

/**
 * شاشة كروت شبكات الوايفاي (WiFi Networks & Cards)
 * 1. قائمة شبكات الوايفاي (اسم الشبكة، رقم صاحبها، موقعها، حالة الإشارة)
 * 2. عند الضغط على أي شبكة تظهر فئاتها والأسعار والسرعات
 * 3. إدخال رقم الهاتف وشراء الكرت وطلبه من الخادم
 * 4. استلام كود الكرت (PIN) والرقم التسلسلي مع إمكانية النسخ
 * 5. تبويب "كروتي المشتراة" لمراجعة أي كروت تم شراؤها مسبقاً
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NetworkCardsScreen(
    userSession: UserSession,
    wifiNetworks: List<WifiNetwork>,
    purchasedWifiCards: List<PurchasedWifiCard>,
    onBackClick: () -> Unit,
    formatMoney: (Double) -> String,
    onPurchaseWifiCard: (WifiNetwork, WifiCardDenomination, String) -> PurchasedWifiCard,
    modifier: Modifier = Modifier
) {
    val clipboardManager = LocalClipboardManager.current

    var selectedTab by remember { mutableStateOf(0) } // 0: الشبكات المتوفرة, 1: كروتي المشتراة
    var searchQuery by remember { mutableStateOf("") }
    var selectedGovernorateFilter by remember { mutableStateOf("الكل") }

    // Dialogs & Sheets
    var selectedNetworkForPurchase by remember { mutableStateOf<WifiNetwork?>(null) }
    var selectedDenominationForPurchase by remember { mutableStateOf<WifiCardDenomination?>(null) }
    var customerPhoneInput by remember { mutableStateOf(userSession.phone) }
    var lastPurchasedCard by remember { mutableStateOf<PurchasedWifiCard?>(null) }
    var showSuccessDialog by remember { mutableStateOf(false) }
    var copySnackbarMessage by remember { mutableStateOf<String?>(null) }

    val governorates = remember(wifiNetworks) {
        listOf("الكل") + wifiNetworks.map { it.governorate }.distinct().filter { it.isNotBlank() }
    }

    val filteredNetworks = remember(wifiNetworks, searchQuery, selectedGovernorateFilter) {
        wifiNetworks.filter { net ->
            val matchQuery = searchQuery.isBlank() ||
                    net.name.contains(searchQuery, ignoreCase = true) ||
                    net.location.contains(searchQuery, ignoreCase = true) ||
                    net.ownerName.contains(searchQuery, ignoreCase = true) ||
                    net.ownerPhone.contains(searchQuery)
            val matchGov = selectedGovernorateFilter == "الكل" || net.governorate == selectedGovernorateFilter
            matchQuery && matchGov
        }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text(
                            text = "كروت شبكات الوايفاي 📶",
                            fontWeight = FontWeight.Bold,
                            fontSize = 18.sp
                        )
                        Text(
                            text = "شبكات الأحياء والحارات • شراء كروت فورية",
                            style = MaterialTheme.typography.labelSmall.copy(color = MaterialTheme.colorScheme.onSurfaceVariant)
                        )
                    }
                },
                navigationIcon = {
                    IconButton(
                        onClick = onBackClick,
                        modifier = Modifier.testTag("wifi_cards_back_button")
                    ) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "رجوع"
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        },
        modifier = modifier
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
        ) {
            // Tabs: الشبكات المتاحة | كروتي المشتراة
            TabRow(
                selectedTabIndex = selectedTab,
                containerColor = MaterialTheme.colorScheme.surface,
                contentColor = MaterialTheme.colorScheme.primary
            ) {
                Tab(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    text = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.Wifi, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("الشبكات المتاحة (${filteredNetworks.size})", fontWeight = FontWeight.Bold)
                        }
                    }
                )
                Tab(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    text = {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Default.ReceiptLong, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(6.dp))
                            Text("كروتي المشتراة (${purchasedWifiCards.size})", fontWeight = FontWeight.Bold)
                        }
                    }
                )
            }

            if (selectedTab == 0) {
                // Search Box
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    placeholder = { Text("ابحث باسم الشبكة، الحي، أو اسم ورقم صاحبها...") },
                    leadingIcon = { Icon(Icons.Default.Search, contentDescription = null) },
                    trailingIcon = {
                        if (searchQuery.isNotBlank()) {
                            IconButton(onClick = { searchQuery = "" }) {
                                Icon(Icons.Default.Close, contentDescription = "مسح")
                            }
                        }
                    },
                    singleLine = true,
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 8.dp)
                        .testTag("wifi_search_input")
                )

                // Governorate Filter Chips
                if (governorates.size > 1) {
                    LazyRow(
                        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 4.dp),
                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        items(governorates) { gov ->
                            FilterChip(
                                selected = selectedGovernorateFilter == gov,
                                onClick = { selectedGovernorateFilter = gov },
                                label = { Text(gov) },
                                colors = FilterChipDefaults.filterChipColors(
                                    selectedContainerColor = MaterialTheme.colorScheme.primaryContainer,
                                    selectedLabelColor = MaterialTheme.colorScheme.onPrimaryContainer
                                )
                            )
                        }
                    }
                }

                // Networks List
                if (filteredNetworks.isEmpty()) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(24.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                imageVector = Icons.Default.WifiOff,
                                contentDescription = null,
                                tint = Color.Gray,
                                modifier = Modifier.size(64.dp)
                            )
                            Spacer(modifier = Modifier.height(12.dp))
                            Text(
                                text = "لم يتم العثور على شبكات وايفاي مطابقة",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.SemiBold
                            )
                            Text(
                                text = "جرب البحث باسم آخر أو اختيار محافظة أخرى",
                                style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray)
                            )
                        }
                    }
                } else {
                    LazyColumn(
                        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        modifier = Modifier.fillMaxSize()
                    ) {
                        items(filteredNetworks) { network ->
                            WifiNetworkCard(
                                network = network,
                                formatMoney = formatMoney,
                                onSelectNetwork = { selectedNetworkForPurchase = network }
                            )
                        }
                    }
                }
            } else {
                // Purchased Cards List
                if (purchasedWifiCards.isEmpty()) {
                    Box(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(24.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                imageVector = Icons.Default.ReceiptLong,
                                contentDescription = null,
                                tint = Color.Gray,
                                modifier = Modifier.size(64.dp)
                            )
                            Spacer(modifier = Modifier.height(12.dp))
                            Text(
                                text = "لا توجد كروت وايفاي مشتراة حتى الآن",
                                style = MaterialTheme.typography.titleMedium,
                                fontWeight = FontWeight.SemiBold
                            )
                            Text(
                                text = "عند شرائك أي كرت وايفاي ستظهر تفاصيل الكود والرقم التسلسلي هنا",
                                style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray),
                                textAlign = TextAlign.Center
                            )
                            Spacer(modifier = Modifier.height(16.dp))
                            Button(
                                onClick = { selectedTab = 0 },
                                shape = RoundedCornerShape(10.dp)
                            ) {
                                Text("تصفح شبكات الوايفاي وشراء كرت")
                            }
                        }
                    }
                } else {
                    LazyColumn(
                        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp),
                        modifier = Modifier.fillMaxSize()
                    ) {
                        items(purchasedWifiCards) { card ->
                            PurchasedCardItem(
                                card = card,
                                formatMoney = formatMoney,
                                onCopyPin = { pin ->
                                    clipboardManager.setText(AnnotatedString(pin))
                                    copySnackbarMessage = "تم نسخ كود الكرت ($pin) بنجاح!"
                                }
                            )
                        }
                    }
                }
            }
        }
    }

    // Modal Sheet / Dialog: Select Denomination for Network
    if (selectedNetworkForPurchase != null && selectedDenominationForPurchase == null) {
        val network = selectedNetworkForPurchase!!
        AlertDialog(
            onDismissRequest = { selectedNetworkForPurchase = null },
            title = {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .size(44.dp)
                            .clip(CircleShape)
                            .background(MaterialTheme.colorScheme.primaryContainer),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Wifi,
                            contentDescription = null,
                            tint = MaterialTheme.colorScheme.primary
                        )
                    }
                    Column {
                        Text(network.name, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                        Text(
                            text = "الموقع: ${network.location}",
                            style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray)
                        )
                    }
                }
            },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    // Owner info
                    Surface(
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f),
                        shape = RoundedCornerShape(8.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier.padding(10.dp),
                            horizontalArrangement = Arrangement.SpaceBetween,
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            Column {
                                Text(
                                    text = "صاحب الشبكة: ${network.ownerName}",
                                    style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.SemiBold)
                                )
                                Text(
                                    text = "رقم التواصل: ${network.ownerPhone}",
                                    style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.primary)
                                )
                            }
                            Icon(
                                imageVector = Icons.Default.Call,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary,
                                modifier = Modifier.size(20.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(6.dp))
                    Text(
                        text = "اختر فئة الكرت المراد شراؤها:",
                        fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.titleSmall
                    )

                    // List of denominations
                    network.denominations.forEach { denom ->
                        Surface(
                            shape = RoundedCornerShape(10.dp),
                            color = MaterialTheme.colorScheme.surface,
                            border = androidx.compose.foundation.BorderStroke(
                                1.dp,
                                MaterialTheme.colorScheme.outlineVariant
                            ),
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable {
                                    selectedDenominationForPurchase = denom
                                }
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(12.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Column(modifier = Modifier.weight(1f)) {
                                    Text(
                                        text = denom.title,
                                        fontWeight = FontWeight.Bold,
                                        style = MaterialTheme.typography.bodyMedium
                                    )
                                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                        Text(
                                            text = "⏱ ${denom.duration}",
                                            style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray)
                                        )
                                        Text(
                                            text = "📦 ${denom.dataQuota}",
                                            style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.primary)
                                        )
                                    }
                                }

                                Surface(
                                    color = MaterialTheme.colorScheme.primaryContainer,
                                    shape = RoundedCornerShape(8.dp)
                                ) {
                                    Text(
                                        text = "${formatMoney(denom.priceYer)} ر.ي",
                                        fontWeight = FontWeight.Bold,
                                        color = MaterialTheme.colorScheme.onPrimaryContainer,
                                        style = MaterialTheme.typography.labelLarge,
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                    )
                                }
                            }
                        }
                    }
                }
            },
            confirmButton = {},
            dismissButton = {
                TextButton(onClick = { selectedNetworkForPurchase = null }) {
                    Text("إلغاء")
                }
            }
        )
    }

    // Modal Sheet / Dialog: Confirm Purchase & Enter Phone Number
    if (selectedNetworkForPurchase != null && selectedDenominationForPurchase != null) {
        val network = selectedNetworkForPurchase!!
        val denom = selectedDenominationForPurchase!!
        var isPurchasing by remember { mutableStateOf(false) }

        AlertDialog(
            onDismissRequest = {
                if (!isPurchasing) {
                    selectedDenominationForPurchase = null
                }
            },
            title = {
                Text("تأكيد شراء كرت الوايفاي 📶", fontWeight = FontWeight.Bold)
            },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    // Summary card
                    Surface(
                        color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.3f),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(modifier = Modifier.padding(12.dp)) {
                            Text("الشبكة: ${network.name}", fontWeight = FontWeight.Bold)
                            Text("الفئة: ${denom.title} (${denom.duration} • ${denom.dataQuota})", style = MaterialTheme.typography.bodySmall)
                            Text("الموقع: ${network.location}", style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray))
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "السعر المطلوب: ${formatMoney(denom.priceYer)} ريال يمني",
                                fontWeight = FontWeight.Bold,
                                color = MaterialTheme.colorScheme.primary,
                                style = MaterialTheme.typography.titleMedium
                            )
                        }
                    }

                    Text(
                        text = "أدخل رقم الهاتف لاستلام بيانات الكود:",
                        fontWeight = FontWeight.SemiBold,
                        style = MaterialTheme.typography.bodyMedium
                    )

                    OutlinedTextField(
                        value = customerPhoneInput,
                        onValueChange = { customerPhoneInput = it },
                        label = { Text("رقم الهاتف (7xxxxxxxx)") },
                        leadingIcon = { Icon(Icons.Default.Phone, contentDescription = null) },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                        singleLine = true,
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier
                            .fillMaxWidth()
                            .testTag("wifi_phone_input")
                    )

                    Text(
                        text = "💡 سيتم خصم المبلغ من رصيدك في المحفظة وطلب الكرت من السيرفر فوراً وإظهار الكود على الشاشة مباشرة.",
                        style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray)
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val phone = customerPhoneInput.ifBlank { "770000000" }
                        isPurchasing = true
                        val card = onPurchaseWifiCard(network, denom, phone)
                        lastPurchasedCard = card
                        isPurchasing = false
                        selectedNetworkForPurchase = null
                        selectedDenominationForPurchase = null
                        showSuccessDialog = true
                    },
                    shape = RoundedCornerShape(8.dp),
                    modifier = Modifier.testTag("confirm_wifi_purchase_button")
                ) {
                    if (isPurchasing) {
                        CircularProgressIndicator(
                            color = Color.White,
                            modifier = Modifier.size(18.dp)
                        )
                    } else {
                        Text("شراء الكرت الآن ⚡", fontWeight = FontWeight.Bold)
                    }
                }
            },
            dismissButton = {
                TextButton(
                    onClick = { selectedDenominationForPurchase = null },
                    enabled = !isPurchasing
                ) {
                    Text("رجوع للفئات")
                }
            }
        )
    }

    // Success Receipt Dialog with PIN Code & Instructions
    if (showSuccessDialog && lastPurchasedCard != null) {
        val card = lastPurchasedCard!!
        AlertDialog(
            onDismissRequest = { showSuccessDialog = false },
            title = {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.CheckCircle,
                        contentDescription = null,
                        tint = Color(0xFF2E7D32),
                        modifier = Modifier.size(28.dp)
                    )
                    Text("تم شراء الكرت بنجاح! 🌟", fontWeight = FontWeight.Bold)
                }
            },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text(
                        text = "تم إصدار كرت وايفاي شبكة (${card.networkName}) فئة ${card.denominationTitle}:",
                        style = MaterialTheme.typography.bodyMedium
                    )

                    // PIN Code Display Card
                    Surface(
                        shape = RoundedCornerShape(12.dp),
                        color = Color(0xFFE8F5E9),
                        border = androidx.compose.foundation.BorderStroke(2.dp, Color(0xFF4CAF50)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(
                            modifier = Modifier.padding(16.dp),
                            horizontalAlignment = Alignment.CenterHorizontally
                        ) {
                            Text(
                                text = "كود كرت الوايفاي (PIN)",
                                style = MaterialTheme.typography.labelMedium.copy(color = Color(0xFF2E7D32))
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = card.pinCode,
                                style = MaterialTheme.typography.headlineMedium.copy(
                                    fontWeight = FontWeight.ExtraBold,
                                    letterSpacing = 3.sp,
                                    color = Color(0xFF1B5E20)
                                )
                            )
                            Spacer(modifier = Modifier.height(8.dp))
                            Button(
                                onClick = {
                                    clipboardManager.setText(AnnotatedString(card.pinCode))
                                    copySnackbarMessage = "تم نسخ كود الكرت (${card.pinCode})!"
                                },
                                shape = RoundedCornerShape(8.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF2E7D32)),
                                modifier = Modifier.testTag("copy_pin_button")
                            ) {
                                Icon(Icons.Default.ContentCopy, contentDescription = null, modifier = Modifier.size(16.dp))
                                Spacer(modifier = Modifier.width(6.dp))
                                Text("نسخ كود الكرت")
                            }
                        }
                    }

                    // Card details
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f), RoundedCornerShape(8.dp))
                            .padding(10.dp),
                        verticalArrangement = Arrangement.spacedBy(4.dp)
                    ) {
                        Text("الرقم التسلسلي: ${card.serialNumber}", style = MaterialTheme.typography.bodySmall)
                        Text("المدة والحجم: ${card.duration} • ${card.dataQuota}", style = MaterialTheme.typography.bodySmall)
                        Text("هاتف صاحب الشبكة للدعم: ${card.ownerPhone}", style = MaterialTheme.typography.bodySmall)
                        Text("طريقة الاستخدام: اتصل بشبكة الوايفاي ${card.networkName} وافتح المتصفح وأدخل الكود أعلاه", style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.primary))
                    }
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        showSuccessDialog = false
                        selectedTab = 1 // Switch to "كروتي المشتراة"
                    },
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text("عرض كروتي المشتراة")
                }
            },
            dismissButton = {
                TextButton(onClick = { showSuccessDialog = false }) {
                    Text("إغلاق")
                }
            }
        )
    }

    // Snackbar alert for copying
    if (copySnackbarMessage != null) {
        AlertDialog(
            onDismissRequest = { copySnackbarMessage = null },
            title = { Text("تم النسخ", fontWeight = FontWeight.Bold) },
            text = { Text(copySnackbarMessage!!) },
            confirmButton = {
                TextButton(onClick = { copySnackbarMessage = null }) {
                    Text("حسناً")
                }
            }
        )
    }
}

/**
 * بطاقة عرض شبكة الوايفاي في القائمة الرئيسية
 */
@Composable
private fun WifiNetworkCard(
    network: WifiNetwork,
    formatMoney: (Double) -> String,
    onSelectNetwork: () -> Unit
) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        modifier = Modifier
            .fillMaxWidth()
            .clickable { onSelectNetwork() }
            .testTag("wifi_network_card_${network.id}")
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Box(
                        modifier = Modifier
                            .size(46.dp)
                            .clip(CircleShape)
                            .background(
                                Brush.linearGradient(
                                    listOf(
                                        Color(0xFF1976D2),
                                        Color(0xFF0D47A1)
                                    )
                                )
                            ),
                        contentAlignment = Alignment.Center
                    ) {
                        Icon(
                            imageVector = Icons.Default.Wifi,
                            contentDescription = null,
                            tint = Color.White,
                            modifier = Modifier.size(26.dp)
                        )
                    }

                    Column {
                        Text(
                            text = network.name,
                            fontWeight = FontWeight.Bold,
                            style = MaterialTheme.typography.titleMedium
                        )
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(
                                imageVector = Icons.Default.Place,
                                contentDescription = null,
                                tint = Color.Gray,
                                modifier = Modifier.size(14.dp)
                            )
                            Spacer(modifier = Modifier.width(2.dp))
                            Text(
                                text = "${network.governorate} • ${network.location}",
                                style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray)
                            )
                        }
                    }
                }

                // Signal & status badge
                Surface(
                    shape = RoundedCornerShape(6.dp),
                    color = if (network.isOnline) Color(0xFFE8F5E9) else Color(0xFFFFEBEE)
                ) {
                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    ) {
                        Text(
                            text = if (network.isOnline) "متصلة 🟢" else "غير متاحة",
                            style = MaterialTheme.typography.labelSmall.copy(
                                color = if (network.isOnline) Color(0xFF2E7D32) else Color(0xFFC62828),
                                fontWeight = FontWeight.Bold
                            )
                        )
                    }
                }
            }

            HorizontalDivider(
                modifier = Modifier.padding(vertical = 10.dp),
                color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f)
            )

            // Owner Details & Denominations Count
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "صاحب الشبكة: ${network.ownerName}",
                        style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Medium)
                    )
                    Text(
                        text = "هاتف: ${network.ownerPhone}",
                        style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.primary)
                    )
                }

                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = MaterialTheme.colorScheme.primaryContainer
                ) {
                    Text(
                        text = "${network.denominations.size} فئات متاحة",
                        style = MaterialTheme.typography.labelSmall.copy(
                            color = MaterialTheme.colorScheme.onPrimaryContainer,
                            fontWeight = FontWeight.Bold
                        ),
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            // Denominations Preview Chips
            LazyRow(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                items(network.denominations) { denom ->
                    Surface(
                        shape = RoundedCornerShape(6.dp),
                        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.5f)
                    ) {
                        Text(
                            text = "${denom.title} (${formatMoney(denom.priceYer)} ر.ي)",
                            style = MaterialTheme.typography.labelSmall,
                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 3.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            Button(
                onClick = onSelectNetwork,
                modifier = Modifier.fillMaxWidth(),
                shape = RoundedCornerShape(10.dp),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
            ) {
                Icon(Icons.Default.ShoppingCart, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(modifier = Modifier.width(6.dp))
                Text("شراء كرت لهذه الشبكة ⚡", fontWeight = FontWeight.Bold)
            }
        }
    }
}

/**
 * عنصر عرض الكرت المشترى مسبقاً
 */
@Composable
private fun PurchasedCardItem(
    card: PurchasedWifiCard,
    formatMoney: (Double) -> String,
    onCopyPin: (String) -> Unit
) {
    Card(
        shape = RoundedCornerShape(14.dp),
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
        modifier = Modifier
            .fillMaxWidth()
            .testTag("purchased_card_${card.id}")
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "شبكة ${card.networkName}",
                        fontWeight = FontWeight.Bold,
                        style = MaterialTheme.typography.titleMedium
                    )
                    Text(
                        text = "${card.denominationTitle} • ${card.duration} (${card.dataQuota})",
                        style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray)
                    )
                }

                Surface(
                    color = Color(0xFFE8F5E9),
                    shape = RoundedCornerShape(8.dp)
                ) {
                    Text(
                        text = "${formatMoney(card.priceYer)} ر.ي",
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF2E7D32),
                        style = MaterialTheme.typography.labelMedium,
                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(10.dp))

            // PIN Box
            Surface(
                shape = RoundedCornerShape(10.dp),
                color = Color(0xFFF1F8E9),
                border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFF81C784)),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 12.dp, vertical = 10.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "كود الكرت (PIN):",
                            style = MaterialTheme.typography.labelSmall.copy(color = Color(0xFF2E7D32))
                        )
                        Text(
                            text = card.pinCode,
                            style = MaterialTheme.typography.titleLarge.copy(
                                fontWeight = FontWeight.Bold,
                                letterSpacing = 2.sp,
                                color = Color(0xFF1B5E20)
                            )
                        )
                    }

                    OutlinedButton(
                        onClick = { onCopyPin(card.pinCode) },
                        shape = RoundedCornerShape(8.dp)
                    ) {
                        Icon(Icons.Default.ContentCopy, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("نسخ")
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    text = "التسلسلي: ${card.serialNumber}",
                    style = MaterialTheme.typography.labelSmall.copy(color = Color.Gray)
                )
                Text(
                    text = "هاتف الدعم: ${card.ownerPhone}",
                    style = MaterialTheme.typography.labelSmall.copy(color = MaterialTheme.colorScheme.primary)
                )
            }
        }
    }
}
