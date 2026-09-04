package com.example.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.TransferCheckResult
import com.example.data.model.UserSession
import com.example.data.model.WalletAccount
import com.example.data.model.WalletTransaction
import kotlinx.coroutines.launch

enum class TransferStep {
    INPUT,
    CONFIRMATION,
    SUCCESS
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun TransferScreen(
    wallet: WalletAccount,
    userSession: UserSession,
    onBackClick: () -> Unit,
    formatMoney: (Double) -> String,
    onCheckEligibility: suspend (phone: String, amount: Double, message: String) -> TransferCheckResult,
    onConfirmTransfer: suspend (giftId: Int?, phone: String, name: String, amount: Double) -> Pair<Boolean, WalletTransaction?>,
    onCancelTransfer: suspend (giftId: Int?) -> Boolean
) {
    val coroutineScope = rememberCoroutineScope()
    var currentStep by remember { mutableStateOf(TransferStep.INPUT) }

    // Input States
    var recipientPhone by remember { mutableStateOf("") }
    var transferAmountText by remember { mutableStateOf("") }
    var transferNotes by remember { mutableStateOf("") }

    // Processing & Result States
    var isChecking by remember { mutableStateOf(false) }
    var isConfirming by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var checkResult by remember { mutableStateOf<TransferCheckResult?>(null) }
    var completedTransaction by remember { mutableStateOf<WalletTransaction?>(null) }

    val quickAmounts = listOf(2000.0, 5000.0, 10000.0, 20000.0, 50000.0)

    val quickContacts = listOf(
        Pair("770123456", "زيدان العطاب"),
        Pair("771234789", "أحمد الشامي"),
        Pair("777111222", "محمد اليماني"),
        Pair("773334444", "ياسر القدسي")
    )

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = when (currentStep) {
                            TransferStep.INPUT -> "تحويل مالي لمشترك"
                            TransferStep.CONFIRMATION -> "مراجعة وتأكيد الحوالة"
                            TransferStep.SUCCESS -> "إشعار إتمام الحوالة"
                        },
                        fontWeight = FontWeight.Bold
                    )
                },
                navigationIcon = {
                    IconButton(
                        onClick = {
                            if (currentStep == TransferStep.CONFIRMATION) {
                                coroutineScope.launch {
                                    onCancelTransfer(checkResult?.giftId)
                                    currentStep = TransferStep.INPUT
                                }
                            } else {
                                onBackClick()
                            }
                        }
                    ) {
                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                            contentDescription = "رجوع"
                        )
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface
                )
            )
        }
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(Color(0xFFF8FAFC)),
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Step Progress Indicator
            item {
                TransferStepIndicator(currentStep = currentStep)
            }

            // Error Banner if server returned an error (insufficient balance or subscriber not found)
            if (!errorMessage.isNullOrBlank()) {
                item {
                    Surface(
                        color = Color(0xFFFEF2F2),
                        shape = RoundedCornerShape(12.dp),
                        border = androidx.compose.foundation.BorderStroke(1.dp, Color(0xFFFCA5A5)),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Row(
                            modifier = Modifier.padding(14.dp),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.Warning,
                                contentDescription = null,
                                tint = Color(0xFFDC2626),
                                modifier = Modifier.size(24.dp)
                            )
                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = "تنبيه من الخادم",
                                    style = MaterialTheme.typography.titleSmall.copy(
                                        color = Color(0xFF991B1B),
                                        fontWeight = FontWeight.Bold
                                    )
                                )
                                Text(
                                    text = errorMessage ?: "",
                                    style = MaterialTheme.typography.bodySmall.copy(
                                        color = Color(0xFFB91C1C)
                                    )
                                )
                            }
                            IconButton(onClick = { errorMessage = null }) {
                                Icon(
                                    imageVector = Icons.Default.Close,
                                    contentDescription = "إغلاق",
                                    tint = Color(0xFF991B1B)
                                )
                            }
                        }
                    }
                }
            }

            // Content per Step
            when (currentStep) {
                TransferStep.INPUT -> {
                    // 1. Available Wallet Balance Card
                    item {
                        WalletBalanceMiniCard(
                            wallet = wallet,
                            formatMoney = formatMoney
                        )
                    }

                    // 2. Input Fields Card
                    item {
                        Card(
                            shape = RoundedCornerShape(18.dp),
                            colors = CardDefaults.cardColors(containerColor = Color.White),
                            elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                            modifier = Modifier.fillMaxWidth()
                        ) {
                            Column(
                                modifier = Modifier.padding(18.dp),
                                verticalArrangement = Arrangement.spacedBy(14.dp)
                            ) {
                                Text(
                                    text = "بيانات المستلم والمبلغ",
                                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                                )

                                // Recipient Phone Field
                                OutlinedTextField(
                                    value = recipientPhone,
                                    onValueChange = {
                                        recipientPhone = it
                                        errorMessage = null
                                    },
                                    label = { Text("رقم هاتف المشترك المستلم") },
                                    placeholder = { Text("مثال: 770123456 أو 771234789") },
                                    leadingIcon = {
                                        Icon(
                                            imageVector = Icons.Default.PhoneAndroid,
                                            contentDescription = null,
                                            tint = MaterialTheme.colorScheme.primary
                                        )
                                    },
                                    singleLine = true,
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .testTag("transfer_recipient_input"),
                                    shape = RoundedCornerShape(12.dp)
                                )

                                // Quick Contacts Suggestion Chips
                                Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                    Text(
                                        text = "مشتركون مقترحون سريعاً:",
                                        style = MaterialTheme.typography.labelSmall.copy(color = Color.Gray)
                                    )
                                    LazyRow(
                                        horizontalArrangement = Arrangement.spacedBy(8.dp)
                                    ) {
                                        items(quickContacts) { contact ->
                                            SuggestionChip(
                                                onClick = {
                                                    recipientPhone = contact.first
                                                    errorMessage = null
                                                },
                                                label = {
                                                    Text(
                                                        text = contact.second,
                                                        fontSize = 12.sp
                                                    )
                                                },
                                                icon = {
                                                    Icon(
                                                        imageVector = Icons.Default.Person,
                                                        contentDescription = null,
                                                        modifier = Modifier.size(16.dp)
                                                    )
                                                }
                                            )
                                        }
                                    }
                                }

                                // Amount Field
                                OutlinedTextField(
                                    value = transferAmountText,
                                    onValueChange = {
                                        transferAmountText = it
                                        errorMessage = null
                                    },
                                    label = { Text("المبلغ المراد تحويله (ر.ي)") },
                                    placeholder = { Text("أدخل المبلغ بالريال اليمني") },
                                    leadingIcon = {
                                        Icon(
                                            imageVector = Icons.Default.Payments,
                                            contentDescription = null,
                                            tint = MaterialTheme.colorScheme.primary
                                        )
                                    },
                                    singleLine = true,
                                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .testTag("transfer_amount_input"),
                                    shape = RoundedCornerShape(12.dp)
                                )

                                // Quick Amount Chips
                                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    items(quickAmounts) { amt ->
                                        OutlinedButton(
                                            onClick = {
                                                transferAmountText = amt.toInt().toString()
                                                errorMessage = null
                                            },
                                            shape = RoundedCornerShape(20.dp),
                                            contentPadding = PaddingValues(horizontal = 10.dp, vertical = 4.dp)
                                        ) {
                                            Text(
                                                text = "${formatMoney(amt)} ر.ي",
                                                fontSize = 12.sp,
                                                fontWeight = FontWeight.SemiBold
                                            )
                                        }
                                    }
                                }

                                // Note / Message Field
                                OutlinedTextField(
                                    value = transferNotes,
                                    onValueChange = { transferNotes = it },
                                    label = { Text("ملاحظة أو رسالة إهداء (اختياري)") },
                                    placeholder = { Text("مثال: هدية عيد، سداد فاتورة، تحويل مصاريف") },
                                    leadingIcon = {
                                        Icon(
                                            imageVector = Icons.Default.Message,
                                            contentDescription = null,
                                            tint = Color.Gray
                                        )
                                    },
                                    singleLine = true,
                                    modifier = Modifier.fillMaxWidth(),
                                    shape = RoundedCornerShape(12.dp)
                                )

                                Spacer(modifier = Modifier.height(4.dp))

                                // Submit to Server Button
                                Button(
                                    onClick = {
                                        val amt = transferAmountText.toDoubleOrNull() ?: 0.0
                                        if (recipientPhone.isBlank()) {
                                            errorMessage = "يرجى إدخال رقم هاتف المستلم للمتابعة"
                                            return@Button
                                        }
                                        if (amt <= 0) {
                                            errorMessage = "يرجى إدخال مبلغ صحيح أكبر من 0 ر.ي"
                                            return@Button
                                        }
                                        isChecking = true
                                        errorMessage = null
                                        coroutineScope.launch {
                                            val res = onCheckEligibility(recipientPhone, amt, transferNotes)
                                            isChecking = false
                                            if (res.isAllowed) {
                                                checkResult = res
                                                currentStep = TransferStep.CONFIRMATION
                                            } else {
                                                errorMessage = res.message
                                            }
                                        }
                                    },
                                    enabled = !isChecking,
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .height(52.dp)
                                        .testTag("verify_transfer_button"),
                                    shape = RoundedCornerShape(14.dp),
                                    colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                                ) {
                                    if (isChecking) {
                                        CircularProgressIndicator(
                                            color = Color.White,
                                            modifier = Modifier.size(24.dp),
                                            strokeWidth = 2.dp
                                        )
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text("جاري فحص رصيدك والمشترك في الخادم...")
                                    } else {
                                        Icon(imageVector = Icons.Default.CheckCircle, contentDescription = null)
                                        Spacer(modifier = Modifier.width(8.dp))
                                        Text("فحص الحساب والمتابعة للتأكيد", fontWeight = FontWeight.Bold, fontSize = 15.sp)
                                    }
                                }
                            }
                        }
                    }
                }

                TransferStep.CONFIRMATION -> {
                    item {
                        ConfirmationReviewCard(
                            checkResult = checkResult,
                            wallet = wallet,
                            notes = transferNotes,
                            isConfirming = isConfirming,
                            formatMoney = formatMoney,
                            onConfirm = {
                                checkResult?.let { res ->
                                    isConfirming = true
                                    coroutineScope.launch {
                                        val (ok, tx) = onConfirmTransfer(
                                            res.giftId,
                                            res.recipientPhone,
                                            res.recipientName ?: "المشترك",
                                            res.amount
                                        )
                                        isConfirming = false
                                        if (ok && tx != null) {
                                            completedTransaction = tx
                                            currentStep = TransferStep.SUCCESS
                                        } else {
                                            errorMessage = "فشل تأكيد العملية على الخادم، يرجى المحاولة لاحقاً."
                                        }
                                    }
                                }
                            },
                            onCancel = {
                                coroutineScope.launch {
                                    onCancelTransfer(checkResult?.giftId)
                                    currentStep = TransferStep.INPUT
                                }
                            }
                        )
                    }
                }

                TransferStep.SUCCESS -> {
                    item {
                        SuccessReceiptCard(
                            tx = completedTransaction,
                            formatMoney = formatMoney,
                            onDone = onBackClick
                        )
                    }
                }
            }
        }
    }
}

