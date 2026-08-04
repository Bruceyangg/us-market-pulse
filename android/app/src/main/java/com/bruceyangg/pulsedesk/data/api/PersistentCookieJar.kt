package com.bruceyangg.pulsedesk.data.api

import android.content.Context
import android.content.SharedPreferences
import okhttp3.Cookie
import okhttp3.CookieJar
import okhttp3.HttpUrl
import org.json.JSONArray
import org.json.JSONObject

/** SharedPreferences-backed CookieJar so pulse_session survives app restarts. */
class PersistentCookieJar(context: Context) : CookieJar {
    private val prefs: SharedPreferences =
        context.applicationContext.getSharedPreferences(PREFS, Context.MODE_PRIVATE)
    private val lock = Any()
    private val store: MutableMap<String, MutableList<Cookie>> = mutableMapOf()

    init {
        load()
    }

    override fun saveFromResponse(url: HttpUrl, cookies: List<Cookie>) {
        if (cookies.isEmpty()) return
        synchronized(lock) {
            val host = url.host
            val bucket = store.getOrPut(host) { mutableListOf() }
            for (cookie in cookies) {
                bucket.removeAll { it.name == cookie.name && it.domain == cookie.domain && it.path == cookie.path }
                if (!cookie.persistent || cookie.expiresAt > System.currentTimeMillis()) {
                    bucket.add(cookie)
                }
            }
            bucket.removeAll { it.expiresAt <= System.currentTimeMillis() }
            persistLocked()
        }
    }

    override fun loadForRequest(url: HttpUrl): List<Cookie> {
        synchronized(lock) {
            val now = System.currentTimeMillis()
            var dirty = false
            val matches = mutableListOf<Cookie>()
            for ((host, cookies) in store) {
                val iter = cookies.iterator()
                while (iter.hasNext()) {
                    val cookie = iter.next()
                    if (cookie.expiresAt <= now) {
                        iter.remove()
                        dirty = true
                        continue
                    }
                    if (host == url.host || cookie.matches(url)) {
                        if (cookie.matches(url)) matches.add(cookie)
                    }
                }
            }
            if (dirty) persistLocked()
            return matches
        }
    }

    fun clear() {
        synchronized(lock) {
            store.clear()
            prefs.edit().clear().apply()
        }
    }

    private fun persistLocked() {
        val root = JSONObject()
        for ((host, cookies) in store) {
            val arr = JSONArray()
            for (cookie in cookies) {
                arr.put(
                    JSONObject()
                        .put("name", cookie.name)
                        .put("value", cookie.value)
                        .put("expiresAt", cookie.expiresAt)
                        .put("domain", cookie.domain)
                        .put("path", cookie.path)
                        .put("secure", cookie.secure)
                        .put("httpOnly", cookie.httpOnly)
                        .put("hostOnly", cookie.hostOnly)
                        .put("persistent", cookie.persistent),
                )
            }
            root.put(host, arr)
        }
        prefs.edit().putString(KEY, root.toString()).apply()
    }

    private fun load() {
        val raw = prefs.getString(KEY, null) ?: return
        runCatching {
            val root = JSONObject(raw)
            val keys = root.keys()
            while (keys.hasNext()) {
                val host = keys.next()
                val arr = root.getJSONArray(host)
                val list = mutableListOf<Cookie>()
                for (i in 0 until arr.length()) {
                    val o = arr.getJSONObject(i)
                    val builder = Cookie.Builder()
                        .name(o.getString("name"))
                        .value(o.getString("value"))
                        .expiresAt(o.getLong("expiresAt"))
                        .path(o.optString("path", "/"))
                    val domain = o.getString("domain")
                    if (o.optBoolean("hostOnly", false)) {
                        builder.hostOnlyDomain(domain)
                    } else {
                        builder.domain(domain)
                    }
                    if (o.optBoolean("secure", false)) builder.secure()
                    if (o.optBoolean("httpOnly", false)) builder.httpOnly()
                    val cookie = builder.build()
                    if (cookie.expiresAt > System.currentTimeMillis()) list.add(cookie)
                }
                if (list.isNotEmpty()) store[host] = list
            }
        }
    }

    companion object {
        private const val PREFS = "pulse_desk_cookies"
        private const val KEY = "jar"
    }
}
