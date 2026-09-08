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
import androidx.compose.foundation.lazy.LazyColumn
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

private val ServicesBackground = Color(0xFFF4F3F8)
private val ServicesCard = Color.White

private fun flattenServices(categories: List<ServiceCategoryDto>): List<ServiceDto> = buildList {
    categories.forEach { category ->
        addAll(category.services)
        addAll(flattenServices(category.children))
    }
}

private fun providerAccent(slug: String, name: String): Color {
    val key = "$slug $name".lowercase()
    return when {
        "yemen-mobile" in key || "يمن موبايل" in key -> Color(0xFFB31946)
        "sabafon" in key || "سبأفون" in key -> Color(0xFF1476B8)
        "you" in key || "يو" in key -> Color(0xFFD08A00)
        "why" in key || "واي" in key -> Color(0xFF5A2A86)
        "4g" in key || "فورجي" in key -> Color(0xFF087C7D)
        "yemen-net" in key || "يمن نت" in key -> Color(0xFF245394)
        "adenet" in key || "عدن نت" in key -> Color(0xFF087F8C)
        else -> Color(0xFF27364A)
    }
}

private fun providerMark(slug: String, name: String): String {
    val key = "$slug $name".lowercase()
    return when {
        "yemen-mobile" in key || "يمن موبايل" in key -> "YM"
        "sabafon" in key || "سبأفون" in key -> "S"
        "you" in key || "يو" in key -> "YOU"
        "why" in key || "واي" in key -> "WHY"
        "4g" in key || "فورجي" in key -> "4G"
        "yemen-net" in key || "يمن نت" in key -> "YN"
        "adenet" in key || "عدن نت" in key -> "AD"
        else -> name.trim().take(2)
    }
}

private fun actionLabel(service: ServiceDto): String = when (service.serviceKind) {
    "query" -> "استعلام"
    "catalog" -> "عرض الباقات"
    else -> when {
        service.name.contains("جملة") -> "جملة"
        service.name.contains("فئة") || service.name.contains("شحن") -> "فئات"
        service.name.contains("باقة") -> "باقات"
        service.name.contains("رصيد") -> "رصيد"
        else -> "تسديد"
    }
}

private fun keyboardFor(field: ServiceFieldDto): KeyboardType = when (field.type) {
    "number", "decimal" -> KeyboardType.Number
    "phone" -> KeyboardType.Phone
    "email" -> KeyboardType.Email
    else -> KeyboardType.Text
}

private fun resultLabel(key: String): String = when (key.lowercase()) {
    "balance" -> "الرصيد"
    "availablecredit" -> "الرصيد المتاح"
    "remainamount", "remaamount" -> "الرصيد المتبقي"
    "mobiletype", "mobiltype" -> "نوع الخط"
    "resultdesc" -> "الرسالة"
    "resultcode" -> "رمز النتيجة"
    "sequenceid" -> "رقم العملية"
    "offername" -> "اسم الباقة"
    "offerid" -> "كود الباقة"
    "offerstartdate" -> "بداية الباقة"
    "offerenddate" -> "نهاية الباقة"
    "reason" -> "السبب"
    else -> key.replace('_', ' ').replaceFirstChar { it.uppercase() }
}

