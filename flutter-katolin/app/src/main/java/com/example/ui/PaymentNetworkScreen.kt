@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.example.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
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
import com.example.data.remote.ServiceCatalogResponse
import com.example.data.remote.ServiceDto
import com.example.data.remote.ServiceFieldDto
import com.example.data.remote.ServiceItemDto
import com.example.data.remote.ServiceMainCategoryDto
import com.example.data.remote.ServiceRequestPayload
import com.example.data.remote.ServiceTransactionDto
import com.example.data.repository.StoreRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.UUID

private val ScreenBg = Color(0xFFF1F2F6)
private val White = Color.White
private val TextDark = Color(0xFF172238)
private val Muted = Color(0xFF7F8490)
private val ErrorRed = Color(0xFFC83D47)
private val SuccessGreen = Color(0xFF2E8B57)
private val YemenMobilePink = Color(0xFFB30B4C)
private val SabafonBlue = Color(0xFF1675A7)
private val YouYellow = Color(0xFFF1C21B)
private val WhyPurple = Color(0xFF503393)
private val FourGBlue = Color(0xFF137EAE)
private val YemenNetPurple = Color(0xFF373083)
private val ControlBlue = Color(0xFF3B9AE8)

private enum class PaymentAction { BALANCE, INSTANT, PACKAGES, WHOLESALE, POSTPAID }
private enum class ProviderKind { YEMEN_MOBILE, SABAFON, YOU, WHY, FOUR_G, YEMEN_NET }

private data class ProviderUi(val kind: ProviderKind, val title: String, val mark: String, val color: Color, val detection: String)
private data class PackageRow(val name: String, val price: Double?, val start: String?, val end: String?, val metadata: Map<String, String>)

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

private fun providerKind(phone: String): ProviderKind? = when (val p = normalizePhone(phone)) {
    else -> when {
        p.startsWith("77") || p.startsWith("78") -> ProviderKind.YEMEN_MOBILE
        p.startsWith("71") -> ProviderKind.SABAFON
        p.startsWith("73") -> ProviderKind.YOU
        p.startsWith("70") -> ProviderKind.WHY
        p.startsWith("10") -> ProviderKind.FOUR_G
        p.startsWith("0") -> ProviderKind.YEMEN_NET
        else -> null
    }
}

private fun providerUi(kind: ProviderKind?): ProviderUi = when (kind) {
    ProviderKind.YEMEN_MOBILE -> ProviderUi(ProviderKind.YEMEN_MOBILE, "Yemen Mobile", "YM", YemenMobilePink, "تم التعرف على يمن موبايل من البادئة 77 / 78")
    ProviderKind.SABAFON -> ProviderUi(ProviderKind.SABAFON, "سبأفون", "S", SabafonBlue, "تم التعرف على سبأفون من البادئة 71")
    ProviderKind.YOU -> ProviderUi(ProviderKind.YOU, "YOU", "YOU", YouYellow, "تم التعرف على YOU من البادئة 73")
    ProviderKind.WHY -> ProviderUi(ProviderKind.WHY, "WHY", "WHY", WhyPurple, "تم التعرف على WHY من البادئة 70")
    ProviderKind.FOUR_G -> ProviderUi(ProviderKind.FOUR_G, "Yemen 4G", "4G", FourGBlue, "تم التعرف على Yemen 4G من البادئة 10")
    ProviderKind.YEMEN_NET -> ProviderUi(ProviderKind.YEMEN_NET, "Yemen Net", "YN", YemenNetPurple, "تم التعرف على يمن نت لأن الرقم يبدأ بـ 0")
    null -> ProviderUi(ProviderKind.YEMEN_MOBILE, "شبكة السداد", "K", ControlBlue, "")
}

private fun flatten(categories: List<ServiceMainCategoryDto>): List<ServiceDto> =
    categories.flatMap { main ->
        main.categories.flatMap { category ->
            fun walk(c: com.example.data.remote.ServiceCategoryDto): List<ServiceDto> = c.services + c.children.flatMap(::walk)
            walk(category)
        }
    }.distinctBy { it.id }

private fun normalizedServiceName(service: ServiceDto): String =
    "${service.code} ${service.name}".lowercase().replace(Regex("[^\\p{L}\\p{Nd}]+"), " ").trim()

private fun serviceContains(service: ServiceDto, text: String): Boolean = normalizedServiceName(service).contains(
    text.lowercase().replace(Regex("[^\\p{L}\\p{Nd}]+"), " ").trim()
)

private fun exactNamedService(all: List<ServiceDto>, expected: String, kind: String? = null): ServiceDto? {
    val target = expected.lowercase().replace(Regex("[^\\p{L}\\p{Nd}]+"), " ").trim()
    return all.firstOrNull { service ->
        (kind == null || service.serviceKind.equals(kind, ignoreCase = true)) &&
            normalizedServiceName(service) == target
    } ?: all.firstOrNull { service ->
        (kind == null || service.serviceKind.equals(kind, ignoreCase = true)) &&
            normalizedServiceName(service).contains(target)
    }
}

