package com.bruceyangg.pulsedesk.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.bruceyangg.pulsedesk.data.api.NetworkModule
import com.bruceyangg.pulsedesk.data.model.EarningsResponse
import com.bruceyangg.pulsedesk.data.model.HoldingIntelResponse
import com.bruceyangg.pulsedesk.data.model.IntelResponse
import com.bruceyangg.pulsedesk.data.model.MarketsResponse
import com.bruceyangg.pulsedesk.data.model.PortfolioResponse
import com.bruceyangg.pulsedesk.data.model.SectorMapResponse
import com.bruceyangg.pulsedesk.data.model.SectorsResponse
import com.bruceyangg.pulsedesk.data.model.SettingsResponse
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch
import retrofit2.HttpException

data class UiState<T>(
    val data: T? = null,
    val loading: Boolean = false,
    val refreshing: Boolean = false,
    val error: String? = null,
    val needsLogin: Boolean = false,
)

class MarketsViewModel : ViewModel() {
    private val _state = MutableStateFlow(UiState<MarketsResponse>())
    val state: StateFlow<UiState<MarketsResponse>> = _state.asStateFlow()
    var timeframe: String = "day"
        private set

    fun setTimeframe(tf: String) {
        timeframe = tf
        // Charts are server-side bundled; client filters displayed tf via charts list if present.
        _state.update { it.copy(data = it.data) }
    }

    fun load(force: Boolean = false) {
        viewModelScope.launch {
            _state.update {
                it.copy(loading = it.data == null, refreshing = force || it.data != null, error = null)
            }
            runCatching { NetworkModule.api.markets(refresh = force) }
                .onSuccess { data -> _state.value = UiState(data = data) }
                .onFailure { e ->
                    _state.update {
                        it.copy(loading = false, refreshing = false, error = e.message ?: "加载失败")
                    }
                }
        }
    }
}

class SectorsViewModel : ViewModel() {
    private val _desk = MutableStateFlow(UiState<SectorsResponse>())
    val desk: StateFlow<UiState<SectorsResponse>> = _desk.asStateFlow()

    private val _map = MutableStateFlow(UiState<SectorMapResponse>())
    val map: StateFlow<UiState<SectorMapResponse>> = _map.asStateFlow()

    var sectorId: String? = null
        private set
    var symbol: String? = null
        private set
    var timeframe: String = "day"
        private set

    fun setTimeframe(tf: String) {
        timeframe = tf
        _desk.update { it.copy(data = it.data) }
    }

    fun selectSector(id: String) {
        sectorId = id
        symbol = null
        loadDesk()
    }

    fun selectSymbol(sym: String, deskId: String? = null) {
        if (deskId != null) sectorId = deskId
        symbol = sym
        loadDesk()
    }

    fun load(force: Boolean = false) {
        loadDesk(force)
        loadMap(force)
    }

    fun loadDesk(force: Boolean = false) {
        viewModelScope.launch {
            _desk.update {
                it.copy(loading = it.data == null, refreshing = force || it.data != null, error = null)
            }
            runCatching {
                NetworkModule.api.sectors(
                    sector = sectorId,
                    symbol = symbol,
                    refresh = force,
                )
            }.onSuccess { data ->
                sectorId = data.active_sector_id ?: sectorId
                symbol = data.selected_symbol ?: symbol
                _desk.value = UiState(data = data)
            }.onFailure { e ->
                _desk.update {
                    it.copy(loading = false, refreshing = false, error = e.message ?: "板块加载失败")
                }
            }
        }
    }

    fun loadMap(force: Boolean = false) {
        viewModelScope.launch {
            _map.update {
                it.copy(loading = it.data == null, refreshing = force || it.data != null, error = null)
            }
            runCatching { NetworkModule.api.sectorMap(refresh = force) }
                .onSuccess { data -> _map.value = UiState(data = data) }
                .onFailure { e ->
                    _map.update {
                        it.copy(loading = false, refreshing = false, error = e.message ?: "涨跌图加载失败")
                    }
                }
        }
    }
}

class EarningsViewModel : ViewModel() {
    private val _state = MutableStateFlow(UiState<EarningsResponse>())
    val state: StateFlow<UiState<EarningsResponse>> = _state.asStateFlow()

    fun load(force: Boolean = false) {
        viewModelScope.launch {
            _state.update {
                it.copy(loading = it.data == null, refreshing = force || it.data != null, error = null)
            }
            runCatching { NetworkModule.api.earnings(refresh = force) }
                .onSuccess { data -> _state.value = UiState(data = data) }
                .onFailure { e ->
                    _state.update {
                        it.copy(loading = false, refreshing = false, error = e.message ?: "财报加载失败")
                    }
                }
        }
    }
}