@Composable
fun TransferStepIndicator(currentStep: TransferStep) {
    val steps = listOf(
        Pair("1. البيانات", TransferStep.INPUT),
        Pair("2. التأكيد أو التراجع", TransferStep.CONFIRMATION),
        Pair("3. الإشعار", TransferStep.SUCCESS)
    )

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        steps.forEachIndexed { index, pair ->
            val isActive = currentStep.ordinal >= pair.second.ordinal
            val isCurrent = currentStep == pair.second

            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(26.dp)
                        .clip(CircleShape)
                        .background(
                            if (isActive) MaterialTheme.colorScheme.primary else Color(0xFFE2E8F0)
                        ),
                    contentAlignment = Alignment.Center
                ) {
                    if (currentStep.ordinal > pair.second.ordinal) {
                        Icon(
                            imageVector = Icons.Default.Check,
                            contentDescription = null,
                            tint = Color.White,
                            modifier = Modifier.size(16.dp)
                        )
                    } else {
                        Text(
                            text = "${index + 1}",
                            color = if (isActive) Color.White else Color.Gray,
                            fontSize = 12.sp,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
                Text(
                    text = pair.first,
                    style = MaterialTheme.typography.labelMedium.copy(
                        color = if (isCurrent) MaterialTheme.colorScheme.primary else if (isActive) Color(0xFF1E293B) else Color.Gray,
                        fontWeight = if (isCurrent) FontWeight.Bold else FontWeight.Normal,
                        fontSize = 11.sp
                    )
                )
            }
        }
    }
}

