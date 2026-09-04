package com.example.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.FastOutSlowInEasing
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.ContactPhone
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.SimCard
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.TabRowDefaults
import androidx.compose.material3.TabRowDefaults.tabIndicatorOffset
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.derivedStateOf
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.rotate
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.TelecomPackage
import com.example.data.model.WalletAccount

enum class YemenOperator(
    val code: String,
    val arabicName: String,
    val primaryColor: Color,
    val darkColor: Color,
    val lightColor: Color,
    val shortBadge: String,
    val supportedTabs: List<String>
) {
    YEMEN_MOBILE(
        code = "yemen_mobile",
        arabicName = "يمن موبايل",
        primaryColor = Color(0xFFC62828), // Red
        darkColor = Color(0xFF880E4F),
        lightColor = Color(0xFFFFEBEE),
        shortBadge = "يمن موبايل",
        supportedTabs = listOf("رصيد", "فوري", "باقات", "جملة", "ريال")
    ),
    SABAFON(
        code = "sabafon",
        arabicName = "سبأفون",
        primaryColor = Color(0xFF0288D1), // Cyan/Blue
        darkColor = Color(0xFF01579B),
        lightColor = Color(0xFFE1F5FE),
        shortBadge = "سبأفون",
        supportedTabs = listOf("رصيد", "فوري", "باقات", "جملة")
    ),
    YOU(
        code = "you",
        arabicName = "يو YOU (إم تي إن سابقاً)",
        primaryColor = Color(0xFFF9A825), // Golden Yellow
        darkColor = Color(0xFFE65100),
        lightColor = Color(0xFFFFFDE7),
        shortBadge = "YOU",
        supportedTabs = listOf("رصيد", "فوري", "باقات", "جملة")
    ),
    Y_TELECOM(
        code = "y",
        arabicName = "واي Y",
        primaryColor = Color(0xFF7B1FA2), // Purple
        darkColor = Color(0xFF4A148C),
        lightColor = Color(0xFFF3E5F5),
        shortBadge = "واي",
        supportedTabs = listOf("رصيد", "فوري", "باقات")
    ),
    FIXED_YEMEN_NET(
        code = "fixed",
        arabicName = "الهاتف الثابت ويمن نت",
        primaryColor = Color(0xFF0D47A1), // Navy
        darkColor = Color(0xFF002171),
        lightColor = Color(0xFFE8EAF6),
        shortBadge = "يمن نت",
        supportedTabs = listOf("رصيد", "باقات")
    )
}

/**
 * شاشة شبكة السداد للاتصالات اليمنية
 * مطابقة تماماً للصور المرفقة
 */
