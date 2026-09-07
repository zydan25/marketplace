package com.example.ui

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.example.data.model.UserSession
import com.example.data.repository.StoreRepository

/**
 * Compatibility entry point kept for MainActivity.
 * The customer-facing service catalog is now server-driven: categories,
 * services, required fields and selectable products are fetched from Django.
 */
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
    DynamicServicesScreen(
        userSession = userSession,
        djangoBaseUrl = StoreRepository.instance.djangoBaseUrl.value,
        onBackClick = onBackClick,
        modifier = modifier
    )
}