private fun providerService(all: List<ServiceDto>, kind: ProviderKind, action: PaymentAction, purchase: Boolean): ServiceDto? {
    if (kind == ProviderKind.YEMEN_MOBILE) {
        return when {
            !purchase && action == PaymentAction.BALANCE -> exactNamedService(all, "Yemen Mobile - استعلام الرصيد", "query")
            !purchase && action == PaymentAction.PACKAGES -> exactNamedService(all, "Yemen Mobile - استعلام الباقات", "query")
            !purchase && action == PaymentAction.POSTPAID -> exactNamedService(all, "Yemen Mobile - فحص السلفة", "query")
            purchase && action == PaymentAction.BALANCE -> exactNamedService(all, "Yemen Mobile - رصيد التسديد", "purchase")
            purchase && action == PaymentAction.PACKAGES -> exactNamedService(all, "Yemen Mobile - فئات", "purchase")
            else -> null
        }
    }

    val title = providerUi(kind).title.lowercase()
    val candidates = all.filter { service ->
        val text = normalizedServiceName(service)
        text.contains(title) || when (kind) {
            ProviderKind.SABAFON -> "sabafon" in text || "سبأفون" in text
            ProviderKind.YOU -> "you" in text || "يو" in text
            ProviderKind.WHY -> "why" in text || "واي" in text
            ProviderKind.FOUR_G -> "4g" in text || "فورجي" in text || "يمن 4" in text
            ProviderKind.YEMEN_NET -> "yemen net" in text || "يمن نت" in text
            ProviderKind.YEMEN_MOBILE -> false
        }
    }.filter { it.serviceKind.equals(if (purchase) "purchase" else "query", ignoreCase = true) }
    return candidates.firstOrNull { s ->
        when (action) {
            PaymentAction.BALANCE -> "استعلام الرصيد" in normalizedServiceName(s) || "balance" in normalizedServiceName(s) || "رصيد" in normalizedServiceName(s)
            PaymentAction.PACKAGES -> "استعلام الباقات" in normalizedServiceName(s) || "packages" in normalizedServiceName(s) || "فئات" in normalizedServiceName(s) || "باقة" in normalizedServiceName(s)
            PaymentAction.INSTANT -> "فوري" in normalizedServiceName(s) || "instant" in normalizedServiceName(s)
            PaymentAction.WHOLESALE -> "جملة" in normalizedServiceName(s) || "wholesale" in normalizedServiceName(s)
            PaymentAction.POSTPAID -> "فاتورة" in normalizedServiceName(s) || "postpaid" in normalizedServiceName(s) || "سلفة" in normalizedServiceName(s)
        }
    } ?: candidates.firstOrNull()
}

private fun isTerminal(status: String?): Boolean = status.orEmpty() in setOf("success", "failed", "refunded", "manual_review")
private fun hasResult(tx: ServiceTransactionDto?): Boolean = !tx?.result.isNullOrEmpty()

private fun fieldKey(field: ServiceFieldDto): String = field.key.lowercase().replace("_", "").replace("-", "")

private fun valueForField(field: ServiceFieldDto, phone: String, amount: String, netType: String): String? {
    val key = fieldKey(field)
    val label = field.label.lowercase()
    return when {
        key in setOf("mobile", "phone", "phonenumber", "msisdn", "mobilenumber", "recipient", "targetmobile") ||
            label.contains("هاتف") || label.contains("جوال") || label.contains("رقم الموبايل") -> normalizePhone(phone)
        key in setOf("amount", "value", "price") || label.contains("المبلغ") -> amount.takeIf { it.isNotBlank() }
        key in setOf("type", "linetype", "connectiontype", "servicetype") || label.contains("نوع الخط") || label.contains("نوع الخدمة") -> {
            val wanted = if (netType == "adsl") setOf("adsl", "dsl", "internet", "internet adsl", "الانترنت الارضي", "الإنترنت الأرضي")
            else setOf("line", "landline", "fixed", "voice", "الهاتف الثابت")
            field.choices.firstOrNull { c -> wanted.any { w -> c.lowercase().contains(w) } } ?: field.choices.firstOrNull() ?: netType
        }
        field.type.equals("select", true) && field.choices.isNotEmpty() -> field.choices.first()
        else -> null
    }
}

private fun buildPayload(service: ServiceDto, phone: String, amount: String, netType: String): Map<String, String?> {
    val out = linkedMapOf<String, String?>()
    service.fields.forEach { field -> valueForField(field, phone, amount, netType)?.let { out[field.key] = it } }
    return out
}

