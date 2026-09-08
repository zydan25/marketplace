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
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CloudDownload
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Inventory2
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
import com.example.data.remote.ServiceRequestPayload
import com.example.data.remote.ServiceTransactionDto
import com.example.data.repository.StoreRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.UUID

private val Bg = Color(0xFFF0F1F5)
private val HeaderBlue = Color(0xFF3A97E8)
private val White = Color.White
private val TextDark = Color(0xFF25262B)
private val Muted = Color(0xFF777B83)
private val Pink = Color(0xFFC01855)
private val Yellow = Color(0xFFFFC72B)
private val Teal = Color(0xFF168B8B)
private val Purple = Color(0xFF7654B7)

private enum class PaymentAction { BALANCE, INSTANT, PACKAGES, WHOLESALE, POSTPAID }

private fun digits(value: String): String = buildString(value.length) {
    value.forEach { append(when (it) {
        '٠' -> '0'; '١' -> '1'; '٢' -> '2'; '٣' -> '3'; '٤' -> '4'; '٥' -> '5'; '٦' -> '6'; '٧' -> '7'; '٨' -> '8'; '٩' -> '9'
        '۰' -> '0'; '۱' -> '1'; '۲' -> '2'; '۳' -> '3'; '۴' -> '4'; '۵' -> '5'; '۶' -> '6'; '۷' -> '7'; '۸' -> '8'; '۹' -> '9'
        else -> it
    }) }
}

