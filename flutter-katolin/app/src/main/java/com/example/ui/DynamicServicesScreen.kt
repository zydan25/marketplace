package com.example.ui

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.itemsIndexed
import androidx.compose.foundation.shape.RoundedCornerShape
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
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.foundation.text.KeyboardOptions
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
import kotlinx.coroutines.launch
import java.util.UUID

private fun serviceApiBaseUrl(baseUrl: String): String {
    val normalized = baseUrl.trim().trimEnd('/')
    return when {
        normalized.endsWith("/api/v2") -> "$normalized/"
        normalized.endsWith("/api") -> "$normalized/v2/"
        normalized.isBlank() -> "https://shopik.alattab.site/api/v2/"
        else -> "$normalized/api/v2/"
    }
}

@Composable
fun DynamicServicesScreen(
    userSession: UserSession,
    djangoBaseUrl: String,
    onBackClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    val scope = rememberCoroutineScope()
    var catalog by remember { mutableStateOf<List<ServiceMainCategoryDto>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var selectedMain by remember { mutableStateOf<ServiceMainCategoryDto?>(null) }
    var selectedCategory by remember { mutableStateOf<ServiceCategoryDto?>(null) }
    var selectedService by remember { mutableStateOf<ServiceDto?>(null) }
    val values = remember { mutableStateMapOf<String, String>() }
    var selectedItem by remember { mutableStateOf<ServiceItemDto?>(null) }
    var submitting by remember { mutableStateOf(false) }
    var resultMessage by remember { mutableStateOf<String?>(null) }
    var search by remember { mutableStateOf("") }

    fun loadCatalog() {
        scope.launch {
            loading = true
            error = null
            try {
                val token = userSession.token
                if (token.isNullOrBlank()) {
                    error = "يجب تسجيل الدخول لعرض خدمات الرصيد والباقات."
                    return@launch
                }
                val response = NetworkClient.getApiService(serviceApiBaseUrl(djangoBaseUrl))
                    .getServiceCatalog("Token $token")
                if (!response.isSuccessful || response.body() == null) {
                    error = "تعذر تحميل الخدمات (HTTP ${response.code()})."
                    return@launch
                }
                catalog = response.body()!!.categories
                selectedMain = selectedMain?.let { old -> catalog.firstOrNull { it.id == old.id } }
                    ?: catalog.firstOrNull()
                selectedCategory = null
                selectedService = null
                selectedItem = null
            } catch (e: Exception) {
                error = e.localizedMessage ?: "تعذر الاتصال بخادم الخدمات."
            } finally {
                loading = false
            }
        }
    }

    LaunchedEffect(userSession.token, djangoBaseUrl) {
        if (userSession.isLoggedIn) loadCatalog()
    }

    val activeMain = selectedMain ?: catalog.firstOrNull()
    val rootCategories = activeMain?.categories.orEmpty()
    val filteredCategories = if (search.isBlank()) rootCategories else rootCategories.filter { category ->
        category.name.contains(search, true) ||
            category.services.any { it.name.contains(search, true) }
    }
    val nestedChildren = selectedCategory?.children.orEmpty()
    val visibleServices = if (selectedCategory == null) filteredCategories.flatMap { it.services } else selectedCategory?.services.orEmpty() + nestedChildren.flatMap { it.services }

    fun chooseService(service: ServiceDto) {
        selectedService = service
        selectedItem = null
        values.clear()
        resultMessage = null
        service.fields.forEach { field ->
            if (field.key == "mobile" && userSession.phone.isNotBlank()) values[field.key] = userSession.phone
            if (field.type == "select" && field.choices.isNotEmpty()) values[field.key] = field.choices.first()
        }
    }

    fun submit() {
        val service = selectedService ?: return
        if (submitting) return
        val missing = service.fields.firstOrNull { it.required && values[it.key].isNullOrBlank() }
        if (missing != null) {
            resultMessage = "الحقل المطلوب: ${missing.label}"
            return
        }
        if (service.pricingMode == "item" && service.items.isNotEmpty() && selectedItem == null) {
            resultMessage = "اختر الباقة أو الفئة أولاً."
            return
        }
        scope.launch {
            submitting = true
            resultMessage = null
            try {
                val token = userSession.token ?: return@launch
                val idempotency = UUID.randomUUID().toString()
                val payload = values.mapValues { it.value.ifBlank { null } }
                val body = com.example.data.remote.ServiceRequestPayload(
                    serviceId = service.id,
                    itemType = selectedItem?.type,
                    itemId = selectedItem?.id,
                    payload = payload,
                    idempotencyKey = idempotency
                )
                val response = NetworkClient.getApiService(serviceApiBaseUrl(djangoBaseUrl))
                    .submitServiceRequest("Token $token", idempotency, body)
                resultMessage = if (response.isSuccessful) {
                    "تم استلام طلب ${service.name} بنجاح. حالة العملية تظهر من الخادم."
                } else {
                    "تعذر تنفيذ العملية (HTTP ${response.code()})."
                }
            } catch (e: Exception) {
                resultMessage = e.localizedMessage ?: "حدث خطأ أثناء تنفيذ الطلب."
            } finally {
                submitting = false
            }
        }
    }

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
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(start = 14.dp, end = 14.dp, bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item {
                Surface(shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.primaryContainer) {
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(14.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Icon(Icons.Default.AccountBalanceWallet, null)
                        Column(modifier = Modifier.weight(1f)) {
                            Text("الخدمات مرتبطة مباشرة بكتالوج الخادم", fontWeight = FontWeight.Bold)
                            Text("الباقات والفئات والحقول تُجلب ديناميكيًا ولا توجد بيانات حساسة للمزود داخل التطبيق.", fontSize = 11.sp)
                        }
                    }
                }
            }

            item {
                OutlinedTextField(
                    value = search,
                    onValueChange = { search = it },
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    leadingIcon = { Icon(Icons.Default.Search, null) },
                    label = { Text("ابحث عن خدمة أو شركة") },
                    shape = RoundedCornerShape(12.dp)
                )
            }

            if (loading) {
                item {
                    Column(modifier = Modifier.fillMaxWidth().padding(30.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                        CircularProgressIndicator()
                        Spacer(Modifier.height(10.dp))
                        Text("جارٍ تحميل الخدمات…")
                    }
                }
            } else if (error != null) {
                item {
                    Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) {
                        Column(Modifier.fillMaxWidth().padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(Icons.Default.ErrorOutline, null)
                            Text(error!!, textAlign = TextAlign.Center)
                            TextButton(onClick = { loadCatalog() }) { Text("إعادة المحاولة") }
                        }
                    }
                }
            } else {
                item {
                    LazyColumn(modifier = Modifier.fillMaxWidth(), contentPadding = PaddingValues(vertical = 2.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        item {
                            Text("الأقسام الرئيسية", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                        }
                        items(catalog) { main ->
                            FilterChip(
                                selected = activeMain?.id == main.id,
                                onClick = { selectedMain = main; selectedCategory = null; selectedService = null; selectedItem = null },
                                label = { Text(main.name) }
                            )
                        }
                    }
                }

                item {
                    Text("فئات الخدمات", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    Spacer(Modifier.height(6.dp))
                }

                items(filteredCategories) { category ->
                    Card(
                        onClick = { selectedCategory = category; selectedService = null; selectedItem = null },
                        shape = RoundedCornerShape(12.dp)
                    ) {
                        Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text(category.name, fontWeight = FontWeight.Bold)
                                Text("${category.services.size} خدمة", fontSize = 11.sp, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Icon(Icons.Default.ChevronLeft, null)
                        }
                    }
                }

                if (selectedCategory != null || visibleServices.isNotEmpty()) {
                    item {
                        Spacer(Modifier.height(4.dp))
                        Text("الخدمات المتاحة", fontWeight = FontWeight.Bold, fontSize = 16.sp)
                    }
                    items(visibleServices.distinctBy { it.id }) { service ->
                        Card(
                            onClick = { chooseService(service) },
                            colors = CardDefaults.cardColors(
                                containerColor = if (selectedService?.id == service.id) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surfaceVariant
                            )
                        ) {
                            Row(Modifier.fillMaxWidth().padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
                                Column(Modifier.weight(1f)) {
                                    Text(service.name, fontWeight = FontWeight.Bold)
                                    Text(service.description.ifBlank { service.code }, fontSize = 11.sp, maxLines = 2)
                                    Text(
                                        when (service.pricingMode) {
                                            "amount" -> "المبلغ يحدده العميل"
                                            "item" -> "يختار من الفئات والباقات"
                                            else -> "سعر ثابت"
                                        },
                                        fontSize = 10.sp,
                                        color = MaterialTheme.colorScheme.primary
                                    )
                                }
                                Icon(Icons.Default.ChevronLeft, null)
                            }
                        }
                    }
                }

                selectedService?.let { service ->
                    item {
                        Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface)) {
                            Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                Text(service.name, fontWeight = FontWeight.Bold, fontSize = 18.sp)
                                if (service.items.isNotEmpty()) {
                                    Text("اختر الفئة أو الباقة", fontWeight = FontWeight.Bold)
                                    service.items.forEach { item ->
                                        Card(
                                            onClick = { selectedItem = item },
                                            colors = CardDefaults.cardColors(
                                                containerColor = if (selectedItem?.id == item.id) MaterialTheme.colorScheme.primaryContainer else MaterialTheme.colorScheme.surfaceVariant
                                            )
                                        ) {
                                            Row(Modifier.fillMaxWidth().padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                                                Column(Modifier.weight(1f)) {
                                                    Text(item.name, fontWeight = FontWeight.Medium)
                                                    Text(item.price?.let { "$it ${item.currency}" } ?: "حسب الخدمة", fontSize = 11.sp)
                                                }
                                                if (selectedItem?.id == item.id) Icon(Icons.Default.CheckCircle, null)
                                            }
                                        }
                                    }
                                }
                                service.fields.forEach { field ->
                                    ServiceInputField(field, values[field.key].orEmpty()) { values[field.key] = it }
                                }
                                resultMessage?.let { msg ->
                                    Text(msg, color = if (msg.contains("بنجاح")) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error, textAlign = TextAlign.Right)
                                }
                                Button(onClick = { submit() }, enabled = !submitting, modifier = Modifier.fillMaxWidth()) {
                                    if (submitting) CircularProgressIndicator(modifier = Modifier.width(18.dp).height(18.dp), strokeWidth = 2.dp)
                                    else Text("تنفيذ ${service.name}")
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
private fun ServiceInputField(field: ServiceFieldDto, value: String, onValueChange: (String) -> Unit) {
    if (field.type == "select" && field.choices.isNotEmpty()) {
        Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Text(field.label, fontWeight = FontWeight.Medium, fontSize = 12.sp)
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                field.choices.take(6).forEach { choice ->
                    FilterChip(selected = value == choice, onClick = { onValueChange(choice) }, label = { Text(choice) })
                }
            }
        }
        return
    }
    val keyboard = when (field.type) {
        "number", "decimal" -> KeyboardType.Number
        "phone" -> KeyboardType.Phone
        "email" -> KeyboardType.Email
        else -> KeyboardType.Text
    }
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        modifier = Modifier.fillMaxWidth(),
        label = { Text(field.label + if (field.required) " *" else "") },
        singleLine = true,
        keyboardOptions = KeyboardOptions(keyboardType = keyboard),
        shape = RoundedCornerShape(10.dp)
    )
}
