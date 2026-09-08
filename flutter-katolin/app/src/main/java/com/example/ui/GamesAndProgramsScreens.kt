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
import androidx.compose.material.icons.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Extension
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
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

private fun flattenCatalog(categories: List<com.example.data.remote.ServiceCategoryDto>): List<ServiceDto> = buildList {
    categories.forEach { category -> addAll(category.services); addAll(flattenCatalog(category.children)) }
}

private fun serviceIcon(code: String, games: Boolean) = if (games) Icons.Default.SportsEsports else Icons.Default.Extension

private fun hideServerGeneratedField(key: String): Boolean = key in setOf("external_code", "num", "packageid", "uniqcode")

@Composable
private fun ServerProductsScreen(
    userSession: UserSession,
    title: String,
    rootSlug: String,
    emptyMessage: String,
    onBackClick: () -> Unit,
    formatMoney: (Double) -> String,
    games: Boolean,
    modifier: Modifier = Modifier
) {
    val repository = remember { StoreRepository.instance }
    val baseUrl by repository.djangoBaseUrl.collectAsState()
    val apiBase = baseUrl.trimEnd('/') + "/v2/"
    val scope = rememberCoroutineScope()
    var catalog by remember { mutableStateOf<List<ServiceMainCategoryDto>>(emptyList()) }
    var services by remember { mutableStateOf<List<ServiceDto>>(emptyList()) }
    var selectedService by remember { mutableStateOf<ServiceDto?>(null) }
    var selectedItem by remember { mutableStateOf<ServiceItemDto?>(null) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var search by remember { mutableStateOf("") }
    var transaction by remember { mutableStateOf<ServiceTransactionDto?>(null) }
    var submitting by remember { mutableStateOf(false) }
    val values = remember { mutableStateMapOf<String, String>() }

    fun reload() {
        val token = userSession.token
        if (token.isNullOrBlank()) { loading = false; error = "سجل الدخول أولاً."; return }
        scope.launch {
            loading = true; error = null
            try {
                val response = NetworkClient.getApiService(apiBase).getServiceCatalog("Token $token")
                if (!response.isSuccessful || response.body() == null) { error = "تعذر تحميل الكتالوج (HTTP ${response.code()})."; return@launch }
                catalog = response.body()!!.categories
                val root = catalog.firstOrNull { it.slug == rootSlug } ?: catalog.firstOrNull { it.name.contains(if (games) "ألعاب" else "بطاقات") }
                services = root?.categories?.flatMap { flattenCatalog(listOf(it)) }?.distinctBy { it.id }.orEmpty()
                selectedService = services.firstOrNull()
                selectedItem = null
            } catch (e: Exception) { error = e.localizedMessage ?: "تعذر الاتصال بالخادم." }
            finally { loading = false }
        }
    }

    fun selectService(service: ServiceDto) {
        selectedService = service; selectedItem = null; transaction = null; values.clear()
        service.fields.forEach { field -> if (field.key == "mobile") values[field.key] = userSession.phone }
    }

    fun submit() {
        val service = selectedService ?: return
        val token = userSession.token ?: return
        if (service.pricingMode == "item" && service.items.isNotEmpty() && selectedItem == null) { error = "اختر الفئة أو المنتج أولاً."; return }
        val missing = service.fields.firstOrNull { it.required && !hideServerGeneratedField(it.key) && values[it.key].isNullOrBlank() }
        if (missing != null) { error = "الحقل المطلوب: ${missing.label}"; return }
        scope.launch {
            submitting = true; error = null; transaction = null
            try {
                val key = UUID.randomUUID().toString()
                val body = ServiceRequestPayload(service.id, selectedItem?.type, selectedItem?.id, values.mapValues { it.value.ifBlank { null } }, key)
                val response = NetworkClient.getApiService(apiBase).submitServiceRequest("Token $token", key, body)
                if (!response.isSuccessful || response.body() == null) { error = "تعذر تنفيذ العملية (HTTP ${response.code()})."; return@launch }
                var latest = response.body()!!
                for (attempt in 0 until 20) {
                    transaction = latest
                    val status = latest.status.orEmpty().lowercase()
                    if (status in setOf("success", "failed", "refunded") || !latest.result.isNullOrEmpty()) break
                    if (attempt == 19) break
                    delay(900)
                    val next = NetworkClient.getApiService(apiBase).getServiceTransaction("Token $token", latest.id)
                    if (next.isSuccessful && next.body() != null) latest = next.body()!!
                }
                transaction = latest
                repository.syncWalletFromServer()
            } catch (e: Exception) { error = e.localizedMessage ?: "تعذر تنفيذ العملية." }
            finally { submitting = false }
        }
    }

    LaunchedEffect(userSession.token, baseUrl) { reload() }
    val visible = services.filter { it.name.contains(search, true) || it.code.contains(search, true) }
    val accent = if (games) Color(0xFF1565C0) else Color(0xFF6A1B9A)

    Scaffold(modifier = modifier.fillMaxSize(), topBar = {
        TopAppBar(title = { Text(title, fontWeight = FontWeight.Bold) }, navigationIcon = { IconButton(onClick = onBackClick) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "رجوع") } }, actions = { IconButton(onClick = { reload() }) { Icon(Icons.Default.Refresh, "تحديث") } }, colors = TopAppBarDefaults.topAppBarColors(containerColor = accent, titleContentColor = Color.White, navigationIconContentColor = Color.White, actionIconContentColor = Color.White))
    }) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding).background(Color(0xFFF6F7FA)), contentPadding = PaddingValues(bottom = 28.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            item {
                Column(Modifier.fillMaxWidth().background(accent).padding(14.dp)) {
                    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                        Surface(shape = CircleShape, color = Color.White.copy(alpha = .16f), modifier = Modifier.size(42.dp)) { Box(contentAlignment = Alignment.Center) { Icon(serviceIcon("", games), null, tint = Color.White) } }
                        Spacer(Modifier.width(10.dp))
                        Column(Modifier.weight(1f)) { Text(title, color = Color.White, fontWeight = FontWeight.Bold); Text("الفئات والأسعار تُقرأ مباشرة من خادم الخدمات", color = Color.White.copy(alpha = .85f), fontSize = 11.sp) }
                    }
                }
            }
            item { OutlinedTextField(search, { search = it }, Modifier.fillMaxWidth().padding(horizontal = 14.dp), singleLine = true, leadingIcon = { Icon(Icons.Default.Search, null) }, label = { Text("البحث عن لعبة أو بطاقة") }, shape = RoundedCornerShape(12.dp)) }
            when {
                loading -> item { Column(Modifier.fillMaxWidth().padding(30.dp), horizontalAlignment = Alignment.CenterHorizontally) { CircularProgressIndicator(color = accent); Spacer(Modifier.height(8.dp)); Text("جارٍ جلب البيانات من الخادم…") } }
                error != null -> item { Card(Modifier.fillMaxWidth().padding(horizontal = 14.dp), colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) { Column(Modifier.padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) { Icon(Icons.Default.ErrorOutline, null); Text(error!!, textAlign = TextAlign.Center); TextButton(onClick = { error = null; reload() }) { Text("إعادة المحاولة") } } } }
                visible.isEmpty() -> item { Card(Modifier.fillMaxWidth().padding(horizontal = 14.dp)) { Text(emptyMessage, Modifier.padding(18.dp)) } }
                else -> {
                    items(visible) { service ->
                        Card(onClick = { selectService(service) }, modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp), shape = RoundedCornerShape(14.dp), colors = CardDefaults.cardColors(containerColor = if (selectedService?.id == service.id) accent.copy(alpha = .10f) else Color.White)) {
                            Row(Modifier.fillMaxWidth().padding(13.dp), verticalAlignment = Alignment.CenterVertically) {
                                Surface(shape = CircleShape, color = accent.copy(alpha = .10f), modifier = Modifier.size(42.dp)) { Box(contentAlignment = Alignment.Center) { Icon(serviceIcon(service.code, games), null, tint = accent, modifier = Modifier.size(21.dp)) } }
                                Spacer(Modifier.width(10.dp))
                                Column(Modifier.weight(1f)) { Text(service.name, fontWeight = FontWeight.Bold); Text("${service.items.size} فئة/منتج", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                            }
                        }
                    }
                    selectedService?.let { service ->
                        item {
                            Card(modifier = Modifier.fillMaxWidth().padding(horizontal = 14.dp), shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(containerColor = Color.White), elevation = CardDefaults.cardElevation(3.dp)) {
                                Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                                    Text(service.name, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                                    if (service.items.isNotEmpty()) {
                                        Text("اختر الفئة / القيمة", fontWeight = FontWeight.Bold)
                                        service.items.forEach { item ->
                                            Card(onClick = { selectedItem = item }, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp), colors = CardDefaults.cardColors(containerColor = if (selectedItem?.id == item.id) accent.copy(alpha = .13f) else Color(0xFFF7F8FB))) {
                                                Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                                                    Column(Modifier.weight(1f)) { Text(item.name, fontWeight = FontWeight.Medium); Text(item.metadata["detail"] ?: "${item.currency}", fontSize = 10.sp, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                                                    Text(item.price?.let { formatMoney(it.toDoubleOrNull() ?: 0.0) + " " + item.currency } ?: "—", color = accent, fontWeight = FontWeight.Bold)
                                                }
                                            }
                                        }
                                    }
                                    service.fields.filterNot { hideServerGeneratedField(it.key) }.forEach { field -> CatalogInput(field, values[field.key].orEmpty()) { values[field.key] = it } }
                                    Button(onClick = { submit() }, enabled = !submitting, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp)) { if (submitting) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp) else Text("شراء وخصم الرصيد", fontWeight = FontWeight.Bold) }
                                    transaction?.let { tx ->
                                        Card(colors = CardDefaults.cardColors(containerColor = if (tx.status == "success") Color(0xFFE8F5E9) else Color(0xFFFFF8E1)), shape = RoundedCornerShape(13.dp)) { Column(Modifier.fillMaxWidth().padding(13.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) { Row(verticalAlignment = Alignment.CenterVertically) { Icon(if (tx.status == "success") Icons.Default.CheckCircle else Icons.Default.Refresh, null, tint = accent); Spacer(Modifier.width(6.dp)); Text(if (tx.status == "success") "تم التنفيذ بنجاح" else "حالة العملية: ${tx.status ?: "قيد المعالجة"}", fontWeight = FontWeight.Bold) } ; tx.result?.forEach { (k,v) -> if (v != null) Text("$k: $v", fontSize = 12.sp) }; tx.errorMessage?.takeIf { it.isNotBlank() }?.let { Text(it, color = MaterialTheme.colorScheme.error) } } }
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
private fun CatalogInput(field: ServiceFieldDto, value: String, onValueChange: (String) -> Unit) {
    val keyboard = when (field.type) { "number", "decimal" -> KeyboardType.Number; "phone" -> KeyboardType.Phone; "email" -> KeyboardType.Email; else -> KeyboardType.Text }
    OutlinedTextField(value = value, onValueChange = onValueChange, modifier = Modifier.fillMaxWidth(), label = { Text(field.label + if (field.required) " *" else "") }, singleLine = true, keyboardOptions = KeyboardOptions(keyboardType = keyboard), shape = RoundedCornerShape(11.dp))
}

@Composable
fun GamesScreen(userSession: UserSession, onBackClick: () -> Unit, formatMoney: (Double) -> String, onRechargeGame: (String, String, Double, String) -> Unit = { _, _, _, _ -> }, modifier: Modifier = Modifier) = ServerProductsScreen(userSession, "شحن الألعاب الإلكترونية", "games", "لا توجد ألعاب أو منتجات مهيأة في الخادم.", onBackClick, formatMoney, true, modifier)

@Composable
fun ProgramsScreen(userSession: UserSession, onBackClick: () -> Unit, formatMoney: (Double) -> String, onPurchaseProgram: (String, String, Double, String) -> Unit = { _, _, _, _ -> }, modifier: Modifier = Modifier) = ServerProductsScreen(userSession, "البطاقات والبرامج الرقمية", "software", "لا توجد بطاقات رقمية مهيأة في الخادم.", onBackClick, formatMoney, false, modifier)