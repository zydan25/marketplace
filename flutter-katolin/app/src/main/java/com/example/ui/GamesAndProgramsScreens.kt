package com.example.ui

import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Diamond
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Movie
import androidx.compose.material.icons.filled.Person
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.SportsEsports
import androidx.compose.material.icons.filled.Star
import androidx.compose.material.icons.filled.Subscriptions
import androidx.compose.material.icons.filled.Verified
import androidx.compose.material.icons.filled.Work
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

data class GameItem(
    val id: String,
    val name: String,
    val category: String,
    val primaryColor: Color,
    val icon: ImageVector,
    val idPlaceholder: String,
    val packages: List<GamePackage>
)

data class GamePackage(
    val id: String,
    val title: String,
    val subtitle: String,
    val priceYer: Double,
    val tag: String? = null
)

/**
 * واجهة شحن الألعاب الرقمية
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun GamesScreen(
    userSession: UserSession,
    onBackClick: () -> Unit,
    formatMoney: (Double) -> String,
    onRechargeGame: (gameName: String, packName: String, price: Double, playerId: String) -> Unit = { _, _, _, _ -> },
    modifier: Modifier = Modifier
) {
    val games = remember {
        listOf(
            GameItem(
                id = "pubg",
                name = "ببجي موبايل (PUBG Mobile)",
                category = "ألعاب باتل رويال",
                primaryColor = Color(0xFFF57C00),
                icon = Icons.Default.SportsEsports,
                idPlaceholder = "أدخل الـ Player ID الخاص باللاعب",
                packages = listOf(
                    GamePackage("p1", "60 شدة UC", "شحن فوري بالآيدي", 750.0),
                    GamePackage("p2", "325 شدة UC + 25 مجاناً", "باقة التوفير الشعبية", 3800.0, "شائع"),
                    GamePackage("p3", "660 شدة UC", "تكفي لفتح الرويال باس RP", 7600.0, "الأكثر طلباً"),
                    GamePackage("p4", "1800 شدة UC", "شحن رسمي مباشر في الحساب", 20500.0),
                    GamePackage("p5", "3850 شدة UC", "حزمة الجولد الملكية", 43000.0, "عرض حصري")
                )
            ),
            GameItem(
                id = "freefire",
                name = "فري فاير (Free Fire)",
                category = "ألعاب باتل رويال",
                primaryColor = Color(0xFFD32F2F),
                icon = Icons.Default.Diamond,
                idPlaceholder = "أدخل الـ ID للاعب فري فاير",
                packages = listOf(
                    GamePackage("ff1", "100+10 جوهرة Diamonds", "شحن فوري بالمعرف", 800.0),
                    GamePackage("ff2", "310+31 جوهرة Diamonds", "باقة السيزون الجديد", 2400.0, "الأكثر مبيعاً"),
                    GamePackage("ff3", "520+52 جوهرة Diamonds", "شحن معتمد ورسمي", 3900.0),
                    GamePackage("ff4", "1060+106 جوهرة Diamonds", "عرض الأبطال", 7800.0),
                    GamePackage("ff5", "بطاقة العضوية الأسبوعية", "جواهر يومية مستمرة", 1500.0)
                )
            ),
            GameItem(
                id = "roblox",
                name = "روبلوكس (Roblox Robux)",
                category = "عوالم ومغامرات",
                primaryColor = Color(0xFF1976D2),
                icon = Icons.Default.SportsEsports,
                idPlaceholder = "اسم المستخدم في روبلوكس (Username)",
                packages = listOf(
                    GamePackage("rb1", "400 Robux", "كود رقمي فوري", 3500.0),
                    GamePackage("rb2", "800 Robux", "بطاقة شحن رقمية", 6900.0, "الأفضل قيمة"),
                    GamePackage("rb3", "1,700 Robux", "شحن رصيد رسمي", 13800.0),
                    GamePackage("rb4", "4,500 Robux", "باقة كبار اللاعبين", 35000.0)
                )
            ),
            GameItem(
                id = "cod",
                name = "كول أوف ديوتي (Call of Duty Mobile)",
                category = "ألعاب تصويب حربية",
                primaryColor = Color(0xFF388E3C),
                icon = Icons.Default.SportsEsports,
                idPlaceholder = "أدخل Player ID أو UID",
                packages = listOf(
                    GamePackage("cod1", "80 CP", "شحن نقاط فوري", 850.0),
                    GamePackage("cod2", "420 CP", "باقة الباتل باس", 4200.0, "الأكثر طلباً"),
                    GamePackage("cod3", "880 CP", "شحن رسمي في اللعبة", 8500.0),
                    GamePackage("cod4", "2,400 CP", "حزمة الأسلحة الملحمية", 22000.0)
                )
            ),
            GameItem(
                id = "pes",
                name = "إي فوتبول بيس (eFootball PES)",
                category = "ألعاب رياضية وكرة قدم",
                primaryColor = Color(0xFF0097A7),
                icon = Icons.Default.SportsEsports,
                idPlaceholder = "أدخل Konami ID أو User ID",
                packages = listOf(
                    GamePackage("pes1", "300 Coins", "كوينز فوري للباكات", 2100.0),
                    GamePackage("pes2", "1,050 Coins", "باقة نجوم الأسبوع", 7200.0, "شائع"),
                    GamePackage("pes3", "2,130 Coins", "كوينز بطاقات الأساطير", 14500.0)
                )
            ),
            GameItem(
                id = "psn",
                name = "بلايستيشن ستور (PlayStation Store)",
                category = "بطاقات كونسول",
                primaryColor = Color(0xFF0D47A1),
                icon = Icons.Default.SportsEsports,
                idPlaceholder = "رقم هاتف استلام الكود الرقمي",
                packages = listOf(
                    GamePackage("ps1", "بطاقة 10$ ستور سعودي / أمريكي", "كود رقمي رسمي", 7500.0),
                    GamePackage("ps2", "بطاقة 20$ ستور سعودي / أمريكي", "كود فوري معتمد", 14800.0),
                    GamePackage("ps3", "بطاقة 50$ ستور سعودي / أمريكي", "شحن المحفظة فوراً", 36500.0),
                    GamePackage("ps4", "اشتراك PlayStation Plus شهر", "عضوية أونلاين", 6900.0)
                )
            )
        )
    }

    var selectedGame by remember { mutableStateOf(games[0]) }
    var playerIdInput by remember { mutableStateOf("") }
    var isVerified by remember { mutableStateOf(false) }
    var verifiedPlayerName by remember { mutableStateOf<String?>(null) }
    var selectedPackageToBuy by remember { mutableStateOf<GamePackage?>(null) }
    var purchaseSuccessData by remember { mutableStateOf<Pair<GamePackage, String>?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "شحن الألعاب الإلكترونية",
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
            // Hero banner
            item {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 10.dp)
                        .clip(RoundedCornerShape(16.dp))
                        .background(
                            Brush.horizontalGradient(
                                listOf(selectedGame.primaryColor, selectedGame.primaryColor.copy(alpha = 0.7f))
                            )
                        )
                        .padding(18.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(14.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(56.dp)
                                .clip(CircleShape)
                                .background(Color.White.copy(alpha = 0.25f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = selectedGame.icon,
                                contentDescription = null,
                                tint = Color.White,
                                modifier = Modifier.size(34.dp)
                            )
                        }

                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = selectedGame.name,
                                style = MaterialTheme.typography.titleLarge.copy(
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold
                                )
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = "شحن فوري بالمعرف ID خلال ثوانٍ ومباشرة في حسابك",
                                style = MaterialTheme.typography.bodySmall.copy(color = Color.White.copy(alpha = 0.9f))
                            )
                        }
                    }
                }
            }

            // Game Selector
            item {
                Text(
                    text = "اختر اللعبة:",
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp)
                )

                LazyRow(
                    contentPadding = PaddingValues(horizontal = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    items(games) { game ->
                        val isSelected = (game.id == selectedGame.id)
                        Card(
                            onClick = {
                                selectedGame = game
                                isVerified = false
                                verifiedPlayerName = null
                            },
                            shape = RoundedCornerShape(12.dp),
                            colors = CardDefaults.cardColors(
                                containerColor = if (isSelected) game.primaryColor.copy(alpha = 0.12f) else MaterialTheme.colorScheme.surface
                            ),
                            border = CardDefaults.outlinedCardBorder().copy(
                                brush = Brush.linearGradient(
                                    if (isSelected) listOf(game.primaryColor, game.primaryColor)
                                    else listOf(Color.LightGray.copy(alpha = 0.5f), Color.LightGray.copy(alpha = 0.5f))
                                )
                            ),
                            modifier = Modifier
                                .width(140.dp)
                                .testTag("game_chip_${game.id}")
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
                                        .size(38.dp)
                                        .clip(CircleShape)
                                        .background(if (isSelected) game.primaryColor else Color.LightGray.copy(alpha = 0.3f)),
                                    contentAlignment = Alignment.Center
                                ) {
                                    Icon(
                                        imageVector = game.icon,
                                        contentDescription = null,
                                        tint = if (isSelected) Color.White else Color.DarkGray,
                                        modifier = Modifier.size(22.dp)
                                    )
                                }
                                Text(
                                    text = game.name.substringBefore("(").trim(),
                                    style = MaterialTheme.typography.labelMedium.copy(
                                        fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal,
                                        color = if (isSelected) game.primaryColor else MaterialTheme.colorScheme.onSurface
                                    ),
                                    textAlign = TextAlign.Center,
                                    maxLines = 1
                                )
                            }
                        }
                    }
                }
            }

            // Player ID input section
            item {
                Spacer(modifier = Modifier.height(14.dp))
                Card(
                    shape = RoundedCornerShape(14.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(14.dp),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        Text(
                            text = "بيانات حساب اللاعب:",
                            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                        )

                        Row(
                            modifier = Modifier.fillMaxWidth(),
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            OutlinedTextField(
                                value = playerIdInput,
                                onValueChange = {
                                    playerIdInput = it
                                    isVerified = false
                                    verifiedPlayerName = null
                                },
                                placeholder = { Text(selectedGame.idPlaceholder) },
                                leadingIcon = {
                                    Icon(imageVector = Icons.Default.Person, contentDescription = null)
                                },
                                singleLine = true,
                                shape = RoundedCornerShape(10.dp),
                                modifier = Modifier
                                    .weight(1f)
                                    .testTag("game_player_id_input")
                            )

                            Button(
                                onClick = {
                                    if (playerIdInput.isNotBlank()) {
                                        isVerified = true
                                        verifiedPlayerName = "لاعب شبيك ${playerIdInput.takeLast(4)}"
                                    }
                                },
                                shape = RoundedCornerShape(10.dp),
                                colors = ButtonDefaults.buttonColors(containerColor = selectedGame.primaryColor)
                            ) {
                                Text("تحقق")
                            }
                        }

                        if (isVerified && verifiedPlayerName != null) {
                            Surface(
                                color = Color(0xFFE8F5E9),
                                shape = RoundedCornerShape(8.dp),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Row(
                                    modifier = Modifier.padding(10.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    Icon(
                                        imageVector = Icons.Default.Verified,
                                        contentDescription = null,
                                        tint = Color(0xFF2E7D32)
                                    )
                                    Text(
                                        text = "تم التحقق: الحساب ($verifiedPlayerName) صالح للشحن الفوري",
                                        style = MaterialTheme.typography.bodySmall.copy(
                                            color = Color(0xFF1B5E20),
                                            fontWeight = FontWeight.Bold
                                        )
                                    )
                                }
                            }
                        }
                    }
                }
            }

            // Packages list
            item {
                Spacer(modifier = Modifier.height(14.dp))
                Text(
                    text = "اختر باقة الشحن:",
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)
                )
            }

            items(selectedGame.packages) { pkg ->
                Card(
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
                                .size(46.dp)
                                .clip(RoundedCornerShape(10.dp))
                                .background(selectedGame.primaryColor.copy(alpha = 0.12f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = selectedGame.icon,
                                contentDescription = null,
                                tint = selectedGame.primaryColor,
                                modifier = Modifier.size(26.dp)
                            )
                        }

                        Column(modifier = Modifier.weight(1f)) {
                            Row(
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                Text(
                                    text = pkg.title,
                                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                                )
                                pkg.tag?.let { t ->
                                    Surface(
                                        color = Color(0xFFFFF3E0),
                                        shape = RoundedCornerShape(4.dp)
                                    ) {
                                        Text(
                                            text = t,
                                            style = MaterialTheme.typography.labelSmall.copy(
                                                color = Color(0xFFE65100),
                                                fontWeight = FontWeight.Bold
                                            ),
                                            modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                        )
                                    }
                                }
                            }

                            Text(
                                text = pkg.subtitle,
                                style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.onSurfaceVariant)
                            )

                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "${formatMoney(pkg.priceYer)} ر.ي",
                                style = MaterialTheme.typography.titleMedium.copy(
                                    color = MaterialTheme.colorScheme.primary,
                                    fontWeight = FontWeight.Bold
                                )
                            )
                        }

                        Button(
                            onClick = {
                                selectedPackageToBuy = pkg
                            },
                            shape = RoundedCornerShape(10.dp),
                            colors = ButtonDefaults.buttonColors(containerColor = selectedGame.primaryColor)
                        ) {
                            Text("شحن فوري", fontWeight = FontWeight.Bold)
                        }
                    }
                }
            }
        }
    }

    // Recharge Confirm Dialog
    selectedPackageToBuy?.let { pkg ->
        AlertDialog(
            onDismissRequest = { selectedPackageToBuy = null },
            title = {
                Text(text = "تأكيد شحن ${pkg.title}", fontWeight = FontWeight.Bold)
            },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(text = "اللعبة: ${selectedGame.name}")
                    Text(text = "المعرف ID: ${playerIdInput.ifBlank { "لم يُدخل (سيتم إرسال كود)" }}")
                    Text(
                        text = "المبلغ الإجمالي: ${formatMoney(pkg.priceYer)} ريال يمني",
                        style = MaterialTheme.typography.titleMedium.copy(
                            color = MaterialTheme.colorScheme.primary,
                            fontWeight = FontWeight.Bold
                        )
                    )
                    Text(
                        text = "يتم الشحن فوراً وتصلك رسالة تأكيد في الحساب.",
                        style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray)
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val transId = "GAME-${(10000..99999).random()}"
                        onRechargeGame(selectedGame.name, pkg.title, pkg.priceYer, playerIdInput.ifBlank { "ID-12345" })
                        purchaseSuccessData = Pair(pkg, transId)
                        selectedPackageToBuy = null
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = selectedGame.primaryColor)
                ) {
                    Text("تأكيد وخصم من الرصيد", fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { selectedPackageToBuy = null }) {
                    Text("إلغاء")
                }
            }
        )
    }

    // Success Dialog
    purchaseSuccessData?.let { (pkg, transId) ->
        AlertDialog(
            onDismissRequest = { purchaseSuccessData = null },
            title = {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(imageVector = Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF2E7D32))
                    Text("تم الشحن بنجاح", fontWeight = FontWeight.Bold)
                }
            },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text("تم إرسال ${pkg.title} بنجاح إلى حسابك في ${selectedGame.name}!")
                    Text("رقم العملية: $transId", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                }
            },
            confirmButton = {
                Button(onClick = { purchaseSuccessData = null }) {
                    Text("تم")
                }
            }
        )
    }
}

data class ProgramItem(
    val id: String,
    val name: String,
    val category: String,
    val primaryColor: Color,
    val icon: ImageVector,
    val description: String,
    val plans: List<ProgramPlan>
)

data class ProgramPlan(
    val id: String,
    val duration: String,
    val details: String,
    val priceYer: Double,
    val isPopular: Boolean = false
)

/**
 * واجهة البرامج والاشتراكات الرقمية
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProgramsScreen(
    userSession: UserSession,
    onBackClick: () -> Unit,
    formatMoney: (Double) -> String,
    onPurchaseProgram: (programName: String, planName: String, price: Double, emailOrPhone: String) -> Unit = { _, _, _, _ -> },
    modifier: Modifier = Modifier
) {
    val programs = remember {
        listOf(
            ProgramItem(
                id = "shahid",
                name = "شاهد VIP (Shahid VIP)",
                category = "بث وترفيه",
                primaryColor = Color(0xFF00C853),
                icon = Icons.Default.Movie,
                description = "مسلسلات حصرية وأفلام وعروض رياضية مباشرة بدقة 4K",
                plans = listOf(
                    ProgramPlan("sh1", "اشتراك شهر واحد VIP", "حساب كامل بدون إعلانات", 3200.0),
                    ProgramPlan("sh2", "اشتراك 3 أشهر VIP", "باقة التوفير مع الرياضة", 8900.0, true),
                    ProgramPlan("sh3", "اشتراك سنة كاملة VIP", "أعلى توفير للمنزل", 29000.0)
                )
            ),
            ProgramItem(
                id = "netflix",
                name = "نتفليكس (Netflix)",
                category = "بث وترفيه",
                primaryColor = Color(0xFFE50914),
                icon = Icons.Default.Movie,
                description = "أفلام ومسلسلات عالمية مع ترجمة عربية وجودة فائقة Ultra HD",
                plans = listOf(
                    ProgramPlan("nf1", "اشتراك شهر ملف شخصي خاص", "جودة 4K UHD برقم سري خاص", 3500.0, true),
                    ProgramPlan("nf2", "حساب كامل 4 شاشات شهر", "شاشات متعددة لجميع العائلة", 11500.0),
                    ProgramPlan("nf3", "بطاقة نتفليكس 25$", "رقمية أصلية لشحن حسابك", 18500.0)
                )
            ),
            ProgramItem(
                id = "canva",
                name = "كانفا برو (Canva Pro)",
                category = "تصميم وإنتاجية",
                primaryColor = Color(0xFF00C4CC),
                icon = Icons.Default.Work,
                description = "قوالب تصميم احترافية وملايين الصور وإزالة الخلفيات بالذكاء الاصطناعي",
                plans = listOf(
                    ProgramPlan("cn1", "اشتراك سنوي رسمي بالبريد", "تفعيل مباشر على إيميلك الشخصي", 4500.0, true),
                    ProgramPlan("cn2", "اشتراك مدى الحياة فريقي", "وصول دائم لجميع أدوات Canva Pro", 8500.0)
                )
            ),
            ProgramItem(
                id = "telegram",
                name = "تيليجرام بريميوم (Telegram Premium)",
                category = "تواصل ومراسلة",
                primaryColor = Color(0xFF24A1DE),
                icon = Icons.Default.Star,
                description = "سرعات تحميل مضاعفة وتحويل الصوت لنص ورموز تعبيرية حصرية",
                plans = listOf(
                    ProgramPlan("tg1", "اشتراك 3 أشهر", "تفعيل فوري برقم التيليجرام", 4900.0),
                    ProgramPlan("tg2", "اشتراك 6 أشهر", "خصم 20% إضافي", 9200.0, true),
                    ProgramPlan("tg3", "اشتراك سنة كاملة", "أفضل عرض سنوي مميز", 16500.0)
                )
            ),
            ProgramItem(
                id = "youtube",
                name = "يوتيوب بريميوم (YouTube Premium)",
                category = "فيديو وموسيقى",
                primaryColor = Color(0xFFFF0000),
                icon = Icons.Default.Subscriptions,
                description = "تشغيل بالخلفية بدون أي إعلانات مع خدمة YouTube Music مجاناً",
                plans = listOf(
                    ProgramPlan("yt1", "اشتراك شهر", "تفعيل على حساب جوجل الشخصي", 1800.0),
                    ProgramPlan("yt2", "اشتراك 6 أشهر", "توفير واستقرار دائم", 9500.0, true),
                    ProgramPlan("yt3", "اشتراك سنوي", "سنة كاملة بدون إعلانات", 18000.0)
                )
            ),
            ProgramItem(
                id = "windows_office",
                name = "ويندوز وأوفيس (Windows & Office)",
                category = "أنظمة وبرامج",
                primaryColor = Color(0xFF0078D7),
                icon = Icons.Default.Security,
                description = "مفاتيح تنشيط أصلية معتمدة من مايكروسوفت مدى الحياة",
                plans = listOf(
                    ProgramPlan("ms1", "Windows 11 Pro كود أصلي", "تنشيط دائم مدى الحياة", 4500.0, true),
                    ProgramPlan("ms2", "Office 2021 Pro Plus كود أصلي", "وورد وإكسل وبوربوينت كامل", 6500.0),
                    ProgramPlan("ms3", "اشتراك Microsoft 365 سنة", "مع مساحة 1 تيرابايت OneDrive", 12000.0)
                )
            )
        )
    }

    var selectedCategoryFilter by remember { mutableStateOf("الكل") }
    val categories = listOf("الكل", "بث وترفيه", "تصميم وإنتاجية", "تواصل ومراسلة", "فيديو وموسيقى", "أنظمة وبرامج")

    var selectedProgramToBuy by remember { mutableStateOf<Pair<ProgramItem, ProgramPlan>?>(null) }
    var userEmailOrPhone by remember { mutableStateOf(if (userSession.isLoggedIn) userSession.phone else "") }
    var generatedProgramLicense by remember { mutableStateOf<Pair<String, String>?>(null) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = {
                    Text(
                        text = "البرامج والاشتراكات الرقمية",
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
            // Header Banner
            item {
                Box(
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 10.dp)
                        .clip(RoundedCornerShape(16.dp))
                        .background(
                            Brush.linearGradient(
                                listOf(Color(0xFF1E88E5), Color(0xFF1565C0))
                            )
                        )
                        .padding(18.dp)
                ) {
                    Row(
                        modifier = Modifier.fillMaxWidth(),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(14.dp)
                    ) {
                        Box(
                            modifier = Modifier
                                .size(56.dp)
                                .clip(CircleShape)
                                .background(Color.White.copy(alpha = 0.2f)),
                            contentAlignment = Alignment.Center
                        ) {
                            Icon(
                                imageVector = Icons.Default.Subscriptions,
                                contentDescription = null,
                                tint = Color.White,
                                modifier = Modifier.size(32.dp)
                            )
                        }

                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                text = "اشتراكات أصلية ومضمونة 100%",
                                style = MaterialTheme.typography.titleLarge.copy(
                                    color = Color.White,
                                    fontWeight = FontWeight.Bold
                                )
                            )
                            Spacer(modifier = Modifier.height(2.dp))
                            Text(
                                text = "تفعيل فوري بالبريد أو بالكود الرقمي لجميع المنصات العالمية",
                                style = MaterialTheme.typography.bodySmall.copy(color = Color.White.copy(alpha = 0.9f))
                            )
                        }
                    }
                }
            }

            // Category filter chips
            item {
                LazyRow(
                    contentPadding = PaddingValues(horizontal = 16.dp),
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    items(categories) { cat ->
                        val isSelected = (selectedCategoryFilter == cat)
                        FilterChip(
                            selected = isSelected,
                            onClick = { selectedCategoryFilter = cat },
                            label = { Text(cat, fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Normal) }
                        )
                    }
                }
            }

            val filteredPrograms = programs.filter {
                selectedCategoryFilter == "الكل" || it.category == selectedCategoryFilter
            }

            items(filteredPrograms) { prog ->
                Card(
                    shape = RoundedCornerShape(16.dp),
                    colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                    elevation = CardDefaults.cardElevation(defaultElevation = 2.dp),
                    modifier = Modifier
                        .fillMaxWidth()
                        .padding(horizontal = 16.dp, vertical = 8.dp)
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(16.dp),
                        verticalArrangement = Arrangement.spacedBy(12.dp)
                    ) {
                        Row(
                            verticalAlignment = Alignment.CenterVertically,
                            horizontalArrangement = Arrangement.spacedBy(12.dp)
                        ) {
                            Box(
                                modifier = Modifier
                                    .size(48.dp)
                                    .clip(CircleShape)
                                    .background(prog.primaryColor.copy(alpha = 0.15f)),
                                contentAlignment = Alignment.Center
                            ) {
                                Icon(
                                    imageVector = prog.icon,
                                    contentDescription = null,
                                    tint = prog.primaryColor,
                                    modifier = Modifier.size(28.dp)
                                )
                            }

                            Column(modifier = Modifier.weight(1f)) {
                                Text(
                                    text = prog.name,
                                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                                )
                                Text(
                                    text = prog.description,
                                    style = MaterialTheme.typography.bodySmall.copy(color = MaterialTheme.colorScheme.onSurfaceVariant)
                                )
                            }
                        }

                        // Plans inside the program card
                        prog.plans.forEach { plan ->
                            Surface(
                                shape = RoundedCornerShape(10.dp),
                                color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.4f),
                                modifier = Modifier.fillMaxWidth()
                            ) {
                                Row(
                                    modifier = Modifier
                                        .fillMaxWidth()
                                        .padding(12.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(10.dp)
                                ) {
                                    Column(modifier = Modifier.weight(1f)) {
                                        Row(
                                            verticalAlignment = Alignment.CenterVertically,
                                            horizontalArrangement = Arrangement.spacedBy(6.dp)
                                        ) {
                                            Text(
                                                text = plan.duration,
                                                style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold)
                                            )
                                            if (plan.isPopular) {
                                                Surface(
                                                    color = Color(0xFFE8F5E9),
                                                    shape = RoundedCornerShape(4.dp)
                                                ) {
                                                    Text(
                                                        text = "الأكثر طلباً",
                                                        style = MaterialTheme.typography.labelSmall.copy(
                                                            color = Color(0xFF2E7D32),
                                                            fontWeight = FontWeight.Bold
                                                        ),
                                                        modifier = Modifier.padding(horizontal = 6.dp, vertical = 2.dp)
                                                    )
                                                }
                                            }
                                        }
                                        Text(
                                            text = plan.details,
                                            style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray)
                                        )
                                        Spacer(modifier = Modifier.height(2.dp))
                                        Text(
                                            text = "${formatMoney(plan.priceYer)} ر.ي",
                                            style = MaterialTheme.typography.titleMedium.copy(
                                                color = MaterialTheme.colorScheme.primary,
                                                fontWeight = FontWeight.Bold
                                            )
                                        )
                                    }

                                    Button(
                                        onClick = {
                                            selectedProgramToBuy = Pair(prog, plan)
                                        },
                                        shape = RoundedCornerShape(8.dp),
                                        colors = ButtonDefaults.buttonColors(containerColor = prog.primaryColor)
                                    ) {
                                        Text("اشتراك", fontWeight = FontWeight.Bold)
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }

    // Purchase Dialog
    selectedProgramToBuy?.let { (prog, plan) ->
        AlertDialog(
            onDismissRequest = { selectedProgramToBuy = null },
            title = {
                Text(text = "تأكيد الاشتراك في ${prog.name}", fontWeight = FontWeight.Bold)
            },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text(text = "الباقة: ${plan.duration} (${plan.details})")
                    Text(
                        text = "السعر: ${formatMoney(plan.priceYer)} ريال يمني",
                        style = MaterialTheme.typography.titleMedium.copy(
                            color = MaterialTheme.colorScheme.primary,
                            fontWeight = FontWeight.Bold
                        )
                    )

                    OutlinedTextField(
                        value = userEmailOrPhone,
                        onValueChange = { userEmailOrPhone = it },
                        label = { Text("البريد الإلكتروني أو رقم الهاتف للتفعيل") },
                        placeholder = { Text("مثال: user@example.com أو 770123456") },
                        singleLine = true,
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    )

                    Text(
                        text = "سيتم التفعيل الفوري وخصم المبلغ من محفظتك الإلكترونية.",
                        style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray)
                    )
                }
            },
            confirmButton = {
                Button(
                    onClick = {
                        val licenseKey = "SHBK-" + (1000..9999).random() + "-" + (1000..9999).random() + "-VIP"
                        onPurchaseProgram(prog.name, plan.duration, plan.priceYer, userEmailOrPhone)
                        generatedProgramLicense = Pair(prog.name, licenseKey)
                        selectedProgramToBuy = null
                    },
                    colors = ButtonDefaults.buttonColors(containerColor = prog.primaryColor)
                ) {
                    Text("تأكيد وتفعيل الاشتراك", fontWeight = FontWeight.Bold)
                }
            },
            dismissButton = {
                OutlinedButton(onClick = { selectedProgramToBuy = null }) {
                    Text("إلغاء")
                }
            }
        )
    }

    // Success dialog
    generatedProgramLicense?.let { (pName, license) ->
        AlertDialog(
            onDismissRequest = { generatedProgramLicense = null },
            title = {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Icon(imageVector = Icons.Default.CheckCircle, contentDescription = null, tint = Color(0xFF2E7D32))
                    Text("تم تفعيل الاشتراك بنجاح", fontWeight = FontWeight.Bold)
                }
            },
            text = {
                Column(
                    modifier = Modifier.fillMaxWidth(),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text("تم تفعيل اشتراك $pName بنجاح!")
                    Surface(
                        color = MaterialTheme.colorScheme.surfaceVariant,
                        shape = RoundedCornerShape(10.dp),
                        modifier = Modifier.fillMaxWidth()
                    ) {
                        Column(
                            modifier = Modifier.padding(12.dp),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(4.dp)
                        ) {
                            Text("كود الترخيص / بيانات الدخول:", style = MaterialTheme.typography.labelSmall)
                            Text(
                                text = license,
                                style = MaterialTheme.typography.titleMedium.copy(
                                    fontWeight = FontWeight.Bold,
                                    color = MaterialTheme.colorScheme.primary
                                )
                            )
                        }
                    }
                }
            },
            confirmButton = {
                Button(onClick = { generatedProgramLicense = null }) {
                    Text("تم")
                }
            }
        )
    }
}
