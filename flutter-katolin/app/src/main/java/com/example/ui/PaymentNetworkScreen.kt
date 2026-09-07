package com.example.ui

import androidx.compose.animation.animateColorAsState
import androidx.compose.animation.core.tween
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Call
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Clear
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
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
import com.example.data.repository.StoreRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.UUID

private fun flattenServices(categories: List<ServiceCategoryDto>): List<ServiceDto> = buildList {
    categories.forEach { category ->
        addAll(category.services)
        addAll(flattenServices(category.children))
    }
}

private fun providerColor(slug: String, name: String): Color {
    val key = "$slug $name".lowercase()
    return when {
        "yemen-mobile" in key || "يمن موبايل" in key -> Color(0xFFC62828)
        "sabafon" in key || "سبأفون" in key -> Color(0xFF0288D1)
        "you" in key || "يو" in key -> Color(0xFFF9A825)
        "why" in key || "واي" in key -> Color(0xFF7B1FA2)
        "yemen-net" in key || "يمن نت" in key -> Color(0xFF0D47A1)
        "adenet" in key || "عدن نت" in key -> Color(0xFF00838F)
        "electric" in key || "كهرب" in key -> Color(0xFFFF8F00)
        "water" in key || "ماء" in key -> Color(0xFF0277BD)
        else -> Color(0xFF1565C0)
    }
}

private fun serviceTabLabel(service: ServiceDto): String {
    val text = service.name.lowercase()
    return when {
        "استعلام" in text || service.serviceKind == "query" -> "استعلام"
        "جملة" in text -> "جملة"
        "فوري" in text || "فئات" in text -> "فوري"
        "باقة" in text || "باقات" in text -> "باقات"
        "ريال" in text -> "ريال"
        "رصيد" in text -> "رصيد"
        else -> service.name.take(14)
    }
}

