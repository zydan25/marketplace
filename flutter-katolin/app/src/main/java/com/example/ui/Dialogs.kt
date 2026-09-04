package com.example.ui

import android.net.Uri
import android.provider.ContactsContract
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Contacts
import androidx.compose.material.icons.filled.Dns
import androidx.compose.material.icons.filled.DoneAll
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Notifications
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Phone
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.platform.LocalContext
import com.example.data.model.TransferCheckResult
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.clip
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.AppNotification
import kotlinx.coroutines.launch
import com.example.data.model.OrderChatMessage
import com.example.data.model.Store

/**
 * حوار تسجيل الدخول برقم الهاتف وكلمة السر (مطلوب بالاسم من المستخدم)
 */
@Composable
fun LoginWithPhoneDialog(
    onDismiss: () -> Unit,
    onLogin: suspend (phone: String, pass: String) -> Pair<Boolean, String?>
) {
    var phone by remember { mutableStateOf("770123456") }
    var password by remember { mutableStateOf("123456") }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var isLoading by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    AlertDialog(
        onDismissRequest = { if (!isLoading) onDismiss() },
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Phone,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary
                )
                Text(
                    text = "تسجيل الدخول",
                    fontWeight = FontWeight.Bold
                )
            }
        },
        text = {
            Column(
                modifier = Modifier.fillMaxWidth(),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(
                    text = "سجل دخولك برقم الهاتف وكلمة السر للربط مع السيرفر والوصول للمحفظة والطلبات",
                    style = MaterialTheme.typography.bodySmall.copy(
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                )

                OutlinedTextField(
                    value = phone,
                    onValueChange = {
                        phone = it
                        errorMessage = null
                    },
                    label = { Text("رقم الهاتف أو اسم المستخدم") },
                    placeholder = { Text("مثال: 770123456") },
                    leadingIcon = {
                        Icon(imageVector = Icons.Default.Phone, contentDescription = null)
                    },
                    singleLine = true,
                    enabled = !isLoading,
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = password,
                    onValueChange = {
                        password = it
                        errorMessage = null
                    },
                    label = { Text("كلمة السر") },
                    visualTransformation = PasswordVisualTransformation(),
                    leadingIcon = {
                        Icon(imageVector = Icons.Default.Lock, contentDescription = null)
                    },
                    singleLine = true,
                    enabled = !isLoading,
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.fillMaxWidth()
                )

                if (errorMessage != null) {
                    Text(
                        text = errorMessage ?: "",
                        style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.error)
                    )
                }
            }
        },
        confirmButton = {
            Button(
                enabled = !isLoading,
                onClick = {
                    if (phone.isBlank()) {
                        errorMessage = "يرجى كتابة رقم الهاتف"
                    } else if (password.length < 4) {
                        errorMessage = "كلمة السر يجب أن تكون 4 خانات على الأقل"
                    } else {
                        isLoading = true
                        errorMessage = null
                        scope.launch {
                            val (success, err) = onLogin(phone, password)
                            isLoading = false
                            if (!success) {
                                errorMessage = err ?: "بيانات الدخول غير صحيحة"
                            }
                        }
                    }
                }
            ) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(18.dp),
                        color = Color.White,
                        strokeWidth = 2.dp
                    )
                    Spacer(modifier = Modifier.width(8.dp))
                    Text("جاري الدخول...")
                } else {
                    Text("تسجيل الدخول", fontWeight = FontWeight.Bold)
                }
            }
        },
        dismissButton = {
            OutlinedButton(
                enabled = !isLoading,
                onClick = onDismiss
            ) {
                Text("إلغاء")
            }
        }
    )
}

/**
 * حوار تغذية وشحن رصيد الحساب عبر الخادم (بالإرسال للخادم مع فحص نقطة التغذية)
 */
