package com.bruceyangg.pulsedesk.data.api

import com.bruceyangg.pulsedesk.data.model.EarningsResponse
import com.bruceyangg.pulsedesk.data.model.IntelResponse
import com.bruceyangg.pulsedesk.data.model.MarketsResponse
import com.bruceyangg.pulsedesk.data.model.PortfolioResponse
import com.bruceyangg.pulsedesk.data.model.SectorMapResponse
import com.bruceyangg.pulsedesk.data.model.SectorsResponse
import retrofit2.http.GET
import retrofit2.http.Query

interface PulseApi {
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
        @Query("refresh") refresh: Boolean = false,
    ): IntelResponse

    @GET("api/portfolio")
    suspend fun portfolio(@Query("refresh") refresh: Boolean = false): PortfolioResponse
}