private suspend fun submitAndPoll(
    baseUrl: String,
    token: String,
    service: ServiceDto,
    phone: String,
    amount: String,
    netType: String,
    item: ServiceItemDto? = null,
    purchase: Boolean
): ServiceTransactionDto {
    val idempotency = UUID.randomUUID().toString()
    val payload = buildPayload(service, phone, amount, netType)
    val missing = service.fields.firstOrNull { it.required && payload[it.key].isNullOrBlank() && item == null }
    if (missing != null) throw IllegalStateException("الحقل المطلوب: ${missing.label}")

    val api = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/")
    val response = api.submitServiceRequest(
        "Token $token",
        idempotency,
        ServiceRequestPayload(
            serviceId = service.id,
            itemType = item?.type,
            itemId = item?.id,
            payload = payload,
            idempotencyKey = idempotency
        )
    )
    if (!response.isSuccessful || response.body() == null) {
        throw IllegalStateException("تعذر تنفيذ ${if (purchase) "العملية" else "الاستعلام"} (HTTP ${response.code()}).")
    }

    var latest = response.body()!!
    repeat(if (purchase) 30 else 24) {
        if (isTerminal(latest.status) || (!purchase && hasResult(latest))) return latest
        delay(if (purchase) 900 else 750)
        val poll = api.getServiceTransaction("Token $token", latest.id)
        if (poll.isSuccessful && poll.body() != null) latest = poll.body()!!
    }
    return latest
}

private fun firstNumber(result: Map<String, Any?>, keys: Set<String>): Double? {
    fun walk(value: Any?): Double? {
        when (value) {
            is Map<*, *> -> {
                value.entries.forEach { (k, v) ->
                    val nk = k.toString().lowercase().replace("_", "").replace(" ", "")
                    if (keys.any { nk.contains(it) }) {
                        v?.toString()?.toDoubleOrNull()?.let { return it }
                    }
                    walk(v)?.let { return it }
                }
            }
            is List<*> -> value.forEach { walk(it)?.let { n -> return n } }
        }
        return null
    }
    return walk(result)
}

private fun firstString(result: Map<String, Any?>, keys: Set<String>): String? {
    fun walk(value: Any?): String? {
        when (value) {
            is Map<*, *> -> {
                value.entries.forEach { (k, v) ->
                    val nk = k.toString().lowercase().replace("_", "").replace(" ", "")
                    if (keys.any { nk.contains(it) } && v != null && v !is Map<*, *> && v !is List<*>) return v.toString()
                    walk(v)?.let { return it }
                }
            }
            is List<*> -> value.forEach { walk(it)?.let { s -> return s } }
        }
        return null
    }
    return walk(result)
}

private fun packageRows(result: Map<String, Any?>): List<PackageRow> {
    val rows = mutableListOf<PackageRow>()
    fun walk(value: Any?) {
        when (value) {
            is Map<*, *> -> {
                val map = value.entries.associate { it.key.toString().lowercase() to it.value }
                val name = (map["offername"] ?: map["packagename"] ?: map["package_name"] ?: map["name"] ?: map["title"])?.toString()
                if (!name.isNullOrBlank()) {
                    val price = (map["amount"] ?: map["price"] ?: map["offerprice"])?.toString()?.toDoubleOrNull()
                    val start = (map["offerstartdate"] ?: map["startdate"] ?: map["start_date"] ?: map["subscriptiondate"])?.toString()
                    val end = (map["offerenddate"] ?: map["enddate"] ?: map["end_date"] ?: map["expirydate"] ?: map["expiredate"])?.toString()
                    val metadata = map.mapNotNull { (k, v) -> v?.let { k to it.toString() } }.toMap()
                    rows += PackageRow(name, price, start, end, metadata)
                }
                value.values.forEach(::walk)
            }
            is List<*> -> value.forEach(::walk)
        }
    }
    result.values.forEach(::walk)
    return rows.distinctBy { "${it.name}|${it.price}|${it.start}|${it.end}" }.take(30)
}

private fun displayValue(value: Any?): String = when (value) {
    null -> "—"
    is Map<*, *> -> value.entries.joinToString("\n") { "${it.key}: ${displayValue(it.value)}" }
    is List<*> -> value.joinToString("\n") { displayValue(it) }
    else -> value.toString()
}

private fun resultLabel(key: String): String = when (key.lowercase().replace("_", "")) {
    "balance" -> "رصيد الرقم"
    "availablecredit" -> "الرصيد المتاح"
    "mobiletype", "mobiltype", "linetype" -> "نوع الرقم"
    "loanamount", "loan", "sulfa", "sulfaamount" -> "السلفة"
    "message", "resultdesc" -> "الرسالة"
    "resultcode" -> "رمز النتيجة"
    "sequenceid", "resultid" -> "رقم العملية"
    else -> key
}

