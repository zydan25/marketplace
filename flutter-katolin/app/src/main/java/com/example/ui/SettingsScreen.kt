package com.example.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.CurrencyRate
import com.example.data.model.UserSession

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(
    userSession: UserSession,
    selectedCurrency: String,
    currencyRates: List<CurrencyRate>,
    notificationsEnabled: Boolean,
    onBackClick: () -> Unit,
    onCurrencyChange: (String) -> Unit,
    onNotificationsToggle: (Boolean) -> Unit,
    onOpenAddresses: () -> Unit,
    onOpenWallet: () -> Unit,
    onOpenDjangoSettings: () -> Unit
) {
    var showPrivacyDialog by remember { mutableStateOf(false) }
    var showTermsDialog by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("الإعدادات العامة", fontWeight = FontWeight.Bold) },
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
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            // Account Section
            Text(
                text = "الحساب والبيانات",
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold, color = Color.Gray)
            )

            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Column {
                    SettingsItemRow(
                        icon = Icons.Default.Person,
                        title = "الملف الشخصي",
                        subtitle = if (userSession.isLoggedIn) userSession.fullName + " (${userSession.phone})" else "زائر غير مسجل",
                        onClick = {}
                    )
                    HorizontalDivider(color = Color(0xFFF1F5F9))
                    SettingsItemRow(
                        icon = Icons.Default.LocationOn,
                        title = "دفتر العناوين والتوصيل",
                        subtitle = "إدارة عناوين التوصيل والمناطق",
                        onClick = onOpenAddresses
                    )
                    HorizontalDivider(color = Color(0xFFF1F5F9))
                    SettingsItemRow(
                        icon = Icons.Default.AccountBalanceWallet,
                        title = "محفظة جيب الإلكترونية",
                        subtitle = "الرصيد والمعاملات والسحب",
                        onClick = onOpenWallet
                    )
                }
            }

            // Currency & Conversion Rates
            Text(
                text = "العملة وأسعار الصرف المعتمدة",
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold, color = Color.Gray)
            )

            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Column(modifier = Modifier.padding(14.dp)) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.CurrencyExchange,
                                contentDescription = null,
                                tint = MaterialTheme.colorScheme.primary
                            )
                            Text("العملة المعتمدة للعرض", fontWeight = FontWeight.Bold)
                        }

                        // Cycle Currency
                        Surface(
                            shape = RoundedCornerShape(8.dp),
                            color = MaterialTheme.colorScheme.primaryContainer,
                            modifier = Modifier.clickable {
                                val next = when (selectedCurrency) {
                                    "YER" -> "SAR"
                                    "SAR" -> "USD"
                                    else -> "YER"
                                }
                                onCurrencyChange(next)
                            }
                        ) {
                            Text(
                                text = when (selectedCurrency) {
                                    "YER" -> "ريال يمني (YER)"
                                    "SAR" -> "ريال سعودي (SAR)"
                                    else -> "دولار أمريكي (USD)"
                                },
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                style = MaterialTheme.typography.labelMedium.copy(
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary
                                )
                            )
                        }
                    }

                    Spacer(modifier = Modifier.height(12.dp))
                    Text(
                        text = "أسعار التحويل المعتمدة في النظام:",
                        style = MaterialTheme.typography.labelSmall.copy(color = Color.Gray)
                    )
                    Spacer(modifier = Modifier.height(6.dp))

                    currencyRates.forEach { rate ->
                        Surface(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(vertical = 3.dp),
                            shape = RoundedCornerShape(8.dp),
                            color = Color(0xFFF8FAFC)
                        ) {
                            Row(
                                modifier = Modifier.padding(horizontal = 10.dp, vertical = 8.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = "${rate.baseCurrency} → ${rate.targetCurrency}",
                                    style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Bold)
                                )
                                Text(
                                    text = rate.rate,
                                    style = MaterialTheme.typography.bodySmall.copy(
                                        color = MaterialTheme.colorScheme.primary,
                                        fontWeight = FontWeight.SemiBold
                                    )
                                )
                            }
                        }
                    }
                }
            }

            // Notifications & Server
            Text(
                text = "الإشعارات والخادم",
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold, color = Color.Gray)
            )

            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Column {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(14.dp),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
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
                            Column {
                                Text("إشعارات الطلبات والعروض", fontWeight = FontWeight.Bold)
                                Text("تنبيهات حالة الطلب وأخبار الحساب", fontSize = 11.sp, color = Color.Gray)
                            }
                        }

                        Switch(
                            checked = notificationsEnabled,
                            onCheckedChange = onNotificationsToggle,
                            modifier = Modifier.testTag("notifications_toggle")
                        )
                    }

                    HorizontalDivider(color = Color(0xFFF1F5F9))

                    SettingsItemRow(
                        icon = Icons.Default.Dns,
                        title = "خادم جانغو (Django API)",
                        subtitle = "فحص الاتصال وتعديل الرابط الحي",
                        onClick = onOpenDjangoSettings
                    )
                }
            }

            // Legal & Info
            Text(
                text = "الشروط والسياسات",
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold, color = Color.Gray)
            )

            Card(
                shape = RoundedCornerShape(14.dp),
                colors = CardDefaults.cardColors(containerColor = Color.White)
            ) {
                Column {
                    SettingsItemRow(
                        icon = Icons.Default.PrivacyTip,
                        title = "سياسة الخصوصية",
                        subtitle = "حماية بيانات الحساب والمعاملات",
                        onClick = { showPrivacyDialog = true }
                    )
                    HorizontalDivider(color = Color(0xFFF1F5F9))
                    SettingsItemRow(
                        icon = Icons.Default.Gavel,
                        title = "الشروط والأحكام",
                        subtitle = "سياسة الاسترجاع والضمان والشحن",
                        onClick = { showTermsDialog = true }
                    )
                }
            }

            // Version Label
            Box(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(vertical = 14.dp),
                contentAlignment = Alignment.Center
            ) {
                Text(
                    text = "شبيك · سوق بلس · إصدار 1.0.0",
                    style = MaterialTheme.typography.labelSmall.copy(color = Color.Gray)
                )
            }
        }
    }

    if (showPrivacyDialog) {
        AlertDialog(
            onDismissRequest = { showPrivacyDialog = false },
            title = { Text("سياسة الخصوصية", fontWeight = FontWeight.Bold) },
            text = {
                Text("يلتزم متجر شبيك وسوق بلس بحماية خصوصية وأمان جميع المستخدمين. بياناتك الشخصية وأرقام هواتفك ومعاملاتك المالية محمية بتشفير عالي ومخصصة حصراً لإتمام الطلبات وسداد الخدمات بأمان.")
            },
            confirmButton = {
                TextButton(onClick = { showPrivacyDialog = false }) {
                    Text("حسناً")
                }
            }
        )
    }

    if (showTermsDialog) {
        AlertDialog(
            onDismissRequest = { showTermsDialog = false },
            title = { Text("الشروط والأحكام", fontWeight = FontWeight.Bold) },
            text = {
                Text("تضمن منصة شبيك حقوق المشتري والتاجر بالكامل. يمكن استبدال أو استرجاع أي منتج به عيب مصنعي خلال 48 ساعة من الاستلام. تخضع المبيعات لأسعار الصرف الرسمية المعلنة في المنصة.")
            },
            confirmButton = {
                TextButton(onClick = { showTermsDialog = false }) {
                    Text("موافق")
                }
            }
        )
    }
}

@Composable
fun SettingsItemRow(
    icon: ImageVector,
    title: String,
    subtitle: String,
    onClick: () -> Unit
) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onClick)
            .padding(14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Row(
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Icon(
                imageVector = icon,
                contentDescription = null,
                tint = MaterialTheme.colorScheme.primary,
                modifier = Modifier.size(22.dp)
            )
            Column {
                Text(
                    text = title,
                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold)
                )
                Text(
                    text = subtitle,
                    style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray, fontSize = 11.sp)
                )
            }
        }

        Icon(
            imageVector = Icons.Default.ChevronLeft,
            contentDescription = null,
            tint = Color.LightGray
        )
    }
}
