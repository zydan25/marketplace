@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.example.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.SessionStore
import com.example.data.model.TelecomPackage
import com.example.data.model.WalletAccount
import com.example.data.remote.NetworkClient
import com.example.data.remote.ServiceCategoryDto
import com.example.data.remote.ServiceCatalogResponse
import com.example.data.remote.ServiceDto
import com.example.data.remote.ServiceItemDto
import com.example.data.remote.ServiceMainCategoryDto
import com.example.data.remote.ServiceRequestPayload
import com.example.data.remote.ServiceTransactionDto
import com.example.data.repository.StoreRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.UUID

private val ScreenBg = Color(0xFFF0F1F5)
private val White = Color.White
private val TextDark = Color(0xFF24252B)
private val Muted = Color(0xFF7D7F86)
private val ErrorRed = Color(0xFFC33A3A)
private val SuccessGreen = Color(0xFF218838)
private val YemenMobilePink = Color(0xFFB30B4C)
private val SabafonBlue = Color(0xFF1675A7)
private val YouYellow = Color(0xFFF1C21B)
private val WhyPurple = Color(0xFF503393)
private val FourGBlue = Color(0xFF137EAE)
private val YemenNetPurple = Color(0xFF373083)
private val ControlBlue = Color(0xFF3B9AE8)

private enum class PaymentAction { BALANCE, INSTANT, PACKAGES, WHOLESALE, POSTPAID }
private enum class ProviderKind { YEMEN_MOBILE, SABAFON, YOU, WHY, FOUR_G, YEMEN_NET }

private fun digits(value: String): String = buildString(value.length) {
    value.forEach { ch ->
        append(
            when (ch) {
                '٠' -> '0'; '١' -> '1'; '٢' -> '2'; '٣' -> '3'; '٤' -> '4'
                '٥' -> '5'; '٦' -> '6'; '٧' -> '7'; '٨' -> '8'; '٩' -> '9'
                '۰' -> '0'; '۱' -> '1'; '۲' -> '2'; '۳' -> '3'; '۴' -> '4'
                '۵' -> '5'; '۶' -> '6'; '۷' -> '7'; '۸' -> '8'; '۹' -> '9'
                else -> ch
            }
        )
    }
}

private fun normalizePhone(value: String): String {
    val raw = digits(value).filter(Char::isDigit)
    return when {
        raw.startsWith("00967") -> raw.removePrefix("00967")
        raw.startsWith("967") -> raw.removePrefix("967")
        else -> raw
    }
}

private fun detectProviderKind(phone: String): ProviderKind? {
    val p = normalizePhone(phone)
    return when {
        p.startsWith("77") || p.startsWith("78") -> ProviderKind.YEMEN_MOBILE
        p.startsWith("71") -> ProviderKind.SABAFON
        p.startsWith("73") -> ProviderKind.YOU
        p.startsWith("70") -> ProviderKind.WHY
        p.startsWith("10") -> ProviderKind.FOUR_G
        p.startsWith("0") -> ProviderKind.YEMEN_NET
        else -> null
    }
}

private fun providerKey(provider: ServiceCategoryDto?): String =
    "${provider?.slug.orEmpty()} ${provider?.name.orEmpty()}".lowercase()

private fun providerMatches(provider: ServiceCategoryDto, kind: ProviderKind): Boolean {
    val k = providerKey(provider)
    return when (kind) {
        ProviderKind.YEMEN_MOBILE -> "yemen-mobile" in k || "yemenmobile" in k || "يمن موبايل" in k
        ProviderKind.SABAFON -> "sabafon" in k || "سبأفون" in k
        ProviderKind.YOU -> "\"you\"" in k || k == "you" || " you " in " $k " || "يو" in k
        ProviderKind.WHY -> "why" in k || "واي" in k
        ProviderKind.FOUR_G -> "4g" in k || "4-g" in k || "فورجي" in k || "يمن 4" in k
        ProviderKind.YEMEN_NET -> "yemen-net" in k || "yemennet" in k || "يمن نت" in k
    }
}

private fun findProviderByPhone(phone: String, providers: List<ServiceCategoryDto>): ServiceCategoryDto? =
    detectProviderKind(phone)?.let { kind -> providers.firstOrNull { providerMatches(it, kind) } }

private fun providerColor(provider: ServiceCategoryDto?): Color {
    if (provider == null) return ControlBlue
    return when {
        providerMatches(provider, ProviderKind.YEMEN_MOBILE) -> YemenMobilePink
        providerMatches(provider, ProviderKind.SABAFON) -> SabafonBlue
        providerMatches(provider, ProviderKind.YOU) -> YouYellow
        providerMatches(provider, ProviderKind.WHY) -> WhyPurple
        providerMatches(provider, ProviderKind.FOUR_G) -> FourGBlue
        providerMatches(provider, ProviderKind.YEMEN_NET) -> YemenNetPurple
        else -> ControlBlue
    }
}