@Composable
private fun ProviderBadge(provider: ProviderUi) {
    Surface(shape = CircleShape, color = provider.color.copy(alpha = .12f), modifier = Modifier.size(58.dp)) {
        Box(contentAlignment = Alignment.Center) {
            Text(provider.mark, color = provider.color, fontWeight = FontWeight.Black, fontSize = 13.sp)
        }
    }
}

@Composable
private fun PhoneCard(phone: String, provider: ProviderUi, onPhoneChange: (String) -> Unit) {
    Card(Modifier.fillMaxWidth(), RoundedCornerShape(22.dp), colors = CardDefaults.cardColors(White), elevation = CardDefaults.cardElevation(4.dp)) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                ProviderBadge(provider)
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f), horizontalAlignment = Alignment.End) {
                    Text("رصيدي", color = provider.color, fontWeight = FontWeight.Black, fontSize = 23.sp)
                    Text("******  •  رصيد مخفي", color = Muted, fontWeight = FontWeight.Bold, fontSize = 10.sp)
                }
                Icon(Icons.Default.Info, null, tint = provider.color, modifier = Modifier.size(24.dp))
            }
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Surface(Modifier.size(38.dp), CircleShape, provider.color.copy(alpha = .10f)) {
                    Box(contentAlignment = Alignment.Center) { Icon(Icons.Default.AccountBalanceWallet, null, tint = provider.color) }
                }
                Spacer(Modifier.width(7.dp))
                Text("+967", color = Muted, fontWeight = FontWeight.Bold, fontSize = 15.sp)
                Spacer(Modifier.width(5.dp))
                OutlinedTextField(
                    value = phone,
                    onValueChange = onPhoneChange,
                    modifier = Modifier.weight(1f),
                    singleLine = true,
                    label = { Text("رقم الهاتف") },
                    leadingIcon = { Icon(Icons.Default.Call, null, tint = provider.color) },
                    trailingIcon = { Icon(Icons.Default.FavoriteBorder, null, tint = provider.color) },
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                    shape = RoundedCornerShape(10.dp)
                )
            }
            if (provider.detection.isNotBlank()) {
                Text(provider.detection, color = provider.color, fontWeight = FontWeight.Bold, fontSize = 8.sp, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.End)
            }
        }
    }
}

@Composable
private fun ActionTabs(provider: ProviderUi, action: PaymentAction, onSelect: (PaymentAction) -> Unit) {
    val labels = if (provider.kind == ProviderKind.YEMEN_NET) {
        listOf(PaymentAction.BALANCE to "الإنترنت الأرضي", PaymentAction.INSTANT to "الهاتف الثابت")
    } else {
        listOf(
            PaymentAction.BALANCE to "الرصيد",
            PaymentAction.INSTANT to "فوري",
            PaymentAction.PACKAGES to "الباقات",
            PaymentAction.WHOLESALE to "جملة",
            PaymentAction.POSTPAID to "ريال"
        )
    }
    Surface(Modifier.fillMaxWidth(), RoundedCornerShape(17.dp), provider.color.copy(alpha = .18f)) {
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(2.dp)) {
            labels.forEach { (item, label) ->
                Box(Modifier.weight(1f).clickable { onSelect(item) }.padding(vertical = 13.dp), contentAlignment = Alignment.Center) {
                    Surface(color = if (action == item) provider.color else Color.Transparent, shape = RoundedCornerShape(12.dp)) {
                        Text(label, color = if (action == item) White else TextDark, fontWeight = FontWeight.Black, fontSize = 11.sp, modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp), textAlign = TextAlign.Center)
                    }
                }
            }
        }
    }
}

