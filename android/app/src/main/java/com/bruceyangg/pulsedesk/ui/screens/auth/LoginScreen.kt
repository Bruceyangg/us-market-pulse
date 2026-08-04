package com.bruceyangg.pulsedesk.ui.screens.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import com.bruceyangg.pulsedesk.ui.components.PulseCard
import com.bruceyangg.pulsedesk.ui.components.ScreenHeader
import com.bruceyangg.pulsedesk.viewmodel.AuthViewModel

@Composable
fun LoginScreen(
    authVm: AuthViewModel,
    onSuccess: () -> Unit,
    onCancel: () -> Unit,
) {
    val auth by authVm.state.collectAsStateWithLifecycle()
    var modeRegister by remember { mutableStateOf(false) }
    var username by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var displayName by remember { mutableStateOf("") }

    LaunchedEffect(Unit) { authVm.clearError() }

    fun submit() {
        if (modeRegister) {
            authVm.register(username, password, displayName, onSuccess = onSuccess)
        } else {
            authVm.login(username, password, onSuccess = onSuccess)
        }
    }

    Column(Modifier.fillMaxSize()) {
        ScreenHeader(
            title = if (modeRegister) "注册" else "登录",
            subtitle = "与网页同一账户 · 持仓云端同步",
        )
        Column(
            Modifier
                .fillMaxSize()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp),
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                FilterChip(
                    selected = !modeRegister,
                    onClick = {
                        modeRegister = false
                        authVm.clearError()
                    },
                    label = { Text("登录") },
                )
                FilterChip(
                    selected = modeRegister,
                    onClick = {
                        modeRegister = true
                        authVm.clearError()
                    },
                    label = { Text("注册") },
                )
            }

            PulseCard {
                Column(
                    Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    OutlinedTextField(
                        value = username,
                        onValueChange = { username = it },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        label = { Text("用户名") },
                        supportingText = { Text("3–24 位字母 / 数字 / 下划线") },
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.Ascii,
                            imeAction = ImeAction.Next,
                        ),
                    )
                    if (modeRegister) {
                        OutlinedTextField(
                            value = displayName,
                            onValueChange = { displayName = it },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true,
                            label = { Text("显示名（可选）") },
                            keyboardOptions = KeyboardOptions(imeAction = ImeAction.Next),
                        )
                    }
                    OutlinedTextField(
                        value = password,
                        onValueChange = { password = it },
                        modifier = Modifier.fillMaxWidth(),
                        singleLine = true,
                        label = { Text("密码") },
                        supportingText = { Text("至少 6 位") },
                        visualTransformation = PasswordVisualTransformation(),
                        keyboardOptions = KeyboardOptions(
                            keyboardType = KeyboardType.Password,
                            imeAction = ImeAction.Done,
                        ),
                        keyboardActions = KeyboardActions(onDone = { submit() }),
                    )

                    auth.error?.let {
                        Text(
                            it,
                            color = MaterialTheme.colorScheme.error,
                            style = MaterialTheme.typography.bodyMedium,
                        )
                    }

                    Button(
                        onClick = { submit() },
                        enabled = !auth.busy,
                        modifier = Modifier.fillMaxWidth(),
                        contentPadding = PaddingValues(vertical = 12.dp),
                    ) {
                        Text(
                            when {
                                auth.busy && modeRegister -> "注册中…"
                                auth.busy -> "登录中…"
                                modeRegister -> "创建账户"
                                else -> "登录"
                            },
                            fontWeight = FontWeight.SemiBold,
                        )
                    }

                    TextButton(
                        onClick = onCancel,
                        modifier = Modifier.align(Alignment.CenterHorizontally),
                    ) {
                        Text("返回")
                    }
                }
            }

            Text(
                "注册后即可在「持仓」添加美股代码，并与网页端同步。",
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(bottom = 24.dp),
            )
            Spacer(Modifier.height(8.dp))
        }
    }
}
