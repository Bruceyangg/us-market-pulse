package com.bruceyangg.pulsedesk.ui.webview

import android.annotation.SuppressLint
import android.content.Intent
import android.graphics.Bitmap
import android.net.Uri
import android.view.ViewGroup
import android.webkit.CookieManager
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.rememberUpdatedState
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.bruceyangg.pulsedesk.BuildConfig
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch

/** Maps native bottom tabs to site paths. */
enum class WebTab(val path: String, val label: String) {
    Desk("/", "持仓"),
    Markets("/markets", "市场"),
    Sectors("/sectors", "板块"),
    Earnings("/earnings", "财报"),
    Intel("/intel", "情报"),
    Chains("/chains", "产业链"),
    Settings("/settings", "设置"),
}

fun webTabFromUrl(url: String?): WebTab? {
    if (url.isNullOrBlank()) return null
    val path = try {
        Uri.parse(url).path?.trimEnd('/')?.ifEmpty { "/" } ?: "/"
    } catch (_: Exception) {
        return null
    }
    return when {
        path == "/" || path == "/desk" -> WebTab.Desk
        path.startsWith("/markets") -> WebTab.Markets
        path.startsWith("/sectors") -> WebTab.Sectors
        path.startsWith("/earnings") -> WebTab.Earnings
        path.startsWith("/intel") -> WebTab.Intel
        path.startsWith("/chains") -> WebTab.Chains
        path.startsWith("/settings") -> WebTab.Settings
        else -> null
    }
}

fun shouldHideNativeTabs(url: String?): Boolean {
    if (url.isNullOrBlank()) return false
    val path = Uri.parse(url).path.orEmpty()
    return path.startsWith("/login") || path.startsWith("/register")
}

fun siteUrl(path: String): String {
    val base = BuildConfig.API_BASE_URL.trimEnd('/')
    val clean = if (path.startsWith("/")) path else "/$path"
    return Uri.parse("$base$clean").buildUpon()
        .appendQueryParameter("app", "1")
        .build()
        .toString()
}

private fun pathKey(url: String?): String {
    if (url.isNullOrBlank()) return ""
    return try {
        Uri.parse(url).path?.trimEnd('/')?.ifEmpty { "/" } ?: "/"
    } catch (_: Exception) {
        ""
    }
}

private const val APP_UA_SUFFIX = " PulseDeskApp/1.2.3"

/** Injects viewport class so site CSS can distinguish phone vs tablet in the app shell. */
private fun injectJs(isTablet: Boolean): String {
    val mode = if (isTablet) "pulse-native-tablet" else "pulse-native-phone"
    return """
(function(){
  try {
    var root = document.documentElement;
    root.classList.add('pulse-native-app', '$mode');
    root.classList.remove('${if (isTablet) "pulse-native-phone" else "pulse-native-tablet"}');
    root.setAttribute('data-pulse-app', '${if (isTablet) "tablet" else "phone"}');
  } catch (e) {}
})();
"""
}