class IntelViewModel : ViewModel() {
    private val _state = MutableStateFlow(UiState<IntelResponse>())
    val state: StateFlow<UiState<IntelResponse>> = _state.asStateFlow()

    fun load(force: Boolean = false) {
        viewModelScope.launch {
            _state.update {
                it.copy(loading = it.data == null, refreshing = force || it.data != null, error = null)
            }
            runCatching { NetworkModule.api.intel(refresh = force) }
                .onSuccess { data -> _state.value = UiState(data = data) }
                .onFailure { e ->
                    _state.update {
                        it.copy(loading = false, refreshing = false, error = e.message ?: "情报加载失败")
                    }
                }
        }
    }
}

class PortfolioViewModel : ViewModel() {
    private val _state = MutableStateFlow(UiState<PortfolioResponse>())
    val state: StateFlow<UiState<PortfolioResponse>> = _state.asStateFlow()
    var timeframe: String = "day"
        private set

    fun setTimeframe(tf: String) {
        timeframe = tf
        _state.update { it.copy(data = it.data) }
    }

    fun load(force: Boolean = false) {
        viewModelScope.launch {
            _state.update {
                it.copy(
                    loading = it.data == null,
                    refreshing = force || it.data != null,
                    error = null,
                    needsLogin = false,
                )
            }
            runCatching { NetworkModule.api.portfolio(refresh = force) }
                .onSuccess { data -> _state.value = UiState(data = data) }
                .onFailure { e ->
                    val login = e is HttpException && e.code() in listOf(401, 403)
                    _state.update {
                        it.copy(
                            loading = false,
                            refreshing = false,
                            needsLogin = login,
                            error = if (login) {
                                "未登录 · 持仓需登录后查看"
                            } else {
                                e.message ?: "持仓加载失败"
                            },
                        )
                    }
                }
        }
    }
}

class HoldingIntelViewModel : ViewModel() {
    private val _state = MutableStateFlow(UiState<HoldingIntelResponse>())
    val state: StateFlow<UiState<HoldingIntelResponse>> = _state.asStateFlow()
    private var selected: String? = null

    fun selectSymbol(symbol: String?) {
        selected = symbol
        load()
    }

    fun load(force: Boolean = false) {
        viewModelScope.launch {
            _state.update {
                it.copy(
                    loading = it.data == null,
                    refreshing = force || it.data != null,
                    error = null,
                    needsLogin = false,
                )
            }
            // Prefer dedicated endpoint; fall back to /api/intel holding_intel for guests.
            val dedicated = runCatching {
                NetworkModule.api.portfolioIntel(symbol = selected, refresh = force)
            }
            if (dedicated.isSuccess) {
                _state.value = UiState(data = dedicated.getOrThrow())
                return@launch
            }
            val err = dedicated.exceptionOrNull()
            if (err is HttpException && err.code() in listOf(401, 403)) {
                val fallback = runCatching {
                    NetworkModule.api.intel(
                        holdingsOnly = true,
                        holding = selected,
                        refresh = force,
                    )
                }
                if (fallback.isSuccess) {
                    val intel = fallback.getOrThrow()
                    val hi = intel.holding_intel
                    if (hi != null) {
                        _state.value = UiState(
                            data = hi.copy(
                                items = if (hi.items.isNotEmpty()) hi.items else intel.items,
                                count = hi.count ?: intel.items.size,
                                total = hi.total ?: intel.items.size,
                            ),
                            needsLogin = hi.symbols.isEmpty() && intel.items.isEmpty(),
                        )
                        return@launch
                    }
                }
                _state.update {
                    it.copy(
                        loading = false,
                        refreshing = false,
                        needsLogin = true,
                        error = "未登录 · 持仓需登录后查看",
                    )
                }
                return@launch
            }
            _state.update {
                it.copy(
                    loading = false,
                    refreshing = false,
                    error = err?.message ?: "持仓情报加载失败",
                )
            }
        }
    }
}

class SettingsViewModel : ViewModel() {
    private val _state = MutableStateFlow(UiState<SettingsResponse>())
    val state: StateFlow<UiState<SettingsResponse>> = _state.asStateFlow()

    fun load(force: Boolean = false) {
        viewModelScope.launch {
            _state.update {
                it.copy(loading = it.data == null, refreshing = force || it.data != null, error = null)
            }
            runCatching { NetworkModule.api.settings() }
                .onSuccess { data -> _state.value = UiState(data = data) }
                .onFailure { e ->
                    _state.update {
                        it.copy(loading = false, refreshing = false, error = e.message ?: "设置加载失败")
                    }
                }
        }
    }
}
