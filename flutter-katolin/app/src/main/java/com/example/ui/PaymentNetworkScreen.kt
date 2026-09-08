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
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CloudDownload
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Inventory2
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Sync
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedButton
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
import com.example.data.remote.ServiceDto
import com.example.data.remote.ServiceFieldDto
import com.example.data.remote.ServiceItemDto
import com.example.data.remote.ServiceMainCategoryDto
import com.example.data.remote.ServiceRequestPayload
import com.example.data.remote.ServiceTransactionDto
import com.example.data.remote.ServiceCatalogResponse
import com.example.data.repository.StoreRepository
import kotlinx.coroutines.launch
import java.util.UUID

private val Bg = Color(0xFFF6F4F8)
private val Pink = Color(0xFFC01855)
private val Neutral = Color(0xFF39445A)

private fun digits(value: String): String = value.map {
    when (it) {
        '٠' -> '0'; '١' -> '1'; '٢' -> '2'; '٣' -> '3'; '٤' -> '4';
        '٥' -> '5'; '٦' -> '6'; '٧' -> '7'; '٨' -> '8'; '٩' -> '9';
        '۰' -> '0'; '۱' -> '1'; '۲' -> '2'; '۳' -> '3'; '۴' -> '4';
        '۵' -> '5'; '۶' -> '6'; '۷' -> '7'; '۸' -> '8'; '۹' -> '9';
        else -> it
    }
}.joinToString("")

private fun isYemenMobile(phone: String): Boolean {
    val p = digits(phone).filter(Char::isDigit)
    return p.startsWith("77") || p.startsWith("78")
}

private fun providerColor(provider: ServiceCategoryDto?): Color {
    val key = "${provider?.slug.orEmpty()} ${provider?.name.orEmpty()}".lowercase()
    return when {
        "yemen-mobile" in key || "يمن موبايل" in key -> Pink
        "sabafon" in key || "سبأفون" in key -> Color(0xFF1976B8)
        "you" in key || "يو" in key -> Color(0xFFD08A00)
        "why" in key || "واي" in key -> Color(0xFF6C4390)
        "4g" in key || "فورجي" in key -> Color(0xFF0A8787)
        "yemen-net" in key || "يمن نت" in key -> Color(0xFF2D5B99)
        else -> Neutral
    }
}

private fun providerTitle(provider: ServiceCategoryDto?): String {
    val key = "${provider?.slug.orEmpty()} ${provider?.name.orEmpty()}".lowercase()
    return when {
        "yemen-mobile" in key || "يمن موبايل" in key -> "Yemen Mobile"
        else -> provider?.name.orEmpty()
    }
}

private fun flattenServices(category: ServiceCategoryDto): List<ServiceDto> =
    category.services + category.children.flatMap(::flattenServices)

private fun isOfferService(service: ServiceDto): Boolean {
    val s = "${service.code} ${service.name}".lowercase()
    return "offer" in s || "باقة" in s || "باقات" in s || "عروض" in s
}

private fun isBalanceService(service: ServiceDto): Boolean = !isOfferService(service)

private fun serviceForQuery(services: List<ServiceDto>, offers: Boolean): ServiceDto? =
    services.firstOrNull { it.serviceKind == "query" && if (offers) isOfferService(it) else isBalanceService(it) }

private fun serviceForPurchase(services: List<ServiceDto>, offers: Boolean): ServiceDto? =
    services.firstOrNull { it.serviceKind == "purchase" && if (offers) isOfferService(it) else isBalanceService(it) }

private fun resultMap(tx: ServiceTransactionDto?): Map<String, Any?> = tx?.result.orEmpty()

private fun findLoan(result: Map<String, Any?>): String? = result.entries.firstOrNull {
    val key = it.key.lowercase().replace("_", "")
    key in setOf("loanamount", "loan", "solfa", "sulfa") || key.contains("سلف") || key.contains("سلفة")
}?.value?.toString()?.takeIf { it.isNotBlank() }

