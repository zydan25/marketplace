package com.example.ui

import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.example.data.model.UserSession

/**
 * Compatibility entry point kept for MainActivity.
 * The old hardcoded telecom/game/program catalog is intentionally removed;
 * all services, fields, branches and provider catalog items now come from the
 * authenticated Django services catalog.
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
        djangoBaseUrl = "https://shopik.alattab.site/api/",
        onBackClick = onBackClick,
        modifier = modifier
    )
}
