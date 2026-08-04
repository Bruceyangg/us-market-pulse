package com.bruceyangg.pulsedesk.ui.screens.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import com.bruceyangg.pulsedesk.ui.components.ErrorState
import com.bruceyangg.pulsedesk.ui.components.LoadingState
import com.bruceyangg.pulsedesk.ui.components.PulseCard
import com.bruceyangg.pulsedesk.ui.components.ScreenHeader
import com.bruceyangg.pulsedesk.ui.theme.ThemeMode
import com.bruceyangg.pulsedesk.ui.theme.ThemePreferences
import com.bruceyangg.pulsedesk.ui.theme.rememberThemeMode
import com.bruceyangg.pulsedesk.viewmodel.AuthViewModel
import com.bruceyangg.pulsedesk.viewmodel.SettingsViewModel

@Composable
fun SettingsScreen(
    vm: SettingsViewModel = viewModel(),
    authVm: AuthViewModel = viewModel(),
    onLoginClick: () -> Unit = {},
) {
    val state by vm.state.collectAsStateWithLifecycle()
    val auth by authVm.state.collectAsStateWithLifecycle()
    val context = LocalContext.current
    val themePrefs = ThemePreferences.get(context)
    val themeMode = rememberThemeMode(themePrefs)

    LaunchedEffect(Unit) {
        if (state.data == null) vm.load()
        if (!auth.bootstrapped) authVm.refreshMe()
    }

    Column(Modifier.fillMaxSize()) {
        ScreenHeader(
            title = "设置",
            subtitle = "账户 · 主题 · 推送与盯盘",
            onRefresh = { vm.load(true) },
            refreshing = state.refreshing,
        )

        LazyColumn(
            contentPadding = PaddingValues(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            item {
                PulseCard {
                    Column(Modifier.padding(14.dp)) {
                        Text("账户", style = MaterialTheme.typography.titleMedium)
                        if (auth.authenticated) {
                            Text(
                                auth.user?.label ?: auth.user?.username.orEmpty(),
                                fontWeight = FontWeight.SemiBold,
                                modifier = Modifier.padding(top = 8.dp),
                            )
                            Text(
                                "@${auth.user?.username.orEmpty()}",
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                style = MaterialTheme.typography.bodyMedium,
                                modifier = Modifier.padding(top = 2.dp),
                            )
                            Spacer(Modifier.height(10.dp))
                            TextButton(onClick = { authVm.logout() }) {
                                Text("退出登录")
                            }
                        } else {
                            Text(
                                "登录后可查看与同步个人持仓",
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                style = MaterialTheme.typography.bodyMedium,
                                modifier = Modifier.padding(top = 6.dp, bottom = 10.dp),
                            )
                            Button(onClick = onLoginClick) {
                                Text("登录 / 注册")
                            }
                        }
                    }
                }
            }

            item {
                PulseCard {
                    Column(Modifier.padding(14.dp)) {
                        Text("昼夜主题", style = MaterialTheme.typography.titleMedium)
                        Text(
                            "与网站一致：自动 / 白天 / 夜晚",
                            color = MaterialTheme.colorScheme.onSurfaceVariant,
                            style = MaterialTheme.typography.bodyMedium,
                            modifier = Modifier.padding(top = 4.dp, bottom = 10.dp),
                        )
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            ThemeMode.entries.forEach { mode ->
                                FilterChip(
                                    selected = themeMode == mode,
                                    onClick = { themePrefs.setMode(mode) },
                                    label = { Text(mode.label) },
                                )
                            }
                        }
                        Spacer(Modifier.height(8.dp))
                        Text(
                            "当前：${themeMode.label}",
                            fontWeight = FontWeight.SemiBold,
                            color = MaterialTheme.colorScheme.primary,
                        )
                    }
                }
            }

            item {
                Text("推送与盯盘", style = MaterialTheme.typography.titleMedium)
            }

            when {
                state.loading && state.data == null -> {
                    item { LoadingState("读取设置…") }
                }
                state.error != null && state.data == null -> {
                    item {
                        ErrorState(state.error!!) { vm.load(true) }
                    }
                }
                else -> {
                    val s = state.data
                    item {
                        PulseCard {
                            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                SettingRow("推送开关", if (s?.push_enabled == true) "已开启" else "已关闭")
                                SettingRow(
                                    "Webhook",
                                    when {
                                        s?.webhook_configured == true ->
                                            s.resolved_webhook_format ?: s.webhook_format ?: "已配置"
                                        else -> "未配置"
                                    },
                                )
                                SettingRow(
                                    "推送间隔",
                                    "${s?.push_interval_minutes ?: 15} 分钟",
                                )
                                SettingRow("时区", s?.push_timezone ?: "Asia/Shanghai")
                                SettingRow(
                                    "定时点",
                                    s?.push_times?.joinToString(", ").orEmpty().ifBlank { "—" },
                                )
                                SettingRow(
                                    "盯盘关键词",
                                    s?.watch_keywords?.joinToString(", ").orEmpty().ifBlank { "—" },
                                )
                                SettingRow(
                                    "邮件通道",
                                    if (s?.email_configured == true) "已配置" else "未配置",
                                )
                                Text(
                                    "修改 Webhook / 关键词请到网页设置页保存；App 侧同步只读展示。",
                                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                                    style = MaterialTheme.typography.bodyMedium,
                                    modifier = Modifier.padding(top = 4.dp),
                                )
                            }
                        }
                    }
                    item {
                        PulseCard {
                            Row(
                                Modifier
                                    .fillMaxWidth()
                                    .padding(14.dp),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically,
                            ) {
                                Column(Modifier.weight(1f)) {
                                    Text("快速切换夜晚模式", fontWeight = FontWeight.SemiBold)
                                    Text(
                                        "打开后强制使用夜晚主题",
                                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                                        style = MaterialTheme.typography.bodyMedium,
                                    )
                                }
                                Switch(
                                    checked = themeMode == ThemeMode.Dark,
                                    onCheckedChange = { on ->
                                        themePrefs.setMode(if (on) ThemeMode.Dark else ThemeMode.Light)
                                    },
                                )
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun SettingRow(label: String, value: String) {
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
    ) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, fontWeight = FontWeight.SemiBold)
    }
}