@Composable
fun PaymentNetworkScreen(
    wallet: WalletAccount,
    packages: List<TelecomPackage>,
    formatMoney: (Double) -> String,
    onBackClick: () -> Unit,
    onSyncBalance: () -> Unit,
    onRechargeSubmit: (phone: String, operatorName: String, category: String, packageName: String, amount: Double) -> Unit,
    modifier: Modifier = Modifier
) {
    var phoneNumber by remember { mutableStateOf("") }
    var isBalanceVisible by remember { mutableStateOf(false) }
    var isFavorite by remember { mutableStateOf(false) }
    var rotationAngle by remember { mutableStateOf(0f) }
    var customAmount by remember { mutableStateOf("1000") }

    // Detect operator dynamically from phone input
    val detectedOperator by remember(phoneNumber) {
        derivedStateOf {
            val clean = phoneNumber.trim()
            when {
                clean.startsWith("77") || clean.startsWith("78") -> YemenOperator.YEMEN_MOBILE
                clean.startsWith("71") -> YemenOperator.SABAFON
                clean.startsWith("73") -> YemenOperator.YOU
                clean.startsWith("70") -> YemenOperator.Y_TELECOM
                clean.startsWith("01") || clean.startsWith("04") || clean.startsWith("104") ||
                        clean.startsWith("02") || clean.startsWith("03") || clean.startsWith("07") -> YemenOperator.FIXED_YEMEN_NET
                else -> YemenOperator.YEMEN_MOBILE // Default
            }
        }
    }

    // Active tab based on detected operator
    val tabs = detectedOperator.supportedTabs
    var selectedTabIndex by remember(detectedOperator) { mutableStateOf(0) }
    val activeTabName = tabs.getOrElse(selectedTabIndex) { tabs.firstOrNull() ?: "رصيد" }

    // Filter packages matching current operator and tab
    val currentPackages = packages.filter {
        it.operator == detectedOperator.code && (it.category == activeTabName || activeTabName == "فوري")
    }

    // Animated header color
    val animatedHeaderColor by animateColorAsState(
        targetValue = detectedOperator.primaryColor,
        animationSpec = tween(durationMillis = 400, easing = FastOutSlowInEasing),
        label = "header_color"
    )

    LazyColumn(
        modifier = modifier
            .fillMaxSize()
            .background(Color(0xFFF7F9FC)),
        contentPadding = PaddingValues(bottom = 32.dp)
    ) {
        // 1. Top Dynamic Operator Header (Matching Photo 1, 2, 3)
        item {
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(animatedHeaderColor)
                    .padding(horizontal = 16.dp, vertical = 14.dp)
            ) {
                Column(modifier = Modifier.fillMaxWidth()) {
                    // Row with Sync Button, "رصيدي", and Settings Gear
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        // Left: Circular Sync/Refresh Button
                        Surface(
                            shape = CircleShape,
                            color = Color.White,
                            shadowElevation = 3.dp,
                            modifier = Modifier
                                .size(44.dp)
                                .clickable {
                                    rotationAngle += 360f
                                    onSyncBalance()
                                }
                        ) {
                            val animatedRotation by animateFloatAsState(
                                targetValue = rotationAngle,
                                animationSpec = tween(durationMillis = 600),
                                label = "sync_rotation"
                            )
                            Box(contentAlignment = Alignment.Center) {
                                Icon(
                                    imageVector = Icons.Default.Refresh,
                                    contentDescription = "مزامنة الرصيد",
                                    tint = animatedHeaderColor,
                                    modifier = Modifier
                                        .size(24.dp)
                                        .rotate(animatedRotation)
                                )
                            }
                        }

                        // Center: "رصيدي" with eye icon and masked/actual balance
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp),
                            modifier = Modifier.clickable { isBalanceVisible = !isBalanceVisible }
                        ) {
                            Text(
                                text = "رصيدي",
                                style = MaterialTheme.typography.titleLarge.copy(
                                    fontWeight = FontWeight.Bold,
                                    color = Color.White
                                )
                            )
                            Icon(
                                imageVector = if (isBalanceVisible) Icons.Default.Visibility else Icons.Default.VisibilityOff,
                                contentDescription = "إظهار/إخفاء الرصيد",
                                tint = Color.White,
                                modifier = Modifier.size(20.dp)
                            )
                            Text(
                                text = if (isBalanceVisible) "${formatMoney(wallet.balanceYer)} ر.ي" else "*****",
                                style = MaterialTheme.typography.titleMedium.copy(
                                    fontWeight = FontWeight.Bold,
                                    color = Color.White
                                )
                            )
                        }

                        // Right: Settings Gear button + Back arrow
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            Surface(
                                shape = CircleShape,
                                color = Color.White,
                                shadowElevation = 3.dp,
                                modifier = Modifier
                                    .size(44.dp)
                                    .clickable { onBackClick() }
                            ) {
                                Box(contentAlignment = Alignment.Center) {
                                    Icon(
                                        imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                                        contentDescription = "رجوع",
                                        tint = animatedHeaderColor,
                                        modifier = Modifier.size(24.dp)
                                    )
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(16.dp))

                    // Title: "تسديد شبكات الاتصالات اليمنية"
                    Text(
                        text = "تسديد شبكات الاتصالات اليمنية",
                        style = MaterialTheme.typography.titleMedium.copy(
                            fontWeight = FontWeight.Bold,
                            color = Color.White
                        ),
                        modifier = Modifier.fillMaxWidth(),
                        textAlign = TextAlign.Center
                    )

                    Spacer(modifier = Modifier.height(12.dp))

                    // Operators circular badges row (Matching Photo 3)
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        listOf(
                            Triple("يمن موبايل", "77", Color(0xFFC62828)),
                            Triple("سبأفون", "71", Color(0xFF0288D1)),
                            Triple("YOU", "73", Color(0xFFF9A825)),
                            Triple("واي Y", "70", Color(0xFF7B1FA2)),
                            Triple("يمن نت", "01", Color(0xFF0D47A1)),
                            Triple("عدن نت", "02", Color(0xFF00838F)),
                            Triple("الهاتف الثابت", "04", Color(0xFF1565C0)),
                            Triple("4G موبايل", "78", Color(0xFFB71C1C))
                        ).forEach { (name, prefix, badgeColor) ->
                            val isCurrent = detectedOperator.arabicName.contains(name) ||
                                    (detectedOperator == YemenOperator.YEMEN_MOBILE && (name.contains("موبايل") || prefix == "77"))
                            Surface(
                                shape = RoundedCornerShape(20.dp),
                                color = if (isCurrent) Color.White else Color.White.copy(alpha = 0.22f),
                                modifier = Modifier.clickable {
                                    phoneNumber = prefix
                                }
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                                ) {
                                    Box(
                                        modifier = Modifier
                                            .size(10.dp)
                                            .clip(CircleShape)
                                            .background(badgeColor)
                                    )
                                    Text(
                                        text = name,
                                        style = MaterialTheme.typography.labelSmall.copy(
                                            color = if (isCurrent) badgeColor else Color.White,
                                            fontWeight = if (isCurrent) FontWeight.Bold else FontWeight.Normal
                                        )
                                    )
                                }
                            }
                        }
                    }
                }
            }
        }

        // 2. Phone Input Card (Matching Photos 1, 2, 3)
        item {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 12.dp)
            ) {
                Text(
                    text = "ادخل رقم الهاتف :",
                    style = MaterialTheme.typography.bodyMedium.copy(
                        fontWeight = FontWeight.SemiBold,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    ),
                    modifier = Modifier.padding(bottom = 8.dp)
                )

                Card(
                    modifier = Modifier
                        .fillMaxWidth()
                        .testTag("phone_recharge_card"),
                    shape = RoundedCornerShape(18.dp),
                    colors = CardDefaults.cardColors(containerColor = Color.White),
                    elevation = CardDefaults.cardElevation(defaultElevation = 4.dp)
                ) {
                    Column(modifier = Modifier.padding(14.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            // Left: Contact book icon and clear button
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                Surface(
                                    shape = RoundedCornerShape(10.dp),
                                    color = detectedOperator.primaryColor.copy(alpha = 0.12f),
                                    modifier = Modifier
                                        .size(42.dp)
                                        .clickable {
                                            phoneNumber = "770123456"
                                        }
                                ) {
                                    Box(contentAlignment = Alignment.Center) {
                                        Icon(
                                            imageVector = Icons.Default.ContactPhone,
                                            contentDescription = "دليل الهاتف",
                                            tint = detectedOperator.primaryColor,
                                            modifier = Modifier.size(24.dp)
                                        )
                                    }
                                }

                                if (phoneNumber.isNotEmpty()) {
                                    IconButton(
                                        onClick = { phoneNumber = "" },
                                        modifier = Modifier.size(28.dp)
                                    ) {
                                        Icon(
                                            imageVector = Icons.Default.Clear,
                                            contentDescription = "مسح الرقم",
                                            tint = Color.Gray,
                                            modifier = Modifier.size(20.dp)
                                        )
                                    }
                                }

                                // Country code +967
                                Text(
                                    text = "+967",
                                    style = MaterialTheme.typography.titleMedium.copy(
                                        fontWeight = FontWeight.Bold,
                                        color = Color(0xFF37474F)
                                    )
                                )
                            }

                            // Center & Right: Phone Number Input + Operator Badge + Favorite Heart
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                // Number Length Indicator
                                if (phoneNumber.isNotEmpty()) {
                                    Surface(
                                        shape = CircleShape,
                                        color = detectedOperator.lightColor
                                    ) {
                                        Text(
                                            text = "${phoneNumber.length}",
                                            style = MaterialTheme.typography.labelSmall.copy(
                                                color = detectedOperator.primaryColor,
                                                fontWeight = FontWeight.Bold
                                            ),
                                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                        )
                                    }
                                }

                                // Phone number text field
                                OutlinedTextField(
                                    value = phoneNumber,
                                    onValueChange = { input ->
                                        // digits only, max 9
                                        val filtered = input.filter { it.isDigit() }
                                        if (filtered.length <= 9) {
                                            phoneNumber = filtered
                                        }
                                    },
                                    placeholder = { Text("777777777", color = Color.LightGray) },
                                    singleLine = true,
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                    textStyle = MaterialTheme.typography.titleMedium.copy(
                                        fontWeight = FontWeight.Bold,
                                        textAlign = TextAlign.Start,
                                        color = Color(0xFF263238),
                                        letterSpacing = 1.sp
                                    ),
                                    colors = OutlinedTextFieldDefaults.colors(
                                        focusedBorderColor = detectedOperator.primaryColor,
                                        unfocusedBorderColor = Color.Transparent,
                                        focusedContainerColor = Color.Transparent,
                                        unfocusedContainerColor = Color.Transparent
                                    ),
                                    modifier = Modifier.width(135.dp)
                                )

                                // Dynamic Operator Badge (Matching Sabafon/YemenMobile circular badge in Photos)
                                Surface(
                                    shape = RoundedCornerShape(12.dp),
                                    color = detectedOperator.lightColor,
                                    border = androidx.compose.foundation.BorderStroke(1.dp, detectedOperator.primaryColor.copy(alpha = 0.4f)),
                                    modifier = Modifier.padding(2.dp)
                                ) {
                                    Column(
                                        horizontalAlignment = Alignment.CenterHorizontally,
                                        modifier = Modifier.padding(horizontal = 8.dp, vertical = 4.dp)
                                    ) {
                                        Text(
                                            text = detectedOperator.shortBadge,
                                            style = MaterialTheme.typography.labelSmall.copy(
                                                color = detectedOperator.primaryColor,
                                                fontWeight = FontWeight.Bold,
                                                fontSize = 11.sp
                                            ),
                                            maxLines = 1
                                        )
                                    }
                                }

                                // Favorite Heart
                                IconButton(
                                    onClick = { isFavorite = !isFavorite },
                                    modifier = Modifier.size(32.dp)
                                ) {
                                    Icon(
                                        imageVector = if (isFavorite) Icons.Default.Favorite else Icons.Default.FavoriteBorder,
                                        contentDescription = "حفظ في المفضلة",
                                        tint = if (isFavorite) Color.Red else Color.LightGray
                                    )
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(14.dp))

                // 3. Tab Row underneath the card: [ رصيد | فوري | باقات | جملة | ريال ] (Matching Photos 1 & 2)
                Card(
                    modifier = Modifier.fillMaxWidth(),
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(
                        containerColor = detectedOperator.lightColor
                    ),
                    elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                ) {
                    TabRow(
                        selectedTabIndex = selectedTabIndex.coerceIn(0, (tabs.size - 1).coerceAtLeast(0)),
                        containerColor = Color.Transparent,
                        contentColor = detectedOperator.primaryColor,
                        indicator = { tabPositions ->
                            if (selectedTabIndex in tabPositions.indices) {
                                TabRowDefaults.SecondaryIndicator(
                                    modifier = Modifier.tabIndicatorOffset(tabPositions[selectedTabIndex]),
                                    color = detectedOperator.primaryColor,
                                    height = 3.dp
                                )
                            }
                        },
                        divider = {}
                    ) {
                        tabs.forEachIndexed { index, tabTitle ->
                            val isSelected = selectedTabIndex == index
                            Tab(
                                selected = isSelected,
                                onClick = { selectedTabIndex = index },
                                text = {
                                    Text(
                                        text = tabTitle,
                                        style = MaterialTheme.typography.titleSmall.copy(
                                            fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                            color = if (isSelected) detectedOperator.primaryColor else Color(0xFF546E7A)
                                        )
                                    )
                                }
                            )
                        }
                    }
                }
            }
        }

        // 4. Tab Content (Packages List or Amount Selection)
        if (activeTabName == "باقات") {
            item {
                Text(
                    text = "باقات ${detectedOperator.arabicName} المتاحة للتفعيل الفوري :",
                    style = MaterialTheme.typography.titleSmall.copy(
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF37474F)
                    ),
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp)
                )
            }

            if (currentPackages.isEmpty()) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(24.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Text(
                            text = "جاري تحديث قائمة باقات ${detectedOperator.arabicName}...",
                            style = MaterialTheme.typography.bodyMedium.copy(color = Color.Gray)
                        )
                    }
                }
            } else {
                items(currentPackages) { pkg ->
                    TelecomPackageCard(
                        pkg = pkg,
                        operator = detectedOperator,
                        formatMoney = formatMoney,
                        onRechargeClick = {
                            val targetNumber = phoneNumber.ifBlank { "770123456" }
                            onRechargeSubmit(targetNumber, detectedOperator.arabicName, activeTabName, pkg.name, pkg.priceYer)
                        },
                        modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp)
                    )
                }
            }
        } else {
            // "رصيد" or "فوري" or "ريال" or "جملة"
            item {
                AmountSelectorSection(
                    activeTabName = activeTabName,
                    operator = detectedOperator,
                    phoneNumber = phoneNumber,
                    customAmount = customAmount,
                    onCustomAmountChange = { customAmount = it },
                    formatMoney = formatMoney,
                    onPay = { amount ->
                        val targetNumber = phoneNumber.ifBlank { "770123456" }
                        onRechargeSubmit(
                            targetNumber,
                            detectedOperator.arabicName,
                            activeTabName,
                            "شحن $activeTabName فئة ${formatMoney(amount)} ر.ي",
                            amount
                        )
                    },
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp)
                )
            }
        }
    }
}

