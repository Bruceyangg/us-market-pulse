package com.bruceyangg.pulsedesk.ui.nav

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.WindowInsets
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.navigationBars
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.material3.NavigationRail
import androidx.compose.material3.NavigationRailItem
import androidx.compose.material3.NavigationRailItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.ripple
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.foundation.interaction.MutableInteractionSource
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalConfiguration
import androidx.compose.ui.semantics.Role
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
    /** Compact label for dense phone bottom bar (≤2 chars preferred). */
    val shortLabel: String,
)

/** All 7 modules — short labels keep a 7-up bar readable on phones. */
private val ALL_TABS = listOf(
    TabSpec(WebTab.Desk, Icons.Outlined.AccountBalance, "持仓"),
    TabSpec(WebTab.Sectors, Icons.Outlined.GridView, "板块"),
    TabSpec(WebTab.Markets, Icons.AutoMirrored.Outlined.ShowChart, "市场"),
    TabSpec(WebTab.Earnings, Icons.Outlined.CalendarMonth, "财报"),
    TabSpec(WebTab.Intel, Icons.AutoMirrored.Outlined.Article, "情报"),
    TabSpec(WebTab.Chains, Icons.Outlined.AccountTree, "产业"),
    TabSpec(WebTab.Settings, Icons.Outlined.Settings, "设置"),
)

/**
 * Adaptive shell with a single shared WebView (survives phone↔tablet rotation):
 * - Phone: equal-width bottom tabs for all modules
 * - Tablet (sw≥600dp): left NavigationRail
 */
@Composable
fun PulseRoot() {
    var selected by rememberSaveable { mutableStateOf(WebTab.Desk.name) }
    var currentUrl by rememberSaveable { mutableStateOf<String?>(null) }

    val selectedTab = WebTab.entries.firstOrNull { it.name == selected } ?: WebTab.Desk
    val hideTabs = shouldHideNativeTabs(currentUrl)
    val isTablet = LocalConfiguration.current.smallestScreenWidthDp >= 600

    val railColors = NavigationRailItemDefaults.colors(
        selectedIconColor = MaterialTheme.colorScheme.primary,
        selectedTextColor = MaterialTheme.colorScheme.primary,
        indicatorColor = MaterialTheme.colorScheme.surfaceVariant,
        unselectedIconColor = MaterialTheme.colorScheme.onSurfaceVariant,
        unselectedTextColor = MaterialTheme.colorScheme.onSurfaceVariant,
    )

    Scaffold(
        bottomBar = {
            if (!isTablet && !hideTabs) {
                PhoneTabBar(
                    selectedTab = selectedTab,
                    onSelect = { selected = it.name },
                )
            }
        },
    ) { padding ->
        Row(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .then(
                    if (isTablet) {
                        Modifier.statusBarsPadding()
                    } else {
                        Modifier
                    },
                ),
        ) {
            if (isTablet && !hideTabs) {
                NavigationRail(
                    modifier = Modifier.fillMaxHeight(),
                    containerColor = MaterialTheme.colorScheme.surface,
                ) {
                    Column(
                        modifier = Modifier
                            .fillMaxHeight()
                            .verticalScroll(rememberScrollState()),
                        horizontalAlignment = Alignment.CenterHorizontally,
                    ) {
                        Text(
                            text = "Pulse",
                            style = MaterialTheme.typography.labelLarge,
                            fontWeight = FontWeight.Bold,
                            color = MaterialTheme.colorScheme.primary,
                            modifier = Modifier.padding(top = 14.dp, bottom = 8.dp),
                        )
                        ALL_TABS.forEach { spec ->
                            NavigationRailItem(
                                selected = selectedTab == spec.tab,
                                onClick = { selected = spec.tab.name },
                                icon = {
                                    Icon(spec.icon, contentDescription = spec.tab.label)
                                },
                                label = {
                                    Text(
                                        text = spec.shortLabel,
                                        fontSize = 11.sp,
                                        fontWeight = if (selectedTab == spec.tab) {
                                            FontWeight.Bold
                                        } else {
                                            FontWeight.Medium
                                        },
                                        maxLines = 1,
                                        overflow = TextOverflow.Ellipsis,
                                    )
                                },
                                alwaysShowLabel = true,
                                colors = railColors,
                            )
                        }
                    }
                }
            }

            PulseWebShell(
                selectedTab = selectedTab,
                isTablet = isTablet,
                onUrlChanged = { currentUrl = it },
                onTabFromWeb = { tab -> selected = tab.name },
                modifier = Modifier
                    .weight(1f)
                    .fillMaxHeight(),
            )
        }
    }
}

/** Equal-weight custom bar — Material NavigationBar is tuned for 3–5 items, not 7. */
@Composable
private fun PhoneTabBar(
    selectedTab: WebTab,
    onSelect: (WebTab) -> Unit,
) {
    Surface(
        tonalElevation = 3.dp,
        shadowElevation = 2.dp,
        color = MaterialTheme.colorScheme.surface,
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .windowInsetsPadding(WindowInsets.navigationBars)
                .height(60.dp)
                .selectableGroup()
                .padding(horizontal = 2.dp, vertical = 4.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            ALL_TABS.forEach { spec ->
                val selected = selectedTab == spec.tab
                Column(
                    modifier = Modifier
                        .weight(1f)
                        .fillMaxHeight()
                        .clip(RoundedCornerShape(12.dp))
                        .selectable(
                            selected = selected,
                            onClick = { onSelect(spec.tab) },
                            role = Role.Tab,
                            interactionSource = remember { MutableInteractionSource() },
                            indication = ripple(bounded = true),
                        )
                        .background(
                            if (selected) {
                                MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.85f)
                            } else {
                                MaterialTheme.colorScheme.surface.copy(alpha = 0f)
                            },
                        )
                        .padding(vertical = 4.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.Center,
                ) {
                    Icon(
                        imageVector = spec.icon,
                        contentDescription = spec.tab.label,
                        modifier = Modifier.size(22.dp),
                        tint = if (selected) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        },
                    )
                    Text(
                        text = spec.shortLabel,
                        fontSize = 10.sp,
                        lineHeight = 12.sp,
                        fontWeight = if (selected) FontWeight.Bold else FontWeight.Medium,
                        color = if (selected) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        },
                        maxLines = 1,
                        overflow = TextOverflow.Ellipsis,
                    )
                }
            }
        }
    }
}