@Composable
fun DepositDialog(
    onDismiss: () -> Unit,
    onFeedViaServer: suspend (phone: String, amount: Double, code: String) -> Pair<Boolean, String>
) {
    var phone by remember { mutableStateOf("770123456") }
    var amountText by remember { mutableStateOf("10000") }
    var codeText by remember { mutableStateOf("") }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var successMessage by remember { mutableStateOf<String?>(null) }
    var isLoading by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    AlertDialog(
        onDismissRequest = { if (!isLoading) onDismiss() },
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.AccountBalanceWallet,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary
                )
                Text(text = "تغذية الحساب عبر الخادم", fontWeight = FontWeight.Bold)
            }
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text(
                    text = "سيتم إرسال طلب التغذية للخادم للتحقق من نقطة التغذية وشحن رصيد محفظتك فورياً.",
                    style = MaterialTheme.typography.bodySmall.copy(
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                )

                OutlinedTextField(
                    value = phone,
                    onValueChange = { phone = it; errorMessage = null },
                    label = { Text("رقم هاتف الحساب المراد تغذيته") },
                    leadingIcon = { Icon(Icons.Default.Phone, contentDescription = null) },
                    singleLine = true,
                    enabled = !isLoading && successMessage == null,
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.fillMaxWidth()
                )

                OutlinedTextField(
                    value = amountText,
                    onValueChange = { amountText = it; errorMessage = null },
                    label = { Text("المبلغ المطلوب شحنه (ر.ي)") },
                    singleLine = true,
                    enabled = !isLoading && successMessage == null,
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.fillMaxWidth()
                )

                // Quick amount chips
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    listOf("5000", "10000", "20000", "50000", "100000").forEach { chipAmount ->
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = if (amountText == chipAmount) MaterialTheme.colorScheme.primaryContainer else Color(0xFFF1F5F9),
                            modifier = Modifier.clickable(enabled = !isLoading && successMessage == null) {
                                amountText = chipAmount
                            }
                        ) {
                            Text(
                                text = "$chipAmount ر.ي",
                                style = MaterialTheme.typography.labelSmall.copy(
                                    fontWeight = if (amountText == chipAmount) FontWeight.Bold else FontWeight.Normal,
                                    color = if (amountText == chipAmount) MaterialTheme.colorScheme.primary else Color(0xFF475569)
                                ),
                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 5.dp)
                            )
                        }
                    }
                }

                OutlinedTextField(
                    value = codeText,
                    onValueChange = { codeText = it; errorMessage = null },
                    label = { Text("رمز الحوالة أو سند الإيداع (اختياري)") },
                    placeholder = { Text("مثال: DEP-98231") },
                    singleLine = true,
                    enabled = !isLoading && successMessage == null,
                    shape = RoundedCornerShape(10.dp),
                    modifier = Modifier.fillMaxWidth()
                )

                if (errorMessage != null) {
                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = MaterialTheme.colorScheme.errorContainer.copy(alpha = 0.8f),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = errorMessage ?: "",
                            style = MaterialTheme.typography.bodySmall.copy(
                                color = MaterialTheme.colorScheme.onErrorContainer,
                                fontWeight = FontWeight.Bold
                            ),
                            modifier = Modifier.padding(10.dp)
                        )
                    }
                }

                if (successMessage != null) {
                    Surface(
                        shape = RoundedCornerShape(8.dp),
                        color = Color(0xFFE8F5E9),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Text(
                            text = "✅ $successMessage",
                            style = MaterialTheme.typography.bodySmall.copy(
                                color = Color(0xFF2E7D32),
                                fontWeight = FontWeight.Bold
                            ),
                            modifier = Modifier.padding(10.dp)
                        )
                    }
                }
            }
        },
        confirmButton = {
            if (successMessage != null) {
                Button(onClick = onDismiss) {
                    Text("إغلاق")
                }
            } else {
                Button(
                    enabled = !isLoading,
                    onClick = {
                        val amt = amountText.toDoubleOrNull() ?: 0.0
                        if (amt <= 0) {
                            errorMessage = "يرجى إدخال مبلغ صحيح للتغذية"
                            return@Button
                        }
                        if (phone.isBlank()) {
                            errorMessage = "يرجى إدخال رقم الهاتف"
                            return@Button
                        }
                        isLoading = true
                        errorMessage = null
                        scope.launch {
                            val (success, msg) = onFeedViaServer(phone, amt, codeText)
                            isLoading = false
                            if (success) {
                                successMessage = msg
                            } else {
                                errorMessage = msg
                            }
                        }
                    }
                ) {
                    if (isLoading) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp, color = Color.White)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("جاري الإرسال للخادم...")
                    } else {
                        Text("إرسال طلب التغذية للخادم", fontWeight = FontWeight.Bold)
                    }
                }
            }
        },
        dismissButton = {
            if (successMessage == null) {
                OutlinedButton(enabled = !isLoading, onClick = onDismiss) {
                    Text("إلغاء")
                }
            }
        }
    )
}

