package com.example.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.remote.NetworkClient
import com.example.data.remote.ServiceTransactionDto
import com.example.data.repository.StoreRepository
import kotlinx.coroutines.launch

private val ReportBg = Color(0xFFF6F4F8)
private val Pending = Color(0xFFC57D00)
private val Success = Color(0xFF218838)
private val Failure = Color(0xFFC43D3D)

private fun stateLabel(s: String?) = when (s.orEmpty()) {
    "success" -> "ناجحة"
    "failed" -> "فاشلة"
    "refunded" -> "مسترجعة"
    "manual_review" -> "مراجعة"
    "pending_provider" -> "معلقة لدى المزود"
    "processing" -> "قيد التنفيذ"
    "queued" -> "في الانتظار"
    "accepted" -> "مقبولة"
    else -> s.orEmpty().ifBlank { "غير معروفة" }
}

private fun stateColor(s: String?) = when (s.orEmpty()) {
    "success" -> Success
    "failed", "refunded" -> Failure
    else -> Pending
}

private fun stateIcon(s: String?) = when (s.orEmpty()) {
    "success" -> Icons.Default.CheckCircle
    "failed", "refunded" -> Icons.Default.ErrorOutline
    else -> Icons.Default.Schedule
}

private fun valueText(v: Any?): String = when (v) {
    null -> "—"
    is Map<*, *> -> v.entries.joinToString("\n") { "${it.key}: ${valueText(it.value)}" }
    is List<*> -> v.joinToString("\n") { valueText(it) }
    else -> v.toString()
}

@Composable
fun ServiceReportsScreen(onBackClick: () -> Unit, modifier: Modifier = Modifier) {
    val repo = remember { StoreRepository.instance }
    val baseUrl by repo.djangoBaseUrl.collectAsState()
    val session by repo.userSession.collectAsState()
    val scope = rememberCoroutineScope()
    var reports by remember { mutableStateOf<List<ServiceTransactionDto>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var checkingId by remember { mutableStateOf<String?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var selected by remember { mutableStateOf<ServiceTransactionDto?>(null) }

    fun load() {
        val token = session.token
        if (token.isNullOrBlank()) { loading = false; error = "سجل الدخول أولًا."; return }
        scope.launch {
            loading = true; error = null
            try {
                val r = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/").getServiceReports("Token $token")
                if (!r.isSuccessful || r.body() == null) error = "تعذر تحميل التقرير (HTTP ${r.code()})."
                else reports = r.body()!!.results
            } catch (e: Exception) { error = e.localizedMessage ?: "تعذر الاتصال بالخادم." }
            finally { loading = false }
        }
    }

    fun checkProvider(tx: ServiceTransactionDto) {
        val token = session.token ?: return
        scope.launch {
            checkingId = tx.id; error = null
            try {
                val r = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/").checkServiceProvider("Token $token", tx.id)
                if (!r.isSuccessful || r.body() == null) error = "تعذر فحص العملية لدى المزود (HTTP ${r.code()})."
                else { val updated = r.body()!!; reports = reports.map { if (it.id == updated.id) updated else it }; selected = updated }
            } catch (e: Exception) { error = e.localizedMessage ?: "تعذر فحص العملية لدى المزود." }
            finally { checkingId = null }
        }
    }

    LaunchedEffect(session.token, baseUrl) { load() }

    Scaffold(modifier.fillMaxSize(), topBar = {
        TopAppBar(title = { Text("تقرير العمليات", fontWeight = FontWeight.Black) }, navigationIcon = { IconButton(onClick = onBackClick) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "رجوع") } }, actions = { IconButton(onClick = ::load) { Icon(Icons.Default.Refresh, "تحديث") } })
    }) { pad ->
        Box(Modifier.fillMaxSize().padding(pad).background(ReportBg)) {
            when {
                loading -> CircularProgressIndicator(Modifier.align(Alignment.Center))
                reports.isEmpty() -> Column(Modifier.align(Alignment.Center).padding(25.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(10.dp)) { Text(error ?: "لا توجد عمليات حتى الآن", textAlign = TextAlign.Center); if (error != null) Button(onClick = ::load) { Text("إعادة المحاولة") } }
                else -> LazyColumn(contentPadding = PaddingValues(12.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    items(reports, key = { it.id }) { tx ->
                        val s = tx.status.orEmpty(); val pending = s in setOf("accepted", "queued", "processing", "pending_provider", "manual_review")
                        Card(Modifier.fillMaxWidth().clickable { selected = tx }, shape = RoundedCornerShape(18.dp), colors = CardDefaults.cardColors(Color.White), elevation = CardDefaults.cardElevation(1.dp)) {
                            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                    Surface(color = stateColor(s).copy(alpha = .12f), shape = RoundedCornerShape(30.dp)) { Row(Modifier.padding(horizontal = 9.dp, vertical = 6.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) { Icon(stateIcon(s), null, tint = stateColor(s), Modifier.size(15.dp)); Text(stateLabel(s), color = stateColor(s), fontSize = 10.sp, fontWeight = FontWeight.Bold) } }
                                    Text(tx.service.orEmpty(), fontWeight = FontWeight.Black, fontSize = 13.sp)
                                }
                                Text("${tx.amount.orEmpty()} ${tx.currency.orEmpty()}", fontWeight = FontWeight.Black, fontSize = 19.sp)
                                Text(tx.createdAt.orEmpty(), color = Color.Gray, fontSize = 9.sp)
                                if (pending) OutlinedButton(onClick = { checkProvider(tx) }, enabled = checkingId == null, Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp)) { if (checkingId == tx.id) CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp) else Icon(Icons.Default.Refresh, null, Modifier.size(16.dp)); Spacer(Modifier.width(6.dp)); Text(if (checkingId == tx.id) "جارٍ الفحص لدى المزود…" else "فحص لدى المزود") }
                            }
                        }
                    }
                }
            }
        }
    }

    selected?.let { tx ->
        AlertDialog(onDismissRequest = { selected = null }, title = { Text("تفاصيل العملية", fontWeight = FontWeight.Black) }, text = {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                item { Text("الخدمة: ${tx.service.orEmpty()}") }
                item { Text("الحالة: ${stateLabel(tx.status)}", fontWeight = FontWeight.Bold) }
                item { Text("المبلغ: ${tx.amount.orEmpty()} ${tx.currency.orEmpty()}") }
                item { Text("المرجع: ${tx.id}", color = Color.Gray, fontSize = 10.sp) }
                tx.providerTransid?.let { item { Text("رقم المزود: $it", color = Color.Gray, fontSize = 10.sp) } }
                tx.errorMessage?.takeIf { it.isNotBlank() }?.let { item { Text("الرسالة: $it", color = Failure, fontSize = 11.sp) } }
                tx.result.orEmpty().entries.sortedBy { it.key }.forEach { (k, v) -> if (v != null) item { Column { Text(k, color = Color.Gray, fontSize = 9.sp); Text(valueText(v), fontWeight = FontWeight.Bold, fontSize = 11.sp) } } }
            }
        }, confirmButton = { TextButton(onClick = { selected = null }) { Text("إغلاق") } })
    }
}