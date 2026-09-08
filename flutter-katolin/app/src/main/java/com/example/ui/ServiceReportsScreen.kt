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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ErrorOutline
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.remote.NetworkClient
import com.example.data.remote.ServiceTransactionDto
import com.example.data.repository.StoreRepository
import kotlinx.coroutines.launch

private val Bg = Color(0xFFF3F2F6)
private val Pending = Color(0xFFC68400)
private val Success = Color(0xFF218838)
private val Failed = Color(0xFFC43D3D)

private fun stateLabel(status: String?): String = when (status.orEmpty()) {
    "success" -> "ناجحة"
    "failed" -> "فاشلة"
    "refunded" -> "مسترجعة"
    "manual_review" -> "مراجعة"
    "pending_provider" -> "معلقة لدى المزود"
    "processing" -> "قيد التنفيذ"
    "queued" -> "في الانتظار"
    "accepted" -> "مقبولة"
    else -> status.orEmpty().ifBlank { "غير معروفة" }
}

private fun stateColor(status: String?): Color = when (status.orEmpty()) {
    "success" -> Success
    "failed", "refunded" -> Failed
    else -> Pending
}

private fun isPending(status: String?): Boolean = status.orEmpty() in setOf("accepted", "queued", "processing", "pending_provider", "manual_review")

private fun valueText(value: Any?): String = when (value) {
    null -> "—"
    is Map<*, *> -> value.entries.joinToString("\n") { "${it.key}: ${valueText(it.value)}" }
    is List<*> -> value.joinToString("\n") { valueText(it) }
    else -> value.toString()
}