private fun providerTitle(provider: ServiceCategoryDto?): String {
    if (provider == null) return "شبكة السداد"
    return when {
        providerMatches(provider, ProviderKind.YEMEN_MOBILE) -> "Yemen Mobile"
        providerMatches(provider, ProviderKind.SABAFON) -> "سبأفون"
        providerMatches(provider, ProviderKind.YOU) -> "YOU"
        providerMatches(provider, ProviderKind.WHY) -> "WHY"
        providerMatches(provider, ProviderKind.FOUR_G) -> "Yemen 4G"
        providerMatches(provider, ProviderKind.YEMEN_NET) -> "Yemen Net"
        else -> provider.name.ifBlank { "شبكة السداد" }
    }
}

private fun providerMark(provider: ServiceCategoryDto?): String {
    if (provider == null) return "K"
    return when {
        providerMatches(provider, ProviderKind.YEMEN_MOBILE) -> "YM"
        providerMatches(provider, ProviderKind.SABAFON) -> "S"
        providerMatches(provider, ProviderKind.YOU) -> "YOU"
        providerMatches(provider, ProviderKind.WHY) -> "WHY"
        providerMatches(provider, ProviderKind.FOUR_G) -> "4G"
        providerMatches(provider, ProviderKind.YEMEN_NET) -> "YN"
        else -> "K"
    }
}

private fun isYemenNet(provider: ServiceCategoryDto?): Boolean =
    providerMatches(provider, ProviderKind.YEMEN_NET)

private fun isYemenMobile(provider: ServiceCategoryDto?): Boolean =
    providerMatches(provider, ProviderKind.YEMEN_MOBILE)

private fun flatten(category: ServiceCategoryDto): List<ServiceDto> =
    category.services + category.children.flatMap(::flatten)

private fun serviceText(service: ServiceDto): String = "${service.code} ${service.name}".lowercase()

private fun actionFromService(service: ServiceDto): PaymentAction {
    val s = serviceText(service)
    return when {
        "جملة" in s || "wholesale" in s -> PaymentAction.WHOLESALE
        "فوتر" in s || "postpaid" in s || "فاتورة" in s -> PaymentAction.POSTPAID
        "فوري" in s || "instant" in s -> PaymentAction.INSTANT
        "offer" in s || "باقة" in s || "باقات" in s || "عروض" in s -> PaymentAction.PACKAGES
        else -> PaymentAction.BALANCE
    }
}

private fun queryService(services: List<ServiceDto>, action: PaymentAction): ServiceDto? =
    services.firstOrNull { it.serviceKind == "query" && actionFromService(it) == action }
        ?: services.firstOrNull { it.serviceKind == "query" }

private fun purchaseService(services: List<ServiceDto>, action: PaymentAction): ServiceDto? =
    services.firstOrNull { it.serviceKind == "purchase" && actionFromService(it) == action }

private fun actionLabel(action: PaymentAction, provider: ServiceCategoryDto?): String {
    if (providerMatches(provider ?: return when (action) {
            PaymentAction.BALANCE -> "الرصيد"
            PaymentAction.INSTANT -> "فوري"
            PaymentAction.PACKAGES -> "باقات"
            PaymentAction.WHOLESALE -> "جملة"
            PaymentAction.POSTPAID -> "فوترة"
        }, ProviderKind.FOUR_G)) {
        return when (action) {
            PaymentAction.PACKAGES -> "باقة يمن 4G"
            PaymentAction.BALANCE -> "رصيد يمن 4G"
            PaymentAction.WHOLESALE -> "تغيير الباقة"
            PaymentAction.INSTANT -> "فايبر"
            PaymentAction.POSTPAID -> "الفواتير"
        }
    }
    return when (action) {
        PaymentAction.BALANCE -> "الرصيد"
        PaymentAction.INSTANT -> "فوري"
        PaymentAction.PACKAGES -> "الباقات"
        PaymentAction.WHOLESALE -> "جملة"
        PaymentAction.POSTPAID -> "الفوترة"
    }
}

private fun formatNumber(value: Double): String =
    if (value % 1.0 == 0.0) value.toInt().toString() else String.format("%.2f", value)

private fun resultLoan(result: Map<String, Any?>): Double {
    result.forEach { (key, value) ->
        val k = key.lowercase().replace("_", "").replace(" ", "")
        if (k.contains("loan") || k.contains("sulfa") || k.contains("solfa") || k.contains("سلفة") || k.contains("سلف")) {
            value?.toString()?.toDoubleOrNull()?.let { return it }
        }
    }
    return 0.0
}

private fun displayValue(value: Any?): String = when (value) {
    null -> "—"
    is Map<*, *> -> value.entries.joinToString("\n") { "${it.key}: ${displayValue(it.value)}" }
    is List<*> -> value.joinToString("\n") { displayValue(it) }
    else -> value.toString()
}

private fun resultLabel(key: String): String = when (key.lowercase().replace("_", "")) {
    "balance" -> "الرصيد"
    "availablecredit" -> "الرصيد المتاح"
    "loanamount", "loan" -> "السلفة"
    "message", "resultdesc" -> "الرسالة"
    "resultcode" -> "رمز النتيجة"
    "mobiletype", "mobiltype" -> "نوع الخط"
    "sequenceid", "resultid" -> "رقم العملية"
    "offername" -> "اسم الباقة"
    "offerid" -> "كود الباقة"
    "offerstartdate" -> "بداية الباقة"
    "offerenddate" -> "نهاية الباقة"
    "status" -> "الحالة"
    else -> key
}

