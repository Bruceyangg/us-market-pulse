package com.bruceyangg.pulsedesk

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import com.bruceyangg.pulsedesk.data.api.NetworkModule
import com.bruceyangg.pulsedesk.ui.nav.PulseRoot
import com.bruceyangg.pulsedesk.ui.theme.PulseDeskTheme
import com.bruceyangg.pulsedesk.ui.theme.ThemePreferences
import com.bruceyangg.pulsedesk.ui.theme.rememberThemeMode
import com.bruceyangg.pulsedesk.ui.theme.resolvesDark

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        NetworkModule.init(this)
        enableEdgeToEdge()
        val themePrefs = ThemePreferences.get(this)
        setContent {
            PulseDeskApp(themePrefs)
        }
    }
}

@Composable
private fun PulseDeskApp(themePrefs: ThemePreferences) {
    val mode = rememberThemeMode(themePrefs)
    PulseDeskTheme(darkTheme = mode.resolvesDark()) {
        Surface(modifier = Modifier.fillMaxSize()) {
            PulseRoot()
        }
    }
}
