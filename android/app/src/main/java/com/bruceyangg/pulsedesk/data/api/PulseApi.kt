package com.bruceyangg.pulsedesk.data.api

import com.bruceyangg.pulsedesk.data.model.AuthActionResponse
import com.bruceyangg.pulsedesk.data.model.AuthFormBody
import com.bruceyangg.pulsedesk.data.model.AuthMeResponse
import com.bruceyangg.pulsedesk.data.model.EarningsResponse
import com.bruceyangg.pulsedesk.data.model.HoldingIntelResponse
import com.bruceyangg.pulsedesk.data.model.IntelResponse
import com.bruceyangg.pulsedesk.data.model.MarketsResponse
import com.bruceyangg.pulsedesk.data.model.OkResponse
import com.bruceyangg.pulsedesk.data.model.PortfolioResponse
import com.bruceyangg.pulsedesk.data.model.SectorMapResponse
import com.bruceyangg.pulsedesk.data.model.SectorsResponse
import com.bruceyangg.pulsedesk.data.model.SettingsResponse
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Query

interface PulseApi {
    @GET("api/auth/me")
    suspend fun authMe(): AuthMeResponse

    @POST("api/auth/login")
    suspend fun login(@Body body: AuthFormBody): AuthActionResponse

    @POST("api/auth/register")
    suspend fun register(@Body body: AuthFormBody): AuthActionResponse

    @POST("api/auth/logout")
    suspend fun logout(): OkResponse

    @GET("api/markets")
    suspend fun markets(@Query("refresh") refresh: Boolean = false): MarketsResponse

    @GET("api/sectors")
    suspend fun sectors(
        @Query("sector") sector: String? = null,
        @Query("symbol") symbol: String? = null,
        @Query("refresh") refresh: Boolean = false,
    ): SectorsResponse

    @GET("api/sectors/map")
    suspend fun sectorMap(@Query("refresh") refresh: Boolean = false): SectorMapResponse

    @GET("api/earnings")
    suspend fun earnings(
        @Query("days") days: Int = 31,
        @Query("refresh") refresh: Boolean = false,
    ): EarningsResponse

    @GET("api/intel")
    suspend fun intel(
        @Query("category") category: String = "all",
        @Query("holdings_only") holdingsOnly: Boolean = false,
        @Query("holding") holding: String? = null,
        @Query("refresh") refresh: Boolean = false,
    ): IntelResponse

    @GET("api/portfolio")
    suspend fun portfolio(@Query("refresh") refresh: Boolean = false): PortfolioResponse

    @GET("api/portfolio/intel")
    suspend fun portfolioIntel(
        @Query("symbol") symbol: String? = null,
        @Query("refresh") refresh: Boolean = false,
        @Query("limit") limit: Int = 24,
    ): HoldingIntelResponse

    @GET("api/settings")
    suspend fun settings(): SettingsResponse
}
