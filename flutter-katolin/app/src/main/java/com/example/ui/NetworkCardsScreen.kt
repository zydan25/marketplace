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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.CreditCard
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
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
import androidx.compose.foundation.text.KeyboardOptions
import com.example.data.model.PurchasedWifiCard
import com.example.data.model.UserSession
import com.example.data.model.WifiCardDenomination
import com.example.data.model.WifiNetwork
import kotlinx.coroutines.launch

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun NetworkCardsScreen(
    userSession: UserSession,
    wifiNetworks: List<WifiNetwork>,
    purchasedWifiCards: List<PurchasedWifiCard>,
    onBackClick: () -> Unit,
    formatMoney: (Double) -> String,
    onPurchaseWifiCard: suspend (WifiNetwork, WifiCardDenomination, String) -> PurchasedWifiCard?,
    modifier: Modifier = Modifier
) {
    val scope = rememberCoroutineScope()
    var selectedNetwork by remember { mutableStateOf<WifiNetwork?>(null) }
    var selectedDenomination by remember { mutableStateOf<WifiCardDenomination?>(null) }
    var phone by remember(userSession.phone) { mutableStateOf(userSession.phone) }
    var purchasing by remember { mutableStateOf(false) }
    var purchased by remember { mutableStateOf<PurchasedWifiCard?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var showCards by remember { mutableStateOf(false) }

    Scaffold(
        modifier = modifier.fillMaxSize(),
        topBar = {
            TopAppBar(
                title = { Text("كروت شبكات الوايفاي", fontWeight = FontWeight.Bold) },
                navigationIcon = { IconButton(onClick = onBackClick) { Icon(Icons.AutoMirrored.Filled.ArrowBack, "رجوع") } },
                actions = { IconButton(onClick = { showCards = !showCards }) { Icon(Icons.Default.CreditCard, "كروتي") } }
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item {
                Card(colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.primaryContainer), shape = RoundedCornerShape(16.dp)) {
                    Row(Modifier.fillMaxWidth().padding(16.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Icon(Icons.Default.Wifi, null)
                        Column(Modifier.weight(1f)) {
                            Text("شبكات متاحة للبيع", fontWeight = FontWeight.Bold)
                            Text("الكروت رقمية وتُسلّم بعد نجاح الخصم المحاسبي فقط.", style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            }
            if (showCards) {
                item { Text("كروتي المشتراة", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium) }
                if (purchasedWifiCards.isEmpty()) item { Text("لا توجد كروت مشتراة حتى الآن.") }
                items(purchasedWifiCards) { card ->
                    Card(shape = RoundedCornerShape(12.dp)) {
                        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                            Text(card.networkName, fontWeight = FontWeight.Bold)
                            Text(card.denominationTitle)
                            Text("الكرت: ${card.serialNumber}")
                            Text("PIN: ${card.pinCode}", fontWeight = FontWeight.Bold)
                            Text(card.purchaseDate, style = MaterialTheme.typography.bodySmall)
                        }
                    }
                }
            } else if (wifiNetworks.isEmpty()) {
                item {
                    Column(Modifier.fillMaxWidth().padding(40.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                        CircularProgressIndicator()
                        Spacer(Modifier.height(8.dp))
                        Text("جارٍ تحميل شبكات الوايفاي…")
                    }
                }
            } else {
                item { Text("اختر شبكة", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium) }
                items(wifiNetworks) { network ->
                    Card(onClick = { selectedNetwork = network; selectedDenomination = null; error = null }, shape = RoundedCornerShape(14.dp)) {
                        Column(Modifier.fillMaxWidth().padding(14.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                            Text(network.name, fontWeight = FontWeight.Bold)
                            Text(network.location, style = MaterialTheme.typography.bodySmall)
                            Text("المالك: ${network.ownerName}  ${network.ownerPhone}", style = MaterialTheme.typography.bodySmall)
                            Text("${network.denominations.size} فئات متاحة", color = MaterialTheme.colorScheme.primary)
                        }
                    }
                }
            }
        }
    }

    selectedNetwork?.let { network ->
        AlertDialog(
            onDismissRequest = { if (!purchasing) selectedNetwork = null },
            title = { Text(network.name, fontWeight = FontWeight.Bold) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    Text(network.location, style = MaterialTheme.typography.bodySmall)
                    if (selectedDenomination == null) {
                        Text("اختر الفئة", fontWeight = FontWeight.Bold)
                        network.denominations.forEach { denom ->
                            Button(onClick = { selectedDenomination = denom }, modifier = Modifier.fillMaxWidth()) {
                                Text("${denom.title} — ${formatMoney(denom.priceYer)} ر.ي")
                            }
                        }
                    } else {
                        Text("الفئة: ${selectedDenomination!!.title}", fontWeight = FontWeight.Bold)
                        OutlinedTextField(value = phone, onValueChange = { phone = it }, label = { Text("رقم الهاتف") }, singleLine = true, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone), modifier = Modifier.fillMaxWidth())
                        Text("السعر: ${formatMoney(selectedDenomination!!.priceYer)} ر.ي")
                        error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
                    }
                }
            },
            confirmButton = {
                if (selectedDenomination != null) {
                    Button(enabled = !purchasing && phone.isNotBlank(), onClick = {
                        val denom = selectedDenomination!!
                        purchasing = true
                        error = null
                        scope.launch {
                            try {
                                val card = onPurchaseWifiCard(network, denom, phone)
                                if (card == null) error = "تعذر تنفيذ الشراء؛ لم يتم خصم الرصيد."
                                else { purchased = card; selectedNetwork = null; selectedDenomination = null }
                            } finally { purchasing = false }
                        }
                    }) { if (purchasing) CircularProgressIndicator(strokeWidth = 2.dp, modifier = Modifier.padding(2.dp)) else Text("شراء وخصم الرصيد") }
                }
            },
            dismissButton = { if (!purchasing) IconButton(onClick = { selectedDenomination = null; selectedNetwork = null }) { Icon(Icons.Default.Refresh, "إلغاء") } }
        )
    }

    purchased?.let { card ->
        AlertDialog(
            onDismissRequest = { purchased = null },
            title = { Text("تم شراء الكرت", fontWeight = FontWeight.Bold) },
            text = { Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Text("الشبكة: ${card.networkName}")
                Text("الفئة: ${card.denominationTitle}")
                Text("الرقم: ${card.serialNumber}")
                Text("PIN: ${card.pinCode}", fontWeight = FontWeight.Bold)
            } },
            confirmButton = { Button(onClick = { purchased = null }) { Text("تم") } }
        )
    }
}
