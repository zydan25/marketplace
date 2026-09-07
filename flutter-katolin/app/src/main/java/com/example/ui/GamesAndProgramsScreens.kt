package com.example.ui

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
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
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import com.example.data.model.UserSession
import com.example.data.remote.NetworkClient
import com.example.data.remote.ServiceCategoryDto
import com.example.data.remote.ServiceDto
import com.example.data.remote.ServiceItemDto
import com.example.data.remote.ServiceRequestPayload
import kotlinx.coroutines.launch
import java.util.UUID

private fun flatten(categories: List<ServiceCategoryDto>): List<ServiceDto> = buildList {
    categories.forEach { category -> addAll(category.services); addAll(flatten(category.children)) }
}

private suspend fun loadCatalog(token: String): List<ServiceDto> {
    val response = NetworkClient.getApiService("https://shopik.alattab.site/api/v2/").getServiceCatalog("Token $token")
    if (!response.isSuccessful || response.body() == null) return emptyList()
    return response.body()!!.categories.flatMap { flatten(it.categories) }
}

@Composable
private fun ProviderCatalogScreen(
    userSession: UserSession,
    title: String,
    allowedCodes: Set<String>,
    targetLabel: String,
    emptyMessage: String,
    onBackClick: () -> Unit,
    modifier: Modifier = Modifier,
) {
    val scope = rememberCoroutineScope()
    var services by remember { mutableStateOf<List<ServiceDto>>(emptyList()) }
    var selectedService by remember { mutableStateOf<ServiceDto?>(null) }
    var selectedItem by remember { mutableStateOf<ServiceItemDto?>(null) }
    var target by remember { mutableStateOf(userSession.phone) }
    var search by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var result by remember { mutableStateOf<String?>(null) }
    var submitting by remember { mutableStateOf(false) }

    fun reload() {
        val token = userSession.token
        if (token.isNullOrBlank()) { loading = false; error = "سجل الدخول أولاً."; return }
        scope.launch {
            loading = true; error = null
            try { services = loadCatalog(token).filter { it.code in allowedCodes } }
            catch (e: Exception) { error = e.localizedMessage ?: "تعذر تحميل الكتالوج." }
            finally { loading = false }
        }
    }
    LaunchedEffect(userSession.token) { reload() }
    val visible = services.filter { it.name.contains(search, true) || it.code.contains(search, true) }

    Scaffold(modifier.fillMaxSize(), topBar = {
        TopAppBar(title = { Text(title, fontWeight = FontWeight.Bold) }, navigationIcon = { IconButton(onClick = onBackClick) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "رجوع") } }, actions = { IconButton(onClick = ::reload) { Icon(Icons.Default.Refresh, "تحديث") } })
    }) { padding ->
        LazyColumn(Modifier.fillMaxSize().padding(padding), contentPadding = PaddingValues(14.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
            item { OutlinedTextField(search, { search = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text("البحث") }, leadingIcon = { Icon(Icons.Default.Search, null) }) }
            when {
                loading -> item { Column(Modifier.fillMaxWidth().padding(30.dp), horizontalAlignment = Alignment.CenterHorizontally) { CircularProgressIndicator(); Spacer(Modifier.height(8.dp)); Text("جارٍ تحميل البيانات…") } }
                error != null -> item { Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.errorContainer)) { Column(Modifier.fillMaxWidth().padding(16.dp), horizontalAlignment = Alignment.CenterHorizontally) { Icon(Icons.Default.ErrorOutline, null); Text(error!!); TextButton(onClick = ::reload) { Text("إعادة المحاولة") } } } }
                visible.isEmpty() -> item { Card { Text(emptyMessage, Modifier.padding(18.dp)) } }
                else -> {
                    item { Text("الخدمات", fontWeight = FontWeight.Bold) }
                    items(visible) { service ->
                        Card(onClick = { selectedService = service; selectedItem = null; result = null }) {
                            Column(Modifier.fillMaxWidth().padding(13.dp)) { Text(service.name, fontWeight = FontWeight.Bold); Text("${service.items.size} عنصر/باقة", style = MaterialTheme.typography.labelSmall) }
                        }
                    }
                    selectedService?.let { service ->
                        item {
                            Card {
                                Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                    Text(service.name, fontWeight = FontWeight.Bold)
                                    if (service.items.isNotEmpty()) {
                                        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                            service.items.forEach { item -> FilterChip(selectedItem?.id == item.id, { selectedItem = item }, label = { Text("${item.name} ${item.price ?: ""}") }) }
                                        }
                                    }
                                    OutlinedTextField(target, { target = it }, Modifier.fillMaxWidth(), singleLine = true, label = { Text(targetLabel) }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Text))
                                    result?.let { Text(it, color = if (it.startsWith("تم")) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.error) }
                                    Button(enabled = selectedItem != null && target.isNotBlank() && !submitting, onClick = {
                                        val item = selectedItem ?: return@Button
                                        scope.launch {
                                            submitting = true; result = null
                                            try {
                                                val token = userSession.token ?: error("سجل الدخول أولاً")
                                                val values = mutableMapOf<String, String?>()
                                                service.fields.forEach { field ->
                                                    when (field.key) { "mobile" -> values[field.key] = userSession.phone.ifBlank { target }; "playerid" -> values[field.key] = target; "email" -> if (target.contains("@")) values[field.key] = target }
                                                }
                                                val key = UUID.randomUUID().toString()
                                                val response = NetworkClient.getApiService("https://shopik.alattab.site/api/v2/").submitServiceRequest("Token $token", key, ServiceRequestPayload(service.id, item.type, item.id, values, key))
                                                result = if (response.isSuccessful) "تم استلام العملية. الحالة: ${response.body()?.status ?: "queued"}" else "تعذر التنفيذ (HTTP ${response.code()})."
                                            } catch (e: Exception) { result = e.localizedMessage ?: "تعذر تنفيذ العملية." }
                                            finally { submitting = false }
                                        }
                                    }, modifier = Modifier.fillMaxWidth()) { if (submitting) CircularProgressIndicator(strokeWidth = 2.dp) else Text("تأكيد وخصم الرصيد") }
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
fun GamesScreen(userSession: UserSession, onBackClick: () -> Unit, formatMoney: (Double) -> String, onRechargeGame: (String, String, Double, String) -> Unit = { _,_,_,_ -> }, modifier: Modifier = Modifier) = ProviderCatalogScreen(userSession, "شحن الألعاب الإلكترونية", setOf("pubg","freefire","legends","loardstelmble","clashroial","genshmbacket","clashofclanz","newstatepobg","praolstars","hidadijwaher","ddihadi","calloffdyoty","pompitch"), "Player ID", "لا توجد بيانات ألعاب مهيأة في الخادم.", onBackClick, modifier)

@Composable
fun ProgramsScreen(userSession: UserSession, onBackClick: () -> Unit, formatMoney: (Double) -> String, onPurchaseProgram: (String, String, Double, String) -> Unit = { _,_,_,_ -> }, modifier: Modifier = Modifier) = ProviderCatalogScreen(userSession, "البطاقات والبرامج الرقمية", setOf("googleplayusa","googleplaykorea","appstore","beinconnect","razergold","crossfire","plastationusa","plastationsar","visacard","mastercard","likee","bigolive"), "البريد أو رقم الهاتف", "الـAPI المرفق لا يعرّف عقود Netflix/Shahid/Canva؛ لا يتم اختلاقها.", onBackClick, modifier)