private fun providerKey(provider: ServiceCategoryDto?): String = "${provider?.slug.orEmpty()} ${provider?.name.orEmpty()}".lowercase()
private fun isYemenMobile(phone: String): Boolean { val p = digits(phone).filter(Char::isDigit); return p.startsWith("77") || p.startsWith("78") }
private fun isYemenNet(provider: ServiceCategoryDto?): Boolean = "yemen-net" in providerKey(provider) || "يمن نت" in providerKey(provider)
private fun providerColor(provider: ServiceCategoryDto?): Color = when {
    "yemen-mobile" in providerKey(provider) || "يمن موبايل" in providerKey(provider) -> Pink
    "sabafon" in providerKey(provider) || "سبأفون" in providerKey(provider) -> HeaderBlue
    "you" in providerKey(provider) || "يو" in providerKey(provider) -> Yellow
    "why" in providerKey(provider) || "واي" in providerKey(provider) -> Purple
    "4g" in providerKey(provider) || "فورجي" in providerKey(provider) -> Teal
    else -> HeaderBlue
}
private fun providerTitle(provider: ServiceCategoryDto?): String = when {
    "yemen-mobile" in providerKey(provider) || "يمن موبايل" in providerKey(provider) -> "Yemen Mobile"
    "sabafon" in providerKey(provider) || "سبأفون" in providerKey(provider) -> "سبأفون"
    "you" in providerKey(provider) || "يو" in providerKey(provider) -> "YOU"
    "why" in providerKey(provider) || "واي" in providerKey(provider) -> "WHY"
    "4g" in providerKey(provider) || "فورجي" in providerKey(provider) -> "Yemen 4G"
    "yemen-net" in providerKey(provider) || "يمن نت" in providerKey(provider) -> "Yemen Net"
    else -> provider?.name.orEmpty().ifBlank { "شبكة السداد" }
}
private fun providerMark(provider: ServiceCategoryDto?): String = when {
    "yemen-mobile" in providerKey(provider) || "يمن موبايل" in providerKey(provider) -> "YM"
    "sabafon" in providerKey(provider) || "سبأفون" in providerKey(provider) -> "S"
    "you" in providerKey(provider) || "يو" in providerKey(provider) -> "YOU"
    "why" in providerKey(provider) || "واي" in providerKey(provider) -> "WHY"
    "4g" in providerKey(provider) || "فورجي" in providerKey(provider) -> "4G"
    "yemen-net" in providerKey(provider) || "يمن نت" in providerKey(provider) -> "YN"
    else -> "K"
}
private fun flatten(category: ServiceCategoryDto): List<ServiceDto> = category.services + category.children.flatMap(::flatten)
private fun serviceText(service: ServiceDto) = "${service.code} ${service.name}".lowercase()
private fun actionFromService(service: ServiceDto): PaymentAction {
    val s = serviceText(service)
    return when {
        "جملة" in s || "wholesale" in s -> PaymentAction.WHOLESALE
        "فوتر" in s || "postpaid" in s -> PaymentAction.POSTPAID
        "فوري" in s || "instant" in s || "4g" in s -> PaymentAction.INSTANT
        "offer" in s || "باقة" in s || "باقات" in s || "عروض" in s -> PaymentAction.PACKAGES
        else -> PaymentAction.BALANCE
    }
}
private fun queryService(services: List<ServiceDto>, action: PaymentAction): ServiceDto? = services.firstOrNull { it.serviceKind == "query" && actionFromService(it) == action } ?: services.firstOrNull { it.serviceKind == "query" }
private fun purchaseService(services: List<ServiceDto>, action: PaymentAction): ServiceDto? = services.firstOrNull { it.serviceKind == "purchase" && actionFromService(it) == action }
private fun actionLabel(action: PaymentAction): String = when (action) {
    PaymentAction.BALANCE -> "رصيد"; PaymentAction.INSTANT -> "فوري"; PaymentAction.PACKAGES -> "باقات"; PaymentAction.WHOLESALE -> "جملة"; PaymentAction.POSTPAID -> "فوترة"
}
private fun resultLoan(result: Map<String, Any?>): Double { result.forEach { (key, value) -> val k = key.lowercase().replace("_", "").replace(" ", ""); if (k.contains("loan") || k.contains("sulfa") || k.contains("solfa") || k.contains("سلفة") || k.contains("سلف")) value?.toString()?.toDoubleOrNull()?.let { return it } }; return 0.0 }
private fun displayValue(value: Any?): String = when (value) {
    null -> "—"
    is Map<*, *> -> value.entries.joinToString("\n") { "${it.key}: ${displayValue(it.value)}" }
    is List<*> -> value.joinToString("\n") { displayValue(it) }
    else -> value.toString()
}
private fun resultLabel(key: String): String = when (key.lowercase().replace("_", "")) {
    "balance" -> "الرصيد"; "availablecredit" -> "الرصيد المتاح"; "loanamount", "loan" -> "السلفة"; "message", "resultdesc" -> "الرسالة"; "resultcode" -> "رمز النتيجة"; "mobiletype", "mobiltype" -> "نوع الخط"; "sequenceid", "resultid" -> "رقم العملية"; "offername" -> "اسم الباقة"; "offerid" -> "كود الباقة"; "offerstartdate" -> "بداية الباقة"; "offerenddate" -> "نهاية الباقة"; "status" -> "الحالة"; else -> key
}
private fun resultOfferItems(result: Map<String, Any?>): List<ServiceItemDto> {
    val found = mutableListOf<ServiceItemDto>(); var id = 1L
    fun walk(value: Any?) {
        when (value) {
            is Map<*, *> -> {
                val m = value.entries.associate { it.key.toString().lowercase() to it.value }
                val name = (m["offername"] ?: m["name"] ?: m["packagename"])?.toString()
                if (!name.isNullOrBlank()) found += ServiceItemDto(id++, "offer", name, (m["amount"] ?: m["price"] ?: m["offerprice"])?.toString(), "YER", m.mapNotNull { (k,v) -> v?.let { k to it.toString() } }.toMap(), emptyMap())
                value.values.forEach(::walk)
            }
            is List<*> -> value.forEach(::walk)
        }
    }
    result.values.forEach(::walk)
    return found.distinctBy { it.name + "|" + it.price }
}