/**
 * حوار تحويل مالي لحساب عميل مع:
 * - إدخال الرقم أو اختياره من جهات الاتصال بزر
 * - اختيار المبلغ
 * - الإرسال للسيرفر للتحقق من رصيد العميل
 * - إرجاع اسم المشارك مع زر تأكيد التحويل
 */
@Composable
fun TransferDialog(
    onDismiss: () -> Unit,
    onCheckEligibility: suspend (recipient: String, amount: Double) -> TransferCheckResult,
    onConfirmTransfer: suspend (recipient: String, recipientName: String, amount: Double) -> Boolean
) {
    val context = LocalContext.current
    var recipient by remember { mutableStateOf("") }
    var amountText by remember { mutableStateOf("10000") }
    var isChecking by remember { mutableStateOf(false) }
    var isExecuting by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var step by remember { mutableStateOf(1) } // 1: Input & Check, 2: Confirm Recipient
    var eligibleResult by remember { mutableStateOf<TransferCheckResult?>(null) }
    val scope = rememberCoroutineScope()

    // Activity launcher to pick contact from device contacts
    val contactPickerLauncher = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.PickContact()
    ) { uri: Uri? ->
        if (uri != null) {
            try {
                val cursor = context.contentResolver.query(uri, null, null, null, null)
                cursor?.use { c ->
                    if (c.moveToFirst()) {
                        val idIndex = c.getColumnIndex(ContactsContract.Contacts._ID)
                        val hasPhoneIndex = c.getColumnIndex(ContactsContract.Contacts.HAS_PHONE_NUMBER)
                        val hasPhone = if (hasPhoneIndex != -1) c.getInt(hasPhoneIndex) > 0 else true

                        if (hasPhone && idIndex != -1) {
                            val contactId = c.getString(idIndex)
                            val phoneCursor = context.contentResolver.query(
                                ContactsContract.CommonDataKinds.Phone.CONTENT_URI,
                                null,
                                ContactsContract.CommonDataKinds.Phone.CONTACT_ID + " = ?",
                                arrayOf(contactId),
                                null
                            )
                            phoneCursor?.use { pc ->
                                if (pc.moveToFirst()) {
                                    val numberIndex = pc.getColumnIndex(ContactsContract.CommonDataKinds.Phone.NUMBER)
                                    if (numberIndex != -1) {
                                        val rawNumber = pc.getString(numberIndex)
                                        val cleaned = rawNumber.replace(" ", "").replace("-", "").replace("+967", "").trim()
                                        recipient = cleaned
                                        errorMessage = null
                                    }
                                }
                            }
                        }
                    }
                }
            } catch (_: Exception) {}
        }
    }

    AlertDialog(
        onDismissRequest = { if (!isChecking && !isExecuting) onDismiss() },
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Send,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary
                )
                Text(
                    text = if (step == 1) "تحويل مالي لحساب عميل" else "تأكيد بيانات المستلم",
                    fontWeight = FontWeight.Bold
                )
            }
        },
        text = {
            if (step == 1) {
                // Step 1: Input recipient phone & choose amount
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(
                        text = "أدخل رقم هاتف العميل أو اختره من جهات الاتصال، ثم حدد المبلغ:",
                        style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.onSurfaceVariant)
                    )

                    // Phone input with Contact Picker button
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        OutlinedTextField(
                            value = recipient,
                            onValueChange = { recipient = it; errorMessage = null },
                            label = { Text("رقم هاتف العميل المستلم") },
                            placeholder = { Text("770123456") },
                            leadingIcon = { Icon(Icons.Default.Phone, contentDescription = null) },
                            singleLine = true,
                            shape = RoundedCornerShape(10.dp),
                            modifier = Modifier.weight(1f)
                        )

                        // زر فتح جهات الاتصال لاختيار رقم العميل (مطلوب بالاسم من المستخدم)
                        Button(
                            onClick = {
                                try {
                                    contactPickerLauncher.launch(null)
                                } catch (_: Exception) {
                                    recipient = "770123456"
                                }
                            },
                            shape = RoundedCornerShape(10.dp),
                            contentPadding = PaddingValues(horizontal = 10.dp, vertical = 12.dp)
                        ) {
                            Icon(imageVector = Icons.Default.Contacts, contentDescription = "جهات الاتصال", modifier = Modifier.size(18.dp))
                            Spacer(modifier = Modifier.width(4.dp))
                            Text("جهات الاتصال", style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold))
                        }
                    }

                    // Quick contacts chips for easy 1-click selection
                    Text(
                        text = "أو اختر عميل سريع:",
                        style = MaterialTheme.typography.labelSmall.copy(color = Color(0xFF64748B))
                    )
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        listOf(
                            "زيدان العطاب" to "770123456",
                            "أحمد الشامي" to "771234567",
                            "محمد اليماني" to "770111222",
                            "عبدالرحمن سنان" to "772223334"
                        ).forEach { (name, phone) ->
                            Surface(
                                shape = RoundedCornerShape(8.dp),
                                color = if (recipient == phone) MaterialTheme.colorScheme.primaryContainer else Color(0xFFF1F5F9),
                                modifier = Modifier.clickable {
                                    recipient = phone
                                    errorMessage = null
                                }
                            ) {
                                Row(
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 5.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                                ) {
                                    Icon(Icons.Default.Person, contentDescription = null, modifier = Modifier.size(12.dp), tint = MaterialTheme.colorScheme.primary)
                                    Text(
                                        text = "$name ($phone)",
                                        style = MaterialTheme.typography.labelSmall.copy(
                                            fontWeight = if (recipient == phone) FontWeight.Bold else FontWeight.Normal,
                                            color = if (recipient == phone) MaterialTheme.colorScheme.primary else Color(0xFF334155)
                                        )
                                    )
                                }
                            }
                        }
                    }

                    Spacer(modifier = Modifier.height(2.dp))

                    OutlinedTextField(
                        value = amountText,
                        onValueChange = { amountText = it; errorMessage = null },
                        label = { Text("المبلغ المراد تحويله (ر.ي)") },
                        leadingIcon = { Icon(Icons.Default.AccountBalanceWallet, contentDescription = null) },
                        singleLine = true,
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    )

                    // Quick amount chips
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        listOf("1000", "5000", "10000", "20000", "50000").forEach { chipAmount ->
                            Surface(
                                shape = RoundedCornerShape(8.dp),
                                color = if (amountText == chipAmount) MaterialTheme.colorScheme.primaryContainer else Color(0xFFF8FAFC),
                                modifier = Modifier.clickable { amountText = chipAmount }
                            ) {
                                Text(
                                    text = "$chipAmount ر.ي",
                                    style = MaterialTheme.typography.labelSmall.copy(
                                        fontWeight = if (amountText == chipAmount) FontWeight.Bold else FontWeight.Normal,
                                        color = if (amountText == chipAmount) MaterialTheme.colorScheme.primary else Color(0xFF475569)
                                    ),
                                    modifier = Modifier.padding(horizontal = 8.dp, vertical = 5.dp)
                                )
                            }
                        }
                    }

                    if (errorMessage != null) {
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = MaterialTheme.colorScheme.errorContainer,
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Text(
                                text = errorMessage ?: "",
                                style = MaterialTheme.typography.bodySmall.copy(
                                    color = MaterialTheme.colorScheme.onErrorContainer,
                                    fontWeight = FontWeight.Bold
                                ),
                                modifier = Modifier.padding(10.dp)
                            )
                        }
                    }
                }
            } else {
                // Step 2: Server returned recipient name and confirmed balance allows transfer!
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Card(
                        shape = RoundedCornerShape(12.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFF0FDF4))
                    ) {
                        Column(modifier = Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                Icon(Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF16A34A), modifier = Modifier.size(20.dp))
                                Text(
                                    text = "رصيدك كافٍ ومسموح بإتمام التحويل",
                                    style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold, color = Color(0xFF166534))
                                )
                            }

                            Spacer(modifier = Modifier.height(4.dp))

                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text("اسم المشارك المستلم:", style = MaterialTheme.typography.bodySmall.copy(color = Color(0xFF475569)))
                                Text(
                                    text = eligibleResult?.recipientName ?: recipient,
                                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                                )
                            }

                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text("رقم هاتف المستلم:", style = MaterialTheme.typography.bodySmall.copy(color = Color(0xFF475569)))
                                Text(recipient, style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold))
                            }

                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text("المبلغ المحول:", style = MaterialTheme.typography.bodySmall.copy(color = Color(0xFF475569)))
                                Text("${eligibleResult?.amount?.toInt() ?: 0} ر.ي", style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold, color = Color(0xFF16A34A)))
                            }

                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                                Text("رسوم العملية:", style = MaterialTheme.typography.bodySmall.copy(color = Color(0xFF475569)))
                                Text("مجاناً 0 ر.ي", style = MaterialTheme.typography.bodySmall.copy(color = Color(0xFF64748B)))
                            }
                        }
                    }

                    if (errorMessage != null) {
                        Text(text = errorMessage ?: "", color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }
        },
        confirmButton = {
            if (step == 1) {
                Button(
                    enabled = !isChecking,
                    onClick = {
                        val amt = amountText.toDoubleOrNull() ?: 0.0
                        if (recipient.isBlank()) {
                            errorMessage = "يرجى إدخال رقم هاتف المستلم"
                            return@Button
                        }
                        if (amt <= 0) {
                            errorMessage = "يرجى تحديد مبلغ تحويل صحيح أكبر من 0"
                            return@Button
                        }
                        isChecking = true
                        errorMessage = null
                        scope.launch {
                            val res = onCheckEligibility(recipient.trim(), amt)
                            isChecking = false
                            if (res.isAllowed) {
                                eligibleResult = res
                                step = 2
                            } else {
                                errorMessage = res.message ?: "عفواً، رصيدك الحالي غير كافٍ لإتمام التحويل"
                            }
                        }
                    }
                ) {
                    if (isChecking) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp, color = Color.White)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("جاري الفحص من السيرفر...")
                    } else {
                        Text("فحص وإرسال للتحقق", fontWeight = FontWeight.Bold)
                    }
                }
            } else {
                // Step 2 Confirm button (زر تأكيد التحويل المطلوب من المستخدم)
                Button(
                    enabled = !isExecuting,
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF16A34A)),
                    onClick = {
                        val amt = eligibleResult?.amount ?: 0.0
                        val recName = eligibleResult?.recipientName ?: recipient
                        isExecuting = true
                        scope.launch {
                            val success = onConfirmTransfer(recipient.trim(), recName, amt)
                            isExecuting = false
                            if (success) {
                                onDismiss()
                            } else {
                                errorMessage = "فشل تنفيذ التحويل، يرجى المحاولة لاحقاً"
                            }
                        }
                    }
                ) {
                    if (isExecuting) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp, color = Color.White)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("جاري التحويل...")
                    } else {
                        Icon(Icons.Default.CheckCircle, contentDescription = null, modifier = Modifier.size(16.dp))
                        Spacer(modifier = Modifier.width(4.dp))
                        Text("تأكيد التحويل الآن", fontWeight = FontWeight.Bold)
                    }
                }
            }
        },
        dismissButton = {
            if (step == 2) {
                OutlinedButton(onClick = { step = 1; errorMessage = null }) {
                    Text("تعديل البيانات")
                }
            } else {
                OutlinedButton(onClick = onDismiss) {
                    Text("إلغاء")
                }
            }
        }
    )
}