@Composable
private fun ResultSummary(
    provider: ProviderUi,
    result: ServiceTransactionDto?,
    loanResult: ServiceTransactionDto?,
    packageMode: Boolean
) {
    val data = result?.result.orEmpty()
    val loan = firstNumber(data, setOf("loan", "sulfa")) ?: firstNumber(loanResult?.result.orEmpty(), setOf("loan", "sulfa"))
    val balance = firstNumber(data, setOf("balance", "availablebalance", "availablecredit"))
    val mobileType = firstString(data, setOf("mobiletype", "mobiltype", "linetype", "type"))
    Card(Modifier.fillMaxWidth(), RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(White), elevation = CardDefaults.cardElevation(1.dp)) {
        Column(Modifier.fillMaxWidth()) {
            Row(Modifier.fillMaxWidth().background(provider.color.copy(alpha = .10f)).padding(horizontal = 14.dp, vertical = 10.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text(if (packageMode) "حالة الباقات" else "نتيجة الاستعلام", color = provider.color, fontWeight = FontWeight.Black, fontSize = 15.sp)
                Icon(if (result?.status == "success" || !data.isNullOrEmpty()) Icons.Default.CheckCircle else Icons.Default.Info, null, tint = provider.color)
            }
            if (!packageMode) {
                if (balance != null) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text(formatYemeni(balance), color = Color(0xFF176C9D), fontWeight = FontWeight.Black, fontSize = 19.sp, modifier = Modifier.padding(12.dp))
                        Text("رصيد الرقم", color = provider.color, fontWeight = FontWeight.Black, modifier = Modifier.padding(12.dp))
                    }
                }
                if (!mobileType.isNullOrBlank()) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(mobileType, color = TextDark, fontWeight = FontWeight.Bold, modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp))
                        Text("نوع الرقم", color = provider.color, fontWeight = FontWeight.Black, modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp))
                    }
                }
                if (loan != null) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text(formatYemeni(loan), color = YemenMobilePink, fontWeight = FontWeight.Black, modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp))
                        Text("السلفة الحالية", color = YemenMobilePink, fontWeight = FontWeight.Black, modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp))
                    }
                }
            } else {
                val items = packageRows(data)
                if (items.isEmpty()) {
                    Text("تم الاستعلام عن الباقات ولم يرجع المزود اشتراكات حالية.", color = Muted, modifier = Modifier.fillMaxWidth().padding(14.dp), textAlign = TextAlign.Center, fontSize = 11.sp)
                } else {
                    items.take(6).forEach { item ->
                        Column(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                            Text(item.name, color = TextDark, fontWeight = FontWeight.Black, fontSize = 15.sp, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.End)
                            item.start?.let { Text("الاشتراك: $it", color = provider.color, fontWeight = FontWeight.Bold, fontSize = 10.sp, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.End) }
                            item.end?.let { Text("الانتهاء: $it", color = ErrorRed, fontWeight = FontWeight.Bold, fontSize = 10.sp, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.End) }
                            item.price?.let { Text("${formatYemeni(it)} ر.ي", color = provider.color, fontWeight = FontWeight.Black, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.End) }
                        }
                    }
                }
            }
        }
    }
}

private fun formatYemeni(v: Double): String = if (v % 1.0 == 0.0) v.toInt().toString() else String.format("%.2f", v)

@Composable
private fun GenericResultCard(tx: ServiceTransactionDto, provider: ProviderUi, onClick: () -> Unit) {
    val pending = !isTerminal(tx.status)
    Card(Modifier.fillMaxWidth().clickable(onClick = onClick), RoundedCornerShape(16.dp), colors = CardDefaults.cardColors(White), elevation = CardDefaults.cardElevation(1.dp)) {
        Column(Modifier.padding(13.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Text("نتيجة العملية", color = TextDark, fontWeight = FontWeight.Black, fontSize = 15.sp)
                Text(if (pending) "مستمرة" else if (tx.status == "success") "ناجحة ✅" else "انتهت", color = if (pending) provider.color else if (tx.status == "success") SuccessGreen else ErrorRed, fontWeight = FontWeight.Bold, fontSize = 10.sp)
            }
            Text(if (pending) "لم تنتهِ العملية لدى الخادم بعد." else (tx.errorMessage ?: "تم استلام النتيجة."), color = Muted, fontSize = 9.sp)
        }
    }
}

@Composable
private fun AmountCard(amount: String, onAmountChange: (String) -> Unit, provider: ProviderUi) {
    Card(Modifier.fillMaxWidth(), RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(White)) {
        Column(Modifier.padding(13.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("*ادخل المبلغ", color = TextDark, fontWeight = FontWeight.Black, fontSize = 16.sp, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.End)
            OutlinedTextField(value = amount, onValueChange = onAmountChange, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("المبلغ") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), trailingIcon = { Text("ر.ي", color = provider.color, fontWeight = FontWeight.Black) }, shape = RoundedCornerShape(10.dp))
        }
    }
}

@Composable
private fun PackagePurchaseCard(item: ServiceItemDto, provider: ProviderUi, onClick: () -> Unit) {
    Card(Modifier.fillMaxWidth().clickable(onClick = onClick), shape = RoundedCornerShape(16.dp), colors = CardDefaults.cardColors(White), elevation = CardDefaults.cardElevation(1.dp)) {
        Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Button(onClick = onClick, shape = RoundedCornerShape(10.dp), colors = ButtonDefaults.buttonColors(containerColor = provider.color)) { Text("تجديد", fontWeight = FontWeight.Black) }
            Column(horizontalAlignment = Alignment.End) {
                Text(item.name, color = TextDark, fontWeight = FontWeight.Black, fontSize = 14.sp)
                Text(item.price?.let { "$it ${item.currency}" } ?: "—", color = provider.color, fontWeight = FontWeight.Bold, fontSize = 11.sp)
            }
        }
    }
}