private fun valueText(value: Any?): String = when (value) {
    null -> "—"
    is Map<*, *> -> value.entries.joinToString("\n") { "${it.key}: ${valueText(it.value)}" }
    is List<*> -> value.joinToString("\n") { valueText(it) }
    else -> value.toString()
}

@Composable
private fun ResultDialog(tx: ServiceTransactionDto, onClose: () -> Unit) {
    val pending = tx.status.orEmpty() in setOf("accepted", "queued", "processing", "pending_provider", "manual_review")
    AlertDialog(
        onDismissRequest = onClose,
        title = { Text("نتيجة العملية", fontWeight = FontWeight.Black) },
        text = {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(9.dp)) {
                item {
                    Surface(color = if (tx.status == "success") Color(0xFFEAF8EF) else Bg, shape = RoundedCornerShape(14.dp)) {
                        Text(
                            when {
                                tx.status == "success" -> "تمت العملية بنجاح ✅"
                                pending -> "العملية ما زالت قيد المعالجة لدى المزود ⏳"
                                tx.status == "refunded" -> "أعيد المبلغ إلى محفظتك."
                                tx.status == "manual_review" -> "العملية تحتاج مراجعة."
                                else -> tx.errorMessage ?: "تعذر تنفيذ العملية."
                            },
                            fontWeight = FontWeight.Bold,
                            modifier = Modifier.fillMaxWidth().padding(11.dp)
                        )
                    }
                }
                item { Text("المرجع: ${tx.id}", color = Color.Gray, fontSize = 10.sp) }
                tx.amount?.let { item { Text("المبلغ: $it ${tx.currency.orEmpty()}", fontWeight = FontWeight.Bold) } }
                tx.providerTransid?.let { item { Text("رقم المزود: $it", color = Color.Gray, fontSize = 10.sp) } }
                findLoan(resultMap(tx))?.let { item { Text("السلفة: $it", color = Pink, fontWeight = FontWeight.Black) } }
                resultMap(tx).entries.sortedBy { it.key }.forEach { (key, value) ->
                    if (value != null) item {
                        Column(Modifier.fillMaxWidth()) {
                            Text(key, color = Color.Gray, fontSize = 9.sp)
                            Text(valueText(value), fontWeight = FontWeight.Bold, fontSize = 11.sp, textAlign = TextAlign.End, modifier = Modifier.fillMaxWidth())
                        }
                    }
                }
            }
        },
        confirmButton = { TextButton(onClick = onClose) { Text("إغلاق") } }
    )
}