@Composable
private fun ProviderCard(provider: ServiceCategoryDto, selected: Boolean, onClick: () -> Unit) {
    val c = providerColor(provider)
    Surface(modifier = Modifier.width(116.dp).clickable(onClick = onClick), shape = RoundedCornerShape(18.dp), color = if (selected) c else White, shadowElevation = if (selected) 4.dp else 1.dp) {
        Column(Modifier.padding(vertical = 9.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Surface(modifier = Modifier.size(42.dp), shape = CircleShape, color = if (selected) White.copy(alpha = .17f) else c.copy(alpha = .10f)) { Box(contentAlignment = Alignment.Center) { Text(providerMark(provider), color = if (selected) White else c, fontWeight = FontWeight.Black, fontSize = 10.sp) } }
            Text(providerTitle(provider), color = if (selected) White else TextDark, fontSize = 10.sp, fontWeight = FontWeight.Bold, maxLines = 1)
        }
    }
}

@Composable
private fun MainTab(action: PaymentAction, selected: Boolean, accent: Color, onClick: () -> Unit) {
    Surface(modifier = Modifier.width(92.dp).clickable(onClick = onClick), shape = RoundedCornerShape(14.dp), color = if (selected) accent else Color.Transparent) { Box(Modifier.padding(vertical = 12.dp), contentAlignment = Alignment.Center) { Text(actionLabel(action), color = if (selected) White else TextDark, fontWeight = FontWeight.Black, fontSize = 13.sp) } }
}

@Composable
private fun SectionTitle(title: String, caption: String? = null) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) { Text(title, fontWeight = FontWeight.Black, fontSize = 16.sp, color = TextDark); caption?.let { Text(it, color = Muted, fontSize = 9.sp) } }
}

@Composable
private fun PackageTile(item: ServiceItemDto, accent: Color, modifier: Modifier = Modifier, onClick: () -> Unit) {
    val amount = item.price?.toDoubleOrNull()
    Card(modifier = modifier.aspectRatio(.72f).clickable(onClick = onClick), shape = RoundedCornerShape(12.dp), colors = CardDefaults.cardColors(containerColor = White), elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)) {
        Column(Modifier.fillMaxSize()) {
            Surface(modifier = Modifier.fillMaxWidth(), color = accent, shape = RoundedCornerShape(topStart = 12.dp, topEnd = 12.dp)) { Column(Modifier.padding(5.dp), horizontalAlignment = Alignment.CenterHorizontally) { Text("فئة", color = White, fontSize = 9.sp, fontWeight = FontWeight.Bold); Text(amount?.let { formatNumber(it) } ?: item.name.take(10), color = White, fontSize = 18.sp, fontWeight = FontWeight.Black, maxLines = 1) } }
            Column(Modifier.fillMaxSize().padding(7.dp), verticalArrangement = Arrangement.SpaceBetween, horizontalAlignment = Alignment.CenterHorizontally) {
                Text("السعر", color = TextDark, fontWeight = FontWeight.Bold, fontSize = 9.sp)
                Text(item.price?.let { "$it ${item.currency}" } ?: "—", color = accent, fontSize = 12.sp, fontWeight = FontWeight.Black)
                Surface(modifier = Modifier.fillMaxWidth(), color = accent.copy(alpha = .10f), shape = RoundedCornerShape(8.dp)) { Text(item.metadata["validity"] ?: item.metadata["duration"] ?: item.metadata["days"] ?: "", color = accent, fontSize = 8.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center, modifier = Modifier.padding(vertical = 5.dp)) }
            }
        }
    }
}
private fun formatNumber(value: Double): String = if (value % 1.0 == 0.0) value.toInt().toString() else String.format("%.2f", value)

