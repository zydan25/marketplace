package com.example.ui

import androidx.compose.animation.AnimatedVisibility
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
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.grid.GridCells
import androidx.compose.foundation.lazy.grid.LazyVerticalGrid
import androidx.compose.foundation.lazy.grid.items
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.Bolt
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.CreditCard
import androidx.compose.material.icons.filled.ElectricBolt
import androidx.compose.material.icons.filled.Language
import androidx.compose.material.icons.filled.LocalAtm
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.PhoneAndroid
import androidx.compose.material.icons.filled.Receipt
import androidx.compose.material.icons.filled.Router
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.SignalCellularAlt
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material.icons.filled.Subscriptions
import androidx.compose.material.icons.filled.WaterDrop
import androidx.compose.material.icons.filled.Wifi
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.FilterChipDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.TopAppBarDefaults
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.example.data.model.UserSession

data class DigitalServiceCategory(
    val id: String,
    val title: String,
    val icon: ImageVector,
    val color: Color
)

data class DigitalServiceItem(
    val id: String,
    val categoryId: String,
    val title: String,
    val subtitle: String,
    val icon: ImageVector,
    val color: Color,
    val badge: String? = null,
    val directAction: (() -> Unit)? = null
)

/**
 * واجهة الخدمات الرقمية وسداد الفواتير الشاملة
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ServicesScreen(
    userSession: UserSession,
    onBackClick: () -> Unit,
    onNavigateToNetworkCards: () -> Unit,
    onNavigateToGames: () -> Unit,
    onNavigateToPrograms: () -> Unit,
    formatMoney: (Double) -> String,
    onPayBill: (billName: String, amount: Double, accountNo: String) -> Unit = { _, _, _ -> },
    modifier: Modifier = Modifier
) {
    var searchQuery by remember { mutableStateOf("") }
    var selectedCategoryFilter by remember { mutableStateOf("الكل") }

    val categories = remember {
        listOf(
            DigitalServiceCategory("all", "الكل", Icons.Default.Receipt, Color(0xFF1E88E5)),
            DigitalServiceCategory("telecom", "شبكات واتصالات", Icons.Default.PhoneAndroid, Color(0xFFC62828)),
            DigitalServiceCategory("games", "ألعاب وبطاقات", Icons.Default.SportsEsports, Color(0xFFF57C00)),
            DigitalServiceCategory("programs", "برامج واشتراكات", Icons.Default.Subscriptions, Color(0xFF00C853)),
            DigitalServiceCategory("utilities", "كهرباء ومياه", Icons.Default.ElectricBolt, Color(0xFFFBC02D)),
            DigitalServiceCategory("finance", "محافظ وتحويلات", Icons.Default.AccountBalanceWallet, Color(0xFF6A1B9A))
        )
    }

    val services = remember {
        listOf(
            DigitalServiceItem(
                id = "s_network_cards",
                categoryId = "telecom",
                title = "كروت وباقات شبكات الاتصالات",
                subtitle = "يمن موبايل، يو، سبأفون، واي، يمن نت، شبكات وايفاي",
                icon = Icons.Default.CreditCard,
                color = Color(0xFFC62828),
                badge = "الواجهة الخاصة",
                directAction = onNavigateToNetworkCards
            ),
            DigitalServiceItem(
                id = "s_games",
                categoryId = "games",
                title = "شحن الألعاب الإلكترونية",
                subtitle = "ببجي موبايل، فري فاير، روبلوكس، كول أوف ديوتي، بيس",
                icon = Icons.Default.SportsEsports,
                color = Color(0xFFF57C00),
                badge = "شحن بالآيدي",
                directAction = onNavigateToGames
            ),
            DigitalServiceItem(
                id = "s_programs",
                categoryId = "programs",
                title = "البرامج والاشتراكات الرقمية",
                subtitle = "شاهد VIP، نتفليكس، كانفا برو، تيليجرام، ويندوز وأوفيس",
                icon = Icons.Default.Subscriptions,
                color = Color(0xFF00C853),
                badge = "اشتراكات أصلية",
                directAction = onNavigateToPrograms
            ),
            DigitalServiceItem(
                id = "s_yemen_net",
                categoryId = "telecom",
                title = "سداد فواتير يمن نت ADSL المنزلي",
                subtitle = "شحن الرصيد وتجديد الاشتراك برقم الهاتف الأرضي",
                icon = Icons.Default.Router,
                color = Color(0xFF00838F),
                badge = "فوري"
            ),
            DigitalServiceItem(
                id = "s_yemen_4g",
                categoryId = "telecom",
                title = "تجديد باقة يمن فورجي 4G",
                subtitle = "تجديد فوري لحسابات مودم يمن فورجي في جميع المحافظات",
                icon = Icons.Default.SignalCellularAlt,
                color = Color(0xFF00695C)
            ),
            DigitalServiceItem(
                id = "s_electricity",
                categoryId = "utilities",
                title = "سداد فواتير الكهرباء الحكومية والتجارية",
                subtitle = "تسديد كروت العدادات الذكية والفواتير الشهرية",
                icon = Icons.Default.ElectricBolt,
                color = Color(0xFFF57F17)
            ),
            DigitalServiceItem(
                id = "s_water",
                categoryId = "utilities",
                title = "سداد فواتير المؤسسة العامة للمياه",
                subtitle = "دفع فواتير استهلاك المياه والصرف الصحي",
                icon = Icons.Default.WaterDrop,
                color = Color(0xFF0288D1)
            ),
            DigitalServiceItem(
                id = "s_cash_transfer",
                categoryId = "finance",
                title = "شحن محفظة كاش وسحب فوري",
                subtitle = "تغذية الحساب عبر النجم، الامتياز، كاش، جيب، جوال",
                icon = Icons.Default.LocalAtm,
                color = Color(0xFF4A148C),
                badge = "عمولة 0%"
            )
        )
    }

    var selectedServiceForPay by remember { mutableStateOf<DigitalServiceItem?>(null) }
    var accountInput by remember { mutableStateOf("") }
    var amountInput by remember { mutableStateOf("") }
    var paySuccessMessage by remember { mutableStateOf<String?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "الخدمات وسداد الفواتير",
                        style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold)
                    )
                },
                navigationIcon = {
                    IconButton(onClick = onBackClick) {
                        Icon(imageVector = Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "رجوع")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.surface)
            )
        }
    ) { padding ->
        LazyColumn(
            modifier = modifier
                .fillMaxSize()
                .padding(padding),
            contentPadding = PaddingValues(bottom = 24.dp)
        ) {
            // Hero Top Banner
            item {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 10.dp)
                        .clip(RoundedCornerShape(16.dp))
                        .background(
                            Brush.linearGradient(
                                listOf(Color(0xFF0D47A1), Color(0xFF1976D2))
                            )
                        )
                        .padding(18.dp)
                ) {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(10.dp)
                        ) {
                            Icon(
                                imageVector = Icons.Default.AccountBalanceWallet,
                                contentDescription = null,
                                tint = Color.White,
                                modifier = Modifier.size(28.dp)
                            )
                            Text(
                                text = "منصة الخدمات الرقمية المتكاملة",
                                style = MaterialTheme.typography.titleLarge.copy(
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold
                                )
                            )
                        }
                        Text(
                            text = "سدد فواتيرك، اشحن كروت الشبكات، باقات الألعاب والبرامج في ثوانٍ معدودة وبأقل عمولة.",
                            style = MaterialTheme.typography.bodySmall.copy(color = Color.White.copy(alpha = 0.9f))
                        )
                    }
                }
            }

            // Search Bar
            item {
                OutlinedTextField(
                    value = searchQuery,
                    onValueChange = { searchQuery = it },
                    placeholder = { Text("ابحث عن خدمة، شبكة، لعبة، أو فاتورة...") },
                    leadingIcon = { Icon(imageVector = Icons.Default.Search, contentDescription = null) },
                    singleLine = true,
                    shape = RoundedCornerShape(12.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 6.dp)
                        .testTag("services_search_input")
                )
            }

            // Category Horizontal Filter
            item {
                LazyRow(
                    contentPadding = PaddingValues(horizontal = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp),
                    modifier = Modifier.padding(vertical = 6.dp)
                ) {
                    items(categories) { cat ->
                        val isSelected = (selectedCategoryFilter == cat.id || (selectedCategoryFilter == "الكل" && cat.id == "all"))
                        FilterChip(
                            selected = isSelected,
                            onClick = { selectedCategoryFilter = if (cat.id == "all") "الكل" else cat.id },
                            label = { Text(cat.title, fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal) },
                            leadingIcon = {
                                Icon(
                                    imageVector = cat.icon,
                                    contentDescription = null,
                                    modifier = Modifier.size(16.dp)
                                )
                            }
                        )
                    }
                }
            }

            // Featured Shortcuts Header
            item {
                Spacer(modifier = Modifier.height(10.dp))
                Text(
                    text = "الواجهات والخدمات الرئيسية:",
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp)
                )
            }

            // Quick Direct Cards (Network Cards, Games, Programs)
            item {
                Row(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    // Network Cards Quick Action
                    Card(
                        onClick = onNavigateToNetworkCards,
                        shape = RoundedCornerShape(14.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFC62828).copy(alpha = 0.1f)),
                        border = CardDefaults.outlinedCardBorder().copy(
                            brush = Brush.linearGradient(listOf(Color(0xFFC62828), Color(0xFFB71C1C)))
                        ),
                        modifier = Modifier
                            .weight(1f)
                            .testTag("quick_network_cards_btn")
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(44.dp)
                                    .clip(CircleShape)
                                    .background(Color(0xFFC62828)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.PhoneAndroid,
                                    contentDescription = null,
                                    tint = Color.White,
                                    modifier = Modifier.size(24.dp)
                                )
                            }
                            Text(
                                text = "كروت الشبكات",
                                style = MaterialTheme.typography.titleSmall.copy(
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFFC62828)
                                ),
                                textAlign = TextAlign.Center
                            )
                            Text(
                                text = "فئات وباقات كل الشبكات",
                                style = MaterialTheme.typography.labelSmall.copy(color = Color.Gray),
                                textAlign = TextAlign.Center
                            )
                        }
                    }

                    // Games Quick Action
                    Card(
                        onClick = onNavigateToGames,
                        shape = RoundedCornerShape(14.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFFF57C00).copy(alpha = 0.1f)),
                        border = CardDefaults.outlinedCardBorder().copy(
                            brush = Brush.linearGradient(listOf(Color(0xFFF57C00), Color(0xFFE65100)))
                        ),
                        modifier = Modifier
                            .weight(1f)
                            .testTag("quick_games_cards_btn")
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(44.dp)
                                    .clip(CircleShape)
                                    .background(Color(0xFFF57C00)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.SportsEsports,
                                    contentDescription = null,
                                    tint = Color.White,
                                    modifier = Modifier.size(24.dp)
                                )
                            }
                            Text(
                                text = "شحن الألعاب",
                                style = MaterialTheme.typography.titleSmall.copy(
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFFF57C00)
                                ),
                                textAlign = TextAlign.Center
                            )
                            Text(
                                text = "ببجي، فري فاير، روبلوكس",
                                style = MaterialTheme.typography.labelSmall.copy(color = Color.Gray),
                                textAlign = TextAlign.Center
                            )
                        }
                    }

                    // Programs Quick Action
                    Card(
                        onClick = onNavigateToPrograms,
                        shape = RoundedCornerShape(14.dp),
                        colors = CardDefaults.cardColors(containerColor = Color(0xFF00C853).copy(alpha = 0.1f)),
                        border = CardDefaults.outlinedCardBorder().copy(
                            brush = Brush.linearGradient(listOf(Color(0xFF00C853), Color(0xFF1B5E20)))
                        ),
                        modifier = Modifier
                            .weight(1f)
                            .testTag("quick_programs_cards_btn")
                    ) {
                        Column(
                            modifier = Modifier
                                .fillMaxWidth()
                                .padding(12.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(6.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(44.dp)
                                    .clip(CircleShape)
                                    .background(Color(0xFF00C853)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = Icons.Default.Subscriptions,
                                    contentDescription = null,
                                    tint = Color.White,
                                    modifier = Modifier.size(24.dp)
                                )
                            }
                            Text(
                                text = "البرامج الرقمية",
                                style = MaterialTheme.typography.titleSmall.copy(
                                    fontWeight = FontWeight.Bold,
                                    color = Color(0xFF00C853)
                                ),
                                textAlign = TextAlign.Center
                            )
                            Text(
                                text = "شاهد، نتفليكس، كانفا",
                                style = MaterialTheme.typography.labelSmall.copy(color = Color.Gray),
                                textAlign = TextAlign.Center
                            )
                        }
                    }
                }
            }

            // Services List
            val filteredServices = services.filter { s ->
                (selectedCategoryFilter == "الكل" || s.categoryId == selectedCategoryFilter) &&
                (searchQuery.isBlank() || s.title.contains(searchQuery, ignoreCase = true) || s.subtitle.contains(searchQuery, ignoreCase = true))
            }

            item {
                Spacer(modifier = Modifier.height(16.dp))
                Text(
                    text = "جميع الخدمات وسداد الفواتير المتاحة:",
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp)
                )
            }

            items(filteredServices) { s ->
                Card(
                    onClick = {
                        if (s.directAction != null) {
                            s.directAction.invoke()
                        } else {
                            selectedServiceForPay = s
                            accountInput = ""
                            amountInput = ""
                        }
                    },
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 6.dp)
                ) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(14.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(48.dp)
                                .clip(RoundedCornerShape(12.dp))
                                .background(s.color.copy(alpha = 0.12f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = s.icon,
                                contentDescription = null,
                                tint = s.color,
                                modifier = Modifier.size(26.dp)
                            )
                        }

                        Column(modifier = Modifier.weight(1f)) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                Text(
                                    text = s.title,
                                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                                )
                                s.badge?.let { b ->
                                    Surface(
                                        color = s.color.copy(alpha = 0.15f),
                                        shape = RoundedCornerShape(4.dp)
                                    ) {
                                        Text(
                                            text = b,
                                            style = MaterialTheme.typography.labelSmall.copy(
                                                color = s.color,
                                                fontWeight = FontWeight.Bold
                                            ),
                                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                        )
                                    }
                                }
                            }

                            Text(
                                text = s.subtitle,
                                style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.onSurfaceVariant)
                            )
                        }

                        Icon(
                            imageVector = Icons.AutoMirrored.Filled.ArrowForward,
                            contentDescription = null,
                            tint = Color.Gray,
                            modifier = Modifier.size(20.dp)
                        )
                    }
                }
            }
        }
    }

    // Direct Payment Dialog
    selectedServiceForPay?.let { service ->
        AlertDialog(
            onDismissRequest = { selectedServiceForPay = null },
            title = {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(imageVector = service.icon, contentDescription = null, tint = service.color)
                    Text(text = service.title, fontWeight = FontWeight.Bold)
                }
            },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text(
                        text = service.subtitle,
                        style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.onSurfaceVariant)
                    )

                    OutlinedTextField(
                        value = accountInput,
                        onValueChange = { accountInput = it },
                        label = { Text("رقم الحساب / العداد / الهاتف") },
                        placeholder = { Text("أدخل الرقم المسجل") },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    )

                    OutlinedTextField(
                        value = amountInput,
                        onValueChange = { amountInput = it },
                        label = { Text("المبلغ المراد سداده (بالريال اليمني)") },
                        placeholder = { Text("مثال: 2000") },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    )

                    Text(
                        text = "يتم السداد المباشر وخصم المبلغ من محفظتك الإلكترونية مع إشعار رسمي فوري.",
                        style = MaterialTheme.typography.labelSmall.copy(color = Color.Gray)
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val amt = amountInput.toDoubleOrNull() ?: 1000.0
                        onPayBill(service.title, amt, accountInput.ifBlank { "000" })
                        paySuccessMessage = "تم سداد ${service.title} بمبلغ ${formatMoney(amt)} ريال يمني بنجاح!"
                        selectedServiceForPay = null
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = service.color)
                ) {
                    Text("سداد فوري", fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { selectedServiceForPay = null }) {
                    Text("إلغاء")
                }
            }
        )
    }

    // Success dialog
    paySuccessMessage?.let { msg ->
        AlertDialog(
            onDismissRequest = { paySuccessMessage = null },
            title = {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(imageVector = Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF2E7D32))
                    Text("تمت العملية بنجاح", fontWeight = FontWeight.Bold)
                }
            },
            text = {
                Text(msg)
            },
            confirmButton = {
                Button(onClick = { paySuccessMessage = null }) {
                    Text("حسناً")
                }
            }
        )
    }
}
