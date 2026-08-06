package com.bruceyangg.pulsedesk.ui.nav

import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.outlined.Article
import androidx.compose.material.icons.automirrored.outlined.ShowChart
import androidx.compose.material.icons.outlined.AccountBalance
import androidx.compose.material.icons.outlined.AccountTree
import androidx.compose.material.icons.outlined.CalendarMonth
import androidx.compose.material.icons.outlined.GridView
import androidx.compose.material.icons.outlined.Settings
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.NavigationBarItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import com.bruceyangg.pulsedesk.ui.webview.PulseWebShell
import com.bruceyangg.pulsedesk.ui.webview.WebTab
import com.bruceyangg.pulsedesk.ui.webview.shouldHideNativeTabs

private data class TabSpec(
    val tab: WebTab,
    val icon: ImageVector,
)

private val TAB_SPECS = listOf(
    TabSpec(WebTab.Desk, Icons.Outlined.AccountBalance),
    TabSpec(WebTab.Markets, Icons.AutoMirrored.Outlined.ShowChart),
    TabSpec(WebTab.Sectors, Icons.Outlined.GridView),
    TabSpec(WebTab.Earnings, Icons.Outlined.CalendarMonth),
    TabSpec(WebTab.Intel, Icons.AutoMirrored.Outlined.Article),
    TabSpec(WebTab.Chains, Icons.Outlined.AccountTree),
    TabSpec(WebTab.Settings, Icons.Outlined.Settings),
)

/**
 * Mobile-first shell: native bottom tabs + full-site WebView.
 * Guarantees 100% parity with the live Pulse Desk website.
 */
@Composable
fun PulseRoot() {
    var selected by rememberSaveable { mutableStateOf(WebTab.Desk.name) }
    var currentUrl by rememberSaveable { mutableStateOf<String?>(null) }

    val selectedTab = WebTab.entries.firstOrNull { it.name == selected } ?: WebTab.Desk
    val hideTabs = shouldHideNativeTabs(currentUrl)

    Scaffold(
        bottomBar = {
            if (!hideTabs) {
                NavigationBar(
                    modifier = Modifier.navigationBarsPadding(),
                    tonalElevation = 3.dp,
                    containerColor = MaterialTheme.colorScheme.surface,
                ) {
                    val colors = NavigationBarItemDefaults.colors(
                        selectedIconColor = MaterialTheme.colorScheme.primary,
                        selectedTextColor = MaterialTheme.colorScheme.primary,
                        indicatorColor = MaterialTheme.colorScheme.surfaceVariant,
                        unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
                        unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant,
                    )
                    TAB_SPECS.forEach { spec ->
                        val isSelected = selectedTab == spec.tab
                        NavigationBarItem(
                            selected = isSelected,
                            onClick = { selected = spec.tab.name },
                            icon = {
                                Icon(spec.icon, contentDescription = spec.tab.label)
                            },
                            label = {
                                Text(
                                    text = spec.tab.label,
                                    fontSize = 10.sp,
                                    fontWeight = if (isSelected) FontWeight.Bold else FontWeight.Medium,
                                    maxLines = 1,
                                    overflow = TextOverflow.Ellipsis,
                                )
                            },
                            alwaysShowLabel = true,
                            colors = colors,
                        )
                    }
                }
            }
        },
    ) { padding ->
        PulseWebShell(
            selectedTab = selectedTab,
            onUrlChanged = { currentUrl = it },
            onTabFromWeb = { tab -> selected = tab.name },
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        )
    }
}