private fun resultOfferItems(result: Map<String, Any?>): List<ServiceItemDto> {
    val found = mutableListOf<ServiceItemDto>()
    var id = 1L
    fun walk(value: Any?) {
        when (value) {
            is Map<*, *> -> {
                val m = value.entries.associate { it.key.toString().lowercase() to it.value }
                val name = (m["offername"] ?: m["name"] ?: m["packagename"])?.toString()
                if (!name.isNullOrBlank()) {
                    found += ServiceItemDto(
                        id++,
                        "offer",
                        name,
                        (m["amount"] ?: m["price"] ?: m["offerprice"])?.toString(),
                        "YER",
                        m.mapNotNull { (k, v) -> v?.let { k to it.toString() } }.toMap(),
                        emptyMap()
                    )
                }
                value.values.forEach(::walk)
            }
            is List<*> -> value.forEach(::walk)
        }
    }
    result.values.forEach(::walk)
    return found.distinctBy { it.name + "|" + it.price }
}

@Composable
private fun ProviderLogo(provider: ServiceCategoryDto?, selected: Boolean, modifier: Modifier = Modifier) {
    val accent = providerColor(provider)
    Surface(
        modifier = modifier.size(48.dp),
        shape = CircleShape,
        color = if (selected) White.copy(alpha = .14f) else accent.copy(alpha = .10f)
    ) {
        Box(contentAlignment = Alignment.Center) {
            Text(providerMark(provider), color = if (selected) White else accent, fontWeight = FontWeight.Black, fontSize = 10.sp)
        }
    }
}

@Composable
private fun ProviderCard(provider: ServiceCategoryDto, selected: Boolean, onClick: () -> Unit) {
    val accent = providerColor(provider)
    Surface(
        modifier = Modifier.width(92.dp).clickable(onClick = onClick),
        shape = RoundedCornerShape(14.dp),
        color = if (selected) accent else White,
        shadowElevation = if (selected) 3.dp else 1.dp
    ) {
        Column(
            modifier = Modifier.padding(vertical = 7.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            ProviderLogo(provider, selected, Modifier.size(34.dp))
            Text(providerTitle(provider), color = if (selected) White else TextDark, fontSize = 9.sp, fontWeight = FontWeight.Bold, maxLines = 1)
        }
    }
}

@Composable
private fun ActionTabs(provider: ServiceCategoryDto?, selected: PaymentAction, onSelect: (PaymentAction) -> Unit) {
    val labels = if (isYemenNet(provider)) {
        listOf(PaymentAction.BALANCE to "الإنترنت الأرضي", PaymentAction.INSTANT to "الهاتف الثابت")
    } else if (providerMatches(provider ?: return, ProviderKind.FOUR_G)) {
        listOf(
            PaymentAction.PACKAGES to "باقة يمن 4G",
            PaymentAction.BALANCE to "رصيد يمن 4G",
            PaymentAction.WHOLESALE to "تغيير الباقة",
            PaymentAction.INSTANT to "فايبر"
        )
    } else {
        listOf(
            PaymentAction.BALANCE,
            PaymentAction.INSTANT,
            PaymentAction.PACKAGES,
            PaymentAction.WHOLESALE,
            PaymentAction.POSTPAID
        ).map { it to actionLabel(it, provider) }
    }
    val accent = providerColor(provider)
    Surface(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(16.dp),
        color = accent.copy(alpha = .18f)
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
            horizontalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            labels.forEach { (action, label) ->
                Surface(
                    modifier = Modifier.width(if (labels.size <= 2) 1f.run { 152.dp } else 96.dp).clickable { onSelect(action) },
                    shape = RoundedCornerShape(13.dp),
                    color = if (selected == action) accent else Color.Transparent
                ) {
                    Box(modifier = Modifier.padding(vertical = 13.dp, horizontal = 9.dp), contentAlignment = Alignment.Center) {
                        Text(label, color = if (selected == action) White else TextDark, fontWeight = FontWeight.Black, fontSize = 11.sp, textAlign = TextAlign.Center, maxLines = 1)
                    }
                }
            }
        }
    }
}

