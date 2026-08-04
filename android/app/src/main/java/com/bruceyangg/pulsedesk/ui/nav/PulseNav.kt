package com.bruceyangg.pulsedesk.ui.nav

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AccountBalance
import androidx.compose.material.icons.outlined.Article
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.GridView
import androidx.compose.material.icons.outlined.ShowChart
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.bruceyangg.pulsedesk.ui.screens.earnings.EarningsScreen
import com.bruceyangg.pulsedesk.ui.screens.intel.IntelScreen
import com.bruceyangg.pulsedesk.ui.screens.markets.MarketsScreen
import com.bruceyangg.pulsedesk.ui.screens.portfolio.PortfolioScreen
import com.bruceyangg.pulsedesk.ui.screens.sectors.SectorsScreen

enum class PulseTab(
    val route: String,
    val label: String,
    val icon: ImageVector,
) {
    Markets("markets", "行情", Icons.Outlined.ShowChart),
    Sectors("sectors", "板块", Icons.Outlined.GridView),
    Earnings("earnings", "财报", Icons.Outlined.CalendarMonth),
    Intel("intel", "情报", Icons.Outlined.Article),
    Portfolio("portfolio", "持仓", Icons.Outlined.AccountBalance),
}

@Composable
fun PulseRoot() {
    val navController = rememberNavController()
    val backStack by navController.currentBackStackEntryAsState()
    val current = backStack?.destination?.route

    Scaffold(
        bottomBar = {
            NavigationBar {
                PulseTab.entries.forEach { tab ->
                    NavigationBarItem(
                        selected = current == tab.route,
                        onClick = {
                            navController.navigate(tab.route) {
                                popUpTo(navController.graph.findStartDestination().id) {
                                    saveState = true
                                }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(tab.icon, contentDescription = tab.label) },
                        label = { Text(tab.label) },
                    )
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = PulseTab.Sectors.route,
            modifier = Modifier.padding(padding),
        ) {
            composable(PulseTab.Markets.route) { MarketsScreen() }
            composable(PulseTab.Sectors.route) { SectorsScreen() }
            composable(PulseTab.Earnings.route) { EarningsScreen() }
            composable(PulseTab.Intel.route) { IntelScreen() }
            composable(PulseTab.Portfolio.route) { PortfolioScreen() }
        }
    }
}
