@file:OptIn(androidx.compose.material3.ExperimentalMaterial3Api::class)

package com.example.ui

import androidx.compose.foundation.background
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
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ChevronLeft
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
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
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.UserSession
import com.example.data.remote.NetworkClient
import com.example.data.remote.ServiceCategoryDto
import com.example.data.remote.ServiceDto
import com.example.data.remote.ServiceFieldDto
import com.example.data.remote.ServiceItemDto
import com.example.data.remote.ServiceMainCategoryDto
import com.example.data.remote.ServiceRequestPayload
import com.example.data.remote.ServiceTransactionDto
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import java.util.UUID

private fun flattenServices(categories: List<ServiceCategoryDto>): List<ServiceDto> = buildList {
    categories.forEach { category ->
        addAll(category.services)
        addAll(flattenServices(category.children))
    }
}

private fun catalogBase(baseUrl: String): String {
    val base = baseUrl.trim().trimEnd('/')
    return when {
        base.endsWith("/api/v2") -> "$base/"
        base.endsWith("/api") -> "$base/v2/"
        base.isBlank() -> "https://shopik.alattab.site/api/v2/"
        else -> "$base/api/v2/"
    }
}

private fun prettyKey(key: String): String = when (key.lowercase()) {
    "resultcode" -> "رمز النتيجة"
    "resultdesc" -> "الرسالة"
    "balance" -> "الرصيد"
    "availablecredit" -> "الرصيد المتاح"
    "mobiletype" -> "نوع الخط"
    "remainamount", "remaamount" -> "المبلغ المتبقي"
    "sequenceid" -> "رقم العملية"
    "offername" -> "اسم الباقة"
    "offerid" -> "معرف الباقة"
    "offerstartdate" -> "بداية الباقة"
    "offerenddate" -> "نهاية الباقة"
    "isdone" -> "مكتملة"
    "isban" -> "محظورة"
    "reason" -> "السبب"
    else -> key.replace('_', ' ')
}

private fun isTerminal(status: String?): Boolean = status?.lowercase() in setOf("success", "failed", "refunded")