private fun prettifyResultKey(key: String): String = when (key.lowercase()) {
    "balance" -> "الرصيد"
    "availablecredit" -> "الرصيد المتاح"
    "remaamount", "remainamount" -> "المبلغ المتبقي"
    "mobiltype", "mobiletype" -> "نوع الخط"
    "mobile" -> "رقم الهاتف"
    "resultdesc" -> "الرسالة"
    "resultcode" -> "رمز النتيجة"
    "sequenceid" -> "رقم العملية لدى المزود"
    "offername" -> "اسم الباقة"
    "offerid" -> "معرف الباقة"
    "offerstartdate" -> "بداية الباقة"
    "offerenddate" -> "نهاية الباقة"
    "reason" -> "السبب"
    else -> key.replace('_', ' ').replaceFirstChar { it.uppercase() }
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
    val repository = remember { StoreRepository.instance }
    val configuredBaseUrl by repository.djangoBaseUrl.collectAsState()
    val baseUrl = configuredBaseUrl.trimEnd('/') + "/v2/"
    val session by repository.userSession.collectAsState()
    val scope = rememberCoroutineScope()

    var catalog by remember { mutableStateOf<List<ServiceMainCategoryDto>>(emptyList()) }
    var selectedProvider by remember { mutableStateOf<ServiceCategoryDto?>(null) }
    var selectedService by remember { mutableStateOf<ServiceDto?>(null) }
    var selectedItem by remember { mutableStateOf<ServiceItemDto?>(null) }
    var loading by remember { mutableStateOf(true) }
    var submitting by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var result by remember { mutableStateOf<ServiceTransactionDto?>(null) }
    var isBalanceVisible by remember { mutableStateOf(true) }
    var phone by remember(session.phone) { mutableStateOf(session.phone) }
    val fieldValues = remember { mutableStateMapOf<String, String>() }

    fun loadCatalog() {
        val token = session.token
        if (token.isNullOrBlank()) {
            loading = false
            error = "سجل الدخول أولاً لاستخدام خدمات التسديد."
            return
        }
        scope.launch {
            loading = true
            error = null
            try {
                val response = NetworkClient.getApiService(baseUrl).getServiceCatalog("Token $token")
                if (!response.isSuccessful || response.body() == null) {
                    error = "تعذر تحميل خدمات التسديد (HTTP ${response.code()})."
                    return@launch
                }
                catalog = response.body()!!.categories
                val payments = catalog.firstOrNull { it.slug == "payments" }
                    ?: catalog.firstOrNull { it.name.contains("تسديد") }
                    ?: catalog.firstOrNull()
                selectedProvider = payments?.categories?.firstOrNull()
                selectedService = selectedProvider?.let { flattenServices(listOf(it)).firstOrNull() }
                selectedItem = null
            } catch (e: Exception) {
                error = e.localizedMessage ?: "تعذر الاتصال بخادم الخدمات."
            } finally {
                loading = false
            }
        }
    }

    LaunchedEffect(session.token, configuredBaseUrl) { loadCatalog() }

    val paymentsRoot = catalog.firstOrNull { it.slug == "payments" }
        ?: catalog.firstOrNull { it.name.contains("تسديد") }
    val providers = paymentsRoot?.categories.orEmpty()
    val providerServices = selectedProvider?.let { flattenServices(listOf(it)) }.orEmpty().distinctBy { it.id }
    val accent by animateColorAsState(providerColor(selectedProvider?.slug.orEmpty(), selectedProvider?.name.orEmpty()), animationSpec = tween(300), label = "payment_accent")
    val tabs = providerServices.map { serviceTabLabel(it) }.distinct()

    fun chooseService(service: ServiceDto) {
        selectedService = service
        selectedItem = null
        result = null
        fieldValues.clear()
        service.fields.forEach { field ->
            if (field.key == "mobile" && phone.isNotBlank()) fieldValues[field.key] = phone
            if (field.type == "select" && field.choices.isNotEmpty()) fieldValues[field.key] = field.choices.first()
        }
    }

    fun submitService() {
        val service = selectedService ?: return
        if (submitting) return
        val token = session.token ?: return
        val missing = service.fields.firstOrNull { it.required && fieldValues[it.key].isNullOrBlank() }
        if (missing != null) {
            error = "الحقل المطلوب: ${missing.label}"
            return
        }
        if (service.pricingMode == "item" && service.items.isNotEmpty() && selectedItem == null) {
            error = "اختر الفئة أو الباقة أولاً."
            return
        }
        scope.launch {
            submitting = true
            error = null
            result = null
            try {
                val key = UUID.randomUUID().toString()
                val body = ServiceRequestPayload(
                    serviceId = service.id,
                    itemType = selectedItem?.type,
                    itemId = selectedItem?.id,
                    payload = fieldValues.mapValues { it.value.ifBlank { null } },
                    idempotencyKey = key
                )
                val response = NetworkClient.getApiService(baseUrl).submitServiceRequest("Token $token", key, body)
                if (!response.isSuccessful || response.body() == null) {
                    error = "تعذر إرسال العملية (HTTP ${response.code()})."
                    return@launch
                }
                var latest = response.body()!!
                repeat(20) {
                    result = latest
                    val status = latest.status.orEmpty().lowercase()
                    val done = status in setOf("success", "failed", "refunded") || (service.serviceKind == "query" && !latest.result.isNullOrEmpty())
                    if (done) return@repeat
                    delay(900)
                    val next = NetworkClient.getApiService(baseUrl).getServiceTransaction("Token $token", latest.id)
                    if (next.isSuccessful && next.body() != null) latest = next.body()!!
                }
                result = latest
                onSyncBalance()
            } catch (e: Exception) {
                error = e.localizedMessage ?: "حدث خطأ أثناء تنفيذ العملية."
            } finally {
                submitting = false
            }
        }
    }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = { Text("تسديد الخدمات", fontWeight = FontWeight.Bold) },
                navigationIcon = { IconButton(onClick = onBackClick) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "رجوع") } },
                actions = { IconButton(onClick = { loadCatalog(); onSyncBalance() }) { Icon(Icons.Default.Refresh, "تحديث") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = accent, titleContentColor = Color.White, navigationIconContentColor = Color.White, actionIconContentColor = Color.White)
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding).background(Color(0xFFF5F7FA)),
            contentPadding = PaddingValues(bottom = 30.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item {
                Column(Modifier.fillMaxWidth().background(accent).padding(horizontal = 16.dp, vertical = 12.dp)) {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.Center) {
                        Surface(shape = CircleShape, color = Color.White.copy(alpha = .18f), modifier = Modifier.clickable { isBalanceVisible = !isBalanceVisible }) {
                            Row(Modifier.padding(horizontal = 14.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                Icon(if (isBalanceVisible) Icons.Default.Visibility else Icons.Default.VisibilityOff, null, tint = Color.White, modifier = Modifier.size(18.dp))
                                Text(if (isBalanceVisible) "${formatMoney(wallet.balanceYer)} ر.ي" else "•••••", color = Color.White, fontWeight = FontWeight.Bold)
                                Text("رصيدي", color = Color.White.copy(alpha = .9f), fontSize = 12.sp)
                            }
                        }
                    }
                    Spacer(Modifier.height(8.dp))
                    Text("تسديد شبكات الاتصالات والخدمات", modifier = Modifier.fillMaxWidth(), color = Color.White, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center, fontSize = 16.sp)
                    Spacer(Modifier.height(8.dp))
                    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                        providers.forEach { provider ->
                            val selected = selectedProvider?.id == provider.id
                            FilterChip(selected = selected, onClick = { selectedProvider = provider; selectedService = flattenServices(listOf(provider)).firstOrNull(); selectedItem = null; result = null }, label = { Text(provider.name) }, leadingIcon = { Icon(Icons.Default.Call, null, modifier = Modifier.size(16.dp)) })
                        }
                    }
                }
            }

            item {
                Card(Modifier.fillMaxWidth().padding(horizontal = 14.dp), shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = Color.White), elevation = CardDefaults.cardElevation(3.dp)) {
                    Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("رقم المستفيد", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        OutlinedTextField(value = phone, onValueChange = { phone = it; fieldValues["mobile"] = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("ادخل رقم الهاتف / الاشتراك") }, leadingIcon = { Icon(Icons.Default.Call, null, tint = accent) }, trailingIcon = { if (phone.isNotEmpty()) IconButton(onClick = { phone = ""; fieldValues.remove("mobile") }) { Icon(Icons.Default.Clear, "مسح") } }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone), shape = RoundedCornerShape(12.dp))
                        Text("+967  ${phone.ifBlank { "—" }}", modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.Center, color = accent, fontWeight = FontWeight.Bold)
                    }
                }
            }

            if (loading) {
                item { Column(Modifier.fillMaxWidth().padding(32.dp), horizontalAlignment = Alignment.CenterHorizontally) { CircularProgressIndicator(color = accent); Spacer(Modifier.height(8.dp)); Text("جارٍ تحميل الخدمات والباقات من الخادم…") } }
            } else if (error != null) {
                item { Card(Modifier.fillMaxWidth().padding(horizontal = 14.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) { Column(Modifier.padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) { Icon(Icons.Default.ErrorOutline, null); Text(error!!, textAlign = TextAlign.Center); TextButton(onClick = { error = null; loadCatalog() }) { Text("إعادة المحاولة") } } } }
            } else {
                if (tabs.isNotEmpty()) {
                    item { Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 14.dp), horizontalArrangement = Arrangement.spacedBy(6.dp)) { tabs.forEach { tab -> val active = selectedService?.let { serviceTabLabel(it) } == tab; FilterChip(selected = active, onClick = { selectedService = providerServices.firstOrNull { serviceTabLabel(it) == tab } }, label = { Text(tab) }) } } }
                }

                items(providerServices) { service ->
                    Card(onClick = { chooseService(service) }, modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp), shape = RoundedCornerShape(14.dp), colors = CardDefaults.cardColors(containerColor = if (selectedService?.id == service.id) accent.copy(alpha = .10f) else Color.White)) {
                        Row(Modifier.fillMaxWidth().padding(13.dp), verticalAlignment = Alignment.CenterVertically) {
                            Surface(shape = CircleShape, color = accent.copy(alpha = .12f), modifier = Modifier.size(40.dp)) { Box(contentAlignment = Alignment.Center) { Icon(if (service.serviceKind == "query") Icons.Default.Search else Icons.Default.AccountBalanceWallet, null, tint = accent, modifier = Modifier.size(19.dp)) } }
                            Spacer(Modifier.width(10.dp))
                            Column(Modifier.weight(1f)) {
                                Text(service.name, fontWeight = FontWeight.Bold, maxLines = 2)
                                Text(if (service.items.isNotEmpty()) "${service.items.size} فئة/باقة" else if (service.serviceKind == "query") "استعلام بدون خصم" else "خدمة حسب المبلغ", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Text(if (service.serviceKind == "query") "استعلام" else serviceTabLabel(service), color = accent, fontSize = 11.sp, fontWeight = FontWeight.Bold)
                        }
                    }
                }

                selectedService?.let { service ->
                    item {
                        Card(Modifier.fillMaxWidth().padding(horizontal = 14.dp), shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(containerColor = Color.White), elevation = CardDefaults.cardElevation(4.dp)) {
                            Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                                    Column(Modifier.weight(1f)) { Text(service.name, fontWeight = FontWeight.Bold, fontSize = 18.sp); Text(service.description.ifBlank { service.code }, fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                                    Surface(shape = CircleShape, color = accent.copy(alpha = .12f), modifier = Modifier.size(40.dp)) { Box(contentAlignment = Alignment.Center) { Icon(Icons.Default.AccountBalanceWallet, null, tint = accent) } }
                                }
                                if (service.items.isNotEmpty()) {
                                    Text("اختر الفئة / الباقة", fontWeight = FontWeight.Bold)
                                    service.items.chunked(2).forEach { rowItems ->
                                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                            rowItems.forEach { item ->
                                                Card(onClick = { selectedItem = item }, modifier = Modifier.weight(1f), shape = RoundedCornerShape(13.dp), colors = CardDefaults.cardColors(containerColor = if (selectedItem?.id == item.id) accent.copy(alpha = .14f) else Color(0xFFF7F8FB))) {
                                                    Column(Modifier.padding(11.dp), horizontalAlignment = Alignment.CenterHorizontally) { Text(item.name, fontWeight = FontWeight.Bold, textAlign = TextAlign.Center, maxLines = 2); Text(item.price?.let { "${formatMoney(it.toDoubleOrNull() ?: 0.0)} ${item.currency}" } ?: "حسب الخدمة", fontSize = 11.sp, color = accent, fontWeight = FontWeight.Bold) }
                                                }
                                            }
                                            if (rowItems.size == 1) Spacer(Modifier.weight(1f))
                                        }
                                    }
                                }
                                service.fields.forEach { field -> PaymentField(field, fieldValues[field.key].orEmpty()) { value -> fieldValues[field.key] = value; if (field.key == "mobile") phone = value } }
                                if (service.serviceKind == "query") Text("لا يتم خصم أي مبلغ من الاستعلام.", color = accent, fontSize = 11.sp, fontWeight = FontWeight.Medium)
                                else if (service.pricingMode == "amount") Text("المبلغ يحدد داخل حدود الخدمة التي أرسلها الخادم.", color = MaterialTheme.colorScheme.onSurfaceVariant, fontSize = 11.sp)
                                Button(onClick = { submitService() }, enabled = !submitting, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(13.dp)) { if (submitting) CircularProgressIndicator(modifier = Modifier.size(18.dp), strokeWidth = 2.dp) else Text(if (service.serviceKind == "query") "استعلام" else "تأكيد وخصم الرصيد", fontWeight = FontWeight.Bold) }
                                result?.let { ResultCard(it, formatMoney, accent) }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun PaymentField(field: ServiceFieldDto, value: String, onValueChange: (String) -> Unit) {
    if (field.key == "mobile") return
    if (field.type == "select" && field.choices.isNotEmpty()) {
        Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Text(field.label, fontWeight = FontWeight.Medium, fontSize = 12.sp)
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) { field.choices.forEach { choice -> FilterChip(selected = value == choice, onClick = { onValueChange(choice) }, label = { Text(choice) }) } }
        }
        return
    }
    val keyboard = when (field.type) { "number", "decimal" -> KeyboardType.Number; "phone" -> KeyboardType.Phone; "email" -> KeyboardType.Email; else -> KeyboardType.Text }
    OutlinedTextField(value = value, onValueChange = onValueChange, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text(field.label + if (field.required) " *" else "") }, keyboardOptions = KeyboardOptions(keyboardType = keyboard), shape = RoundedCornerShape(11.dp))
}

@Composable
private fun ResultCard(transaction: ServiceTransactionDto, formatMoney: (Double) -> String, accent: Color) {
    val status = transaction.status.orEmpty().lowercase()
    val resultMap = transaction.result.orEmpty()
    val success = status == "success" || resultMap["resultCode"]?.toString() == "0"
    val pending = status in setOf("queued", "processing", "pending_provider", "accepted")
    val cardColor = if (success) Color(0xFFE8F5E9) else if (pending) Color(0xFFFFF8E1) else MaterialTheme.colorScheme.errorContainer
    Card(colors = CardDefaults.cardColors(containerColor = cardColor), shape = RoundedCornerShape(15.dp)) {
        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Icon(if (success) Icons.Default.CheckCircle else if (pending) Icons.Default.Refresh else Icons.Default.ErrorOutline, null, tint = accent, modifier = Modifier.size(22.dp))
                Spacer(Modifier.width(7.dp))
                Text(if (success) "تمت العملية بنجاح" else if (pending) "العملية قيد المعالجة" else "تعذر إتمام العملية", fontWeight = FontWeight.Bold, modifier = Modifier.weight(1f))
                Text(transaction.amount?.toDoubleOrNull()?.let { formatMoney(it) + " " + (transaction.currency ?: "ر.ي") } ?: "", color = accent, fontWeight = FontWeight.Bold)
            }
            resultMap.entries.forEach { (key, value) ->
                if (value != null && value.toString().isNotBlank()) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text(prettifyResultKey(key), fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant); Text(value.toString(), fontSize = 12.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.End) }
                }
            }
            Text("رقم العملية: ${transaction.id}", fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
            transaction.errorMessage?.takeIf { it.isNotBlank() }?.let { Text(it, color = MaterialTheme.colorScheme.error, fontSize = 11.sp) }
        }
    }
}