/**
 * حوار إعدادات وربط خادم جانغو (Django API Settings)
 */
@Composable
fun DjangoSettingsDialog(
    currentUrl: String,
    onDismiss: () -> Unit,
    onSaveUrl: (String) -> Unit
) {
    var urlText by remember { mutableStateOf(currentUrl) }
    var pingStatus by remember { mutableStateOf<String?>(null) }
    var isPinging by remember { mutableStateOf(false) }
    val scope = rememberCoroutineScope()

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Dns,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary
                )
                Text(text = "إعدادات خادم جانغو (Django)", fontWeight = FontWeight.Bold)
            }
        },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text(
                    text = "يمكنك تغيير رابط API الأساسي للربط مع سيرفر جانغو الخاص بك:",
                    style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.onSurfaceVariant)
                )

                OutlinedTextField(
                    value = urlText,
                    onValueChange = {
                        urlText = it
                        pingStatus = null
                    },
                    label = { Text("Django Base URL") },
                    placeholder = { Text("https://shopik.alattab.site/api/") },
                    shape = RoundedCornerShape(10.dp),
                    singleLine = true,
                    modifier = Modifier.fillMaxWidth()
                )

                Button(
                    enabled = !isPinging,
                    onClick = {
                        isPinging = true
                        pingStatus = null
                        scope.launch {
                            val ok = com.example.data.repository.StoreRepository.instance.testDjangoConnection(urlText)
                            isPinging = false
                            pingStatus = if (ok) {
                                "✅ تم الاتصال بنجاح بالخادم واسترجاع البيانات!"
                            } else {
                                "❌ تعذر الاتصال بالرابط، يرجى التأكد من تشغيل السيرفر أو الاتصال بالإنترنت."
                            }
                        }
                    },
                    colors = ButtonDefaults.buttonColors(
                        containerColor = MaterialTheme.colorScheme.secondaryContainer,
                        contentColor = MaterialTheme.colorScheme.onSecondaryContainer
                    )
                ) {
                    if (isPinging) {
                        CircularProgressIndicator(modifier = Modifier.size(16.dp), strokeWidth = 2.dp)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("جاري الفحص...")
                    } else {
                        Text("اختبار الاتصال بالخادم")
                    }
                }

                if (pingStatus != null) {
                    Text(
                        text = pingStatus ?: "",
                        style = MaterialTheme.typography.bodySmall.copy(
                            color = if (pingStatus?.startsWith("✅") == true) Color(0xFF2E7D32) else MaterialTheme.colorScheme.error,
                            fontWeight = FontWeight.Bold
                        )
                    )
                }
            }
        },
        confirmButton = {
            Button(onClick = { onSaveUrl(urlText) }) {
                Text("حفظ الإعدادات", fontWeight = FontWeight.Bold)
            }
        },
        dismissButton = {
            OutlinedButton(onClick = onDismiss) {
                Text("إغلاق")
            }
        }
    )
}

