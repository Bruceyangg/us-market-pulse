package com.bruceyangg.pulsedesk.data.api

import android.content.Context
import com.bruceyangg.pulsedesk.BuildConfig
import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import java.util.concurrent.TimeUnit
import java.util.concurrent.atomic.AtomicReference

object NetworkModule {
    private val json = Json {
        ignoreUnknownKeys = true
        isLenient = true
        coerceInputValues = true
    }

    private val cookieJarRef = AtomicReference<PersistentCookieJar?>()
    private val clientRef = AtomicReference<OkHttpClient?>()
    private val apiRef = AtomicReference<PulseApi?>()

    fun init(context: Context) {
        if (cookieJarRef.get() != null) return
        synchronized(this) {
            if (cookieJarRef.get() != null) return
            val jar = PersistentCookieJar(context.applicationContext)
            cookieJarRef.set(jar)
            val logging = HttpLoggingInterceptor().apply {
                level = if (BuildConfig.DEBUG) {
                    HttpLoggingInterceptor.Level.BASIC
                } else {
                    HttpLoggingInterceptor.Level.NONE
                }
            }
            val client = OkHttpClient.Builder()
                .cookieJar(jar)
                .connectTimeout(45, TimeUnit.SECONDS)
                .readTimeout(60, TimeUnit.SECONDS)
                .writeTimeout(45, TimeUnit.SECONDS)
                .addInterceptor(logging)
                .addInterceptor { chain ->
                    chain.proceed(
                        chain.request().newBuilder()
                            .header("Accept", "application/json")
                            .header("User-Agent", "PulseDesk-Android/${BuildConfig.VERSION_NAME}")
                            .build(),
                    )
                }
                .build()
            clientRef.set(client)
            apiRef.set(
                Retrofit.Builder()
                    .baseUrl(BuildConfig.API_BASE_URL)
                    .client(client)
                    .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
                    .build()
                    .create(PulseApi::class.java),
            )
        }
    }

    val cookieJar: PersistentCookieJar
        get() = cookieJarRef.get()
            ?: error("NetworkModule.init(context) must be called before use")

    val api: PulseApi
        get() = apiRef.get()
            ?: error("NetworkModule.init(context) must be called before use")

    fun clearSessionCookies() {
        cookieJarRef.get()?.clear()
    }
}