@Composable
fun TelecomPackageCard(
    pkg: TelecomPackage,
    operator: YemenOperator,
    formatMoney: (Double) -> String,
    onRechargeClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(14.dp)) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = pkg.name,
                    style = MaterialTheme.typography.titleMedium.copy(
                        fontWeight = FontWeight.Bold,
                        color = Color(0xFF263238)
                    ),
                    modifier = Modifier.weight(1f)
                )

                Surface(
                    shape = RoundedCornerShape(8.dp),
                    color = operator.lightColor
                ) {
                    Text(
                        text = "${formatMoney(pkg.priceYer)} ر.ي",
                        style = MaterialTheme.typography.titleSmall.copy(
                            fontWeight = FontWeight.Bold,
                            color = operator.primaryColor
                        ),
                        modifier = Modifier.padding(horizontal = 10.dp, vertical = 4.dp)
                    )
                }
            }

            Spacer(modifier = Modifier.height(6.dp))

            Text(
                text = pkg.description,
                style = MaterialTheme.typography.bodySmall.copy(
                    color = Color(0xFF546E7A),
                    lineHeight = 18.sp
                )
            )

            Spacer(modifier = Modifier.height(12.dp))

            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Check,
                        contentDescription = null,
                        tint = Color(0xFF2E7D32),
                        modifier = Modifier.size(16.dp)
                    )
                    Text(
                        text = "تفعيل فوري مباشر",
                        style = MaterialTheme.typography.labelSmall.copy(color = Color(0xFF2E7D32))
                    )
                }

                Button(
                    onClick = onRechargeClick,
                    shape = RoundedCornerShape(10.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = operator.primaryColor),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 6.dp)
                ) {
                    Text(
                        text = "تسديد فوري",
                        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold)
                    )
                }
            }
        }
    }
}