@Composable
fun DynamicServicesScreen(
    userSession: UserSession,
    djangoBaseUrl: String,
    onBackClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val apiBase = catalogBase(djangoBaseUrl)
    val scope = rememberCoroutineScope()
    var catalog by remember { mutableStateOf<List<ServiceMainCategoryDto>>(emptyList()) }
    var selectedMain by remember { mutableStateOf<ServiceMainCategoryDto?>(null) }
    var selectedCategory by remember { mutableStateOf<ServiceCategoryDto?>(null) }
    var selectedService by remember { mutableStateOf<ServiceDto?>(null) }
    var selectedItem by remember { mutableStateOf<ServiceItemDto?>(null) }
    var loading by remember { mutableStateOf(true) }
    var submitting by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var search by remember { mutableStateOf("") }
    var transaction by remember { mutableStateOf<ServiceTransactionDto?>(null) }
    val values = remember { mutableStateMapOf<String, String>() }

    fun loadCatalog() {
        val token = userSession.token
        if (token.isNullOrBlank()) {
            loading = false
            error = "سجل الدخول أولاً لاستخدام خدمات التسديد والشحن."
            return
        }
        scope.launch {
            loading = true
            error = null
            try {
                val response = NetworkClient.getApiService(apiBase).getServiceCatalog("Token $token")
                if (!response.isSuccessful || response.body() == null) {
                    error = "تعذر تحميل الخدمات (HTTP ${response.code()})."
                    return@launch
                }
                catalog = response.body()!!.categories
                selectedMain = catalog.firstOrNull()
                selectedCategory = null
                selectedService = null
                selectedItem = null
                transaction = null
            } catch (e: Exception) {
                error = e.localizedMessage ?: "تعذر الاتصال بخادم الخدمات."
            } finally {
                loading = false
            }
        }
    }

    fun chooseService(service: ServiceDto) {
        selectedService = service
        selectedItem = null
        transaction = null
        error = null
        values.clear()
        service.fields.forEach { field ->
            if (field.key == "mobile" && userSession.phone.isNotBlank()) values[field.key] = userSession.phone
            if (field.type == "select" && field.choices.isNotEmpty()) values[field.key] = field.choices.first()
        }
    }

    fun submitService() {
        val service = selectedService ?: return
        if (submitting) return
        val token = userSession.token ?: return
        val missing = service.fields.firstOrNull { it.required && values[it.key].isNullOrBlank() }
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
            transaction = null
            try {
                val key = UUID.randomUUID().toString()
                val body = ServiceRequestPayload(
                    serviceId = service.id,
                    itemType = selectedItem?.type,
                    itemId = selectedItem?.id,
                    payload = values.mapValues { it.value.ifBlank { null } },
                    idempotencyKey = key
                )
                val response = NetworkClient.getApiService(apiBase).submitServiceRequest("Token $token", key, body)
                if (!response.isSuccessful || response.body() == null) {
                    error = "تعذر تنفيذ العملية (HTTP ${response.code()})."
                    return@launch
                }
                var latest = response.body()!!
                for (attempt in 0 until 20) {
                    transaction = latest
                    if (isTerminal(latest.status) || !latest.result.isNullOrEmpty()) break
                    if (attempt == 19) break
                    delay(900)
                    val next = NetworkClient.getApiService(apiBase).getServiceTransaction("Token $token", latest.id)
                    if (next.isSuccessful && next.body() != null) latest = next.body()!!
                }
                transaction = latest
            } catch (e: Exception) {
                error = e.localizedMessage ?: "حدث خطأ أثناء تنفيذ العملية."
            } finally {
                submitting = false
            }
        }
    }

    LaunchedEffect(userSession.token, djangoBaseUrl) { loadCatalog() }

    val activeMain = selectedMain ?: catalog.firstOrNull()
    val categories = activeMain?.categories.orEmpty()
    val filteredCategories = if (search.isBlank()) categories else categories.filter { c ->
        c.name.contains(search, true) || c.services.any { s -> s.name.contains(search, true) }
    }
    val visibleServices = if (selectedCategory == null) {
        filteredCategories.flatMap { it.services }
    } else {
        flattenServices(listOf(selectedCategory!!))
    }.distinctBy { it.id }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = { Text("التسديدات والخدمات", fontWeight = FontWeight.Bold) },
                navigationIcon = { IconButton(onClick = onBackClick) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "رجوع") } },
                actions = { IconButton(onClick = { loadCatalog() }) { Icon(Icons.Default.Refresh, "تحديث") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding).background(Color(0xFFF6F7FA)),
            contentPadding = PaddingValues(start = 12.dp, end = 12.dp, bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item {
                Card(shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer)) {
                    Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Surface(shape = CircleShape, color = MaterialTheme.colorScheme.primary.copy(alpha = .12f), modifier = Modifier.size(40.dp)) { Box(contentAlignment = Alignment.Center) { Icon(Icons.Default.AccountBalanceWallet, null, tint = MaterialTheme.colorScheme.primary) } }
                        Column(Modifier.weight(1f)) {
                            Text("الخدمات من الخادم", fontWeight = FontWeight.Bold)
                            Text("الفئات والحقول والباقات وأسعار العناصر تُقرأ مباشرة من الكتالوج المركزي.", fontSize = 11.sp)
                        }
                    }
                }
            }
            item {
                OutlinedTextField(search, { search = it }, Modifier.fillMaxWidth(), singleLine = true, leadingIcon = { Icon(Icons.Default.Search, null) }, label = { Text("ابحث عن خدمة أو شركة") }, shape = RoundedCornerShape(12.dp))
            }
            when {
                loading -> item { Column(Modifier.fillMaxWidth().padding(32.dp), horizontalAlignment = Alignment.CenterHorizontally) { CircularProgressIndicator(); Spacer(Modifier.height(8.dp)); Text("جارٍ تحميل الخدمات…") } }
                error != null && catalog.isEmpty() -> item { Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) { Column(Modifier.fillMaxWidth().padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) { Icon(Icons.Default.ErrorOutline, null); Text(error!!, textAlign = TextAlign.Center); TextButton(onClick = { loadCatalog() }) { Text("إعادة المحاولة") } } } }
                else -> {
                    item {
                        Text("الأقسام الرئيسية", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                        Spacer(Modifier.height(6.dp))
                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                            catalog.forEach { main -> FilterChip(selected = selectedMain?.id == main.id, onClick = { selectedMain = main; selectedCategory = null; selectedService = null; selectedItem = null }, label = { Text(main.name) }) }
                        }
                    }
                    item {
                        Text("فئات الخدمات", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                        Spacer(Modifier.height(6.dp))
                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                            filteredCategories.forEach { category -> FilterChip(selected = selectedCategory?.id == category.id, onClick = { selectedCategory = category; selectedService = null; selectedItem = null }, label = { Text(category.name) }) }
                        }
                    }
                    if (visibleServices.isNotEmpty()) {
                        item { Text("الخدمات", fontWeight = FontWeight.Bold, fontSize = 16.sp) }
                        items(visibleServices) { service ->
                            Card(onClick = { chooseService(service) }, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(14.dp), colors = CardDefaults.cardColors(containerColor = if (selectedService?.id == service.id) MaterialTheme.colorScheme.secondaryContainer else Color.White)) {
                                Row(Modifier.fillMaxWidth().padding(13.dp), verticalAlignment = Alignment.CenterVertically) {
                                    Column(Modifier.weight(1f)) { Text(service.name, fontWeight = FontWeight.Bold); Text(if (service.items.isNotEmpty()) "${service.items.size} فئة/باقة" else if (service.serviceKind == "query") "استعلام بدون خصم" else "خدمة حسب المبلغ", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                                    Icon(Icons.Default.ChevronLeft, null)
                                }
                            }
                        }
                    }
                    selectedService?.let { service ->
                        item {
                            Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = Color.White), elevation = CardDefaults.cardElevation(3.dp)) {
                                Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                    Text(service.name, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                                    if (service.items.isNotEmpty()) {
                                        Text("اختر الفئة / الباقة", fontWeight = FontWeight.Bold)
                                        service.items.forEach { item ->
                                            Card(onClick = { selectedItem = item }, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp), colors = CardDefaults.cardColors(containerColor = if (selectedItem?.id == item.id) MaterialTheme.colorScheme.primaryContainer else Color(0xFFF7F8FB))) {
                                                Row(Modifier.fillMaxWidth().padding(11.dp), verticalAlignment = Alignment.CenterVertically) {
                                                    Column(Modifier.weight(1f)) { Text(item.name, fontWeight = FontWeight.Medium); Text(item.metadata["detail"] ?: "${item.currency}", fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                                                    Text(item.price?.let { "${it} ${item.currency}" } ?: "حسب الخدمة", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                                                }
                                            }
                                        }
                                    }
                                    service.fields.forEach { field -> ServiceInput(field, values[field.key].orEmpty()) { values[field.key] = it } }
                                    if (service.serviceKind == "query") Text("هذا استعلام: لا يتم خصم الرصيد.", color = MaterialTheme.colorScheme.primary, fontSize = 11.sp)
                                    Button(onClick = { submitService() }, enabled = !submitting, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp)) { if (submitting) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp) else Text(if (service.serviceKind == "query") "استعلام" else "تنفيذ وخصم الرصيد", fontWeight = FontWeight.Bold) }
                                    error?.let { Text(it, color = MaterialTheme.colorScheme.error, fontSize = 12.sp) }
                                    transaction?.let { tx ->
                                        Card(colors = CardDefaults.cardColors(containerColor = when {
                                            tx.status == "success" -> Color(0xFFE8F5E9)
                                            tx.status in setOf("queued", "processing", "pending_provider", "accepted") -> Color(0xFFFFF8E1)
                                            else -> MaterialTheme.colorScheme.errorContainer
                                        }), shape = RoundedCornerShape(15.dp)) {
                                            Column(Modifier.fillMaxWidth().padding(13.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                                Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                                                    Icon(if (tx.status == "success") Icons.Default.CheckCircle else Icons.Default.Refresh, null, tint = MaterialTheme.colorScheme.primary)
                                                    Spacer(Modifier.width(7.dp))
                                                    Text(if (tx.status == "success") "تمت العملية بنجاح" else "حالة العملية: ${tx.status ?: "غير محددة"}", fontWeight = FontWeight.Bold)
                                                }
                                                tx.result?.forEach { (key, value) -> if (value != null && value.toString().isNotBlank()) Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text(prettyKey(key), fontSize = 12.sp, color = MaterialTheme.colorScheme.onSurfaceVariant); Text(value.toString(), fontSize = 12.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.End) } }
                                                tx.errorMessage?.takeIf { it.isNotBlank() }?.let { Text(it, color = MaterialTheme.colorScheme.error, fontSize = 11.sp) }
                                                Text("رقم العملية: ${tx.id}", fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun ServiceInput(field: ServiceFieldDto, value: String, onValueChange: (String) -> Unit) {
    if (field.type == "select" && field.choices.isNotEmpty()) {
        Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Text(field.label, fontWeight = FontWeight.Medium, fontSize = 12.sp)
            Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) { field.choices.forEach { choice -> FilterChip(selected = value == choice, onClick = { onValueChange(choice) }, label = { Text(choice) }) } }
        }
        return
    }
    val keyboard = when (field.type) { "number", "decimal" -> KeyboardType.Number; "phone" -> KeyboardType.Phone; "email" -> KeyboardType.Email; else -> KeyboardType.Text }
    OutlinedTextField(value, onValueChange, Modifier.fillMaxWidth(), label = { Text(field.label + if (field.required) " *" else "") }, singleLine = true, keyboardOptions = KeyboardOptions(keyboardType = keyboard), shape = RoundedCornerShape(11.dp))
}