@Composable
private fun OfferCard(
    name: String,
    value: Any?,
    amount: String?,
    loan: String?,
    accent: Color,
    onSelect: () -> Unit
) {
    Card(Modifier.fillMaxWidth().clickable(onClick = onSelect), shape = RoundedCornerShape(16.dp), colors = CardDefaults.cardColors(Color.White), elevation = CardDefaults.cardElevation(1.dp)) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Text("اختيار", color = accent, fontWeight = FontWeight.Bold, fontSize = 9.sp)
                Text(name, fontWeight = FontWeight.Black, fontSize = 12.sp, textAlign = TextAlign.End)
            }
            Text(valueText(value), color = Color.Gray, fontSize = 9.sp, textAlign = TextAlign.End, modifier = Modifier.fillMaxWidth())
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                amount?.let { Text("قيمة: $it", color = accent, fontWeight = FontWeight.Black, fontSize = 10.sp) }
                loan?.let { Text("سلفة: $it", color = Pink, fontWeight = FontWeight.Bold, fontSize = 10.sp) }
            }
        }
    }
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
    var service by remember { mutableStateOf<ServiceDto?>(null) }
    var selectedItem by remember { mutableStateOf<ServiceItemDto?>(null) }
    var phone by remember(session.phone) { mutableStateOf(session.phone) }
    var amount by remember { mutableStateOf("") }
    var syncing by remember { mutableStateOf(false) }
    var working by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var result by remember { mutableStateOf<ServiceTransactionDto?>(null) }
    var showResult by remember { mutableStateOf(false) }
    var showReports by remember { mutableStateOf(false) }
    var selectedPackage by remember { mutableStateOf<ServiceItemDto?>(null) }
    var showPackageConfirmation by remember { mutableStateOf(false) }
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
            syncing = true; error = null
            try {
                val response = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/").getServiceCatalog("Token $token")
                if (!response.isSuccessful || response.body() == null) {
                    throw IllegalStateException("تعذر مزامنة الكتالوج (HTTP ${response.code()}).")
                }
                val body = response.body()!!
                catalog = body.categories
                SessionStore.saveLocalString(cacheKey, NetworkClient.moshi().adapter(ServiceCatalogResponse::class.java).toJson(body))
                provider = null; service = null; selectedItem = null
            } catch (e: Exception) {
                error = e.localizedMessage ?: "تعذر مزامنة الخدمات."
            } finally { syncing = false }
        }
    }

    LaunchedEffect(baseUrl, session.token) { restoreCatalog() }

    val root = catalog.firstOrNull { it.slug == "payments" } ?: catalog.firstOrNull { it.name.contains("تسديد") }
    val providers = root?.categories.orEmpty()
    val services = provider?.let(::flattenServices).orEmpty().distinctBy { it.id }
    val accent = providerColor(provider)
    val ym = isYemenMobile(phone)

    fun chooseProvider(p: ServiceCategoryDto) {
        provider = p; service = null; selectedItem = null; selectedPackage = null; result = null; values.clear(); error = null
    }

    fun chooseService(s: ServiceDto) {
        service = s; selectedItem = null; result = null; amount = ""; error = null; values.clear()
        s.fields.forEach { f ->
            if (f.key == "mobile") values[f.key] = digits(phone)
            if (f.type == "select" && f.choices.isNotEmpty()) values[f.key] = f.choices.first()
        }
    }

    fun query(serviceToRun: ServiceDto) {
        val token = session.token ?: return
        chooseService(serviceToRun)
        scope.launch {
            working = true; error = null; result = null
            try {
                val id = UUID.randomUUID().toString()
                val payload = ServiceRequestPayload(serviceToRun.id, null, null, values.toMap(), id)
                val response = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/").submitServiceRequest("Token $token", id, payload)
                if (!response.isSuccessful || response.body() == null) throw IllegalStateException("تعذر الاستعلام (HTTP ${response.code()}).")
                result = response.body(); showResult = false
            } catch (e: Exception) { error = e.localizedMessage ?: "فشل الاستعلام." }
            finally { working = false }
        }
    }

    fun purchase(item: ServiceItemDto? = selectedItem) {
        val s = service ?: return
        val token = session.token ?: return
        scope.launch {
            working = true; error = null
            try {
                val payloadMap = values.toMutableMap()
                item?.metadata?.get("offerid")?.let { payloadMap["offerid"] = it }
                item?.metadata?.get("offerkey")?.let { payloadMap["offerkey"] = it }
                if (amount.isNotBlank()) payloadMap["amount"] = amount
                val missing = s.fields.firstOrNull { it.required && payloadMap[it.key].isNullOrBlank() }
                if (missing != null) throw IllegalStateException("الحقل المطلوب: ${missing.label}")
                if (s.pricingMode == "item" && s.items.isNotEmpty() && item == null) throw IllegalStateException("اختر الباقة أولًا.")
                val id = UUID.randomUUID().toString()
                val body = ServiceRequestPayload(s.id, item?.type, item?.id, payloadMap.mapValues { it.value }, id)
                val response = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/").submitServiceRequest("Token $token", id, body)
                if (!response.isSuccessful || response.body() == null) throw IllegalStateException("تعذر تنفيذ العملية (HTTP ${response.code()}).")
                result = response.body(); showResult = true
                if (result?.status == "success" || result?.status == "refunded") onSyncBalance()
                if (result?.status == "success") onRechargeSubmit(phone, providerTitle(provider), s.name, item?.name ?: s.name, result?.amount?.toDoubleOrNull() ?: 0.0)
            } catch (e: Exception) { error = e.localizedMessage ?: "حدث خطأ أثناء التنفيذ." }
            finally { working = false }
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
                title = { Text("شبكة السداد", fontWeight = FontWeight.Black, fontSize = 20.sp) },
                navigationIcon = { IconButton(onClick = onBackClick) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "رجوع") } },
                actions = {
                    IconButton(onClick = { showReports = true }) { Icon(Icons.Default.Inventory2, "التقرير") }
                    IconButton(onClick = ::syncCatalog) { Icon(Icons.Default.CloudDownload, "مزامنة") }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = if (ym) Pink.copy(alpha = .08f) else Bg)
            )
        }
    ) { pad ->
        LazyColumn(Modifier.fillMaxSize().padding(pad).background(Bg), contentPadding = PaddingValues(12.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            item {
                Card(shape = RoundedCornerShape(24.dp), colors = CardDefaults.cardColors(if (ym) Pink.copy(alpha = .10f) else Color.White), elevation = CardDefaults.cardElevation(1.dp)) {
                    Column(Modifier.fillMaxWidth().padding(15.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(if (ym) "Yemen Mobile" else "خدمات التسديد", fontWeight = FontWeight.Black, fontSize = 22.sp, color = if (ym) Pink else Neutral)
                                Text(if (catalog.isEmpty()) "اضغط مزامنة أولًا لتحميل خدمات وباقات الخادم." else "الكتالوج محفوظ محليًا ولا يُعاد تحميله تلقائيًا.", color = Color.Gray, fontSize = 10.sp)
                            }
                            Surface(shape = CircleShape, color = if (ym) Pink else Neutral.copy(alpha = .10f), modifier = Modifier.size(58.dp)) {
                                Box(contentAlignment = Alignment.Center) { Text(if (ym) "YM" else "K", color = if (ym) Color.White else Neutral, fontWeight = FontWeight.Black) }
                            }
                        }
                        OutlinedTextField(phone, { phone = it; service?.let { s -> if (s.fields.any { f -> f.key == "mobile" }) values["mobile"] = digits(it) } }, Modifier.fillMaxWidth(), singleLine = true, label = { Text("رقم الهاتف / المستفيد") }, leadingIcon = { Icon(Icons.Default.Call, null, tint = if (ym) Pink else accent) }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone), shape = RoundedCornerShape(15.dp))
                        if (ym) Text("تم التعرف على يمن موبايل من بادئة 77 / 78", color = Pink, fontWeight = FontWeight.Bold, fontSize = 10.sp)
                    }
                }
            }

            item {
                Card(shape = RoundedCornerShape(22.dp), colors = CardDefaults.cardColors(Color.White), elevation = CardDefaults.cardElevation(1.dp)) {
                    Column(Modifier.padding(13.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text("الشبكات", fontWeight = FontWeight.ExtraBold); Text("من الكتالوج المحلي", color = Color.Gray, fontSize = 9.sp) }
                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            providers.forEach { p ->
                                val selected = provider?.id == p.id
                                Surface(Modifier.width(120.dp).clickable { chooseProvider(p) }, RoundedCornerShape(16.dp), if (selected) providerColor(p) else Color(0xFFFAF9FB)) {
                                    Column(Modifier.padding(10.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(5.dp)) {
                                        Box(Modifier.size(42.dp).background(if (selected) Color.White.copy(alpha = .15f) else providerColor(p).copy(alpha = .10f), CircleShape), contentAlignment = Alignment.Center) { Text(providerTitle(p).take(3), color = if (selected) Color.White else providerColor(p), fontWeight = FontWeight.Black, fontSize = 10.sp) }
                                        Text(providerTitle(p), color = if (selected) Color.White else Color.Black, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                                    }
                                }
                            }
                        }
                    }
                }
            }

            provider?.let { p ->
                item {
                    Card(shape = RoundedCornerShape(22.dp), colors = CardDefaults.cardColors(Color.White), elevation = CardDefaults.cardElevation(1.dp)) {
                        Column(Modifier.padding(13.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                            Text(providerTitle(p), color = accent, fontSize = 18.sp, fontWeight = FontWeight.Black)
                            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                                FilterChip(false, { serviceForQuery(services, false)?.let(::query) }, label = { Text("الرصيد") }, leadingIcon = { Icon(Icons.Default.AccountBalanceWallet, null, Modifier.size(16.dp)) })
                                FilterChip(false, { serviceForQuery(services, true)?.let(::query) }, label = { Text("الباقات") }, leadingIcon = { Icon(Icons.Default.Inventory2, null, Modifier.size(16.dp)) })
                                FilterChip(false, { serviceForPurchase(services, false)?.let(::chooseService) }, label = { Text("تسديد") }, leadingIcon = { Icon(Icons.Default.CheckCircle, null, Modifier.size(16.dp)) })
                            }
                            if (services.isNotEmpty()) {
                                Text("خدمات إضافية", color = Color.Gray, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                                Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) { services.take(10).forEach { s -> FilterChip(selected = service?.id == s.id, onClick = { chooseService(s) }, label = { Text(s.name, fontSize = 9.sp) }) } }
                            }
                        }
                    }
                }
            }

            result?.let { tx ->
                val offerEntries = resultMap(tx).entries.filter { (k, v) ->
                    val keyName = k.lowercase()
                    keyName.contains("offer") || keyName.contains("package") || keyName.contains("باقة") || keyName.contains("عروض") || v is List<*> && v.any { it is Map<*, *> }
                }
                if (offerEntries.isNotEmpty()) {
                    item {
                        Card(shape = RoundedCornerShape(22.dp), colors = CardDefaults.cardColors(Color.White), elevation = CardDefaults.cardElevation(1.dp)) {
                            Column(Modifier.padding(13.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Text("نتائج الباقات", fontWeight = FontWeight.Black, fontSize = 15.sp, color = accent)
                                val loan = findLoan(resultMap(tx))
                                offerEntries.forEach { (keyName, value) ->
                                    if (value is List<*>) value.forEachIndexed { index, entry ->
                                        OfferCard("$keyName ${index + 1}", entry, null, loan, accent) { selectedPackage = null }
                                    } else OfferCard(keyName, value, null, loan, accent) { selectedPackage = null }
                                }
                            }
                        }
                    }
                }
                item { ResultSummary(tx, accent) { showResult = true } }
            }

            service?.let { s ->
                item {
                    Card(shape = RoundedCornerShape(22.dp), colors = CardDefaults.cardColors(Color.White), elevation = CardDefaults.cardElevation(2.dp)) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Column(Modifier.weight(1f)) { Text(s.name, color = accent, fontWeight = FontWeight.Black, fontSize = 18.sp); Text(if (s.serviceKind == "query") "استعلام" else "عملية مدفوعة", color = Color.Gray, fontSize = 9.sp) }
                                if (s.serviceKind == "query") Icon(Icons.Default.Search, null, tint = accent)
                            }
                            s.items.take(50).forEach { item ->
                                val selected = selectedItem?.id == item.id && selectedItem?.type == item.type
                                Surface(Modifier.fillMaxWidth().clickable { selectedItem = item; if (isOfferService(s)) { selectedPackage = item; showPackageConfirmation = true } }, RoundedCornerShape(14.dp), if (selected) accent.copy(alpha = .10f) else Color(0xFFFAF9FB), border = androidx.compose.foundation.BorderStroke(1.dp, if (selected) accent else Color(0xFFE8E5EA))) {
                                    Row(Modifier.padding(10.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) { Text(item.name, fontWeight = FontWeight.Bold, fontSize = 11.sp, modifier = Modifier.weight(1f)); Text(item.price ?: "—", color = accent, fontWeight = FontWeight.Black, fontSize = 10.sp) }
                                }
                            }
                            s.fields.filter { it.key != "mobile" && it.key !in setOf("external_code", "num", "packageid", "uniqcode") }.forEach { f ->
                                OutlinedTextField(values[f.key].orEmpty(), { values[f.key] = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text(f.label + if (f.required) " *" else "") }, shape = RoundedCornerShape(13.dp), keyboardOptions = KeyboardOptions(keyboardType = when (f.type) { "number", "decimal" -> KeyboardType.Number; "phone" -> KeyboardType.Phone; else -> KeyboardType.Text }))
                            }
                            if (s.pricingMode == "amount" || s.name.contains("رصيد") || s.name.contains("شحن")) OutlinedTextField(amount, { amount = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text("المبلغ") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), shape = RoundedCornerShape(13.dp))
                            Button(onClick = { if (s.serviceKind == "query") query(s) else purchase() }, enabled = !working, Modifier.fillMaxWidth().height(49.dp), shape = RoundedCornerShape(14.dp), colors = ButtonDefaults.buttonColors(containerColor = accent)) {
                                if (working) CircularProgressIndicator(Modifier.size(18.dp), color = Color.White, strokeWidth = 2.dp) else Icon(if (s.serviceKind == "query") Icons.Default.Search else Icons.Default.CheckCircle, null, Modifier.size(18.dp))
                                Spacer(Modifier.width(7.dp)); Text(if (s.serviceKind == "query") "استعلام" else "تسديد + تفعيل", fontWeight = FontWeight.Black)
                            }
                        }
                    }
                }
            }

            if (syncing) item { Box(Modifier.fillMaxWidth().padding(25.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator(color = accent) } }
            error?.let { item { Text(it, color = Color(0xFFC23A3A), textAlign = TextAlign.Center, modifier = Modifier.fillMaxWidth().background(Color(0xFFFFEEEE), RoundedCornerShape(14.dp)).padding(12.dp), fontSize = 10.sp) } }
        }
    }

    if (showPackageConfirmation && selectedPackage != null) {
        val loan = findLoan(resultMap(result))
        val packageAmount = selectedPackage?.price ?: result?.amount
        AlertDialog(
            onDismissRequest = { showPackageConfirmation = false },
            title = { Text("تأكيد الباقة", fontWeight = FontWeight.Black) },
            text = { Column(verticalArrangement = Arrangement.spacedBy(9.dp)) { Text(selectedPackage?.name.orEmpty(), fontWeight = FontWeight.Black); Text("قيمة الباقة: ${packageAmount ?: "—"}"); Text("السلفة: ${loan ?: "لا توجد سلفة ظاهرة"}", color = Pink, fontWeight = FontWeight.Bold); Text("سيقوم الخادم بتنفيذ التسديد والتفعيل حسب الربطية والـAPI.", color = Color.Gray, fontSize = 10.sp) } },
            confirmButton = { Button(onClick = { showPackageConfirmation = false; purchase(selectedPackage) }, enabled = !working) { Text("تسديد + تفعيل") } },
            dismissButton = { TextButton(onClick = { showPackageConfirmation = false }) { Text("إلغاء") } }
        )
    }

    if (showResult && result != null) ResultDialog(result!!) { showResult = false }
}

@Composable
private fun ResultSummary(tx: ServiceTransactionDto, accent: Color, onOpen: () -> Unit) {
    val pending = tx.status.orEmpty() in setOf("accepted", "queued", "processing", "pending_provider", "manual_review")
    Card(Modifier.fillMaxWidth().clickable(onClick = onOpen), shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(Color.White), elevation = CardDefaults.cardElevation(2.dp)) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text("نتيجة العملية", fontWeight = FontWeight.Black, fontSize = 15.sp); Text(if (tx.status == "success") "نجاح ✅" else if (pending) "معلقة ⏳" else "انتهت", color = accent, fontSize = 10.sp, fontWeight = FontWeight.Bold) }
            tx.errorMessage?.takeIf { it.isNotBlank() }?.let { Text(it, color = Color.Gray, fontSize = 9.sp) }
            Text("اضغط لعرض كامل استجابة المزود", color = accent, fontSize = 9.sp, fontWeight = FontWeight.Bold)
        }
    }
}