@Composable
fun WalletBalanceMiniCard(
    wallet: WalletAccount,
    formatMoney: (Double) -> String
) {
    Card(
        shape = RoundedCornerShape(16.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .background(
                    Brush.horizontalGradient(
                        listOf(Color(0xFF0F172A), Color(0xFF1E293B), Color(0xFF0284C7))
                    )
                )
                .padding(16.dp)
        ) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween,
                verticalAlignment = Alignment.CenterVertically
            ) {
                Column {
                    Text(
                        text = "الرصيد المتاح للتحويل في محفظتك:",
                        color = Color(0xFF94A3B8),
                        fontSize = 12.sp
                    )
                    Spacer(modifier = Modifier.height(4.dp))
                    Text(
                        text = "${formatMoney(wallet.balanceYer)} ر.ي",
                        color = Color.White,
                        style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold)
                    )
                    Text(
                        text = "حساب رقم: ${wallet.accountNumber}",
                        color = Color(0xFFBAE6FD),
                        fontSize = 11.sp
                    )
                }

                Surface(
                    color = Color.White.copy(alpha = 0.15f),
                    shape = RoundedCornerShape(12.dp)
                ) {
                    Icon(
                        imageVector = Icons.Default.AccountBalanceWallet,
                        contentDescription = null,
                        tint = Color.White,
                        modifier = Modifier
                            .padding(10.dp)
                            .size(28.dp)
                    )
                }
            }
        }
    }
}

