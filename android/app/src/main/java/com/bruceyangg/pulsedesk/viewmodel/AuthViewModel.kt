package com.bruceyangg.pulsedesk.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bruceyangg.pulsedesk.data.api.NetworkModule
import com.bruceyangg.pulsedesk.data.model.ApiErrorDetail
import com.bruceyangg.pulsedesk.data.model.AuthFormBody
import com.bruceyangg.pulsedesk.data.model.AuthUser
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import kotlinx.serialization.json.Json
import retrofit2.HttpException

data class AuthUiState(
    val loading: Boolean = false,
    val bootstrapped: Boolean = false,
    val authenticated: Boolean = false,
    val user: AuthUser? = null,
    val error: String? = null,
    val busy: Boolean = false,
)

class AuthViewModel : ViewModel() {
    private val _state = MutableStateFlow(AuthUiState())
    val state: StateFlow<AuthUiState> = _state.asStateFlow()

    private val errorJson = Json { ignoreUnknownKeys = true }

    fun refreshMe() {
        viewModelScope.launch {
            _state.update { it.copy(loading = !it.bootstrapped, error = null) }
            runCatching { NetworkModule.api.authMe() }
                .onSuccess { me ->
                    _state.value = AuthUiState(
                        loading = false,
                        bootstrapped = true,
                        authenticated = me.authenticated && me.user != null,
                        user = me.user,
                    )
                }
                .onFailure {
                    _state.update {
                        it.copy(
                            loading = false,
                            bootstrapped = true,
                            authenticated = false,
                            user = null,
                        )
                    }
                }
        }
    }

    fun login(username: String, password: String, onSuccess: () -> Unit = {}) {
        submit(isRegister = false, username = username, password = password, onSuccess = onSuccess)
    }

    fun register(
        username: String,
        password: String,
        displayName: String?,
        onSuccess: () -> Unit = {},
    ) {
        submit(
            isRegister = true,
            username = username,
            password = password,
            displayName = displayName,
            onSuccess = onSuccess,
        )
    }

    fun logout(onDone: () -> Unit = {}) {
        viewModelScope.launch {
            _state.update { it.copy(busy = true, error = null) }
            runCatching { NetworkModule.api.logout() }
            NetworkModule.clearSessionCookies()
            _state.value = AuthUiState(bootstrapped = true, authenticated = false, user = null)
            onDone()
        }
    }

    fun clearError() {
        _state.update { it.copy(error = null) }
    }

    private fun submit(
        isRegister: Boolean,
        username: String,
        password: String,
        displayName: String? = null,
        onSuccess: () -> Unit,
    ) {
        val user = username.trim()
        val pass = password
        when {
            user.length !in 3..24 -> {
                _state.update { it.copy(error = "用户名需 3–24 位字母/数字/下划线") }
                return
            }
            !user.matches(Regex("^[A-Za-z0-9_]+$")) -> {
                _state.update { it.copy(error = "用户名只能包含字母、数字和下划线") }
                return
            }
            pass.length < 6 -> {
                _state.update { it.copy(error = "密码至少 6 位") }
                return
            }
        }
        viewModelScope.launch {
            _state.update { it.copy(busy = true, error = null) }
            val body = AuthFormBody(
                username = user,
                password = pass,
                display_name = displayName?.trim()?.takeIf { it.isNotEmpty() },
            )
            val result = runCatching {
                if (isRegister) NetworkModule.api.register(body)
                else NetworkModule.api.login(body)
            }
            result
                .onSuccess { res ->
                    _state.value = AuthUiState(
                        bootstrapped = true,
                        authenticated = true,
                        user = res.user,
                        busy = false,
                    )
                    onSuccess()
                }
                .onFailure { e ->
                    _state.update {
                        it.copy(busy = false, error = httpDetail(e) ?: e.message ?: "登录失败")
                    }
                }
        }
    }

    private fun httpDetail(err: Throwable): String? {
        val http = err as? HttpException ?: return null
        val raw = http.response()?.errorBody()?.string().orEmpty()
        return runCatching {
            errorJson.decodeFromString(ApiErrorDetail.serializer(), raw).detail
        }.getOrNull() ?: when (http.code()) {
            401 -> "用户名或密码错误"
            400 -> "注册信息无效"
            else -> "请求失败（${http.code()}）"
        }
    }
}