@Composable
private fun ConfirmDialog(name: String, amount: Double, provider: ProviderUi, onConfirm: () -> Unit, onCancel: () -> Unit) {
    AlertDialog(onDismissRequest = onCancel, title = { Text("تأكيد التسديد", fontWeight = FontWeight.Black) }, text = { Column(verticalArrangement = Arrangement.spacedBy(7.dp)) { Text(name, fontWeight = FontWeight.Black); Text("المبلغ: ${formatYemeni(amount)} ر.ي") } }, confirmButton = { Button(onClick = onConfirm, colors = ButtonDefaults.buttonColors(containerColor = provider.color)) { Text("تأكيد") } }, dismissButton = { TextButton(onClick = onCancel) { Text("إلغاء") } })
}

@Composable
private fun ResultDialog(tx: ServiceTransactionDto, provider: ProviderUi, onClose: () -> Unit) {
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text("نتيجة العملية", fontWeight = FontWeight.Black) },
        text = {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(7.dp)) {
                item {
                    Text(
                        when {
                            tx.status == "success" -> "تمت العملية بنجاح ✅"
                            isTerminal(tx.status) -> tx.errorMessage ?: "تعذر تنفيذ العملية."
                            else -> "العملية لا تزال قيد التنفيذ لدى الخادم."
                        },
                        fontWeight = FontWeight.Bold
                    )
                }
                item { Text("المرجع: ${tx.id}", color = Muted, fontSize = 10.sp) }
                tx.amount?.let { item { Text("المبلغ: $it ${tx.currency.orEmpty()}") } }
                tx.providerTransactionId?.let { item { Text("معرف المزود: $it", color = Muted, fontSize = 10.sp) } }
                tx.providerTransid?.let { item { Text("رقم المزود: $it", color = Muted, fontSize = 10.sp) } }
                tx.result.orEmpty().entries.sortedBy { it.key }.forEach { (key, value) -> item { Text("${resultLabel(key)}: ${displayValue(value)}", fontSize = 11.sp) } }
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
    var phone by remember(session.phone) { mutableStateOf(session.phone) }
    var action by remember { mutableStateOf(PaymentAction.BALANCE) }
    var amount by remember { mutableStateOf("") }
    var netType by remember { mutableStateOf("adsl") }
    var smartCharge by remember { mutableStateOf(false) }
    var queryResult by remember { mutableStateOf<ServiceTransactionDto?>(null) }
    var loanResult by remember { mutableStateOf<ServiceTransactionDto?>(null) }
    var operationResult by remember { mutableStateOf<ServiceTransactionDto?>(null) }
    var selectedItem by remember { mutableStateOf<ServiceItemDto?>(null) }
    var selectedPurchaseService by remember { mutableStateOf<ServiceDto?>(null) }
    var loading by remember { mutableStateOf(false) }
    var syncing by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var showConfirm by remember { mutableStateOf(false) }
    var showResult by remember { mutableStateOf(false) }

    val detectedKind = providerKind(phone)
    val provider = providerUi(detectedKind)
    val allServices = remember(catalog) { flatten(catalog) }
    val balanceQuery = detectedKind?.let { providerService(allServices, it, PaymentAction.BALANCE, false) }
    val packageQuery = detectedKind?.let { providerService(allServices, it, PaymentAction.PACKAGES, false) }
    val loanQuery = detectedKind?.let { providerService(allServices, it, PaymentAction.POSTPAID, false) }
    val balancePurchase = detectedKind?.let { providerService(allServices, it, PaymentAction.BALANCE, true) }
    val packagePurchase = detectedKind?.let { providerService(allServices, it, PaymentAction.PACKAGES, true) }

    fun restoreCatalog() {
        SessionStore.loadLocalString("service_catalog_${baseUrl.trimEnd('/')}")?.let { raw ->
            runCatching { NetworkClient.moshi().adapter(ServiceCatalogResponse::class.java).fromJson(raw) }.getOrNull()?.let { catalog = it.categories }
        }
    }

    fun syncCatalog() {
        if (syncing) return
        val token = session.token ?: run { error = "سجل الدخول أولًا."; return }
        scope.launch {
            syncing = true
            error = null
            try {
                val api = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/")
                val response = api.getServiceCatalog("Token $token")
                if (!response.isSuccessful || response.body() == null) throw IllegalStateException("تعذر مزامنة الخدمات (HTTP ${response.code()}).")
                catalog = response.body()!!.categories
                SessionStore.saveLocalString("service_catalog_${baseUrl.trimEnd('/')}", NetworkClient.moshi().adapter(ServiceCatalogResponse::class.java).toJson(response.body()!!))
            } catch (e: Exception) { error = e.localizedMessage ?: "تعذر مزامنة الخدمات." }
            finally { syncing = false }
        }
    }

    LaunchedEffect(baseUrl, session.token) { restoreCatalog() }

    fun runBalanceQuery() {
        val token = session.token ?: return
        val service = balanceQuery ?: run { error = "خدمة استعلام الرصيد ليمن موبايل غير مهيأة."; return }
        scope.launch {
            loading = true; error = null; operationResult = null
            try {
                queryResult = submitAndPoll(baseUrl, token, service, phone, "", netType, purchase = false)
                loanResult = loanQuery?.let { submitAndPoll(baseUrl, token, it, phone, "", netType, purchase = false) }
            } catch (e: Exception) { error = e.localizedMessage ?: "تعذر استعلام الرصيد." }
            finally { loading = false }
        }
    }

    fun runPackageQuery() {
        val token = session.token ?: return
        val service = packageQuery ?: run { error = "خدمة استعلام الباقات ليمن موبايل غير مهيأة."; return }
        scope.launch {
            loading = true; error = null; queryResult = null; operationResult = null
            try { queryResult = submitAndPoll(baseUrl, token, service, phone, "", netType, purchase = false) }
            catch (e: Exception) { error = e.localizedMessage ?: "تعذر استعلام الباقات." }
            finally { loading = false }
        }
    }

    fun runAction(next: PaymentAction) {
        action = next
        error = null
        queryResult = null
        loanResult = null
        operationResult = null
        selectedItem = null
        showConfirm = false
        when (next) {
            PaymentAction.BALANCE -> runBalanceQuery()
            PaymentAction.PACKAGES -> runPackageQuery()
            PaymentAction.INSTANT, PaymentAction.WHOLESALE, PaymentAction.POSTPAID -> {
                selectedPurchaseService = detectedKind?.let { providerService(allServices, it, next, true) }
                if (selectedPurchaseService == null) error = "لا توجد خدمة ${provider.title} لهذه العملية."
            }
        }
    }

    fun doPurchase(item: ServiceItemDto? = null) {
        val token = session.token ?: return
        val service = selectedPurchaseService ?: when (action) {
            PaymentAction.BALANCE -> balancePurchase
            PaymentAction.PACKAGES -> packagePurchase
            else -> selectedPurchaseService
        }
        if (service == null) { error = "خدمة التسديد غير مهيأة لهذا المزود."; return }
        if (service.fields.any { it.required && valueForField(it, phone, amount, netType).isNullOrBlank() && item == null }) {
            val missing = service.fields.first { it.required && valueForField(it, phone, amount, netType).isNullOrBlank() }
            error = "الحقل المطلوب: ${missing.label}"
            return
        }
        scope.launch {
            loading = true; error = null
            try {
                val latest = submitAndPoll(baseUrl, token, service, phone, amount, netType, item = item, purchase = true)
                operationResult = latest
                showResult = true
                if (latest.status == "success") {
                    onSyncBalance()
                    onRechargeSubmit(phone, provider.title, service.name, item?.name ?: service.name, latest.amount?.toDoubleOrNull() ?: amount.toDoubleOrNull() ?: 0.0)
                }
            } catch (e: Exception) { error = e.localizedMessage ?: "تعذر تنفيذ التسديد." }
            finally { loading = false; showConfirm = false }
        }
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = {
                    Column(horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("رصيدي", color = White, fontWeight = FontWeight.Black, fontSize = 20.sp)
                        Text("******  •  رصيد مخفي", color = White.copy(.88f), fontSize = 9.sp, fontWeight = FontWeight.Bold)
                    }
                },
                navigationIcon = { IconButton(onClick = ::syncCatalog) { Surface(modifier = Modifier.size(42.dp), shape = CircleShape, color = White) { Box(contentAlignment = Alignment.Center) { Icon(Icons.Default.Refresh, null, tint = provider.color) } } } },
                actions = { IconButton(onClick = onBackClick) { Text("رجوع", color = White, fontWeight = FontWeight.Bold, fontSize = 11.sp) } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = provider.color, titleContentColor = White)
            )
        }
    ) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding).background(ScreenBg), contentPadding = PaddingValues(horizontal = 12.dp, vertical = 10.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            item { PhoneCard(phone, provider, onPhoneChange = { phone = it }) }
            item { ActionTabs(provider, action, ::runAction) }

            if (detectedKind == ProviderKind.YEMEN_NET) {
                item {
                    Surface(Modifier.fillMaxWidth(), RoundedCornerShape(13.dp), provider.color.copy(alpha = .12f)) {
                        Row(Modifier.fillMaxWidth().padding(4.dp), horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                            listOf("adsl" to "الإنترنت الأرضي", "line" to "الهاتف الثابت").forEach { (type, label) ->
                                Surface(Modifier.weight(1f).clickable { netType = type }, RoundedCornerShape(10.dp), if (netType == type) provider.color else Color.Transparent) {
                                    Text(label, color = if (netType == type) White else TextDark, fontWeight = FontWeight.Black, modifier = Modifier.padding(vertical = 10.dp), textAlign = TextAlign.Center, fontSize = 11.sp)
                                }
                            }
                        }
                    }
                }
            }

            if (action == PaymentAction.BALANCE) {
                item { AmountCard(amount, { amount = it }, provider) }
                item {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = ::runBalanceQuery, modifier = Modifier.weight(1f).height(50.dp), colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFFFDDAE)), shape = RoundedCornerShape(12.dp)) { Text("استعلام", color = provider.color, fontWeight = FontWeight.Black, fontSize = 16.sp) }
                        Button(onClick = { showConfirm = true; selectedPurchaseService = balancePurchase }, enabled = balancePurchase != null && !loading, modifier = Modifier.weight(1f).height(50.dp), colors = ButtonDefaults.buttonColors(containerColor = Color(0xFFFFDDAE)), shape = RoundedCornerShape(12.dp)) { Text("تسديد", color = provider.color, fontWeight = FontWeight.Black, fontSize = 16.sp) }
                    }
                }
                if (queryResult != null) item { ResultSummary(provider, queryResult, loanResult, packageMode = false) }
            }

            if (action == PaymentAction.PACKAGES) {
                item {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Text("الباقات", color = TextDark, fontWeight = FontWeight.Black, fontSize = 18.sp)
                        Text(if (smartCharge) "الشاحن الذكي: مفعل" else "الشاحن الذكي", color = Muted, fontSize = 9.sp, fontWeight = FontWeight.Bold)
                    }
                }
                item {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = ::runPackageQuery, modifier = Modifier.weight(1f).height(50.dp), colors = ButtonDefaults.buttonColors(containerColor = provider.color), shape = RoundedCornerShape(12.dp)) { Text("استعلام الباقات", fontWeight = FontWeight.Black) }
                        Button(onClick = { smartCharge = !smartCharge }, modifier = Modifier.weight(1f).height(50.dp), colors = ButtonDefaults.buttonColors(containerColor = White), shape = RoundedCornerShape(12.dp)) { Text(if (smartCharge) "إيقاف الشاحن" else "الشاحن الذكي", color = provider.color, fontWeight = FontWeight.Black) }
                    }
                }
                if (queryResult != null) item { ResultSummary(provider, queryResult, null, packageMode = true) }
                val purchaseItems = packagePurchase?.items.orEmpty().take(20)
                if (purchaseItems.isNotEmpty()) {
                    item { Text("الفئات المتاحة للتجديد", color = TextDark, fontWeight = FontWeight.Black, fontSize = 16.sp, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.End) }
                    purchaseItems.forEach { itemDto -> item { PackagePurchaseCard(itemDto, provider) { selectedItem = itemDto; selectedPurchaseService = packagePurchase; showConfirm = true } } }
                }
            }

            if (action == PaymentAction.INSTANT || action == PaymentAction.WHOLESALE || action == PaymentAction.POSTPAID) {
                item { AmountCard(amount, { amount = it }, provider) }
                item {
                    Button(onClick = { selectedPurchaseService = detectedKind?.let { providerService(allServices, it, action, true) }; showConfirm = true }, enabled = selectedPurchaseService != null && !loading, modifier = Modifier.fillMaxWidth().height(52.dp), colors = ButtonDefaults.buttonColors(containerColor = provider.color), shape = RoundedCornerShape(13.dp)) { Text("تسديد", fontWeight = FontWeight.Black, fontSize = 16.sp) }
                }
            }

            operationResult?.let { tx ->
                item { GenericResultCard(tx, provider) { showResult = true } }
            }
            error?.let { msg -> item { Surface(Modifier.fillMaxWidth(), RoundedCornerShape(13.dp), Color(0xFFFFEEEE)) { Text(msg, color = ErrorRed, modifier = Modifier.padding(11.dp), textAlign = TextAlign.Center, fontWeight = FontWeight.Bold, fontSize = 10.sp) } } }
            if (loading || syncing) item { Box(Modifier.fillMaxWidth().padding(12.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator(color = provider.color) } }
        }
    }

    if (showConfirm) {
        val service = selectedPurchaseService ?: when (action) { PaymentAction.BALANCE -> balancePurchase; PaymentAction.PACKAGES -> packagePurchase; else -> null }
        ConfirmDialog(selectedItem?.name ?: service?.name.orEmpty(), selectedItem?.price?.toDoubleOrNull() ?: amount.toDoubleOrNull() ?: service?.price?.toDoubleOrNull() ?: 0.0, provider, onConfirm = { doPurchase(selectedItem) }, onCancel = { showConfirm = false })
    }
    if (showResult && operationResult != null) ResultDialog(operationResult!!, provider, onClose = { showResult = false })
}