@Composable
fun ConfirmationReviewCard(
    checkResult: TransferCheckResult?,
    wallet: WalletAccount,
    notes: String,
    isConfirming: Boolean,
    formatMoney: (Double) -> String,
    onConfirm: () -> Unit,
    onCancel: () -> Unit
) {
    val result = checkResult ?: return
    val remainingBalance = (wallet.balanceYer - result.amount).coerceAtLeast(0.0)

    Card(
        shape = RoundedCornerShape(20.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 3.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            // Header Success Badge
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Box(
                    modifier = Modifier
                        .size(36.dp)
                        .clip(CircleShape)
                        .background(Color(0xFFDCFCE7)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.Verified,
                        contentDescription = null,
                        tint = Color(0xFF16A34A),
                        modifier = Modifier.size(22.dp)
                    )
                }
                Column {
                    Text(
                        text = "تم العثور على المشترك والتحقق من رصيدك",
                        style = MaterialTheme.typography.titleMedium.copy(
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF15803D)
                        )
                    )
                    Text(
                        text = "يرجى مراجعة تفاصيل الحوالة ثم الضغط على تأكيد أو تراجع",
                        style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray)
                    )
                }
            }

            HorizontalDivider()

            // Beneficiary Details Box
            Surface(
                color = Color(0xFFF1F5F9),
                shape = RoundedCornerShape(14.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(14.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(text = "اسم المشترك المستلم:", color = Color.Gray, fontSize = 13.sp)
                        Text(
                            text = result.recipientName ?: "غير محدد",
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF0F172A),
                            fontSize = 14.sp
                        )
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(text = "رقم هاتف المشترك:", color = Color.Gray, fontSize = 13.sp)
                        Text(
                            text = result.recipientPhone,
                            fontWeight = FontWeight.SemiBold,
                            color = Color(0xFF0F172A),
                            fontSize = 14.sp
                        )
                    }
                    if (notes.isNotBlank()) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(text = "الرسالة أو الملاحظة:", color = Color.Gray, fontSize = 13.sp)
                            Text(
                                text = notes,
                                fontWeight = FontWeight.Normal,
                                color = Color(0xFF334155),
                                fontSize = 13.sp
                            )
                        }
                    }
                }
            }

            // Financial Summary
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(text = "مبلغ التحويل الصافي:", style = MaterialTheme.typography.bodyMedium)
                    Text(
                        text = "${formatMoney(result.amount)} ر.ي",
                        fontWeight = FontWeight.Bold,
                        color = MaterialTheme.colorScheme.primary,
                        fontSize = 16.sp
                    )
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(text = "رسوم التحويل:", style = MaterialTheme.typography.bodyMedium)
                    Text(
                        text = "0 ر.ي (مجاناً)",
                        color = Color(0xFF16A34A),
                        fontWeight = FontWeight.Bold
                    )
                }
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween
                ) {
                    Text(text = "الرصيد المتبقي بعد العملية:", style = MaterialTheme.typography.bodyMedium)
                    Text(
                        text = "${formatMoney(remainingBalance)} ر.ي",
                        fontWeight = FontWeight.SemiBold,
                        color = Color(0xFF475569)
                    )
                }
            }

            Spacer(modifier = Modifier.height(6.dp))

            // Action Buttons: Confirm vs Cancel
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                // Cancel / Back Button (تراجع)
                OutlinedButton(
                    onClick = onCancel,
                    enabled = !isConfirming,
                    modifier = Modifier
                        .weight(1f)
                        .height(50.dp)
                        .testTag("transfer_cancel_button"),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.outlinedButtonColors(contentColor = Color(0xFF64748B))
                ) {
                    Icon(imageVector = Icons.Default.Cancel, contentDescription = null)
                    Spacer(modifier = Modifier.width(6.dp))
                    Text("تراجع", fontWeight = FontWeight.Bold)
                }

                // Confirm Button (تأكيد التحويل)
                Button(
                    onClick = onConfirm,
                    enabled = !isConfirming,
                    modifier = Modifier
                        .weight(1.3f)
                        .height(50.dp)
                        .testTag("transfer_confirm_button"),
                    shape = RoundedCornerShape(12.dp),
                    colors = ButtonDefaults.buttonColors(containerColor = Color(0xFF16A34A))
                ) {
                    if (isConfirming) {
                        CircularProgressIndicator(
                            color = Color.White,
                            modifier = Modifier.size(20.dp),
                            strokeWidth = 2.dp
                        )
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("جاري التأكيد...")
                    } else {
                        Icon(imageVector = Icons.Default.Check, contentDescription = null)
                        Spacer(modifier = Modifier.width(6.dp))
                        Text("تأكيد التحويل", fontWeight = FontWeight.Bold)
                    }
                }
            }
        }
    }
}

