package com.bruceyangg.pulsedesk

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier.Modifier
import com.bruceyangg.pulsedesk.ui.nav.PulseRoot
import com.bruceyangg.pulsedesk.ui.theme.PulseDeskTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            PulseDeskTheme(darkTheme = true) {
                Surface(modifier = Modifier.fillMaxSize()) {
                    PulseRoot()
                }
            }
        }
    }
}