@OptIn(ExperimentalMaterial3Api::class)
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun PulseWebShell(
    selectedTab: WebTab,
    isTablet: Boolean = false,
    onUrlChanged: (String?) -> Unit,
    onTabFromWeb: (WebTab) -> Unit,
    modifier: Modifier = Modifier,
) {
    val scope = rememberCoroutineScope()
    var webView by remember { mutableStateOf<WebView?>(null) }
    var loading by remember { mutableStateOf(true) }
    var progress by remember { mutableFloatStateOf(0f) }
    var refreshing by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<String?>(null) }
    var canGoBack by remember { mutableStateOf(false) }
    val tabletNow by rememberUpdatedState(isTablet)

    val targetUrl = remember(selectedTab) { siteUrl(selectedTab.path) }

    LaunchedEffect(targetUrl, webView) {
        val wv = webView ?: return@LaunchedEffect
        val want = pathKey(targetUrl)
        val cur = pathKey(wv.url)
        if (cur != want) {
            loading = true
            errorMessage = null
            wv.loadUrl(targetUrl)
        }
    }

    // Re-stamp phone/tablet class after rotation without full reload.
    LaunchedEffect(isTablet, webView) {
        webView?.evaluateJavascript(injectJs(isTablet), null)
    }

    BackHandler(enabled = canGoBack) {
        webView?.goBack()
    }

    Box(modifier = modifier.fillMaxSize()) {
        PullToRefreshBox(
            isRefreshing = refreshing,
            onRefresh = {
                refreshing = true
                errorMessage = null
                webView?.reload()
                scope.launch {
                    delay(900)
                    refreshing = false
                }
            },
            modifier = Modifier.fillMaxSize(),
        ) {
            AndroidView(
                modifier = Modifier.fillMaxSize(),
                factory = { ctx ->
                    WebView(ctx).apply {
                        layoutParams = ViewGroup.LayoutParams(
                            ViewGroup.LayoutParams.MATCH_PARENT,
                            ViewGroup.LayoutParams.MATCH_PARENT,
                        )
                        settings.javaScriptEnabled = true
                        settings.domStorageEnabled = true
                        settings.loadsImagesAutomatically = true
                        settings.mixedContentMode = WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE
                        settings.cacheMode = WebSettings.LOAD_DEFAULT
                        settings.useWideViewPort = true
                        settings.loadWithOverviewMode = true
                        settings.setSupportZoom(false)
                        settings.builtInZoomControls = false
                        settings.displayZoomControls = false
                        settings.mediaPlaybackRequiresUserGesture = false
                        settings.userAgentString = settings.userAgentString + APP_UA_SUFFIX
                        CookieManager.getInstance().setAcceptCookie(true)
                        CookieManager.getInstance().setAcceptThirdPartyCookies(this, true)
                        isVerticalScrollBarEnabled = false
                        isHorizontalScrollBarEnabled = false
                        overScrollMode = android.view.View.OVER_SCROLL_NEVER

                        webChromeClient = object : WebChromeClient() {
                            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                                progress = newProgress / 100f
                                loading = newProgress < 100
                            }
                        }

                        webViewClient = object : WebViewClient() {
                            override fun shouldOverrideUrlLoading(
                                view: WebView?,
                                request: WebResourceRequest?,
                            ): Boolean {
                                val uri = request?.url ?: return false
                                val host = uri.host.orEmpty()
                                val appHost = Uri.parse(BuildConfig.API_BASE_URL).host.orEmpty()
                                if (host.isNotEmpty() && appHost.isNotEmpty() &&
                                    !host.equals(appHost, ignoreCase = true)
                                ) {
                                    try {
                                        ctx.startActivity(
                                            Intent(Intent.ACTION_VIEW, uri).addFlags(
                                                Intent.FLAG_ACTIVITY_NEW_TASK,
                                            ),
                                        )
                                    } catch (_: Exception) {
                                        // ignore
                                    }
                                    return true
                                }
                                return false
                            }

                            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                                loading = true
                                errorMessage = null
                                canGoBack = view?.canGoBack() == true
                                onUrlChanged(url)
                                // Early class so first paint uses app layout (avoids flash of web chrome)
                                view?.evaluateJavascript(injectJs(tabletNow), null)
                                webTabFromUrl(url)?.let(onTabFromWeb)
                            }

                            override fun onPageFinished(view: WebView?, url: String?) {
                                loading = false
                                refreshing = false
                                canGoBack = view?.canGoBack() == true
                                onUrlChanged(url)
                                view?.evaluateJavascript(injectJs(tabletNow), null)
                                CookieManager.getInstance().flush()
                                webTabFromUrl(url)?.let(onTabFromWeb)
                            }

                            override fun onReceivedError(
                                view: WebView?,
                                request: WebResourceRequest?,
                                error: WebResourceError?,
                            ) {
                                if (request?.isForMainFrame == true) {
                                    loading = false
                                    refreshing = false
                                    errorMessage = "网络不稳定或服务唤醒中，请下拉重试"
                                }
                            }
                        }

                        webView = this
                        loadUrl(targetUrl)
                    }
                },
            )
        }

        if (loading && errorMessage == null) {
            LinearProgressIndicator(
                progress = { progress.coerceIn(0f, 1f) },
                modifier = Modifier
                    .fillMaxWidth()
                    .align(Alignment.TopCenter),
            )
        }

        if (errorMessage != null) {
            Column(
                modifier = Modifier
                    .fillMaxSize()
                    .background(MaterialTheme.colorScheme.background.copy(alpha = 0.96f))
                    .padding(24.dp),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally,
            ) {
                if (loading) {
                    CircularProgressIndicator()
                }
                Text(
                    text = errorMessage ?: "",
                    style = MaterialTheme.typography.bodyLarge,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(top = 16.dp, bottom = 12.dp),
                )
                Text(
                    text = "免费服务首次打开可能需要 20–40 秒唤醒",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                    modifier = Modifier.padding(bottom = 16.dp),
                )
                Button(onClick = {
                    errorMessage = null
                    loading = true
                    webView?.loadUrl(targetUrl)
                }) {
                    Text("重新加载")
                }
            }
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            webView?.apply {
                stopLoading()
                loadUrl("about:blank")
                removeAllViews()
                destroy()
            }
            webView = null
        }
    }
}