@Composable
fun SuccessReceiptCard(
    tx: WalletTransaction?,
    formatMoney: (Double) -> String,
    onDone: () -> Unit
) {
    val transaction = tx ?: return

    Card(
        shape = RoundedCornerShape(22.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(
            modifier = Modifier.padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Box(
                modifier = Modifier
                    .size(64.dp)
                    .clip(CircleShape)
                    .background(Color(0xFFDCFCE7)),
                contentAlignment = Alignment.Center
            ) {
                Icon(
                    imageVector = Icons.Default.CheckCircle,
                    contentDescription = null,
                    tint = Color(0xFF16A34A),
                    modifier = Modifier.size(42.dp)
                )
            }

            Text(
                text = "تم التحويل بنجاح! 🌟",
                style = MaterialTheme.typography.titleLarge.copy(
                    fontWeight = FontWeight.Bold,
                    color = Color(0xFF15803D)
                )
            )

            Text(
                text = "تم خصم المبلغ وإضافته لحساب المشترك فوراً.",
                style = MaterialTheme.typography.bodyMedium.copy(color = Color.Gray),
                textAlign = TextAlign.Center
            )

            HorizontalDivider()

            Surface(
                color = Color(0xFFF8FAFC),
                shape = RoundedCornerShape(14.dp),
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(text = "رقم المرجع:", color = Color.Gray, fontSize = 13.sp)
                        Text(
                            text = transaction.referenceCode ?: transaction.id,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary,
                            fontSize = 13.sp
                        )
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(text = "المستلم:", color = Color.Gray, fontSize = 13.sp)
                        Text(
                            text = "${transaction.recipientName} (${transaction.recipientPhone})",
                            fontWeight = FontWeight.SemiBold,
                            fontSize = 13.sp
                        )
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(text = "المبلغ المحول:", color = Color.Gray, fontSize = 13.sp)
                        Text(
                            text = "${formatMoney(transaction.amount)} ر.ي",
                            fontWeight = FontWeight.Bold,
                            color = Color(0xFF16A34A),
                            fontSize = 15.sp
                        )
                    }
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween
                    ) {
                        Text(text = "تاريخ ووقت العملية:", color = Color.Gray, fontSize = 13.sp)
                        Text(
                            text = transaction.date,
                            color = Color.DarkGray,
                            fontSize = 12.sp
                        )
                    }
                }
            }

            Spacer(modifier = Modifier.height(8.dp))

            Button(
                onClick = onDone,
                modifier = Modifier
                    .fillMaxWidth()
                    .height(50.dp)
                    .testTag("transfer_done_button"),
                shape = RoundedCornerShape(14.dp),
                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
            ) {
                Text("العودة إلى الحساب والمحفظة", fontWeight = FontWeight.Bold, fontSize = 15.sp)
            }
        }
    }
}
