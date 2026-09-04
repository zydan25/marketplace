package com.example.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.SupportChatMessage
import com.example.data.model.SupportTicket

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SupportScreen(
    tickets: List<SupportTicket>,
    chatMessages: List<SupportChatMessage>,
    onBackClick: () -> Unit,
    onSendMessage: (String) -> Unit,
    onCreateTicket: (String, String, String) -> Unit
) {
    val context = LocalContext.current
    var selectedTab by remember { mutableStateOf(0) } // 0: Chat, 1: Tickets, 2: FAQ
    var messageText by remember { mutableStateOf("") }
    var showNewTicketDialog by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("الدعم الفني وخدمة العملاء", fontWeight = FontWeight.Bold) },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
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
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(Color(0xFFF7F8FA))
        ) {
            // Fast Contact Options Bar
            Surface(
                color = Color.White,
                shadowElevation = 1.dp
            ) {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(12.dp),
                    horizontalArrangement = Arrangement.SpaceEvenly
                ) {
                    ContactChannelButton(
                        icon = Icons.Default.Phone,
                        label = "اتصال هاتفي",
                        color = Color(0xFF0288D1),
                        onClick = {
                            val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:770123456"))
                            context.startActivity(intent)
                        }
                    )
                    ContactChannelButton(
                        icon = Icons.Default.Chat,
                        label = "واتساب الدعم",
                        color = Color(0xFF25D366),
                        onClick = {
                            val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://wa.me/967770123456"))
                            context.startActivity(intent)
                        }
                    )
                    ContactChannelButton(
                        icon = Icons.Default.Send,
                        label = "تيليجرام",
                        color = Color(0xFF0088CC),
                        onClick = {
                            val intent = Intent(Intent.ACTION_VIEW, Uri.parse("https://t.me/shopik_support"))
                            context.startActivity(intent)
                        }
                    )
                }
            }

            // Tab Selector
            TabRow(
                selectedTabIndex = selectedTab,
                containerColor = Color.White,
                contentColor = MaterialTheme.colorScheme.primary
            ) {
                Tab(
                    selected = selectedTab == 0,
                    onClick = { selectedTab = 0 },
                    text = { Text("المحادثة الفورية", fontWeight = FontWeight.Bold) },
                    icon = { Icon(Icons.Default.SupportAgent, contentDescription = null) }
                )
                Tab(
                    selected = selectedTab == 1,
                    onClick = { selectedTab = 1 },
                    text = { Text("التذاكر والشكاوى", fontWeight = FontWeight.Bold) },
                    icon = { Icon(Icons.Default.ConfirmationNumber, contentDescription = null) }
                )
                Tab(
                    selected = selectedTab == 2,
                    onClick = { selectedTab = 2 },
                    text = { Text("الأسئلة الشائعة", fontWeight = FontWeight.Bold) },
                    icon = { Icon(Icons.Default.HelpOutline, contentDescription = null) }
                )
            }

            when (selectedTab) {
                0 -> {
                    // Chat Tab
                    Column(modifier = Modifier.fillMaxSize()) {
                        LazyColumn(
                            modifier = Modifier
                                .weight(1f)
                                .padding(horizontal = 16.dp, vertical = 8.dp),
                            verticalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            items(chatMessages) { msg ->
                                SupportMessageBubble(msg = msg)
                            }
                        }

                        // Message Input
                        Surface(
                            color = Color.White,
                            shadowElevation = 8.dp
                        ) {
                            Row(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .padding(horizontal = 12.dp, vertical = 8.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(8.dp)
                            ) {
                                OutlinedTextField(
                                    value = messageText,
                                    onValueChange = { messageText = it },
                                    modifier = Modifier
                                        .weight(1f)
                                        .testTag("support_chat_input"),
                                    placeholder = { Text("اكتب رسالتك لخدمة العملاء...") },
                                    shape = RoundedCornerShape(24.dp),
                                    maxLines = 3
                                )

                                FilledIconButton(
                                    onClick = {
                                        if (messageText.isNotBlank()) {
                                            onSendMessage(messageText)
                                            messageText = ""
                                        }
                                    },
                                    modifier = Modifier.size(48.dp),
                                    colors = IconButtonDefaults.filledIconButtonColors(
                                        containerColor = MaterialTheme.colorScheme.primary
                                    )
                                ) {
                                    Icon(
                                        imageVector = Icons.AutoMirrored.Filled.Send,
                                        contentDescription = "إرسال",
                                        tint = Color.White
                                    )
                                }
                            }
                        }
                    }
                }

                1 -> {
                    // Tickets Tab
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        item {
                            Button(
                                onClick = { showNewTicketDialog = true },
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .height(46.dp),
                                shape = RoundedCornerShape(12.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = MaterialTheme.colorScheme.primary)
                            ) {
                                Icon(Icons.Default.Add, contentDescription = null)
                                Spacer(modifier = Modifier.width(8.dp))
                                Text("فتح تذكرة أو تقديم شكوى جديدة", fontWeight = FontWeight.Bold)
                            }
                        }

                        items(tickets) { ticket ->
                            Card(
                                modifier = Modifier.fillMaxWidth(),
                                shape = RoundedCornerShape(12.dp),
                                colors = CardDefaults.cardColors(containerColor = Color.White),
                                elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
                            ) {
                                Column(modifier = Modifier.padding(14.dp)) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Text(
                                            text = ticket.id,
                                            style = MaterialTheme.typography.labelSmall.copy(
                                                color = Color.Gray,
                                                fontWeight = FontWeight.Bold
                                            )
                                        )

                                        val statusColor = when (ticket.status) {
                                            "تم الرد" -> Color(0xFF15803D)
                                            "قيد المعالجة" -> Color(0xFFD97706)
                                            else -> Color.Gray
                                        }
                                        Surface(
                                            shape = RoundedCornerShape(12.dp),
                                            color = statusColor.copy(alpha = 0.15f)
                                        ) {
                                            Text(
                                                text = ticket.status,
                                                color = statusColor,
                                                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                                                modifier = Modifier.padding(horizontal = 8.dp, vertical = 2.dp)
                                            )
                                        }
                                    }

                                    Spacer(modifier = Modifier.height(6.dp))
                                    Text(
                                        text = ticket.subject,
                                        style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold)
                                    )
                                    Text(
                                        text = ticket.lastMessage,
                                        style = MaterialTheme.typography.bodySmall.copy(color = Color(0xFF475569))
                                    )

                                    Spacer(modifier = Modifier.height(8.dp))
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween
                                    ) {
                                        Text(
                                            text = "التصنيف: ${ticket.category}",
                                            style = MaterialTheme.typography.labelSmall.copy(color = MaterialTheme.colorScheme.primary)
                                        )
                                        Text(
                                            text = ticket.date,
                                            style = MaterialTheme.typography.labelSmall.copy(color = Color.Gray)
                                        )
                                    }
                                }
                            }
                        }
                    }
                }

                2 -> {
                    // FAQ Tab
                    LazyColumn(
                        modifier = Modifier
                            .fillMaxSize()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        item {
                            Text(
                                text = "الأسئلة الأكثر شيوعاً",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                            )
                        }

                        val faqs = listOf(
                            "كيف أقوم بتغذية رصيد محفظتي الإلكترونية؟" to "يمكنك تغذية رصيدك عن طريق التحويل عبر بنك الكريمي أو شبكات النجم والامتياز، أو بطلب كود سداد من شاشة الحساب وربطه فورياً.",
                            "ما هي مدة توصيل الطلبات في صنعاء والمحافظات؟" to "التوصيل داخل أمانة العاصمة صنعاء يتم خلال 30 إلى 60 دقيقة عبر مناديب شبيك، وإلى باقي المحافظات خلال 24 ساعة عبر شركات النقل المعتمدة.",
                            "هل المنتجات مكفولة بضمان استرجاع؟" to "نعم، جميع المنتجات المباعة عبر متاجر شبيك تتمتع بحماية المشتري وإمكانية الاسترجاع أو الاستبدال خلال 48 ساعة من استلام الشحنة في حال وجود أي عيب مصنعي.",
                            "كيف يمكنني سداد باقات يمن موبايل وسبأفون؟" to "من خلال تبويب 'شبكة سداد الاتصالات' في شاشة حسابي، يمكنك اختيار الشركة والباقة وسدادها برقم هاتفك بنقرة واحدة من رصيد المحفظة."
                        )

                        items(faqs) { (q, a) ->
                            var expanded by remember { mutableStateOf(false) }
                            Card(
                                modifier = Modifier
                                    .fillMaxWidth()
                                    .clickable { expanded = !expanded },
                                shape = RoundedCornerShape(12.dp),
                                colors = CardDefaults.cardColors(containerColor = Color.White)
                            ) {
                                Column(modifier = Modifier.padding(14.dp)) {
                                    Row(
                                        modifier = Modifier.fillMaxWidth(),
                                        horizontalArrangement = Arrangement.SpaceBetween,
                                        verticalAlignment = Alignment.CenterVertically
                                    ) {
                                        Text(
                                            text = q,
                                            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                                            modifier = Modifier.weight(1f)
                                        )
                                        Icon(
                                            imageVector = if (expanded) Icons.Default.ExpandLess else Icons.Default.ExpandMore,
                                            contentDescription = null,
                                            tint = Color.Gray
                                        )
                                    }
                                    if (expanded) {
                                        Spacer(modifier = Modifier.height(8.dp))
                                        HorizontalDivider(color = Color(0xFFF1F5F9))
                                        Spacer(modifier = Modifier.height(8.dp))
                                        Text(
                                            text = a,
                                            style = MaterialTheme.typography.bodySmall.copy(color = Color(0xFF475569), lineHeight = 20.sp)
                                        )
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    if (showNewTicketDialog) {
        var subject by remember { mutableStateOf("") }
        var category by remember { mutableStateOf("استفسار عن طلب") }
        var details by remember { mutableStateOf("") }

        AlertDialog(
            onDismissRequest = { showNewTicketDialog = false },
            title = { Text("فتح تذكرة دعم جديدة", fontWeight = FontWeight.Bold) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedTextField(
                        value = subject,
                        onValueChange = { subject = it },
                        label = { Text("عنوان التذكرة") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = category,
                        onValueChange = { category = it },
                        label = { Text("التصنيف (طلب، دفع، شحن، شكوى)") },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true
                    )
                    OutlinedTextField(
                        value = details,
                        onValueChange = { details = it },
                        label = { Text("تفاصيل المشكلة أو البلاغ") },
                        modifier = Modifier.fillMaxWidth(),
                        maxLines = 4
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        if (subject.isNotBlank() && details.isNotBlank()) {
                            onCreateTicket(subject, category, details)
                            showNewTicketDialog = false
                            selectedTab = 1
                        }
                    },
                    enabled = subject.isNotBlank() && details.isNotBlank()
                ) {
                    Text("إرسال التذكرة")
                }
            },
            dismissButton = {
                TextButton(onClick = { showNewTicketDialog = false }) {
                    Text("إلغاء")
                }
            }
        )
    }
}

@Composable
fun ContactChannelButton(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String,
    color: Color,
    onClick: () -> Unit
) {
    Column(
        horizontalAlignment = Alignment.CenterHorizontally,
        modifier = Modifier.clickable(onClick = onClick)
    ) {
        Box(
            modifier = Modifier
                .size(44.dp)
                .clip(CircleShape)
                .background(color.copy(alpha = 0.15f)),
            contentAlignment = Alignment.Center
        ) {
            Icon(
                imageVector = icon,
                contentDescription = label,
                tint = color,
                modifier = Modifier.size(22.dp)
            )
        }
        Spacer(modifier = Modifier.height(4.dp))
        Text(
            text = label,
            style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold)
        )
    }
}

@Composable
fun SupportMessageBubble(msg: SupportChatMessage) {
    val isUser = msg.isFromUser
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = if (isUser) Arrangement.Start else Arrangement.End
    ) {
        Card(
            shape = RoundedCornerShape(
                topStart = 14.dp,
                topEnd = 14.dp,
                bottomStart = if (isUser) 2.dp else 14.dp,
                bottomEnd = if (isUser) 14.dp else 2.dp
            ),
            colors = CardDefaults.cardColors(
                containerColor = if (isUser) Color(0xFF161618) else Color.White
            ),
            elevation = CardDefaults.cardElevation(defaultElevation = 1.dp),
            modifier = Modifier.widthIn(max = 290.dp)
        ) {
            Column(modifier = Modifier.padding(12.dp)) {
                Text(
                    text = msg.sender,
                    style = MaterialTheme.typography.labelSmall.copy(
                        fontWeight = FontWeight.Bold,
                        color = if (isUser) Color(0xFFFCA5A5) else MaterialTheme.colorScheme.primary
                    )
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = msg.message,
                    style = MaterialTheme.typography.bodyMedium.copy(
                        color = if (isUser) Color.White else Color(0xFF1E293B),
                        lineHeight = 20.sp
                    )
                )
                Spacer(modifier = Modifier.height(4.dp))
                Text(
                    text = msg.time,
                    style = MaterialTheme.typography.labelSmall.copy(
                        color = if (isUser) Color.LightGray else Color.Gray,
                        fontSize = 10.sp
                    ),
                    modifier = Modifier.align(Alignment.End)
                )
            }
        }
    }
}