@Composable
fun ServiceReportsScreen(onBackClick: () -> Unit, modifier: Modifier = Modifier) {
    val repo = remember { StoreRepository.instance }
    val baseUrl by repo.djangoBaseUrl.collectAsState()
    val session by repo.userSession.collectAsState()
    val scope = rememberCoroutineScope()
    var reports by remember { mutableStateOf<List<ServiceTransactionDto>>(emptyList()) }
    var loading by remember { mutableStateOf(false) }
    var checkingId by remember { mutableStateOf<String?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var selected by remember { mutableStateOf<ServiceTransactionDto?>(null) }

    fun load() {
        val token = session.token ?: run { error = "سجل الدخول أولًا."; return }
        scope.launch {
            loading = true; error = null
            try {
                val response = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/").getServiceReports("Token $token")
                if (!response.isSuccessful || response.body() == null) error = "تعذر تحميل التقرير (HTTP ${response.code()})." else reports = response.body()!!.results
            } catch (e: Exception) { error = e.localizedMessage ?: "تعذر الاتصال بالخادم." }
            finally { loading = false }
        }
    }

    fun checkProvider(tx: ServiceTransactionDto) {
        val token = session.token ?: return
        scope.launch {
            checkingId = tx.id; error = null
            try {
                val response = NetworkClient.getApiService(baseUrl.trimEnd('/') + "/").checkServiceProvider("Token $token", tx.id)
                if (!response.isSuccessful || response.body() == null) error = "تعذر فحص العملية لدى المزود (HTTP ${response.code()})." else { val updated = response.body()!!; reports = reports.map { if (it.id == updated.id) updated else it }; selected = updated }
            } catch (e: Exception) { error = e.localizedMessage ?: "تعذر فحص العملية." }
            finally { checkingId = null }
        }
    }

    LaunchedEffect(baseUrl, session.token) { load() }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = { Text("تقرير العمليات", fontWeight = FontWeight.Black) },
                navigationIcon = { IconButton(onClick = onBackClick) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "رجوع") } },
                actions = { IconButton(onClick = ::load) { Icon(Icons.Default.Refresh, "تحديث") } },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = Bg)
            )
        }
    ) { padding ->
        Box(Modifier.fillMaxSize().padding(padding).background(Bg)) {
            when {
                loading -> CircularProgressIndicator(Modifier.align(Alignment.Center))
                reports.isEmpty() -> Column(Modifier.align(Alignment.Center).padding(24.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(10.dp)) { Text(error ?: "لا توجد عمليات حتى الآن", textAlign = TextAlign.Center); if (error != null) Button(onClick = ::load) { Text("إعادة المحاولة") } }
                else -> LazyColumn(contentPadding = PaddingValues(12.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    items(reports, key = { it.id }) { tx ->
                        val status = tx.status.orEmpty(); val c = stateColor(status)
                        Card(Modifier.fillMaxWidth().clickable { selected = tx }, shape = RoundedCornerShape(20.dp), colors = CardDefaults.cardColors(containerColor = Color.White), elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)) {
                            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                    Surface(color = c.copy(alpha = .10f), shape = RoundedCornerShape(24.dp)) {
                                        Row(Modifier.padding(horizontal = 9.dp, vertical = 6.dp), verticalAlignment = Alignment.CenterVertically) {
                                            val icon = when (status) { "success" -> Icons.Default.CheckCircle; "failed", "refunded" -> Icons.Default.ErrorOutline; else -> Icons.Default.Schedule }
                                            Icon(icon, null, tint = c, modifier = Modifier.size(15.dp)); Spacer(Modifier.width(5.dp)); Text(stateLabel(status), color = c, fontSize = 10.sp, fontWeight = FontWeight.Bold)
                                        }
                                    }
                                    Text(tx.service.orEmpty(), fontWeight = FontWeight.Black, fontSize = 13.sp, textAlign = TextAlign.End)
                                }
                                Text("${tx.amount.orEmpty()} ${tx.currency.orEmpty()}", fontWeight = FontWeight.Black, fontSize = 19.sp)
                                Text(tx.createdAt.orEmpty(), color = Color.Gray, fontSize = 9.sp)
                                if (isPending(status)) {
                                    Button(onClick = { checkProvider(tx) }, enabled = checkingId == null, modifier = Modifier.fillMaxWidth(), shape = RoundedCornerShape(12.dp)) {
                                        if (checkingId == tx.id) CircularProgressIndicator(Modifier.size(16.dp), strokeWidth = 2.dp) else Icon(Icons.Default.Refresh, null, Modifier.size(16.dp))
                                        Spacer(Modifier.width(6.dp)); Text(if (checkingId == tx.id) "جارٍ الفحص لدى المزود…" else "فحص لدى المزود", fontWeight = FontWeight.Bold)
                                    }
                                }
                                Text("اضغط لعرض تفاصيل العملية", color = Color.Gray, fontSize = 9.sp, modifier = Modifier.fillMaxWidth(), textAlign = TextAlign.End)
                            }
                        }
                    }
                }
            }
        }
    }

    selected?.let { tx ->
        AlertDialog(
            onDismissRequest = { selected = null },
            title = { Text("تفاصيل العملية", fontWeight = FontWeight.Black) },
            text = {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    item { Text("الخدمة: ${tx.service.orEmpty()}") }
                    item { Text("الحالة: ${stateLabel(tx.status)}", fontWeight = FontWeight.Bold) }
                    item { Text("المبلغ: ${tx.amount.orEmpty()} ${tx.currency.orEmpty()}") }
                    item { Text("المرجع: ${tx.id}", color = Color.Gray, fontSize = 10.sp) }
                    tx.providerTransid?.let { item { Text("رقم المزود: $it", color = Color.Gray, fontSize = 10.sp) } }
                    tx.providerTransactionId?.takeIf { it.isNotBlank() }?.let { item { Text("معرف المزود: $it", color = Color.Gray, fontSize = 10.sp) } }
                    tx.errorMessage?.takeIf { it.isNotBlank() }?.let { item { Text("الرسالة: $it", color = Failed, fontSize = 11.sp) } }
                    tx.result.orEmpty().entries.sortedBy { it.key }.forEach { (key, value) ->
                        if (value != null) item { Column { Text(key, color = Color.Gray, fontSize = 9.sp); Text(valueText(value), fontWeight = FontWeight.Bold, fontSize = 11.sp) } }
                    }
                }
            },
            confirmButton = { TextButton(onClick = { selected = null }) { Text("إغلاق") } }
        )
    }
}