@Composable
private fun ResultDetailsDialog(tx: ServiceTransactionDto, onClose: () -> Unit) {
    val pending = tx.status.orEmpty() in setOf("accepted", "queued", "processing", "pending_provider", "manual_review")
    AlertDialog(onDismissRequest = onClose, title = { Text("نتيجة العملية", fontWeight = FontWeight.Black) }, text = {
        LazyColumn(verticalArrangement = Arrangement.spacedBy(7.dp)) {
            item { Surface(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp), color = if (tx.status == "success") Color(0xFFE9F7EE) else Bg) { Text(when { tx.status == "success" -> "تمت العملية بنجاح ✅"; pending -> "العملية قيد المعالجة لدى المزود ⏳"; tx.status == "refunded" -> "أعيد المبلغ إلى محفظتك."; else -> tx.errorMessage ?: "تعذر إكمال العملية." }, fontWeight = FontWeight.Bold, modifier = Modifier.padding(10.dp)) } }
            item { Text("المرجع: ${tx.id}", color = Muted, fontSize = 10.sp) }
            tx.amount?.let { item { Text("المبلغ: $it ${tx.currency.orEmpty()}", fontWeight = FontWeight.Bold) } }
            tx.providerTransid?.let { item { Text("رقم المزود: $it", color = Muted, fontSize = 10.sp) } }
            tx.result.orEmpty().entries.sortedBy { it.key }.forEach { (key, value) -> item { Column(Modifier.fillMaxWidth()) { Text(resultLabel(key), color = Muted, fontSize = 9.sp); Text(displayValue(value), fontWeight = FontWeight.Bold, fontSize = 11.sp, textAlign = TextAlign.End, modifier = Modifier.fillMaxWidth()) } } }
        }
    }, confirmButton = { TextButton(onClick = onClose) { Text("إغلاق") } })
}

