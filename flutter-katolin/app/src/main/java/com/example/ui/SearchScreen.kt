package com.example.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import coil.compose.AsyncImage
import com.example.data.model.Product

enum class SortOption(val label: String) {
    DEFAULT("الأكثر صلة"),
    PRICE_LOW("الأقل سعراً"),
    PRICE_HIGH("الأعلى سعراً"),
    RATING("الأعلى تقييماً")
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SearchScreen(
    products: List<Product>,
    favorites: Set<Int>,
    initialQuery: String = "",
    onBackClick: () -> Unit,
    onProductClick: (Product) -> Unit,
    onAddToCart: (Product) -> Unit,
    onToggleFavorite: (Int) -> Unit,
    formatMoney: (Double) -> String
) {
    var searchQuery by remember { mutableStateOf(initialQuery) }
    var selectedCategory by remember { mutableStateOf("الكل") }
    var selectedPriceRange by remember { mutableStateOf("الكل") }
    var sortOption by remember { mutableStateOf(SortOption.DEFAULT) }

    val categories = remember(products) {
        listOf("الكل") + products.map { it.category }.distinct()
    }
    val priceRanges = listOf("الكل", "أقل من 5,000", "5,000 - 20,000", "أكثر من 20,000")

    val searchResults = remember(products, searchQuery, selectedCategory, selectedPriceRange, sortOption) {
        var list = products.filter { product ->
            val matchQuery = searchQuery.isBlank() ||
                    product.name.contains(searchQuery, ignoreCase = true) ||
                    product.description.contains(searchQuery, ignoreCase = true) ||
                    product.storeName.contains(searchQuery, ignoreCase = true)

            val matchCat = selectedCategory == "الكل" || product.category == selectedCategory

            val matchPrice = when (selectedPriceRange) {
                "أقل من 5,000" -> product.priceYer < 5000.0
                "5,000 - 20,000" -> product.priceYer in 5000.0..20000.0
                "أكثر من 20,000" -> product.priceYer > 20000.0
                else -> true
            }

            matchQuery && matchCat && matchPrice
        }

        list = when (sortOption) {
            SortOption.DEFAULT -> list
            SortOption.PRICE_LOW -> list.sortedBy { it.priceYer }
            SortOption.PRICE_HIGH -> list.sortedByDescending { it.priceYer }
            SortOption.RATING -> list.sortedByDescending { it.rating }
        }
        list
    }

    Scaffold(
        topBar = {
            Surface(
                color = MaterialTheme.colorScheme.surface,
                shadowElevation = 2.dp
            ) {
                Column(modifier = Modifier.padding(bottom = 8.dp)) {
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(horizontal = 8.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        IconButton(onClick = onBackClick) {
                            Icon(
                                imageVector = Icons.AutoMirrored.Filled.ArrowBack,
                                contentDescription = "رجوع"
                            )
                        }

                        OutlinedTextField(
                            value = searchQuery,
                            onValueChange = { searchQuery = it },
                            modifier = Modifier
                                .weight(1f)
                                .height(50.dp)
                                .testTag("search_input_field"),
                            placeholder = { Text("ابحث عن منتج، متجر، أو ماركة...") },
                            leadingIcon = {
                                Icon(
                                    imageVector = Icons.Default.Search,
                                    contentDescription = null,
                                    tint = MaterialTheme.colorScheme.primary
                                )
                            },
                            trailingIcon = {
                                if (searchQuery.isNotEmpty()) {
                                    IconButton(onClick = { searchQuery = "" }) {
                                        Icon(
                                            imageVector = Icons.Default.Close,
                                            contentDescription = "مسح"
                                        )
                                    }
                                }
                            },
                            singleLine = true,
                            shape = RoundedCornerShape(12.dp)
                        )
                    }

                    // Categories Bar
                    LazyRow(
                        modifier = Modifier.fillMaxWidth(),
                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        items(categories) { cat ->
                            val active = cat == selectedCategory
                            FilterChip(
                                selected = active,
                                onClick = { selectedCategory = cat },
                                label = { Text(cat, fontSize = 12.sp) }
                            )
                        }
                    }

                    // Price & Sort Row
                    LazyRow(
                        modifier = Modifier.fillMaxWidth(),
                        contentPadding = PaddingValues(horizontal = 12.dp, vertical = 2.dp),
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        items(priceRanges) { pr ->
                            val active = pr == selectedPriceRange
                            FilterChip(
                                selected = active,
                                onClick = { selectedPriceRange = pr },
                                label = { Text(pr, fontSize = 11.sp) }
                            )
                        }

                        item {
                            AssistChip(
                                onClick = {
                                    sortOption = when (sortOption) {
                                        SortOption.DEFAULT -> SortOption.PRICE_LOW
                                        SortOption.PRICE_LOW -> SortOption.PRICE_HIGH
                                        SortOption.PRICE_HIGH -> SortOption.RATING
                                        SortOption.RATING -> SortOption.DEFAULT
                                    }
                                },
                                label = { Text("الترتيب: ${sortOption.label}", fontSize = 11.sp) },
                                leadingIcon = {
                                    Icon(
                                        imageVector = Icons.Default.SwapVert,
                                        contentDescription = null,
                                        modifier = Modifier.size(14.dp)
                                    )
                                }
                            )
                        }
                    }
                }
            }
        }
    ) { innerPadding ->
        LazyColumn(
            modifier = Modifier
                .fillMaxSize()
                .padding(innerPadding)
                .background(Color(0xFFF7F8FA)),
            contentPadding = PaddingValues(12.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            item {
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = "نتائج البحث (${searchResults.size})",
                        style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold)
                    )
                    if (searchQuery.isNotBlank() || selectedCategory != "الكل" || selectedPriceRange != "الكل") {
                        TextButton(onClick = {
                            searchQuery = ""
                            selectedCategory = "الكل"
                            selectedPriceRange = "الكل"
                            sortOption = SortOption.DEFAULT
                        }) {
                            Text("إعادة ضبط الفلاتر", fontSize = 11.sp)
                        }
                    }
                }
            }

            if (searchResults.isEmpty()) {
                item {
                    Box(
                        modifier = Modifier
                            .fillMaxWidth()
                            .padding(vertical = 60.dp),
                        contentAlignment = Alignment.Center
                    ) {
                        Column(horizontalAlignment = Alignment.CenterHorizontally) {
                            Icon(
                                imageVector = Icons.Default.SearchOff,
                                contentDescription = null,
                                tint = Color.LightGray,
                                modifier = Modifier.size(60.dp)
                            )
                            Spacer(modifier = Modifier.height(10.dp))
                            Text(
                                text = "لم يتم العثور على منتجات مطابقة",
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
                            )
                            Spacer(modifier = Modifier.height(4.dp))
                            Text(
                                text = "جرّب البحث بكلمات أخرى أو اختر تصنيفاً مختلفاً",
                                style = MaterialTheme.typography.bodySmall.copy(color = Color.Gray)
                            )
                        }
                    }
                }
            } else {
                items(searchResults) { product ->
                    SearchProductRow(
                        product = product,
                        isFavorite = favorites.contains(product.id),
                        onProductClick = { onProductClick(product) },
                        onAddToCart = { onAddToCart(product) },
                        onToggleFavorite = { onToggleFavorite(product.id) },
                        formatMoney = formatMoney
                    )
                }
            }
        }
    }
}

