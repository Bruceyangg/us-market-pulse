package com.bruceyangg.pulsedesk.ui.theme

import android.content.Context
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

enum class ThemeMode(val label: String) {
    Auto("自动"),
    Light("白天"),
    Dark("夜晚");

    fun next(): ThemeMode = when (this) {
        Auto -> Light
        Light -> Dark
        Dark -> Auto
    }

    companion object {
        fun fromStorage(value: String?): ThemeMode =
            entries.firstOrNull { it.name.equals(value, ignoreCase = true) } ?: Auto
    }
}

class ThemePreferences(context: Context) {
    private val prefs = context.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val _mode = MutableStateFlow(ThemeMode.fromStorage(prefs.getString(KEY_MODE, ThemeMode.Auto.name)))
    val mode: StateFlow<ThemeMode> = _mode.asStateFlow()

    fun setMode(mode: ThemeMode) {
        prefs.edit().putString(KEY_MODE, mode.name).apply()
        _mode.value = mode
    }

    fun cycle() {
        setMode(_mode.value.next())
    }

    companion object {
        private const val PREFS = "pulse_theme"
        private const val KEY_MODE = "mode"

        @Volatile
        private var instance: ThemePreferences? = null

        fun get(context: Context): ThemePreferences =
            instance ?: synchronized(this) {
                instance ?: ThemePreferences(context.applicationContext).also { instance = it }
            }
    }
}

@Composable
fun ThemeMode.resolvesDark(): Boolean = when (this) {
    ThemeMode.Auto -> isSystemInDarkTheme()
    ThemeMode.Light -> false
    ThemeMode.Dark -> true
}

@Composable
fun rememberThemeMode(prefs: ThemePreferences): ThemeMode {
    val mode by prefs.mode.collectAsState()
    return mode
}