@Composable
private fun PurchaseConfirmDialog(name: String, amount: Double, loan: Double, accent: Color, onConfirm: () -> Unit, onCancel: () -> Unit) {
    AlertDialog(onDismissRequest = onCancel, title = { Text("تأكيد التسديد", fontWeight = FontWeight.Black) }, text = { Column(verticalArrangement = Arrangement.spacedBy(8.dp)) { Text(name, fontWeight = FontWeight.Black, fontSize = 17.sp); Text("قيمة الباقة: ${formatNumber(amount)} ر.ي"); Text("السلفة: ${formatNumber(loan)} ر.ي", color = Pink, fontWeight = FontWeight.Bold); Text("الإجمالي: ${formatNumber(amount + loan)} ر.ي", color = accent, fontSize = 18.sp, fontWeight = FontWeight.Black) } }, confirmButton = { Button(onClick = onConfirm, colors = ButtonDefaults.buttonColors(containerColor = accent)) { Text("تسديد + تفعيل", fontWeight = FontWeight.Black) } }, dismissButton = { TextButton(onClick = onCancel) { Text("إلغاء") } })
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

    fun restoreCatalog() { SessionStore.loadLocalString(cacheKey)?.let { raw -> runCatching { NetworkClient.moshi().adapter(ServiceCatalogResponse::class.java).fromJson(raw) }.getOrNull()?.let { catalog = it.categories } } }
    fun syncCatalog() {
        if (syncing) return
        val token = session.token ?: run { error = "سجل الدخول أولًا."; return }
        scope.launch {
            syncing = true; error = null
            try {
                val response = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/").getServiceCatalog("Token $token")
                if (!response.isSuccessful || response.body() == null) throw IllegalStateException("تعذر مزامنة الخدمات (HTTP ${response.code()}).")
                val body = response.body()!!
                catalog = body.categories
                SessionStore.saveLocalString(cacheKey, NetworkClient.moshi().adapter(ServiceCatalogResponse::class.java).toJson(body))
                provider = null; service = null; selectedItem = null; result = null
            } catch (e: Exception) { error = e.localizedMessage ?: "تعذر المزامنة." }
            finally { syncing = false }
        }
    }
    LaunchedEffect(baseUrl, session.token) { restoreCatalog() }

    val root = catalog.firstOrNull { it.slug == "payments" } ?: catalog.firstOrNull { it.name.contains("تسديد") }
    val providers = root?.categories.orEmpty()
    val providerServices = provider?.let(::flatten).orEmpty().distinctBy { it.id }
    val accent = providerColor(provider)
    val yemenMobile = isYemenMobile(phone)
    val yemenNet = isYemenNet(provider)
    val isYellowProvider = "you" in providerKey(provider) || "يو" in providerKey(provider)
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
    fun selectProvider(p: ServiceCategoryDto) { provider = p; service = null; selectedItem = null; result = null; error = null; values.clear() }
    fun runQuery(s: ServiceDto) {
        val token = session.token ?: return
        service = s; fillService(s)
        scope.launch {
            working = true; error = null; result = null
            try {
                val payload = values.toMutableMap(); if (yemenNet) payload["type"] = netType; if (smartCharge) payload["smart"] = "true"
                val id = UUID.randomUUID().toString()
                val response = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/").submitServiceRequest("Token $token", id, ServiceRequestPayload(s.id, null, null, payload, id))
                if (!response.isSuccessful || response.body() == null) throw IllegalStateException("تعذر الاستعلام (HTTP ${response.code()}).")
                result = response.body()
            } catch (e: Exception) { error = e.localizedMessage ?: "فشل الاستعلام." }
            finally { working = false }
        }
    }
    fun selectAction(next: PaymentAction) {
        action = next; selectedItem = null; result = null; error = null
        val target = queryService(providerServices, next)
        if (next == PaymentAction.BALANCE || next == PaymentAction.PACKAGES || next == PaymentAction.INSTANT) {
            if (target == null) error = "لا توجد خدمة ${actionLabel(next)} مهيأة لهذا المزود." else runQuery(target)
        } else {
            service = purchaseService(providerServices, next); service?.let(::fillService)
        }
    }
    fun confirmPurchase() {
        val s = service ?: return; val token = session.token ?: return; if (working) return
        scope.launch {
            working = true; waitingPurchase = true; error = null; result = null
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
                val id = UUID.randomUUID().toString()
                var latest = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/").submitServiceRequest("Token $token", id, ServiceRequestPayload(s.id, selectedItem?.type, selectedItem?.id, payload, id)).body() ?: throw IllegalStateException("لم تصل نتيجة العملية.")
                repeat(25) {
                    result = latest
                    if (latest.status.orEmpty() in setOf("success", "failed", "refunded", "manual_review")) return@repeat
                    delay(800)
                    val poll = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/").getServiceTransaction("Token $token", latest.id)
                    if (poll.isSuccessful && poll.body() != null) latest = poll.body()!!
                }
                result = latest; showResult = true
                if (latest.status == "success" || latest.status == "refunded") onSyncBalance()
                if (latest.status == "success") onRechargeSubmit(phone, providerTitle(provider), s.name, selectedOfferName.ifBlank { selectedItem?.name ?: s.name }, latest.amount?.toDoubleOrNull() ?: selectedOfferAmount)
            } catch (e: Exception) { error = e.localizedMessage ?: "تعذر تنفيذ التسديد." }
            finally { waitingPurchase = false; working = false; showConfirmation = false }
        }
    }

    if (showReports) { ServiceReportsScreen(onBackClick = { showReports = false }, modifier = modifier); return }

    Scaffold(modifier = modifier.fillMaxSize(), topBar = {
        TopAppBar(
            title = { Column(horizontalAlignment = Alignment.CenterHorizontally) { Text("رصيدي", color = White, fontWeight = FontWeight.Black, fontSize = 20.sp); Text("******  •  رصيد مخفي", color = White.copy(alpha = .88f), fontSize = 9.sp, fontWeight = FontWeight.Bold) } },
            navigationIcon = { IconButton(onClick = ::syncCatalog) { Surface(shape = CircleShape, color = White, modifier = Modifier.size(42.dp)) { Box(contentAlignment = Alignment.Center) { Icon(Icons.Default.Refresh, "مزامنة الخدمات", tint = if (yemenMobile) Pink else accent) } } } },
            actions = { IconButton(onClick = { showReports = true }) { Surface(shape = CircleShape, color = White, modifier = Modifier.size(42.dp)) { Box(contentAlignment = Alignment.Center) { Icon(Icons.Default.Settings, "التقرير", tint = if (yemenMobile) Pink else accent) } } } },
            colors = TopAppBarDefaults.topAppBarColors(containerColor = if (yemenMobile) Pink else accent, titleContentColor = White)
        )
    }) { pad ->
        LazyColumn(Modifier.fillMaxSize().padding(pad).background(Bg), contentPadding = PaddingValues(bottom = 28.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            item {
                Card(Modifier.fillMaxWidth().padding(horizontal = 12.dp), shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(containerColor = White), elevation = CardDefaults.cardElevation(2.dp)) {
                    Column(Modifier.padding(11.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            Surface(Modifier.size(48.dp), CircleShape, if (yemenMobile) Pink else accent.copy(alpha = .10f)) { Box(contentAlignment = Alignment.Center) { Text(if (yemenMobile) "YM" else providerMark(provider), color = if (yemenMobile) White else accent, fontWeight = FontWeight.Black, fontSize = 11.sp) } }
                            Spacer(Modifier.width(8.dp))
                            Column(Modifier.weight(1f), horizontalAlignment = Alignment.End) { Text(if (provider != null) providerTitle(provider) else "الشبكة", fontWeight = FontWeight.Black, fontSize = 18.sp, color = if (yemenMobile) Pink else TextDark); Text("رصيدي  •  ******", color = Muted, fontWeight = FontWeight.Bold, fontSize = 11.sp) }
                            Icon(Icons.Default.Settings, null, tint = if (yemenMobile) Pink else accent, modifier = Modifier.size(25.dp))
                        }
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                            Surface(Modifier.size(38.dp), CircleShape, if (yemenMobile) Pink.copy(alpha = .12f) else accent.copy(alpha = .10f)) { Box(contentAlignment = Alignment.Center) { Icon(Icons.Default.AccountBalanceWallet, null, tint = if (yemenMobile) Pink else accent) } }
                            Spacer(Modifier.width(7.dp))
                            OutlinedTextField(value = phone, onValueChange = { phone = it; service?.let { s -> if (s.fields.any { f -> f.key == "mobile" }) values["mobile"] = digits(it) } }, modifier = Modifier.weight(1f), singleLine = true, label = { Text("رقم الهاتف") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone), leadingIcon = { Icon(Icons.Default.Call, null, tint = if (yemenMobile) Pink else accent) }, trailingIcon = { Icon(Icons.Default.FavoriteBorder, null, tint = if (yemenMobile) Pink else accent) }, shape = RoundedCornerShape(8.dp))
                        }
                        if (yemenMobile) Text("تم التعرف على يمن موبايل من البادئة 77 / 78", color = Pink, fontWeight = FontWeight.Bold, fontSize = 9.sp, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.End)
                    }
                }
            }
            item {
                Surface(Modifier.fillMaxWidth().padding(horizontal = 12.dp), shape = RoundedCornerShape(16.dp), color = if (isYellowProvider) Yellow.copy(alpha = .20f) else if (yemenMobile) Pink.copy(alpha = .12f) else accent.copy(alpha = .10f)) {
                    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.SpaceEvenly) { listOf(PaymentAction.BALANCE, PaymentAction.INSTANT, PaymentAction.PACKAGES, PaymentAction.WHOLESALE, PaymentAction.POSTPAID).forEach { a -> MainTab(a, action == a, if (yemenMobile) Pink else accent) { selectAction(a) } } }
                }
            }
            if (provider == null && providers.isNotEmpty()) item {
                Column(Modifier.padding(horizontal = 12.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) { SectionTitle("اختر الشبكة", "المحفوظة محليًا"); Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) { providers.forEach { p -> ProviderCard(p, false, ::selectProvider) } } }
            }
            if (provider != null) item {
                Card(Modifier.fillMaxWidth().padding(horizontal = 12.dp), shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = White), elevation = CardDefaults.cardElevation(1.dp)) {
                    Column(Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) { Text("الشبكة", color = Muted, fontSize = 9.sp); Text(providerTitle(provider), color = if (yemenMobile) Pink else accent, fontWeight = FontWeight.Black, fontSize = 17.sp) }
                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) { providers.forEach { p -> ProviderCard(p, p.id == provider?.id, ::selectProvider) } }
                        if (isYemenNet) Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(7.dp)) { listOf("adsl" to "إنترنت ADSL", "line" to "الخط الثابت").forEach { (type, label) -> val selected = netType == type; Surface(Modifier.weight(1f).clickable { netType = type; service?.let(::runQuery) }, RoundedCornerShape(10.dp), if (selected) accent else Bg) { Text(label, color = if (selected) White else TextDark, fontWeight = FontWeight.Bold, fontSize = 10.sp, textAlign = TextAlign.Center, modifier = Modifier.padding(vertical = 9.dp)) } } }
                    }
                }
            }
            if (yemenMobile) item { Surface(Modifier.fillMaxWidth().padding(horizontal = 12.dp), color = Pink.copy(alpha = .08f), shape = RoundedCornerShape(13.dp)) { Text("Yemen Mobile", color = Pink, fontWeight = FontWeight.Black, fontSize = 13.sp, modifier = Modifier.padding(10.dp)) } }
            if (action == PaymentAction.PACKAGES) item {
                Column(Modifier.padding(horizontal = 12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) { SectionTitle("الباقات", "اضغط على الباقة للتسديد"); if (provider != null) Row(verticalAlignment = Alignment.CenterVertically) { Text("الشاحن الذكي", fontSize = 9.sp, color = Muted); Switch(checked = smartCharge, onCheckedChange = { smartCharge = it }) } }
                    val items = if (resultOffers.isNotEmpty()) resultOffers else purchaseService(providerServices, PaymentAction.PACKAGES)?.items.orEmpty().take(30)
                    if (items.isEmpty()) Surface(Modifier.fillMaxWidth(), RoundedCornerShape(14.dp), White) { Text("سيتم عرض الباقات بعد استعلام الباقات من المزود.", color = Muted, fontSize = 10.sp, modifier = Modifier.padding(14.dp), textAlign = TextAlign.Center) }
                    else items.chunked(3).forEach { row -> Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(7.dp)) { row.forEach { item -> PackageTile(item, if (yemenMobile) Pink else accent, Modifier.weight(1f)) { selectedItem = item; selectedOfferName = item.name; selectedOfferAmount = item.price?.toDoubleOrNull() ?: 0.0; service = purchaseService(providerServices, PaymentAction.PACKAGES) ?: service; showConfirmation = true } }; if (row.size < 3) repeat(3 - row.size) { Spacer(Modifier.weight(1f)) } } }
                }
            }
            if (action == PaymentAction.BALANCE && result != null) item {
                Card(Modifier.fillMaxWidth().padding(horizontal = 12.dp), shape = RoundedCornerShape(19.dp), colors = CardDefaults.cardColors(containerColor = White), elevation = CardDefaults.cardElevation(2.dp)) {
                    Column(Modifier.padding(13.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) { SectionTitle("نتيجة الاستعلام"); result!!.result.orEmpty().entries.sortedBy { it.key }.forEach { (key, value) -> Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text(resultLabel(key), color = Muted, fontSize = 10.sp); Text(displayValue(value), color = TextDark, fontWeight = FontWeight.Bold, fontSize = 10.sp, textAlign = TextAlign.End) } }; Surface(Modifier.fillMaxWidth(), Pink.copy(alpha = .09f), RoundedCornerShape(11.dp)) { Row(Modifier.fillMaxWidth().padding(10.dp), horizontalArrangement = Arrangement.SpaceBetween) { Text("السلفة الحالية", color = Pink, fontWeight = FontWeight.Bold, fontSize = 11.sp); Text(formatNumber(loan), color = Pink, fontWeight = FontWeight.Black, fontSize = 12.sp) } } }
                }
            }
            if (action != PaymentAction.BALANCE && action != PaymentAction.PACKAGES && service != null) item {
                Card(Modifier.fillMaxWidth().padding(horizontal = 12.dp), shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = White), elevation = CardDefaults.cardElevation(2.dp)) { Column(Modifier.padding(13.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) { Text(actionLabel(action), color = if (yemenMobile) Pink else accent, fontWeight = FontWeight.Black, fontSize = 18.sp); service!!.fields.filter { it.key != "mobile" }.forEach { f -> OutlinedTextField(values[f.key].orEmpty(), { values[f.key] = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text(f.label + if (f.required) " *" else "") }, shape = RoundedCornerShape(10.dp)) }; if (service!!.pricingMode == "amount" || action == PaymentAction.INSTANT) OutlinedTextField(amount, { amount = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text("المبلغ") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), shape = RoundedCornerShape(10.dp)); Button(onClick = { selectedOfferName = service!!.name; selectedOfferAmount = amount.toDoubleOrNull() ?: service!!.price.toDoubleOrNull() ?: 0.0; showConfirmation = true }, enabled = !working, modifier = Modifier.fillMaxWidth().height(49.dp), shape = RoundedCornerShape(12.dp), colors = ButtonDefaults.buttonColors(containerColor = if (yemenMobile) Pink else accent)) { Icon(Icons.Default.CheckCircle, null, Modifier.size(18.dp)); Spacer(Modifier.width(6.dp)); Text("تسديد + تفعيل", fontWeight = FontWeight.Black) } } }
            }
            result?.let { tx -> if ((action != PaymentAction.BALANCE && action != PaymentAction.PACKAGES) || tx.status != "success") item { Card(Modifier.fillMaxWidth().padding(horizontal = 12.dp).clickable { showResult = true }, shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = White), elevation = CardDefaults.cardElevation(2.dp)) { Column(Modifier.padding(13.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) { Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text("نتيجة العملية", fontWeight = FontWeight.Black, fontSize = 15.sp); Text(when(tx.status) { "success" -> "نجاح ✅"; "accepted", "queued", "processing", "pending_provider", "manual_review" -> "معلقة ⏳"; else -> "انتهت" }, color = if (tx.status == "success") Color(0xFF218838) else accent, fontWeight = FontWeight.Bold, fontSize = 10.sp) }; Text("اضغط لعرض كل بيانات المزود", color = Muted, fontSize = 9.sp) } } } }
            error?.let { msg -> item { Surface(Modifier.fillMaxWidth().padding(horizontal = 12.dp), shape = RoundedCornerShape(13.dp), color = Color(0xFFFFEEEE)) { Text(msg, color = Color(0xFFC13D3D), textAlign = TextAlign.Center, fontSize = 10.sp, modifier = Modifier.padding(11.dp)) } } }
            if (syncing) item { Box(Modifier.fillMaxWidth().padding(18.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator(color = if (yemenMobile) Pink else accent) } }
        }
    }

    if (showConfirmation) PurchaseConfirmDialog(selectedOfferName.ifBlank { selectedItem?.name.orEmpty() }, selectedOfferAmount, loan, if (yemenMobile) Pink else accent, ::confirmPurchase) { showConfirmation = false }
    if (waitingPurchase) AlertDialog(onDismissRequest = {}, title = { Text("تنفيذ العملية", fontWeight = FontWeight.Black) }, text = { Column(Modifier.fillMaxWidth(), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(10.dp)) { CircularProgressIndicator(color = if (yemenMobile) Pink else accent); Text("جاري انتظار النتيجة من المزود…", fontWeight = FontWeight.Bold); Text("لن يتم إغلاق العملية حتى تصل نتيجة الخادم.", color = Muted, fontSize = 10.sp, textAlign = TextAlign.Center) } }, confirmButton = {})
    if (showResult && result != null) ResultDetailsDialog(result!!) { showResult = false }
}