@Composable
fun SearchProductRow(
    product: Product,
    isFavorite: Boolean,
    onProductClick: () -> Unit,
    onAddToCart: () -> Unit,
    onToggleFavorite: () -> Unit,
    formatMoney: (Double) -> String
) {
    Card(
        modifier = Modifier
            .fillMaxWidth()
            .clickable(onClick = onProductClick)
            .testTag("search_item_${product.id}"),
        shape = RoundedCornerShape(12.dp),
        colors = CardDefaults.cardColors(containerColor = Color.White),
        elevation = CardDefaults.cardElevation(defaultElevation = 1.dp)
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(10.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            val img = product.images.firstOrNull()
            if (!img.isNullOrBlank()) {
                AsyncImage(
                    model = img,
                    contentDescription = product.name,
                    modifier = Modifier
                        .size(76.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(Color(0xFFF1F5F9)),
                    contentScale = ContentScale.Crop
                )
            } else {
                Box(
                    modifier = Modifier
                        .size(76.dp)
                        .clip(RoundedCornerShape(8.dp))
                        .background(Color(0xFFF1F5F9)),
                    contentAlignment = Alignment.Center
                ) {
                    Icon(
                        imageVector = Icons.Default.ShoppingBag,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
            }

            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = product.name,
                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
                Text(
                    text = "${product.storeName} · ${product.category}",
                    style = MaterialTheme.typography.labelSmall.copy(color = Color.Gray),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )

                Spacer(modifier = Modifier.height(6.dp))

                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    Text(
                        text = "${formatMoney(product.priceYer)} ر.ي",
                        style = MaterialTheme.typography.bodyMedium.copy(
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary
                        )
                    )
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(
                            imageVector = Icons.Default.Star,
                            contentDescription = null,
                            tint = Color(0xFFF59E0B),
                            modifier = Modifier.size(13.dp)
                        )
                        Text(
                            text = "${product.rating}",
                            style = MaterialTheme.typography.labelSmall.copy(
                                fontWeight = FontWeight.Bold,
                                fontSize = 11.sp
                            )
                        )
                    }
                }
            }

            Column(
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(4.dp)
            ) {
                IconButton(
                    onClick = onToggleFavorite,
                    modifier = Modifier.size(32.dp)
                ) {
                    Icon(
                        imageVector = if (isFavorite) Icons.Default.Favorite else Icons.Default.FavoriteBorder,
                        contentDescription = null,
                        tint = if (isFavorite) Color(0xFFE11D48) else Color.Gray,
                        modifier = Modifier.size(20.dp)
                    )
                }

                FilledIconButton(
                    onClick = onAddToCart,
                    modifier = Modifier.size(34.dp),
                    colors = IconButtonDefaults.filledIconButtonColors(
                        containerColor = MaterialTheme.colorScheme.primaryContainer
                    )
                ) {
                    Icon(
                        imageVector = Icons.Default.AddShoppingCart,
                        contentDescription = "إضافة للسلة",
                        tint = MaterialTheme.colorScheme.primary,
                        modifier = Modifier.size(18.dp)
                    )
                }
            }
        }
    }
}