@Composable
fun AmountSelectorSection(
    activeTabName: String,
    operator: YemenOperator,
    phoneNumber: String,
    customAmount: String,
    onCustomAmountChange: (String) -> Unit,
    formatMoney: (Double) -> String,
    onPay: (Double) -> Unit,
    modifier: Modifier = Modifier
) {
    val quickAmounts = when (activeTabName) {
        "جملة" -> listOf(5000.0, 10000.0, 20000.0, 50000.0)
        "ريال" -> listOf(200.0, 500.0, 1000.0, 2000.0, 3000.0)
        else -> listOf(500.0, 1000.0, 2000.0, 3000.0, 5000.0, 10000.0)
    }

    Card(
        modifier = modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(
                text = "اختر مبلغ السداد لخدمة ($activeTabName) :",
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold)
            )

            Spacer(modifier = Modifier.height(12.dp))

            // Quick Amount Chips Grid
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                quickAmounts.forEach { amt ->
                    val isSelected = customAmount == amt.toInt().toString()
                    Surface(
                        shape = RoundedCornerShape(10.dp),
                        color = if (isSelected) operator.primaryColor else operator.lightColor,
                        modifier = Modifier.clickable {
                            onCustomAmountChange(amt.toInt().toString())
                        }
                    ) {
                        Text(
                            text = "${formatMoney(amt)} ر.ي",
                            style = MaterialTheme.typography.labelMedium.copy(
                                fontWeight = FontWeight.Bold,
                                color = if (isSelected) Color.White else operator.primaryColor
                            ),
                            modifier = Modifier.padding(horizontal = 14.dp, vertical = 8.dp)
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Custom Amount input
            OutlinedTextField(
                value = customAmount,
                onValueChange = { input ->
                    onCustomAmountChange(input.filter { it.isDigit() })
                },
                label = { Text("أو أدخل مبلغاً مخصصاً (بالريال اليمني)") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                singleLine = true,
                shape = RoundedCornerShape(12.dp),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedBorderColor = operator.primaryColor
                ),
                modifier = Modifier.fillMaxWidth()
            )

            Spacer(modifier = Modifier.height(18.dp))

            // Summary row
            val finalAmount = customAmount.toDoubleOrNull() ?: 0.0
            Surface(
                shape = RoundedCornerShape(12.dp),
                color = Color(0xFFF1F5F9),
                modifier = Modifier.fillMaxWidth()
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Column {
                        Text(
                            text = "الإجمالي المطلوب خصمه:",
                            style = MaterialTheme.typography.bodySmall.copy(color = Color(0xFF64748B))
                        )
                        Text(
                            text = "${formatMoney(finalAmount)} ر.ي",
                            style = MaterialTheme.typography.titleMedium.copy(
                                fontWeight = FontWeight.Bold,
                                color = operator.primaryColor
                            )
                        )
                    }

                    Column(horizontalAlignment = Alignment.End) {
                        Text(
                            text = "رسوم الخدمة:",
                            style = MaterialTheme.typography.bodySmall.copy(color = Color(0xFF64748B))
                        )
                        Text(
                            text = "مجاناً (0 ر.ي)",
                            style = MaterialTheme.typography.labelMedium.copy(
                                fontWeight = FontWeight.Bold,
                                color = Color(0xFF2E7D32)
                            )
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(16.dp))

            // Big Pay Button
            Button(
                onClick = {
                    if (finalAmount > 0) {
                        onPay(finalAmount)
                    }
                },
                enabled = finalAmount > 0,
                shape = RoundedCornerShape(12.dp),
                colors = ButtonDefaults.buttonColors(containerColor = operator.primaryColor),
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp)
            ) {
                Text(
                    text = "تسديد الآن خصماً من الرصيد",
                    style = MaterialTheme.typography.titleSmall.copy(
                        fontWeight = FontWeight.Bold,
                        color = Color.White
                    )
                )
            }
        }
    }
}