/**
 * قائمة الإشعارات مع دعم الضغط على الإشعار لتمييزه كمقروء فورياً
 */
@Composable
fun NotificationsDialog(
    notifications: List<AppNotification>,
    onDismiss: () -> Unit,
    onNotificationClick: (AppNotification) -> Unit = {},
    onMarkAllAsRead: () -> Unit = {}
) {
    val unreadCount = notifications.count { !it.isRead }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(
                modifier = Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.Notifications,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary
                    )
                    Text(text = "الإشعارات والتنبيهات", fontWeight = FontWeight.Bold)
                }

                if (unreadCount > 0) {
                    TextButton(onClick = onMarkAllAsRead) {
                        Text("تحديد الكل كمقروء", style = MaterialTheme.typography.labelSmall)
                    }
                }
            }
        },
        text = {
            if (notifications.isEmpty()) {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(24.dp),
                    contentAlignment = Alignment.Center
                ) {
                    Text(
                        text = "لا توجد إشعارات جديدة حالياً",
                        style = MaterialTheme.typography.bodyMedium.copy(color = Color.Gray)
                    )
                }
            } else {
                LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(notifications) { notification ->
                        val isUnread = !notification.isRead
                        Card(
                            modifier = Modifier
                                .fillMaxWidth()
                                .clickable { onNotificationClick(notification) },
                            shape = RoundedCornerShape(12.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = if (isUnread) Color(0xFFEFF6FF) else Color(0xFFF8FAFC)
                            ),
                            border = if (isUnread) androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFBFDBFE)) else null
                        ) {
                            Column(modifier = Modifier.padding(12.dp)) {
                                Row(
                                    modifier = Modifier.fillMaxWidth(),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.SpaceBetween
                                ) {
                                    Row(
                                        verticalAlignment = Alignment.CenterVertically,
                                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                                    ) {
                                        if (isUnread) {
                                            Box(
                                                modifier = Modifier
                                                    .size(8.dp)
                                                    .clip(CircleShape)
                                                    .background(Color(0xFF2563EB))
                                            )
                                        }
                                        Text(
                                            text = notification.title,
                                            style = MaterialTheme.typography.titleSmall.copy(
                                                fontWeight = if (isUnread) FontWeight.Bold else FontWeight.Medium,
                                                color = if (isUnread) Color(0xFF1E3A8A) else Color(0xFF1E293B)
                                            )
                                        )
                                    }

                                    if (isUnread) {
                                        Surface(
                                            shape = RoundedCornerShape(6.dp),
                                            color = Color(0xFFDBEAFE)
                                        ) {
                                            Text(
                                                text = "جديد",
                                                style = MaterialTheme.typography.labelSmall.copy(
                                                    color = Color(0xFF1D4ED8),
                                                    fontWeight = FontWeight.Bold
                                                ),
                                                modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                            )
                                        }
                                    } else {
                                        Text(
                                            text = "مقروء ✓",
                                            style = MaterialTheme.typography.labelSmall.copy(color = Color(0xFF94A3B8))
                                        )
                                    }
                                }

                                Spacer(modifier = Modifier.height(4.dp))
                                Text(
                                    text = notification.message,
                                    style = MaterialTheme.typography.bodySmall.copy(
                                        color = if (isUnread) Color(0xFF334155) else Color(0xFF64748B)
                                    )
                                )
                                Spacer(modifier = Modifier.height(6.dp))
                                Text(
                                    text = notification.time,
                                    style = MaterialTheme.typography.labelSmall.copy(color = Color(0xFF94A3B8))
                                )
                            }
                        }
                    }
                }
            }
        },
        confirmButton = {
            Button(onClick = onDismiss) {
                Text("إغلاق")
            }
        }
    )
}

