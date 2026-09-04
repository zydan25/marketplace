package com.example.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.*

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun VendorPortalScreen(
    finance: VendorFinance,
    payouts: List<VendorPayoutRequest>,
    products: List<Product>,
    orders: List<StoreOrder>,
    onBackClick: () -> Unit,
    onRequestPayout: (Double, String) -> Boolean,
    onAddProduct: (String, String, Double, String, Int, String?) -> Unit,
    onUpdateOrderStatus: (String, String, Int) -> Unit,
    formatMoney: (Double) -> String
) {
    var selectedTab by remember { mutableStateOf(0) } // 0: Overview & Products, 1: Orders, 2: Payouts & Wallet, 3: Settings
    var showAddProductDialog by remember { mutableStateOf(false) }
    var showPayoutDialog by remember { mutableStateOf(false) }
    var payoutMessage by remember { mutableStateOf<String?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Column {
                        Text("لوحة إدارة التاجر", fontWeight = FontWeight.Bold, fontSize = 17.sp)
                        Text(finance.vendorName, style = MaterialTheme.typography.labelSmall.copy(color = Color.Gray))
                    }
                },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "رجوع"
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
            )
        }
    ) { innerPadding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(Color(0xFFF7F8FA))
        ) {
            // Vendor Hero Card
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(12.dp),
                shape = RoundedCornerShape(16.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF161618))
            ) {
                Column(modifier = Modifier.padding(16.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(36.dp)
                                    .clip(RoundedCornerShape(10.dp))
                                    .background(Color(0xFFE11D48)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Storefront,
                                    contentDescription = null,
                                    tint = Color.White,
                                    modifier = Modifier.size(20.dp)
                                )
                            }
                            Text(
                                text = "محفظة وأرباح المتجر",
                                color = Color(0xFFD1D5DB),
                                style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Bold)
                            )
                        }

                        Surface(
                            shape = RoundedCornerShape(20.dp),
                            color = Color(0xFF22C55E).copy(alpha = 0.2f)
                        ) {
                            Text(
                                text = "متجر موثق نشط",
                                color = Color(0xFF4ADE80),
                                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp)
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))

                    Text(
                        text = "${formatMoney(finance.walletBalance)} ${finance.currency}",
                        style = MaterialTheme.typography.headlineMedium.copy(
                            color = Color.White,
                            fontWeight = FontWeight.Black
                        )
                    )

                    Spacer(modifier = Modifier.height(8.dp))

                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Column {
                            Text("المتاح للسحب الفوري", style = MaterialTheme.typography.labelSmall.copy(color = Color.Gray))
                            Text(
                                text = "${formatMoney(finance.availableBalance)} ${finance.currency}",
                                color = Color(0xFF38BDF8),
                                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold)
                            )
                        }

                        Button(
                            onClick = { showPayoutDialog = true },
                            shape = RoundedCornerShape(8.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFE11D48)),
                            contentPadding = PaddingValues(horizontal = 14.dp, vertical = 6.dp)
                        ) {
                            Icon(Icons.Default.ArrowUpward, contentDescription = null, modifier = Modifier.size(16.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("طلب سحب", fontWeight = FontWeight.Bold, fontSize = 12.sp)
                        }
                    }
                }
            }

            // Tabs Selector
            ScrollableTabRow(
                selectedTabIndex = selectedTab,
                containerColor = Color.White,
                contentColor = MaterialTheme.colorScheme.primary,
                edgePadding = 8.dp
            ) {
                Tab(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    text = { Text("المنتجات (${products.size})", fontWeight = FontWeight.Bold) }
                )
                Tab(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    text = { Text("طلبات المتجر (${orders.size})", fontWeight = FontWeight.Bold) }
                )
                Tab(
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 },
                    text = { Text("سجل السحوبات", fontWeight = FontWeight.Bold) }
                )
                Tab(
                    selected = selectedTab == 3,
                    onClick = { selectedTab = 3 },
                    text = { Text("بيانات المتجر", fontWeight = FontWeight.Bold) }
                )
            }

            when (selectedTab) {
                0 -> {
                    // Products Management Tab
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        item {
                            Button(
                                onClick = { showAddProductDialog = true },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(44.dp)
                                    .testTag("add_vendor_product_btn"),
                                shape = RoundedCornerShape(10.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                            ) {
                                Icon(Icons.Default.Add, contentDescription = null)
                                Spacer(modifier = Modifier.width(6.dp))
                                Text("إضافة منتج جديد للمتجر", fontWeight = FontWeight.Bold)
                            }
                        }

                        items(products) { product ->
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(12.dp),
                                colors = CardDefaults.cardColors(containerColor = Color.White)
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(12.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                                ) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        Text(
                                            text = product.name,
                                            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold)
                                        )
                                        Text(
                                            text = "${product.category} · المخزون: ${if (product.inStock) "متوفر" else "نفذ"}",
                                            style = MaterialTheme.typography.labelSmall.copy(color = Color.Gray)
                                        )
                                        Spacer(modifier = Modifier.height(4.dp))
                                        Text(
                                            text = "${formatMoney(product.priceYer)} ر.ي",
                                            style = MaterialTheme.typography.titleSmall.copy(
                                                fontWeight = FontWeight.Bold,
                                                color = MaterialTheme.colorScheme.primary
                                            )
                                        )
                                    }

                                    Surface(
                                        shape = RoundedCornerShape(8.dp),
                                        color = if (product.inStock) Color(0xFFDCFCE7) else Color(0xFFFEE2E2)
                                    ) {
                                        Text(
                                            text = if (product.inStock) "معروض للبيع" else "غير متاح",
                                            color = if (product.inStock) Color(0xFF15803D) else Color(0xFFB91C1C),
                                            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                        )
                                    }
                                }
                            }
                        }
                    }
                }

                1 -> {
                    // Orders Management Tab
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        items(orders) { order ->
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(12.dp),
                                colors = CardDefaults.cardColors(containerColor = Color.White)
                            ) {
                                Column(modifier = Modifier.padding(14.dp)) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        Text(
                                            text = order.id,
                                            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold)
                                        )
                                        Surface(
                                            shape = RoundedCornerShape(8.dp),
                                            color = MaterialTheme.colorScheme.primaryContainer
                                        ) {
                                            Text(
                                                text = order.status,
                                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp),
                                                style = MaterialTheme.typography.labelSmall.copy(
                                                    fontWeight = FontWeight.Bold,
                                                    color = MaterialTheme.colorScheme.primary
                                                )
                                            )
                                        }
                                    }

                                    Spacer(modifier = Modifier.height(6.dp))
                                    Text(
                                        text = "المبلغ: ${formatMoney(order.totalAmount)} ${order.currency} · ${order.itemsCount} عناصر",
                                        style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold)
                                    )
                                    Text(
                                        text = "العنوان: ${order.deliveryAddress}",
                                        style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray)
                                    )

                                    Spacer(modifier = Modifier.height(10.dp))

                                    // Action buttons for vendor
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                                    ) {
                                        OutlinedButton(
                                            onClick = { onUpdateOrderStatus(order.id, "قيد التجهيز", 1) },
                                            modifier = Modifier.weight(1f),
                                            contentPadding = PaddingValues(0.dp)
                                        ) {
                                            Text("تجهيز الطلب", fontSize = 11.sp)
                                        }
                                        Button(
                                            onClick = { onUpdateOrderStatus(order.id, "تم الشحن مع المندوب", 2) },
                                            modifier = Modifier.weight(1f),
                                            contentPadding = PaddingValues(0.dp)
                                        ) {
                                            Text("تسليم للمندوب", fontSize = 11.sp)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }

                2 -> {
                    // Payouts & Withdrawals
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(12.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        item {
                            Text(
                                text = "سجل طلبات السحب والحوالات",
                                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold)
                            )
                        }

                        items(payouts) { p ->
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(12.dp),
                                colors = CardDefaults.cardColors(containerColor = Color.White)
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(14.dp),
                                    horizontalArrangement = Arrangement.SpaceBetween,
                                    verticalAlignment = Alignment.CenterVertically
                                ) {
                                    Column {
                                        Text(
                                            text = "${formatMoney(p.amount)} ${p.currency}",
                                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                                        )
                                        Text(
                                            text = p.reference,
                                            style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray)
                                        )
                                        Text(
                                            text = p.date,
                                            style = MaterialTheme.typography.labelSmall.copy(color = Color.LightGray)
                                        )
                                    }

                                    val (statusText, statusColor) = when (p.status) {
                                        "paid" -> "مدفوع ومحول" to Color(0xFF15803D)
                                        "approved" -> "معتمد" to Color(0xFF0288D1)
                                        "rejected" -> "مرفوض" to Color(0xFFB91C1C)
                                        else -> "قيد المراجعة" to Color(0xFFD97706)
                                    }

                                    Surface(
                                        shape = RoundedCornerShape(8.dp),
                                        color = statusColor.copy(alpha = 0.15f)
                                    ) {
                                        Text(
                                            text = statusText,
                                            color = statusColor,
                                            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                            modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                        )
                                    }
                                }
                            }
                        }
                    }
                }

                3 -> {
                    // Store Settings
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        item {
                            Card(
                                shape = RoundedCornerShape(14.dp),
                                colors = CardDefaults.cardColors(containerColor = Color.White)
                            ) {
                                Column(modifier = Modifier.padding(16.dp)) {
                                    Text("بيانات المتجر الرسمية", fontWeight = FontWeight.Bold)
                                    Spacer(modifier = Modifier.height(10.dp))
                                    Text("اسم المتجر: ${finance.vendorName}", style = MaterialTheme.typography.bodyMedium)
                                    Text("هاتف التواصل: 770123456", style = MaterialTheme.typography.bodyMedium)
                                    Text("المدينة: صنعاء - شارع حدة", style = MaterialTheme.typography.bodyMedium)
                                    Text("حالة المتجر: مفتوح ويستقبل الطلبات على مدار الساعة", style = MaterialTheme.typography.bodySmall.copy(color = Color(0xFF15803D)))
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Add Product Dialog
    if (showAddProductDialog) {
        var prodName by remember { mutableStateOf("") }
        var prodDesc by remember { mutableStateOf("") }
        var prodPrice by remember { mutableStateOf("") }
        var prodCat by remember { mutableStateOf("عطور وبخور") }
        var prodStock by remember { mutableStateOf("10") }
        var prodBadge by remember { mutableStateOf("جديد 🔥") }

        AlertDialog(
            onDismissRequest = { showAddProductDialog = false },
            title = { Text("إضافة منتج جديد للمتجر", fontWeight = FontWeight.Bold) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = prodName,
                        onValueChange = { prodName = it },
                        label = { Text("اسم المنتج") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = prodPrice,
                        onValueChange = { prodPrice = it },
                        label = { Text("السعر بالريال اليمني (YER)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = prodCat,
                        onValueChange = { prodCat = it },
                        label = { Text("التصنيف") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = prodDesc,
                        onValueChange = { prodDesc = it },
                        label = { Text("وصف المنتج") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val priceVal = prodPrice.toDoubleOrNull() ?: 0.0
                        val stockVal = prodStock.toIntOrNull() ?: 10
                        if (prodName.isNotBlank() && priceVal > 0) {
                            onAddProduct(prodName, prodDesc, priceVal, prodCat, stockVal, prodBadge)
                            showAddProductDialog = false
                        }
                    },
                    enabled = prodName.isNotBlank() && (prodPrice.toDoubleOrNull() ?: 0.0) > 0
                ) {
                    Text("إضافة المنتج")
                }
            },
            dismissButton = {
                TextButton(onClick = { showAddProductDialog = false }) {
                    Text("إلغاء")
                }
            }
        )
    }

    // Payout Dialog
    if (showPayoutDialog) {
        var withdrawAmount by remember { mutableStateOf("") }
        var withdrawRef by remember { mutableStateOf("حوالة الكريمي - 770123456") }

        AlertDialog(
            onDismissRequest = { showPayoutDialog = false },
            title = { Text("طلب سحب أرباح المتجر", fontWeight = FontWeight.Bold) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        text = "الرصيد المتاح للسحب: ${formatMoney(finance.availableBalance)} ${finance.currency}",
                        style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.Bold)
                    )
                    OutlinedTextField(
                        value = withdrawAmount,
                        onValueChange = { withdrawAmount = it },
                        label = { Text("المبلغ المطلوب سحبه (ر.ي)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                    OutlinedTextField(
                        value = withdrawRef,
                        onValueChange = { withdrawRef = it },
                        label = { Text("طريقة التحويل وبيانات الحساب (الكريمي/النجم)") },
                        modifier = Modifier.fillMaxWidth()
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val amt = withdrawAmount.toDoubleOrNull() ?: 0.0
                        if (amt > 0) {
                            val success = onRequestPayout(amt, withdrawRef)
                            if (success) {
                                showPayoutDialog = false
                            }
                        }
                    }
                ) {
                    Text("تأكيد طلب السحب")
                }
            },
            dismissButton = {
                TextButton(onClick = { showPayoutDialog = false }) {
                    Text("إلغاء")
                }
            }
        )
    }
}