@Composable
private fun ProviderInputCard(
    provider: ServiceCategoryDto?,
    phone: String,
    onPhoneChange: (String) -> Unit
) {
    val accent = providerColor(provider)
    val detected = detectProviderKind(phone)
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = White),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp)
    ) {
        Column(modifier = Modifier.padding(horizontal = 11.dp, vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Surface(modifier = Modifier.size(50.dp), shape = CircleShape, color = if (provider != null) accent else ControlBlue.copy(alpha = .10f)) {
                    Box(contentAlignment = Alignment.Center) {
                        ProviderLogo(provider, selected = provider != null, Modifier.size(42.dp))
                    }
                }
                Spacer(Modifier.width(8.dp))
                Column(modifier = Modifier.weight(1f), horizontalAlignment = Alignment.End) {
                    Text("رصيدي", color = accent, fontWeight = FontWeight.Black, fontSize = 22.sp)
                    Text("******  •  رصيد مخفي", color = Muted, fontWeight = FontWeight.Bold, fontSize = 10.sp)
                }
                Icon(Icons.Default.Info, contentDescription = null, tint = accent, modifier = Modifier.size(25.dp))
            }
            Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Surface(modifier = Modifier.size(36.dp), shape = CircleShape, color = accent.copy(alpha = .11f)) {
                    Box(contentAlignment = Alignment.Center) { Icon(Icons.Default.AccountBalanceWallet, null, tint = accent) }
                }
                Spacer(Modifier.width(7.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Text("+967", color = Muted, fontSize = 15.sp, fontWeight = FontWeight.Bold, modifier = Modifier.width(47.dp), textAlign = TextAlign.Center)
                        OutlinedTextField(
                            value = phone,
                            onValueChange = onPhoneChange,
                            modifier = Modifier.weight(1f),
                            singleLine = true,
                            label = { Text("رقم الهاتف") },
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                            leadingIcon = { Icon(Icons.Default.Call, null, tint = accent) },
                            trailingIcon = { Icon(Icons.Default.FavoriteBorder, null, tint = accent) },
                            shape = RoundedCornerShape(8.dp)
                        )
                    }
                    detected?.let { kind ->
                        Text(
                            when (kind) {
                                ProviderKind.YEMEN_MOBILE -> "تم التعرف على يمن موبايل من البادئة 77 / 78"
                                ProviderKind.SABAFON -> "تم التعرف على سبأفون من البادئة 71"
                                ProviderKind.YOU -> "تم التعرف على YOU من البادئة 73"
                                ProviderKind.WHY -> "تم التعرف على WHY من البادئة 70"
                                ProviderKind.FOUR_G -> "تم التعرف على Yemen 4G من البادئة 10"
                                ProviderKind.YEMEN_NET -> "تم التعرف على يمن نت لأن الرقم يبدأ بـ 0"
                            },
                            color = accent,
                            fontSize = 8.sp,
                            fontWeight = FontWeight.Bold,
                            textAlign = TextAlign.End,
                            modifier = Modifier.fillMaxWidth().padding(end = 4.dp)
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun AmountCard(amount: String, onAmountChange: (String) -> Unit, accent: Color) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = White),
        elevation = CardDefaults.cardElevation(defaultElevation = 0.dp)
    ) {
        Column(modifier = Modifier.padding(horizontal = 14.dp, vertical = 12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("*ادخل المبلغ", color = TextDark, fontWeight = FontWeight.Black, fontSize = 17.sp, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.End)
            OutlinedTextField(
                value = amount,
                onValueChange = onAmountChange,
                modifier = Modifier.fillMaxWidth(),
                singleLine = true,
                label = { Text("المبلغ") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                leadingIcon = { Icon(Icons.Default.Info, null, tint = accent) },
                trailingIcon = { Text("ر.ي", color = accent, fontWeight = FontWeight.Black, fontSize = 14.sp) },
                shape = RoundedCornerShape(8.dp)
            )
        }
    }
}

@Composable
private fun ResultTable(result: Map<String, Any?>, loan: Double, accent: Color) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(18.dp),
        colors = CardDefaults.cardColors(containerColor = White),
        elevation = CardDefaults.cardElevation(0.dp)
    ) {
        Column(Modifier.fillMaxWidth()) {
            result.entries.sortedBy { it.key }.forEach { (key, value) ->
                Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                    Box(modifier = Modifier.weight(1f).background(Color(0xFFFDFDFD)).padding(10.dp), contentAlignment = Alignment.CenterEnd) {
                        Text(displayValue(value), color = TextDark, fontWeight = FontWeight.Bold, fontSize = 10.sp, textAlign = TextAlign.End)
                    }
                    Box(modifier = Modifier.weight(1f).background(accent.copy(alpha = .17f)).padding(10.dp), contentAlignment = Alignment.CenterEnd) {
                        Text(resultLabel(key), color = accent, fontWeight = FontWeight.Black, fontSize = 11.sp, textAlign = TextAlign.End)
                    }
                }
            }
            Row(modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Box(modifier = Modifier.weight(1f).background(Color(0xFFFFFAFA)).padding(10.dp), contentAlignment = Alignment.CenterEnd) {
                    Text(formatNumber(loan), color = YemenMobilePink, fontWeight = FontWeight.Black, fontSize = 12.sp)
                }
                Box(modifier = Modifier.weight(1f).background(YemenMobilePink.copy(alpha = .10f)).padding(10.dp), contentAlignment = Alignment.CenterEnd) {
                    Text("السلفة الحالية", color = YemenMobilePink, fontWeight = FontWeight.Black, fontSize = 11.sp)
                }
            }
        }
    }
}

@Composable
private fun PackageTile(item: ServiceItemDto, accent: Color, onClick: () -> Unit) {
    Card(
        modifier = Modifier.aspectRatio(.72f).clickable(onClick = onClick),
        shape = RoundedCornerShape(13.dp),
        colors = CardDefaults.cardColors(containerColor = White),
        elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
    ) {
        Column(Modifier.fillMaxSize()) {
            Surface(
                modifier = Modifier.fillMaxWidth(),
                color = accent,
                shape = RoundedCornerShape(topStart = 12.dp, topEnd = 12.dp)
            ) {
                Column(Modifier.padding(vertical = 7.dp, horizontal = 6.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text("☰", color = White, fontSize = 15.sp)
                        Text("باقة", color = White, fontWeight = FontWeight.Black, fontSize = 13.sp)
                    }
                    Text(item.name, color = White, fontWeight = FontWeight.Black, fontSize = 20.sp, textAlign = TextAlign.Center, maxLines = 1)
                }
            }
            Column(Modifier.fillMaxSize().padding(horizontal = 5.dp, vertical = 6.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.SpaceBetween) {
                Text("السعر", color = accent, fontWeight = FontWeight.Black, fontSize = 11.sp)
                Surface(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(8.dp), color = Color(0xFFE4E4E5)) {
                    Text(
                        item.price?.let { "$it ${item.currency}" } ?: "—",
                        color = accent,
                        fontWeight = FontWeight.Black,
                        fontSize = 14.sp,
                        textAlign = TextAlign.Center,
                        modifier = Modifier.padding(vertical = 8.dp)
                    )
                }
            }
        }
    }
}

@Composable
private fun LoadingDialog(accent: Color) {
    AlertDialog(
        onDismissRequest = {},
        title = null,
        text = {
            Column(modifier = Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(12.dp)) {
                CircularProgressIndicator(color = accent, modifier = Modifier.size(38.dp))
                Text("الرجاء الإنتظار قليلاً....", color = TextDark, fontWeight = FontWeight.Black, fontSize = 17.sp, textAlign = TextAlign.Center)
            }
        },
        confirmButton = {}
    )
}

@Composable
private fun PurchaseConfirmDialog(name: String, amount: Double, loan: Double, accent: Color, onConfirm: () -> Unit, onCancel: () -> Unit) {
    AlertDialog(
        onDismissRequest = onCancel,
        title = { Text("تأكيد التسديد", fontWeight = FontWeight.Black) },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text(name, fontWeight = FontWeight.Black, fontSize = 17.sp)
                Text("قيمة الباقة: ${formatNumber(amount)} ر.ي")
                Text("السلفة: ${formatNumber(loan)} ر.ي", color = YemenMobilePink, fontWeight = FontWeight.Bold)
                Text("الإجمالي: ${formatNumber(amount + loan)} ر.ي", color = accent, fontSize = 18.sp, fontWeight = FontWeight.Black)
            }
        },
        confirmButton = { Button(onClick = onConfirm, colors = ButtonDefaults.buttonColors(containerColor = accent)) { Text("تسديد + تفعيل", fontWeight = FontWeight.Black) } },
        dismissButton = { TextButton(onClick = onCancel) { Text("إلغاء") } }
    )
}