/**
 * حوار المحادثة المباشرة مع المتجر (مطلوب من المستخدم)
 */
@Composable
fun StoreChatDialog(
    store: com.example.data.model.Store,
    messages: List<com.example.data.model.OrderChatMessage>,
    onSendMessage: (String) -> Unit,
    onDismiss: () -> Unit
) {
    var textInput by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Icon(
                    imageVector = Icons.Default.Phone,
                    contentDescription = null,
                    tint = MaterialTheme.colorScheme.primary
                )
                Column {
                    Text(text = "محادثة متجر: ${store.name}", fontWeight = FontWeight.Bold, style = MaterialTheme.typography.titleMedium)
                    Text(text = "متاح الآن • يرد خلال دقائق", style = MaterialTheme.typography.labelSmall.copy(color = Color(0xFF2E7D32)))
                }
            }
        },
        text = {
            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .height(340.dp)
            ) {
                LazyColumn(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    items(messages) { msg ->
                        val isUser = msg.isFromUser
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = if (isUser) Arrangement.End else Arrangement.Start
                        ) {
                            Surface(
                                shape = RoundedCornerShape(
                                    topStart = 12.dp,
                                    topEnd = 12.dp,
                                    bottomStart = if (isUser) 12.dp else 2.dp,
                                    bottomEnd = if (isUser) 2.dp else 12.dp
                                ),
                                color = if (isUser) MaterialTheme.colorScheme.primary else Color(0xFFF1F5F9),
                                modifier = Modifier.widthIn(max = 240.dp)
                            ) {
                                Column(modifier = Modifier.padding(10.dp)) {
                                    Text(
                                        text = msg.senderName,
                                        style = MaterialTheme.typography.labelSmall.copy(
                                            color = if (isUser) Color.White.copy(alpha = 0.8f) else MaterialTheme.colorScheme.primary,
                                            fontWeight = FontWeight.Bold
                                        )
                                    )
                                    Spacer(modifier = Modifier.height(2.dp))
                                    Text(
                                        text = msg.message,
                                        style = MaterialTheme.typography.bodySmall.copy(
                                            color = if (isUser) Color.White else Color(0xFF1E293B)
                                        )
                                    )
                                    Spacer(modifier = Modifier.height(2.dp))
                                    Text(
                                        text = msg.time,
                                        style = MaterialTheme.typography.labelSmall.copy(
                                            color = if (isUser) Color.White.copy(alpha = 0.6f) else Color.Gray,
                                            fontSize = 9.sp
                                        ),
                                        modifier = Modifier.align(Alignment.End)
                                    )
                                }
                            }
                        }
                    }
                }

                Spacer(modifier = Modifier.height(8.dp))

                Row(
                    modifier = Modifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    OutlinedTextField(
                        value = textInput,
                        onValueChange = { textInput = it },
                        placeholder = { Text("اكتب استفسارك هنا...") },
                        shape = RoundedCornerShape(10.dp),
                        singleLine = true,
                        modifier = Modifier.weight(1f)
                    )

                    Button(
                        onClick = {
                            if (textInput.isNotBlank()) {
                                onSendMessage(textInput)
                                textInput = ""
                            }
                        },
                        shape = RoundedCornerShape(10.dp),
                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 8.dp)
                    ) {
                        Text("إرسال")
                    }
                }
            }
        },
        confirmButton = {
            TextButton(onClick = onDismiss) {
                Text("إغلاق")
            }
        }
    )
}