@Composable
private fun ProviderBadge(provider: ServiceCategoryDto, selected: Boolean, onClick: () -> Unit) {
    val accent = providerAccent(provider.slug, provider.name)
    Surface(modifier = Modifier.width(112.dp).clickable(onClick = onClick), shape = RoundedCornerShape(17.dp), color = if (selected) accent else ServicesCard, shadowElevation = if (selected) 4.dp else 1.dp) {
        Column(modifier = Modifier.padding(vertical = 9.dp, horizontal = 8.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Box(modifier = Modifier.size(42.dp).background(if (selected) Color.White.copy(alpha = .18f) else accent.copy(alpha = .11f), CircleShape), contentAlignment = Alignment.Center) {
                Text(providerMark(provider.slug, provider.name), color = if (selected) Color.White else accent, fontSize = 11.sp, fontWeight = FontWeight.ExtraBold)
            }
            Text(provider.name, color = if (selected) Color.White else Color(0xFF26262B), fontSize = 11.sp, fontWeight = FontWeight.Bold, maxLines = 1)
        }
    }
}

@Composable
private fun OperationRow(service: ServiceDto, selected: Boolean, accent: Color, onClick: () -> Unit) {
    Surface(modifier = Modifier.fillMaxWidth().clickable(onClick = onClick), shape = RoundedCornerShape(15.dp), color = if (selected) accent.copy(alpha = .09f) else ServicesCard, border = androidx.compose.foundation.BorderStroke(1.dp, if (selected) accent else Color(0xFFE8E6EC)), shadowElevation = if (selected) 2.dp else 0.dp) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 11.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
            Box(Modifier.size(39.dp).background(accent.copy(alpha = .12f), CircleShape), contentAlignment = Alignment.Center) {
                Icon(if (service.serviceKind == "query") Icons.Default.Search else Icons.Default.AccountBalanceWallet, null, tint = accent, modifier = Modifier.size(19.dp))
            }
            Column(Modifier.weight(1f)) { Text(actionLabel(service), fontWeight = FontWeight.Bold, fontSize = 13.sp); Text(service.name, color = Color(0xFF707078), fontSize = 9.sp, maxLines = 2) }
            Text(if (service.serviceKind == "query") "استعلام" else if (service.serviceKind == "catalog") "عرض" else "مدفوع", color = accent, fontSize = 9.sp, fontWeight = FontWeight.Bold)
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
    val repository = remember { StoreRepository.instance }
    val baseUrl by repository.djangoBaseUrl.collectAsState()
    val session by repository.userSession.collectAsState()
    val scope = rememberCoroutineScope()
    var catalog by remember { mutableStateOf<List<ServiceMainCategoryDto>>(emptyList()) }
    var selectedProvider by remember { mutableStateOf<ServiceCategoryDto?>(null) }
    var selectedBranch by remember { mutableStateOf<ServiceCategoryDto?>(null) }
    var selectedService by remember { mutableStateOf<ServiceDto?>(null) }
    var selectedItem by remember { mutableStateOf<ServiceItemDto?>(null) }
    var selectedPlanTypeId by remember { mutableStateOf<Int?>(null) }
    var phone by remember(session.phone) { mutableStateOf(session.phone) }
    var loading by remember { mutableStateOf(true) }
    var submitting by remember { mutableStateOf(false) }
    var showBalance by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var result by remember { mutableStateOf<ServiceTransactionDto?>(null) }
    val values = remember { mutableStateMapOf<String, String>() }

    fun chooseService(service: ServiceDto) {
        selectedService = service; selectedItem = null; selectedPlanTypeId = null; result = null; values.clear()
        service.fields.forEach { field -> if (field.key == "mobile" && phone.isNotBlank()) values[field.key] = phone; if (field.type == "select" && field.choices.isNotEmpty()) values[field.key] = field.choices.first() }
    }

    fun chooseProvider(provider: ServiceCategoryDto) {
        selectedProvider = provider
        selectedBranch = provider.children.firstOrNull()
        flattenServices(listOf(selectedBranch ?: provider)).distinctBy { it.id }.firstOrNull()?.let(::chooseService)
    }

    fun loadCatalog() {
        val token = session.token
        if (token.isNullOrBlank()) { loading = false; error = "سجل الدخول أولاً لاستخدام خدمات التسديد."; return }
        scope.launch {
            loading = true; error = null
            try {
                val api = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/")
                val response = api.getServiceCatalog("Token $token")
                if (!response.isSuccessful || response.body() == null) { error = "تعذر تحميل الخدمات (HTTP ${response.code()})."; return@launch }
                catalog = response.body()!!.categories
                val root = catalog.firstOrNull { it.slug == "payments" } ?: catalog.firstOrNull { it.name.contains("تسديد") }
                root?.categories?.firstOrNull()?.let(::chooseProvider)
            } catch (e: Exception) { error = e.localizedMessage ?: "تعذر الاتصال بخادم الخدمات." }
            finally { loading = false }
        }
    }

    LaunchedEffect(session.token, baseUrl) { loadCatalog() }

    val root = catalog.firstOrNull { it.slug == "payments" } ?: catalog.firstOrNull { it.name.contains("تسديد") }
    val providers = root?.categories.orEmpty()
    val branches = selectedProvider?.children.orEmpty()
    val services = flattenServices(listOfNotNull(selectedBranch, selectedProvider)).distinctBy { it.id }
    val accent = providerAccent(selectedProvider?.slug.orEmpty(), selectedProvider?.name.orEmpty())
    val selectedType = selectedService?.planTypes?.firstOrNull { it.id == selectedPlanTypeId }
    val visibleItems = selectedService?.items.orEmpty().filter { selectedType == null || it.id in selectedType.planIds }

    fun submit() {
        val service = selectedService ?: return
        val token = session.token ?: return
        if (submitting) return
        val missing = service.fields.firstOrNull { it.required && values[it.key].isNullOrBlank() }
        if (missing != null) { error = "الحقل المطلوب: ${missing.label}"; return }
        if (service.pricingMode == "item" && service.items.isNotEmpty() && selectedItem == null) { error = "اختر الفئة أو الباقة أولاً."; return }
        scope.launch {
            submitting = true; error = null; result = null
            try {
                val key = UUID.randomUUID().toString()
                val payload = ServiceRequestPayload(service.id, selectedItem?.type, selectedItem?.id, values.mapValues { it.value.ifBlank { null } }, key)
                val api = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/")
                val response = api.submitServiceRequest("Token $token", key, payload)
                if (!response.isSuccessful || response.body() == null) {
                    val details = response.errorBody()?.string().orEmpty()
                    error = if (details.isBlank()) "تعذر إرسال العملية (HTTP ${response.code()})." else "رفض الخادم العملية: ${details.take(260)}"
                    return@launch
                }
                var latest = response.body()!!
                for (attempt in 0 until 20) {
                    result = latest
                    val state = latest.status.orEmpty().lowercase()
                    val done = state in setOf("success", "failed", "refunded", "manual_review") || (service.serviceKind == "query" && !latest.result.isNullOrEmpty())
                    if (done || attempt == 19) break
                    delay(900)
                    val next = api.getServiceTransaction("Token $token", latest.id)
                    if (next.isSuccessful && next.body() != null) latest = next.body()!!
                }
                result = latest
                if (latest.status == "success" || latest.status == "refunded") onSyncBalance()
                if (latest.status == "success") onRechargeSubmit(phone, selectedProvider?.name.orEmpty(), selectedBranch?.name.orEmpty(), selectedItem?.name ?: service.name, latest.amount?.toDoubleOrNull() ?: 0.0)
            } catch (e: Exception) { error = e.localizedMessage ?: "حدث خطأ أثناء التنفيذ." }
            finally { submitting = false }
        }
    }

    Scaffold(modifier = modifier.fillMaxSize(), topBar = {
        TopAppBar(title = { Text("خدمات التسديد", fontWeight = FontWeight.Bold, fontSize = 18.sp) }, navigationIcon = { IconButton(onClick = onBackClick) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "رجوع") } }, actions = { IconButton(onClick = { loadCatalog(); onSyncBalance() }) { Icon(Icons.Default.Refresh, "تحديث") } }, colors = TopAppBarDefaults.topAppBarColors(containerColor = ServicesBackground))
    }) { padding ->
        LazyColumn(modifier = Modifier.fillMaxSize().padding(padding).background(ServicesBackground), contentPadding = PaddingValues(horizontal = 12.dp, vertical = 9.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            item {
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Column { Text("التسديد", fontWeight = FontWeight.ExtraBold, fontSize = 23.sp); Text("اختر الشركة ثم نوع العملية", color = Color(0xFF77747D), fontSize = 10.sp) }
                    Surface(modifier = Modifier.clickable { showBalance = !showBalance }, shape = RoundedCornerShape(14.dp), color = ServicesCard, shadowElevation = 1.dp) {
                        Row(Modifier.padding(horizontal = 10.dp, vertical = 8.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) { Icon(if (showBalance) Icons.Default.Visibility else Icons.Default.VisibilityOff, null, tint = accent, modifier = Modifier.size(16.dp)); Text(if (showBalance) "${formatMoney(wallet.balanceYer)} ر.ي" else "••••••", fontSize = 11.sp, fontWeight = FontWeight.Bold) }
                    }
                }
            }
            item {
                Surface(shape = RoundedCornerShape(19.dp), color = ServicesCard, shadowElevation = 1.dp, modifier = Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("الشركات", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFF6B6870))
                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) { providers.forEach { provider -> ProviderBadge(provider, selectedProvider?.id == provider.id) { chooseProvider(provider) } } }
                    }
                }
            }
            if (branches.isNotEmpty()) {
                item { Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) { branches.forEach { branch -> FilterChip(selected = selectedBranch?.id == branch.id, onClick = { selectedBranch = branch; flattenServices(listOf(branch)).distinctBy { it.id }.firstOrNull()?.let(::chooseService) }, label = { Text(branch.name, fontSize = 10.sp) }) } } }
            }
            item {
                Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(19.dp), colors = CardDefaults.cardColors(containerColor = ServicesCard), elevation = CardDefaults.cardElevation(1.dp)) {
                    Column(Modifier.padding(10.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) { Text("نوع الخدمة", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFF6B6870)); services.forEach { service -> OperationRow(service, selectedService?.id == service.id, accent) { chooseService(service) } } }
                }
            }
            if (loading) item { Box(Modifier.fillMaxWidth().padding(35.dp), contentAlignment = Alignment.Center) { CircularProgressIndicator(color = accent) } }
            selectedService?.let { service ->
                item {
                    Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(containerColor = ServicesCard), elevation = CardDefaults.cardElevation(1.dp)) {
                        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text(service.name, fontWeight = FontWeight.ExtraBold, fontSize = 16.sp)
                            if (service.planTypes.isNotEmpty()) {
                                Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                    FilterChip(selected = selectedPlanTypeId == null, onClick = { selectedPlanTypeId = null; selectedItem = null }, label = { Text("كل الأنواع", fontSize = 9.sp) })
                                    service.planTypes.forEach { type -> FilterChip(selected = selectedPlanTypeId == type.id, onClick = { selectedPlanTypeId = type.id; selectedItem = null }, label = { Text(type.name, fontSize = 9.sp) }) }
                                }
                            }
                            if (visibleItems.isNotEmpty()) {
                                Text("الفئات / الباقات", fontSize = 11.sp, fontWeight = FontWeight.Bold, color = Color(0xFF69666E))
                                visibleItems.forEach { item ->
                                    val selected = selectedItem?.id == item.id && selectedItem?.type == item.type
                                    Surface(modifier = Modifier.fillMaxWidth().clickable(enabled = item.availability["available"] != "false") { selectedItem = item }, shape = RoundedCornerShape(13.dp), color = if (selected) accent.copy(alpha = .09f) else Color(0xFFFAF9FB), border = androidx.compose.foundation.BorderStroke(1.dp, if (selected) accent else Color(0xFFE7E4EA))) {
                                        Row(Modifier.padding(horizontal = 10.dp, vertical = 9.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) { Column(Modifier.weight(1f)) { Text(item.name, fontSize = 11.sp, fontWeight = FontWeight.Bold); if (item.availability["available"] == "false") Text(item.availability["reason"] ?: "غير متاح", fontSize = 9.sp, color = Color(0xFFAC3C3C)) }; Text(item.price?.let { "${formatMoney(it.toDoubleOrNull() ?: 0.0)} ${item.currency}" } ?: "—", fontSize = 10.sp, fontWeight = FontWeight.ExtraBold, color = accent) }
                                    }
                                }
                            }
                            service.fields.filter { it.key != "mobile" }.forEach { field ->
                                val value = values[field.key].orEmpty()
                                if (field.type == "select") {
                                    Text(field.label, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                                    Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) { field.choices.forEach { choice -> FilterChip(selected = value == choice, onClick = { values[field.key] = choice }, label = { Text(choice, fontSize = 9.sp) }) } }
                                } else {
                                    OutlinedTextField(value = value, onValueChange = { values[field.key] = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text(field.label + if (field.required) " *" else "", fontSize = 10.sp) }, keyboardOptions = KeyboardOptions(keyboardType = keyboardFor(field)), trailingIcon = if (value.isNotEmpty()) ({ IconButton(onClick = { values.remove(field.key) }) { Icon(Icons.Default.Clear, "مسح") } }) else null, shape = RoundedCornerShape(12.dp))
                                }
                            }
                            if (service.fields.any { it.key == "mobile" }) {
                                OutlinedTextField(value = phone, onValueChange = { phone = it; values["mobile"] = it }, modifier = Modifier.fillMaxWidth(), singleLine = true, label = { Text("رقم الهاتف / المستفيد", fontSize = 10.sp) }, leadingIcon = { Icon(Icons.Default.Call, null, tint = accent) }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone), shape = RoundedCornerShape(12.dp))
                            }
                            Text(when (service.serviceKind) { "query" -> "الاستعلام لا يخصم من محفظتك."; "catalog" -> "عرض معلومات الكتالوج فقط."; else -> "سيتم حجز المبلغ محاسبيًا قبل الإرسال." }, color = Color(0xFF727078), fontSize = 9.sp)
                            Button(onClick = ::submit, enabled = !submitting, modifier = Modifier.fillMaxWidth().height(49.dp), shape = RoundedCornerShape(14.dp), colors = androidx.compose.material3.ButtonDefaults.buttonColors(containerColor = accent)) {
                                if (submitting) { CircularProgressIndicator(color = Color.White, modifier = Modifier.size(19.dp), strokeWidth = 2.dp); Spacer(Modifier.width(7.dp)); Text("جارٍ التنفيذ…", fontWeight = FontWeight.Bold, fontSize = 12.sp) }
                                else { Icon(if (service.serviceKind == "query") Icons.Default.Search else Icons.Default.CheckCircle, null, modifier = Modifier.size(18.dp)); Spacer(Modifier.width(6.dp)); Text(actionLabel(service), fontWeight = FontWeight.Bold, fontSize = 12.sp) }
                            }
                        }
                    }
                }
            }
            error?.let { message ->
                item { Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(15.dp), colors = CardDefaults.cardColors(containerColor = Color(0xFFFFEEEE))) { Column(Modifier.fillMaxWidth().padding(12.dp), horizontalAlignment = Alignment.CenterHorizontally) { Icon(Icons.Default.ErrorOutline, null, tint = Color(0xFFAE3434)); Text(message, textAlign = TextAlign.Center, fontSize = 10.sp); TextButton(onClick = { error = null; loadCatalog() }) { Text("إعادة المحاولة", fontSize = 10.sp) } } } }
            }
            result?.let { tx ->
                item { Card(modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(19.dp), colors = CardDefaults.cardColors(containerColor = ServicesCard), elevation = CardDefaults.cardElevation(2.dp)) { Column(Modifier.padding(13.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) { Text("نتيجة العملية", fontWeight = FontWeight.ExtraBold, fontSize = 15.sp); Text(when (tx.status.orEmpty()) { "success" -> "تمت العملية بنجاح ✅"; "refunded" -> "أعيد المبلغ إلى الرصيد."; "manual_review" -> "العملية تحتاج مراجعة تشغيلية."; "queued", "processing", "pending_provider", "accepted" -> "العملية قيد المعالجة لدى المزود."; else -> tx.errorMessage ?: "تعذر إكمال العملية." }, fontSize = 11.sp, fontWeight = FontWeight.Bold); Text("رقم المرجع: ${tx.id}", fontSize = 9.sp, color = Color(0xFF77747C)); tx.result.orEmpty().entries.sortedBy { it.key }.forEach { (key, value) -> if (value != null) Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) { Text(resultLabel(key), fontSize = 9.sp, color = Color(0xFF727078)); Text(value.toString(), fontSize = 9.sp, fontWeight = FontWeight.Bold, textAlign = TextAlign.End) } } } } }
            }
        }
    }
}
