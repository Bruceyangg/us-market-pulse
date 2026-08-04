package com.bruceyangg.pulsedesk.ui.nav

import androidx.compose.animation.EnterTransition
import androidx.compose.animation.ExitTransition
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.outlined.AccountBalance
import androidx.compose.material.icons.outlined.Article
import androidx.compose.material.icons.outlined.BrightnessAuto
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.DarkMode
import androidx.compose.material.icons.outlined.GridView
import androidx.compose.material.icons.outlined.LightMode
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material.icons.outlined.ShowChart
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.bruceyangg.pulsedesk.ui.screens.auth.LoginScreen
import com.bruceyangg.pulsedesk.ui.screens.earnings.EarningsScreen
import com.bruceyangg.pulsedesk.ui.screens.intel.IntelScreen
import com.bruceyangg.pulsedesk.ui.screens.markets.MarketsScreen
import com.bruceyangg.pulsedesk.ui.screens.portfolio.PortfolioScreen
import com.bruceyangg.pulsedesk.ui.screens.sectors.SectorsScreen
import com.bruceyangg.pulsedesk.ui.screens.settings.SettingsScreen
import com.bruceyangg.pulsedesk.ui.theme.ThemeMode
import com.bruceyangg.pulsedesk.ui.theme.ThemePreferences
import com.bruceyangg.pulsedesk.ui.theme.rememberThemeMode
import com.bruceyangg.pulsedesk.viewmodel.AuthViewModel

/** Matches website desk-nav order (持仓情报 merged into 持仓). */
enum class PulseTab(
    val route: String,
    val label: String,
    val icon: ImageVector,
) {
    Portfolio("desk", "持仓", Icons.Outlined.AccountBalance),
    Markets("markets", "市场", Icons.Outlined.ShowChart),
    Sectors("sectors", "板块", Icons.Outlined.GridView),
    Earnings("earnings", "财报", Icons.Outlined.CalendarMonth),
    Intel("intel", "情报", Icons.Outlined.Article),
    Settings("settings", "设置", Icons.Outlined.Settings),
}

private const val ROUTE_LOGIN = "login"

@Composable
fun PulseRoot(authVm: AuthViewModel = viewModel()) {
    val navController = rememberNavController()
    val backStack by navController.currentBackStackEntryAsState()
    val current = backStack?.destination?.route
    val context = LocalContext.current
    val themePrefs = ThemePreferences.get(context)
    val themeMode = rememberThemeMode(themePrefs)
    val auth by authVm.state.collectAsStateWithLifecycle()

    LaunchedEffect(Unit) {
        if (!auth.bootstrapped) authVm.refreshMe()
    }

    val hideBottomBar = current == ROUTE_LOGIN

    Scaffold(
        topBar = {
            Row(
                Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 8.dp, vertical = 2.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Text(
                    text = "Pulse Desk",
                    style = MaterialTheme.typography.titleMedium,
                    modifier = Modifier
                        .weight(1f)
                        .padding(start = 8.dp),
                )
                if (auth.authenticated) {
                    Text(
                        text = auth.user?.label.orEmpty(),
                        style = MaterialTheme.typography.labelLarge,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                        modifier = Modifier
                            .padding(end = 4.dp)
                            .widthIn(max = 96.dp)
                            .clickable {
                                navController.navigate(PulseTab.Settings.route) {
                                    launchSingleTop = true
                                }
                            },
                    )
                } else if (auth.bootstrapped && current != ROUTE_LOGIN) {
                    TextButton(onClick = { navController.navigate(ROUTE_LOGIN) }) {
                        Text("登录")
                    }
                }
                TextButton(onClick = { themePrefs.cycle() }) {
                    Icon(
                        imageVector = when (themeMode) {
                            ThemeMode.Auto -> Icons.Outlined.BrightnessAuto
                            ThemeMode.Light -> Icons.Outlined.LightMode
                            ThemeMode.Dark -> Icons.Outlined.DarkMode
                        },
                        contentDescription = "切换主题",
                    )
                    Text(
                        text = themeMode.label,
                        modifier = Modifier.padding(start = 4.dp),
                    )
                }
            }
        },
        bottomBar = {
            if (!hideBottomBar) {
                Surface(tonalElevation = 3.dp, shadowElevation = 6.dp) {
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .horizontalScroll(rememberScrollState())
                            .padding(horizontal = 4.dp, vertical = 6.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        PulseTab.entries.forEach { tab ->
                            val selected = current == tab.route
                            val tint =
                                if (selected) MaterialTheme.colorScheme.primary
                                else MaterialTheme.colorScheme.onSurfaceVariant
                            Column(
                                modifier = Modifier
                                    .widthIn(min = 72.dp)
                                    .clickable {
                                        navController.navigate(tab.route) {
                                            popUpTo(navController.graph.findStartDestination().id) {
                                                saveState = true
                                            }
                                            launchSingleTop = true
                                            restoreState = true
                                        }
                                    }
                                    .padding(horizontal = 8.dp, vertical = 4.dp),
                                horizontalAlignment = Alignment.CenterHorizontally,
                                verticalArrangement = Arrangement.spacedBy(2.dp),
                            ) {
                                Icon(tab.icon, contentDescription = tab.label, tint = tint)
                                Text(
                                    tab.label,
                                    color = tint,
                                    fontSize = 11.sp,
                                    fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            }
                        }
                    }
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = PulseTab.Portfolio.route,
            modifier = Modifier.padding(padding),
            enterTransition = { EnterTransition.None },
            exitTransition = { ExitTransition.None },
            popEnterTransition = { EnterTransition.None },
            popExitTransition = { ExitTransition.None },
        ) {
            composable(PulseTab.Portfolio.route) {
                PortfolioScreen(
                    authVm = authVm,
                    onLoginClick = { navController.navigate(ROUTE_LOGIN) },
                )
            }
            composable(PulseTab.Markets.route) { MarketsScreen() }
            composable(PulseTab.Sectors.route) { SectorsScreen() }
            composable(PulseTab.Earnings.route) { EarningsScreen() }
            composable(PulseTab.Intel.route) { IntelScreen() }
            composable(PulseTab.Settings.route) {
                SettingsScreen(
                    authVm = authVm,
                    onLoginClick = { navController.navigate(ROUTE_LOGIN) },
                )
            }
            composable(ROUTE_LOGIN) {
                LoginScreen(
                    authVm = authVm,
                    onSuccess = {
                        navController.popBackStack()
                        navController.navigate(PulseTab.Portfolio.route) {
                            launchSingleTop = true
                        }
                    },
                    onCancel = { navController.popBackStack() },
                )
            }
        }
    }
}