@Composable
private fun ResultDetailsDialog(tx: ServiceTransactionDto, onClose: () -> Unit) {
    val pending = tx.status.orEmpty() in setOf("accepted", "queued", "processing", "pending_provider", "manual_review")
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text("نتيجة العملية", fontWeight = FontWeight.Black) },
        text = {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(7.dp)) {
                item {
                    Surface(
                        modifier = Modifier.fillMaxWidth(),
                        shape = RoundedCornerShape(12.dp),
                        color = if (tx.status == "success") Color(0xFFE9F7EE) else ScreenBg
                    ) {
                        Text(
                            when {
                                tx.status == "success" -> "تمت العملية بنجاح ✅"
                                pending -> "العملية قيد المعالجة لدى المزود ⏳"
                                tx.status == "refunded" -> "أعيد المبلغ إلى محفظتك."
                                else -> tx.errorMessage ?: "تعذر إكمال العملية."
                            },
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.padding(10.dp)
                        )
                    }
                }
                item { Text("المرجع: ${tx.id}", color = Muted, fontSize = 10.sp) }
                tx.amount?.let { item { Text("المبلغ: $it ${tx.currency.orEmpty()}", fontWeight = FontWeight.Bold) } }
                tx.providerTransactionId?.let { item { Text("رقم المزود: $it", color = Muted, fontSize = 10.sp) } }
                tx.providerTransid?.let { item { Text("رقم العملية لدى المزود: $it", color = Muted, fontSize = 10.sp) } }
            }
        },
        confirmButton = { TextButton(onClick = onClose) { Text("إغلاق") } }
    )
}

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
    val repo = remember { StoreRepository.instance }
    val baseUrl by repo.djangoBaseUrl.collectAsState()
    val session by repo.userSession.collectAsState()
    val scope = rememberCoroutineScope()

    var catalog by remember { mutableStateOf<List<ServiceMainCategoryDto>>(emptyList()) }
    var provider by remember { mutableStateOf<ServiceCategoryDto?>(null) }
    var action by remember { mutableStateOf(PaymentAction.BALANCE) }
    var service by remember { mutableStateOf<ServiceDto?>(null) }
    var selectedItem by remember { mutableStateOf<ServiceItemDto?>(null) }
    var phone by remember(session.phone) { mutableStateOf(session.phone) }
    var amount by remember { mutableStateOf("") }
    var netType by remember { mutableStateOf("adsl") }
    var smartCharge by remember { mutableStateOf(false) }
    var syncing by remember { mutableStateOf(false) }
    var working by remember { mutableStateOf(false) }
    var waitingPurchase by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var result by remember { mutableStateOf<ServiceTransactionDto?>(null) }
    var showResult by remember { mutableStateOf(false) }
    var showReports by remember { mutableStateOf(false) }
    var showConfirmation by remember { mutableStateOf(false) }
    var selectedOfferName by remember { mutableStateOf("") }
    var selectedOfferAmount by remember { mutableStateOf(0.0) }
    val values = remember { mutableStateMapOf<String, String>() }

    val cacheKey = "service_catalog_${baseUrl.trimEnd('/')}"

    fun restoreCatalog() {
        SessionStore.loadLocalString(cacheKey)?.let { raw ->
            runCatching {
                NetworkClient.moshi().adapter(ServiceCatalogResponse::class.java).fromJson(raw)
            }.getOrNull()?.let { catalog = it.categories }
        }
    }

    fun syncCatalog() {
        if (syncing) return
        val token = session.token ?: run { error = "سجل الدخول أولًا."; return }
        scope.launch {
            syncing = true
            error = null
            try {
                val response = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/").getServiceCatalog("Token $token")
                if (!response.isSuccessful || response.body() == null) {
                    throw IllegalStateException("تعذر مزامنة الخدمات (HTTP ${response.code()}).")
                }
                val body = response.body()!!
                catalog = body.categories
                SessionStore.saveLocalString(cacheKey, NetworkClient.moshi().adapter(ServiceCatalogResponse::class.java).toJson(body))
                provider = null
                service = null
                selectedItem = null
                result = null
            } catch (e: Exception) {
                error = e.localizedMessage ?: "تعذر المزامنة."
            } finally {
                syncing = false
            }
        }
    }

    LaunchedEffect(baseUrl, session.token) { restoreCatalog() }

    val root = catalog.firstOrNull { it.slug == "payments" } ?: catalog.firstOrNull { it.name.contains("تسديد") }
    val providers = root?.categories.orEmpty()
    val providerServices = provider?.let(::flatten).orEmpty().distinctBy { it.id }
    val accent = providerColor(provider)
    val yemenNet = isYemenNet(provider)
    val resultOffers = result?.result?.let(::resultOfferItems).orEmpty()
    val loan = resultLoan(result?.result.orEmpty())

    fun fillService(s: ServiceDto) {
        values.clear()
        s.fields.forEach { field ->
            if (field.key == "mobile") values[field.key] = digits(phone)
            if (field.type == "select" && field.choices.isNotEmpty()) values[field.key] = field.choices.first()
        }
        if (yemenNet) values["type"] = netType
    }

    fun selectProvider(p: ServiceCategoryDto) {
        provider = p
        service = null
        selectedItem = null
        result = null
        error = null
        values.clear()
        action = if (isYemenNet(p)) PaymentAction.BALANCE else PaymentAction.BALANCE
    }

    LaunchedEffect(phone, providers.map { it.id }) {
        val target = findProviderByPhone(phone, providers)
        if (target != null && provider?.id != target.id) selectProvider(target)
    }

    fun runQuery(s: ServiceDto) {
        val token = session.token ?: return
        service = s
        fillService(s)
        scope.launch {
            working = true
            error = null
            result = null
            try {
                val payload = values.toMutableMap()
                if (yemenNet) payload["type"] = netType
                if (smartCharge) payload["smart"] = "true"
                val idempotency = UUID.randomUUID().toString()
                val response = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/").submitServiceRequest(
                    "Token $token",
                    idempotency,
                    ServiceRequestPayload(s.id, null, null, payload, idempotency)
                )
                if (!response.isSuccessful || response.body() == null) {
                    throw IllegalStateException("تعذر الاستعلام (HTTP ${response.code()}).")
                }
                result = response.body()
            } catch (e: Exception) {
                error = e.localizedMessage ?: "فشل الاستعلام."
            } finally {
                working = false
            }
        }
    }

    fun selectAction(next: PaymentAction) {
        action = next
        selectedItem = null
        selectedOfferName = ""
        selectedOfferAmount = 0.0
        result = null
        error = null
        val target = queryService(providerServices, next)
        if (next == PaymentAction.BALANCE || next == PaymentAction.PACKAGES || next == PaymentAction.INSTANT) {
            if (target == null) {
                error = "لا توجد خدمة ${actionLabel(next, provider)} مهيأة لهذا المزود."
            } else {
                runQuery(target)
            }
        } else {
            service = purchaseService(providerServices, next)
            service?.let(::fillService)
        }
    }

    fun confirmPurchase() {
        val s = service ?: return
        val token = session.token ?: return
        if (working) return
        scope.launch {
            working = true
            waitingPurchase = true
            error = null
            result = null
            try {
                val payload = values.toMutableMap()
                selectedItem?.metadata?.get("offerid")?.let { payload["offerid"] = it }
                selectedItem?.metadata?.get("offerkey")?.let { payload["offerkey"] = it }
                if (selectedOfferName.isNotBlank()) payload["offername"] = selectedOfferName
                if (selectedOfferAmount > 0) payload["amount"] = selectedOfferAmount.toString()
                if (amount.isNotBlank()) payload["amount"] = amount
                if (yemenNet) payload["type"] = netType

                val missing = s.fields.firstOrNull { it.required && payload[it.key].isNullOrBlank() }
                if (missing != null) throw IllegalStateException("الحقل المطلوب: ${missing.label}")

                val idempotency = UUID.randomUUID().toString()
                var latest = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/").submitServiceRequest(
                    "Token $token",
                    idempotency,
                    ServiceRequestPayload(s.id, selectedItem?.type, selectedItem?.id, payload, idempotency)
                ).body() ?: throw IllegalStateException("لم تصل نتيجة العملية.")

                repeat(25) {
                    result = latest
                    if (latest.status.orEmpty() in setOf("success", "failed", "refunded", "manual_review")) return@repeat
                    delay(800)
                    val poll = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/").getServiceTransaction("Token $token", latest.id)
                    if (poll.isSuccessful && poll.body() != null) latest = poll.body()!!
                }
                result = latest
                showResult = true
                if (latest.status == "success" || latest.status == "refunded") onSyncBalance()
                if (latest.status == "success") {
                    onRechargeSubmit(
                        phone,
                        providerTitle(provider),
                        s.name,
                        selectedOfferName.ifBlank { selectedItem?.name ?: s.name },
                        latest.amount?.toDoubleOrNull() ?: selectedOfferAmount
                    )
                }
            } catch (e: Exception) {
                error = e.localizedMessage ?: "تعذر تنفيذ التسديد."
            } finally {
                waitingPurchase = false
                working = false
                showConfirmation = false
            }
        }
    }

    if (showReports) {
        ServiceReportsScreen(onBackClick = { showReports = false }, modifier = modifier)
        return
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("رصيدي", color = White, fontWeight = FontWeight.Black, fontSize = 20.sp)
                        Text("******  •  رصيد مخفي", color = White.copy(alpha = .88f), fontSize = 9.sp, fontWeight = FontWeight.Bold)
                    }
                },
                navigationIcon = {
                    IconButton(onClick = { syncCatalog() }) {
                        Surface(shape = CircleShape, color = White, modifier = Modifier.size(42.dp)) {
                            Box(contentAlignment = Alignment.Center) { Icon(Icons.Default.Refresh, "مزامنة الخدمات", tint = if (provider != null) accent else ControlBlue) }
                        }
                    }
                },
                actions = {
                    IconButton(onClick = { showReports = true }) {
                        Surface(shape = CircleShape, color = White, modifier = Modifier.size(42.dp)) {
                            Box(contentAlignment = Alignment.Center) { Icon(Icons.Default.Settings, "التقرير", tint = if (provider != null) accent else ControlBlue) }
                        }
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = accent, titleContentColor = White)
            )
        }
    ) { pad: PaddingValues ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(pad).background(ScreenBg),
            contentPadding = PaddingValues(horizontal = 12.dp, vertical = 10.dp),
            verticalArrangement = Arrangement.spacedBy(9.dp)
        ) {
            item {
                ProviderInputCard(
                    provider = provider,
                    phone = phone,
                    onPhoneChange = { value ->
                        phone = value
                        service?.let { s -> if (s.fields.any { field -> field.key == "mobile" }) values["mobile"] = digits(value) }
                    }
                )
            }

            if (providers.isNotEmpty()) {
                item {
                    Surface(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(16.dp), color = White) {
                        Column(Modifier.padding(9.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                            Text("الشبكة", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.End)
                            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                                providers.forEach { p -> ProviderCard(p, p.id == provider?.id, onClick = { selectProvider(p) }) }
                            }
                        }
                    }
                }
            }

            if (provider != null) {
                item { ActionTabs(provider = provider, selected = action, onSelect = ::selectAction) }

                if (yemenNet) {
                    item {
                        Surface(Modifier.fillMaxWidth(), RoundedCornerShape(13.dp), accent.copy(alpha = .14f)) {
                            Row(Modifier.fillMaxWidth().padding(4.dp), horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                                listOf("adsl" to "الإنترنت الأرضي", "line" to "الهاتف الثابت").forEach { (type, label) ->
                                    val selected = netType == type
                                    Surface(
                                        modifier = Modifier.weight(1f).clickable {
                                            netType = type
                                            service?.let(::runQuery)
                                        },
                                        shape = RoundedCornerShape(10.dp),
                                        color = if (selected) accent else Color.Transparent
                                    ) {
                                        Text(label, color = if (selected) White else TextDark, fontWeight = FontWeight.Black, fontSize = 11.sp, textAlign = TextAlign.Center, modifier = Modifier.padding(vertical = 10.dp))
                                    }
                                }
                            }
                        }
                    }
                }

                if (action == PaymentAction.PACKAGES) {
                    item {
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                Text("الباقات", color = TextDark, fontWeight = FontWeight.Black, fontSize = 17.sp)
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text("الشاحن الذكي", color = Muted, fontSize = 9.sp)
                                    Switch(checked = smartCharge, onCheckedChange = { smartCharge = it })
                                }
                            }
                            val items = if (resultOffers.isNotEmpty()) resultOffers else purchaseService(providerServices, PaymentAction.PACKAGES)?.items.orEmpty().take(30)
                            if (items.isEmpty()) {
                                Surface(Modifier.fillMaxWidth(), RoundedCornerShape(14.dp), White) {
                                    Text("سيتم عرض الباقات بعد استعلام الباقات من المزود.", color = Muted, fontSize = 10.sp, modifier = Modifier.padding(14.dp), textAlign = TextAlign.Center)
                                }
                            } else {
                                items.chunked(3).forEach { row ->
                                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                                        row.forEach { item ->
                                            Box(Modifier.weight(1f)) {
                                                PackageTile(item, accent) {
                                                    selectedItem = item
                                                    selectedOfferName = item.name
                                                    selectedOfferAmount = item.price?.toDoubleOrNull() ?: 0.0
                                                    service = purchaseService(providerServices, PaymentAction.PACKAGES) ?: service
                                                    showConfirmation = true
                                                }
                                            }
                                        }
                                        if (row.size < 3) repeat(3 - row.size) { Spacer(Modifier.weight(1f)) }
                                    }
                                }
                            }
                        }
                    }
                }

                if (action != PaymentAction.PACKAGES) {
                    item { AmountCard(amount = amount, onAmountChange = { amount = it }, accent = accent) }
                    item {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                            Button(
                                onClick = { service?.let { runQuery(it) } },
                                modifier = Modifier.weight(1f).height(51.dp),
                                shape = RoundedCornerShape(12.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFFFDDAE))
                            ) { Text("استعلام", color = accent, fontWeight = FontWeight.Black, fontSize = 16.sp) }
                            Button(
                                onClick = {
                                    service?.let {
                                        selectedOfferName = it.name
                                        selectedOfferAmount = amount.toDoubleOrNull() ?: it.price.toDoubleOrNull() ?: 0.0
                                        showConfirmation = true
                                    }
                                },
                                enabled = service != null && !working,
                                modifier = Modifier.weight(1f).height(51.dp),
                                shape = RoundedCornerShape(12.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFFFDDAE))
                            ) { Text("تسديد", color = accent, fontWeight = FontWeight.Black, fontSize = 16.sp) }
                        }
                    }
                }

                if (action == PaymentAction.BALANCE && result != null) {
                    item { ResultTable(result = result!!.result.orEmpty(), loan = loan, accent = accent) }
                }

                if (action != PaymentAction.BALANCE && result != null && result!!.status != "success") {
                    item {
                        Card(
                            Modifier.fillMaxWidth().clickable { showResult = true },
                            shape = RoundedCornerShape(16.dp),
                            colors = CardDefaults.cardColors(containerColor = White),
                            elevation = CardDefaults.cardElevation(1.dp)
                        ) {
                            Column(Modifier.padding(13.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                    Text("نتيجة العملية", fontWeight = FontWeight.Black, fontSize = 15.sp)
                                    Text(
                                        when (result?.status) {
                                            "success" -> "نجاح ✅"
                                            "accepted", "queued", "processing", "pending_provider", "manual_review" -> "معلقة ⏳"
                                            else -> "انتهت"
                                        },
                                        color = if (result?.status == "success") SuccessGreen else accent,
                                        fontWeight = FontWeight.Bold,
                                        fontSize = 10.sp
                                    )
                                }
                                Text("اضغط لعرض كل بيانات المزود", color = Muted, fontSize = 9.sp)
                            }
                        }
                    }
                }
            }

            error?.let { msg ->
                item {
                    Surface(Modifier.fillMaxWidth(), RoundedCornerShape(13.dp), Color(0xFFFFEEEE)) {
                        Text(msg, color = ErrorRed, textAlign = TextAlign.Center, fontSize = 10.sp, fontWeight = FontWeight.Bold, modifier = Modifier.padding(11.dp))
                    }
                }
            }
            if (syncing || working) item { Box(Modifier.fillMaxWidth().padding(12.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator(color = accent) } }
        }
    }

    if (showConfirmation) {
        PurchaseConfirmDialog(
            name = selectedOfferName.ifBlank { selectedItem?.name.orEmpty() },
            amount = selectedOfferAmount,
            loan = loan,
            accent = accent,
            onConfirm = ::confirmPurchase,
            onCancel = { showConfirmation = false }
        )
    }
    if (waitingPurchase) LoadingDialog(accent)
    if (showResult && result != null) ResultDetailsDialog(result!!, onClose = { showResult = false })
}
