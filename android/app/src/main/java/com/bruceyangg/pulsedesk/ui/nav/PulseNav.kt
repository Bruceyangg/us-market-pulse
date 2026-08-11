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
import androidx.compose.foundation.layout.windowInsetsPadding
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.selection.selectableGroup
import androidx.compose.foundation.shape.RoundedCornerShape
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
    /** Compact label for dense bottom bar (≤2 chars preferred). */
    val shortLabel: String,
)

/** All 7 website modules — matches live site coverage. */
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
 * Adaptive shell with a single shared WebView:
 * - Bottom tab bar on phone and tablet (fixed size — does not scale with WebView zoom)
 * - Tablet WebView enables pinch zoom for page content
 */
@Composable
fun PulseRoot() {
    var selected by rememberSaveable { mutableStateOf(WebTab.Desk.name) }
    var currentUrl by rememberSaveable { mutableStateOf<String?>(null) }

    val selectedTab = WebTab.entries.firstOrNull { it.name == selected } ?: WebTab.Desk
    val hideTabs = shouldHideNativeTabs(currentUrl)
    val isTablet = LocalConfiguration.current.smallestScreenWidthDp >= 600

    Scaffold(
        bottomBar = {
            if (!hideTabs) {
                AppTabBar(
                    selectedTab = selectedTab,
                    onSelect = { selected = it.name },
                    isTablet = isTablet,
                )
            }
        },
    ) { padding ->
        PulseWebShell(
            selectedTab = selectedTab,
            isTablet = isTablet,
            onUrlChanged = { currentUrl = it },
            onTabFromWeb = { tab -> selected = tab.name },
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        )
    }
}

/** Equal-weight custom bar — stays outside WebView so zoom never resizes tabs. */
@Composable
private fun AppTabBar(
    selectedTab: WebTab,
    onSelect: (WebTab) -> Unit,
    isTablet: Boolean,
) {
    val barHeight = if (isTablet) 68.dp else 60.dp
    val iconSize = if (isTablet) 24.dp else 22.dp
    val labelSize = if (isTablet) 11.sp else 10.sp

    Surface(
        tonalElevation = 3.dp,
        shadowElevation = 2.dp,
        color = MaterialTheme.colorScheme.surface,
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .windowInsetsPadding(WindowInsets.navigationBars)
                .height(barHeight)
                .selectableGroup()
                .padding(horizontal = if (isTablet) 6.dp else 2.dp, vertical = 4.dp),
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
                        modifier = Modifier.size(iconSize),
                        tint = if (selected) {
                            MaterialTheme.colorScheme.primary
                        } else {
                            MaterialTheme.colorScheme.onSurfaceVariant
                        },
                    )
                    Text(
                        text = spec.shortLabel,
                        fontSize = labelSize,
                        lineHeight = (labelSize.value + 2).sp,
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
