const CATEGORY_LABELS = {
  all: "跨市场情报总览",
  markets: "美股行情与企业动态",
  fed: "利率决议、声明与官员讲话",
  treasury: "收益率、拍卖与财政部动态",
  policy: "SEC、白宫经济与监管政策",
  politics: "影响市场的政治与地缘事件",
};

const KIND_LABELS = {
  fomc: "FOMC",
  fed: "美联储",
  inflation: "通胀",
  labor: "就业",
  treasury: "国债",
};

const state = {
  category: "all",
  sentiment: "all",
  sort: "bearish",
  watchOnly: false,
  q: "",
  eventsById: {},
  marketTf: "intraday",
  markets: null,
  portfolio: null,
  portfolioTf: "intraday",
  portfolioSort: { key: "change_pct", dir: "desc" },
  portfolioPreview: null,
  portfolioSelectBusy: false,
  portfolioSelectPending: null,
  portfolioBoardCache: {},
  holdingToggleBusy: false,
  holdingToggleBusySyms: null,
  intradayPollBusy: false,
  holdingSymbols: null,
  holdingsOnly: false,
  holdingFilter: "",
  holdingIntel: null,
  sectors: null,
  sectorCache: {},
  sectorId: "",
  sectorSymbol: "",
  sectorTf: "intraday",
  sectorPrefetchTimer: null,
  usMarkets: null,
  usFuturesTf: "intraday",
  usMarketsPollBusy: false,
  earnings: null,
  earningsDate: "",
  earningsSession: "all",
  earningsQ: "",
  chartZoom: {},
  chartZoomScope: {},
  chains: null,
  chainId: "",
  chainQ: "",
  chainsBound: false,
};

const CHART_ZOOM_MIN_BARS = 12;
const CHART_ZOOM_STEP = 1.22;
/** Default visible bars for dense candle series so K-lines stay readable. */
const CHART_DEFAULT_VISIBLE = {
  day: 90,
  week: 80,
  month: 72,
  quarter: 64,
  year: 60,
};
const chartZoomData = new Map();

const PORTFOLIO_TF_KEYS = ["intraday", "day", "month", "quarter"];
if (!PORTFOLIO_TF_KEYS.includes(state.portfolioTf)) {
  state.portfolioTf = "intraday";
}
let PAGE = document.body?.dataset?.page || "desk";
const AUTHED = Boolean(document.getElementById("user-chip") || document.getElementById("btn-logout"));
const pageTimers = [];
const PAGE_DATA_TTL_MS = 5 * 60 * 1000;

const els = {
  status: document.getElementById("status-line"),
  indicators: document.getElementById("indicator-grid"),
  indexGrid: document.getElementById("index-grid"),
  chartGrid: document.getElementById("chart-grid"),
  marketsBlurb: document.getElementById("markets-blurb"),
  chartTfNote: document.getElementById("chart-tf-note"),
  tfFilters: document.getElementById("tf-filters"),
  portfolioSection: document.getElementById("portfolio"),
  portfolioBlurb: document.getElementById("portfolio-blurb"),
  holdingRail: document.getElementById("holding-rail"),
  portfolioChart: document.getElementById("portfolio-chart"),
  portfolioTfFilters: document.getElementById("portfolio-tf-filters"),
  portfolioTfNote: document.getElementById("portfolio-tf-note"),
  portfolioManage: document.getElementById("portfolio-manage"),
  portfolioManageBtn: document.getElementById("btn-portfolio-manage"),
  portfolioAddForm: document.getElementById("portfolio-add-form"),
  portfolioSymbol: document.getElementById("portfolio-symbol"),
  portfolioName: document.getElementById("portfolio-name"),
  portfolioSymbolSuggest: document.getElementById("portfolio-symbol-suggest"),
  portfolioLookupHint: document.getElementById("portfolio-lookup-hint"),
  portfolioRemove: document.getElementById("btn-portfolio-remove"),
  portfolioRefresh: document.getElementById("btn-portfolio-refresh"),
  portfolioExport: document.getElementById("btn-portfolio-export"),
  portfolioImport: document.getElementById("portfolio-import"),
  portfolioListHead: document.querySelector("#portfolio .holding-list-head"),
  holdingIntelBlurb: document.getElementById("holding-intel-blurb"),
  holdingIntelChips: document.getElementById("holding-intel-chips"),
  holdingIntelList: document.getElementById("holding-intel-list"),
  holdingIntelRefresh: document.getElementById("btn-holding-intel-refresh"),
  holdingIntelAllLink: document.getElementById("holding-intel-all-link"),
  intelHoldingChips: document.getElementById("intel-holding-chips"),
  filterHoldings: document.getElementById("filter-holdings"),
  agenda: document.getElementById("agenda-rail"),
  agendaBlurb: document.getElementById("agenda-blurb"),
  digest: document.getElementById("digest-line"),
  moodBoard: document.getElementById("mood-board"),
  moodBlurb: document.getElementById("mood-blurb"),
  spotlight: document.getElementById("spotlight-list"),
  spotlightBlurb: document.getElementById("spotlight-blurb"),
  warDeskBlurb: document.getElementById("war-desk-blurb"),
  warLatestUsIran: document.getElementById("war-latest-us-iran"),
  warLatestUkraine: document.getElementById("war-latest-ukraine"),
  warBearishGrid: document.getElementById("war-bearish-grid"),
  warBearishBlurb: document.getElementById("war-bearish-blurb"),
  aiDeskBlurb: document.getElementById("ai-desk-blurb"),
  hotDeskTitle: document.getElementById("hot-desk-title"),
  aiAnalysisCard: document.getElementById("ai-analysis-card"),
  aiNewsList: document.getElementById("ai-news-list"),
  hotSectorsBlurb: document.getElementById("hot-sectors-blurb"),
  sectorMapBlurb: document.getElementById("sector-map-blurb"),
  sectorMapCanvas: document.getElementById("sector-map-canvas"),
  usMarketsBlurb: document.getElementById("us-markets-blurb"),
  usMarketsStrip: document.getElementById("us-markets-strip"),
  usFuturesTfFilters: document.getElementById("us-futures-tf-filters"),
  usFuturesGrid: document.getElementById("us-futures-grid"),
  sectorEtfGrid: document.getElementById("sector-etf-grid"),
  sectorPicksTitle: document.getElementById("sector-picks-title"),
  sectorPicksBlurb: document.getElementById("sector-picks-blurb"),
  sectorPickList: document.getElementById("sector-pick-list"),
  sectorsDesk: document.querySelector(".sectors-desk"),
  sectorPickChart: document.getElementById("sector-pick-chart"),
  sectorTfFilters: document.getElementById("sector-tf-filters"),
  sectorNewsList: document.getElementById("sector-news-list"),
  sectorNewsBlurb: document.getElementById("sector-news-blurb"),
  sectorNewsLink: document.getElementById("sector-news-link"),
  symbolNewsList: document.getElementById("symbol-news-list"),
  symbolNewsBlurb: document.getElementById("symbol-news-blurb"),
  symbolNewsLink: document.getElementById("symbol-news-link"),
  valueChainBlurb: document.getElementById("value-chain-blurb"),
  valueChainBody: document.getElementById("value-chain-body"),
  earningsList: document.getElementById("earnings-list"),
  earningsBlurb: document.getElementById("earnings-blurb"),
  monthChart: document.getElementById("month-chart"),
  monthPanelBlurb: document.getElementById("month-panel-blurb"),
  moveAnalysis: document.getElementById("move-analysis"),
  stockEarnings: document.getElementById("stock-earnings"),
  sectorsRefresh: document.getElementById("btn-sectors-refresh"),
  earningsPageBlurb: document.getElementById("earnings-page-blurb"),
  earningsRefresh: document.getElementById("btn-earnings-refresh"),
  earningsDateTabs: document.getElementById("earnings-date-tabs"),
  earningsSessionFilters: document.getElementById("earnings-session-filters"),
  earningsQ: document.getElementById("earnings-q"),
  earningsMega: document.getElementById("earnings-mega"),
  earningsFocus: document.getElementById("earnings-focus"),
  earningsTable: document.getElementById("earnings-table"),
  earningsTableTitle: document.getElementById("earnings-table-title"),
  earningsTableBlurb: document.getElementById("earnings-table-blurb"),
  earningsCount: document.getElementById("earnings-count"),
  chainsBlurb: document.getElementById("chains-blurb"),
  chainsSearch: document.getElementById("chains-search"),
  chainsQ: document.getElementById("chains-q"),
  chainsSuggest: document.getElementById("chains-suggest"),
  chainsEmpty: document.getElementById("chains-empty"),
  chainsMap: document.getElementById("chains-map"),
  chainsMapTitle: document.getElementById("chains-map-title"),
  chainsMapBlurb: document.getElementById("chains-map-blurb"),
  chainsMindmap: document.getElementById("chains-mindmap"),
  chainsPanels: document.getElementById("chains-panels"),
  briefGrid: document.getElementById("brief-grid"),
  briefBlurb: document.getElementById("brief-blurb"),
  eventRail: document.getElementById("event-rail"),
  eventsBlurb: document.getElementById("events-blurb"),
  dayTimeline: document.getElementById("day-timeline"),
  timelineBlurb: document.getElementById("timeline-blurb"),
  eventDrawer: document.getElementById("event-drawer"),
  eventDrawerTitle: document.getElementById("event-drawer-title"),
  eventDrawerMeta: document.getElementById("event-drawer-meta"),
  eventDrawerTimeline: document.getElementById("event-drawer-timeline"),
  eventDrawerClose: document.getElementById("event-drawer-close"),
  pushStatus: document.getElementById("push-status"),
  pushBlurb: document.getElementById("push-blurb"),
  pushTest: document.getElementById("btn-push-test"),
  saveSettings: document.getElementById("btn-save-settings"),
  settingsForm: document.getElementById("settings-form"),
  watchHits: document.getElementById("watch-hits"),
  feed: document.getElementById("feed-list"),
  blurb: document.getElementById("feed-blurb"),
  filters: document.getElementById("filters"),
  sortFilters: document.getElementById("sort-filters"),
  sentimentFilters: document.getElementById("sentiment-filters"),
  filterWatch: document.getElementById("filter-watch"),
  searchForm: document.getElementById("search-form"),
  searchInput: document.getElementById("search-input"),
  refresh: document.getElementById("btn-refresh"),
  liveBriefPin: document.getElementById("live-brief-pin"),
  liveBriefRail: document.getElementById("live-brief-rail"),
  cfgWebhook: document.getElementById("cfg-webhook"),
  cfgFormat: document.getElementById("cfg-format"),
  cfgInterval: document.getElementById("cfg-interval"),
  cfgTimes: document.getElementById("cfg-times"),
  cfgTz: document.getElementById("cfg-tz"),
  cfgEnabled: document.getElementById("cfg-enabled"),
  cfgKeywords: document.getElementById("cfg-keywords"),
};

function formatNumber(value, unit) {
  const n = Number(value);
  if (value == null || !Number.isFinite(n)) return "—";
  const abs = Math.abs(n);
  const digits = abs >= 100 ? 1 : abs >= 10 ? 2 : 3;
  const text = n.toFixed(digits);
  return unit === "%" ? `${text}%` : text;
}

function formatDelta(delta) {
  const n = Number(delta);
  if (delta == null || !Number.isFinite(n)) return { text: "—", cls: "" };
  const sign = n > 0 ? "+" : "";
  const cls = n > 0 ? "up" : n < 0 ? "down" : "";
  return { text: `${sign}${n.toFixed(3)}`, cls };
}

function relativeTime(iso) {
  if (!iso) return "时间未知";
  const ts = Date.parse(iso);
  if (Number.isNaN(ts)) return "时间未知";
  const diff = Date.now() - ts;
  const mins = Math.round(diff / 60000);
  if (mins < 1) return "刚刚";
  if (mins < 60) return `${mins} 分钟前`;
  const hours = Math.round(mins / 60);
  if (hours < 24) return `${hours} 小时前`;
  const days = Math.round(hours / 24);
  if (days < 14) return `${days} 天前`;
  return new Date(ts).toLocaleDateString("zh-CN", {
    month: "short",
    day: "numeric",
  });
}

function daysLabel(days) {
  if (days == null) return "";
  if (days <= 0) return "今天";
  if (days === 1) return "明天";
  return `${days} 天后`;
}

function renderIndicators(rows) {
  if (!els.indicators) return;
  if (!rows?.length) {
    els.indicators.innerHTML =
      '<p class="empty">暂时无法读取 FRED 指标，请稍后刷新。</p>';
    return;
  }
  els.indicators.innerHTML = rows
    .map((row) => {
      const delta = formatDelta(row.delta);
      return `
        <a class="indicator" href="${row.url}" target="_blank" rel="noopener noreferrer">
          <div class="label">${row.label}</div>
          <div class="value">${formatNumber(row.value, row.unit)}</div>
          <div class="meta">
            <span>${row.date || ""}</span>
            <span class="delta ${delta.cls}">${delta.text}</span>
          </div>
        </a>
      `;
    })
    .join("");
}

function sparklinePath(points, width = 120, height = 36, pad = 2) {
  const vals = (points || [])
    .map((p) => {
      if (!p) return NaN;
      // Candle bars store volume in `v` — prefer close for price sparks
      if (
        p.c != null &&
        (p.o != null || p.h != null || p.l != null)
      ) {
        return Number(p.c);
      }
      return Number(p.v ?? p.c);
    })
    .filter((v) => !Number.isNaN(v));
  if (vals.length < 2) return "";
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const span = max - min || 1;
  const stepX = (width - pad * 2) / (vals.length - 1);
  return vals
    .map((v, i) => {
      const x = pad + i * stepX;
      const y = pad + (1 - (v - min) / span) * (height - pad * 2);
      return `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`;
    })
    .join(" ");
}

// Chinese tape colors: red = up, green = down
const TAPE_UP = "#d92b2b";
const TAPE_DOWN = "#0f8a6a";
const TAPE_UP_SOFT = "rgba(217,43,43,0.14)";
const TAPE_DOWN_SOFT = "rgba(15,138,106,0.12)";

function themeMutedFill() {
  return (
    getComputedStyle(document.documentElement)
      .getPropertyValue("--ink-soft")
      .trim() || "#3a4d63"
  );
}

const MA_PERIODS = [
  { n: 5, label: "MA5", color: "#c47a16" },
  { n: 10, label: "MA10", color: "#2f6f9f" },
  { n: 30, label: "MA30", color: "#0f8a6a" },
  { n: 60, label: "MA60", color: "#a35c2a" },
  { n: 120, label: "MA120", color: "#b42318" },
  { n: 250, label: "MA250", color: "#3a4d63" },
];

const MA_CHART_TFS = new Set(["day", "week", "month", "quarter", "year"]);

function smaSeries(values, period) {
  const out = new Array(values.length).fill(null);
  if (!period || values.length < period) return out;
  let sum = 0;
  for (let i = 0; i < values.length; i += 1) {
    sum += values[i];
    if (i >= period) sum -= values[i - period];
    if (i >= period - 1) out[i] = sum / period;
  }
  return out;
}

function maLegendHtml(activePeriods = MA_PERIODS) {
  if (!activePeriods.length) return "";
  return `<div class="ma-legend" aria-label="均线图例">${activePeriods
    .map(
      (m) =>
        `<span class="ma-legend-item"><i style="background:${m.color}"></i>${escapeHtml(
          m.label
        )}</span>`
    )
    .join("")}</div>`;
}

function clamp(n, lo, hi) {
  return Math.min(hi, Math.max(lo, n));
}

function defaultChartZoom(len, tf, kind) {
  const n = Math.max(2, len || 0);
  if (kind !== "candle" || n <= 96) {
    return { start: 0, count: n };
  }
  const prefer = CHART_DEFAULT_VISIBLE[tf] || 90;
  const count = Math.min(n, Math.max(CHART_ZOOM_MIN_BARS, prefer));
  return { start: Math.max(0, n - count), count };
}

function normalizeChartZoom(z, len) {
  const count = clamp(
    Math.round(z?.count ?? len),
    Math.min(CHART_ZOOM_MIN_BARS, len),
    Math.max(2, len)
  );
  const start = clamp(Math.round(z?.start ?? 0), 0, Math.max(0, len - count));
  return { start, count };
}

function ensureChartZoom(key, scope, len, tf = "day", kind = "candle") {
  const prevLen = state.chartZoomLen?.[key];
  if (!state.chartZoomLen) state.chartZoomLen = {};
  // Reset window when the series grows (e.g. 夜盘 tip appended) or scope changes.
  if (state.chartZoomScope[key] !== scope || (prevLen != null && len > prevLen)) {
    state.chartZoomScope[key] = scope;
    state.chartZoom[key] = defaultChartZoom(len, tf, kind);
  }
  state.chartZoomLen[key] = len;
  state.chartZoom[key] = normalizeChartZoom(state.chartZoom[key], len);
  return state.chartZoom[key];
}

function zoomChartWindow(key, factor, pivot = 0.5) {
  const meta = chartZoomData.get(key);
  if (!meta) return;
  const len = meta.len;
  const z = normalizeChartZoom(state.chartZoom[key], len);
  if (factor === 1 || len <= CHART_ZOOM_MIN_BARS) {
    state.chartZoom[key] = defaultChartZoom(len, meta.tf, meta.kind);
    paintZoomableChart(key);
    return;
  }
  const pivotIdx = z.start + pivot * z.count;
  const nextCount = clamp(
    Math.round(z.count / factor),
    Math.min(CHART_ZOOM_MIN_BARS, len),
    len
  );
  const nextStart = clamp(
    Math.round(pivotIdx - pivot * nextCount),
    0,
    Math.max(0, len - nextCount)
  );
  state.chartZoom[key] = { start: nextStart, count: nextCount };
  paintZoomableChart(key);
}

function panChartWindow(key, deltaBars) {
  const meta = chartZoomData.get(key);
  if (!meta || !deltaBars) return;
  const len = meta.len;
  const z = normalizeChartZoom(state.chartZoom[key], len);
  if (z.count >= len) return;
  state.chartZoom[key] = {
    start: clamp(z.start + deltaBars, 0, len - z.count),
    count: z.count,
  };
  paintZoomableChart(key);
}

function chartLiveRefreshIconHtml() {
  // Clockwise circular arrow (matches the desk refresh glyph).
  return `
    <svg class="chart-live-refresh-icon" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        fill="none"
        stroke="currentColor"
        stroke-width="2.4"
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M20.5 12a8.5 8.5 0 1 1-2.4-5.9"
      />
      <path
        fill="none"
        stroke="currentColor"
        stroke-width="2.4"
        stroke-linecap="round"
        stroke-linejoin="round"
        d="M20.5 4.2v4.6h-4.6"
      />
    </svg>
  `;
}

function chartZoomControlsHtml(zoomed, { showLiveRefresh = false } = {}) {
  return `
    <div class="chart-zoom-bar">
      <button type="button" class="chart-live-refresh${
        showLiveRefresh ? "" : " is-hidden"
      }" data-zoom-act="live-refresh" title="实时刷新分时" aria-label="实时刷新分时">${chartLiveRefreshIconHtml()}</button>
      <span class="chart-zoom-hint">缩放</span>
      <div class="chart-zoom-controls" role="group" aria-label="图表缩放">
        <button type="button" class="chart-zoom-btn" data-zoom-act="out" title="缩小" aria-label="缩小">−</button>
        <button type="button" class="chart-zoom-btn" data-zoom-act="in" title="放大" aria-label="放大">+</button>
        <button type="button" class="chart-zoom-btn chart-zoom-reset${
          zoomed ? "" : " is-hidden"
        }" data-zoom-act="reset" title="重置" aria-label="重置缩放">重置</button>
      </div>
    </div>
  `;
}

async function refreshChartLive(key) {
  const meta = chartZoomData.get(key);
  if (!meta || meta.tf !== "intraday") return;
  const btn = meta.root?.querySelector('[data-zoom-act="live-refresh"]');
  if (btn) {
    btn.classList.add("is-busy");
    btn.disabled = true;
  }
  try {
    if (String(key || "").startsWith("us-fut-")) {
      await loadUsMarketsDesk({ force: true });
    } else {
      await refreshActiveIntraday({ force: true });
    }
  } finally {
    if (btn) {
      btn.classList.remove("is-busy");
      btn.disabled = false;
    }
  }
}

function renderChartSvg(points, { up = true, viewStart = 0, viewEnd = null } = {}) {
  const width = 320;
  const height = 140;
  const padX = 8;
  const padY = 12;
  const all = (points || [])
    .map((p) => Number(p.v ?? p.c))
    .filter((v) => !Number.isNaN(v));
  const end = viewEnd == null ? all.length : Math.min(all.length, viewEnd);
  const start = clamp(viewStart, 0, Math.max(0, end));
  const vals = all.slice(start, end);
  if (vals.length < 2) {
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="暂无走势"><text x="16" y="72" fill="${themeMutedFill()}" font-size="13">暂无走势数据</text></svg>`;
  }
  const min = Math.min(...vals);
  const max = Math.max(...vals);
  const span = max - min || 1;
  const stepX = (width - padX * 2) / (vals.length - 1);
  const coords = vals.map((v, i) => {
    const x = padX + i * stepX;
    const y = padY + (1 - (v - min) / span) * (height - padY * 2);
    return [x, y];
  });
  const line = coords
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`)
    .join(" ");
  const area = `${line} L${coords[coords.length - 1][0].toFixed(2)},${height} L${coords[0][0].toFixed(2)},${height} Z`;
  const stroke = up ? TAPE_UP : TAPE_DOWN;
  const fill = up ? TAPE_UP_SOFT : TAPE_DOWN_SOFT;
  return `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="分时走势图">
      <path class="intraday-area" d="${area}" fill="${fill}"></path>
      <path class="intraday-line" d="${line}" fill="none" stroke="${stroke}" stroke-width="0.6" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"></path>
    </svg>
  `;
}

const SESSION_LABELS = {
  pre: "盘前",
  regular: "盘中",
  post: "盘后",
  night: "夜盘",
};
const SESSION_LABEL_ORDER = ["盘前", "盘中", "盘后"];

/** Yahoo 1D tape window (ET): 04:00 → 20:00. */
const YAHOO_DAY_START_MINS = 4 * 60;
const YAHOO_DAY_END_MINS = 20 * 60;
const YAHOO_DAY_SPAN_MINS = YAHOO_DAY_END_MINS - YAHOO_DAY_START_MINS;
const YAHOO_TIME_TICKS = [5, 7, 9, 11, 13, 15, 17, 19].map((h) => h * 60);

function etParts(ts) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "America/New_York",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(Number(ts) * 1000));
  let hour = Number(parts.find((p) => p.type === "hour")?.value || 0);
  const minute = Number(parts.find((p) => p.type === "minute")?.value || 0);
  if (hour === 24) hour = 0;
  return { hour, minute, mins: hour * 60 + minute };
}

function sessionIdFromTs(ts) {
  if (!ts) return "regular";
  try {
    const { mins } = etParts(ts);
    if (mins >= 4 * 60 && mins < 9 * 60 + 30) return "pre";
    if (mins >= 9 * 60 + 30 && mins < 16 * 60) return "regular";
    if (mins >= 16 * 60 && mins < 20 * 60) return "post";
    return "night";
  } catch {
    return "regular";
  }
}

function formatEtClockLabel(mins) {
  const h24 = Math.floor(mins / 60) % 24;
  const m = mins % 60;
  const am = h24 < 12;
  const h12 = h24 % 12 || 12;
  const mm = m === 0 ? "" : `:${String(m).padStart(2, "0")}`;
  return `${h12}${mm} ${am ? "AM" : "PM"}`;
}

/** CME equity-index futures 1D: Beijing 06:00 → next day 05:00. */
const FUTURES_BJ_TICK_HOURS = [6, 10, 14, 18, 22, 2, 5];

function bjParts(ts) {
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Shanghai",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(new Date(Number(ts) * 1000));
  let hour = Number(parts.find((p) => p.type === "hour")?.value || 0);
  const minute = Number(parts.find((p) => p.type === "minute")?.value || 0);
  if (hour === 24) hour = 0;
  return { hour, minute, mins: hour * 60 + minute };
}

function formatBjClockLabel(hour) {
  return `${String(hour % 24).padStart(2, "0")}:00`;
}

function futuresCycleBounds(points, cycleStart, cycleEnd) {
  const start = Number(cycleStart);
  const end = Number(cycleEnd);
  if (Number.isFinite(start) && Number.isFinite(end) && end > start) {
    return { start, end };
  }
  const ts = (points || [])
    .map((p) => Number(p?.t))
    .filter((t) => Number.isFinite(t));
  if (!ts.length) return null;
  const last = Math.max(...ts);
  // Walk back to the active 06:00 BJ open for this tape.
  const d = new Date(last * 1000);
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Shanghai",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(d);
  const y = Number(parts.find((p) => p.type === "year")?.value);
  const mo = Number(parts.find((p) => p.type === "month")?.value);
  const day = Number(parts.find((p) => p.type === "day")?.value);
  const hour = Number(parts.find((p) => p.type === "hour")?.value);
  // Approximate BJ midnight UTC offset (+8); then add 06:00.
  let openMs = Date.UTC(y, mo - 1, day, 6 - 8, 0, 0);
  if (hour < 6) openMs -= 24 * 3600 * 1000;
  const open = Math.floor(openMs / 1000);
  return { start: open, end: open + 23 * 3600 };
}

function formatPriceTick(v) {
  const n = Number(v);
  if (!Number.isFinite(n)) return "";
  if (Math.abs(n) >= 1000) return n.toFixed(1);
  if (Math.abs(n) >= 100) return n.toFixed(2);
  return n.toFixed(2);
}

/** Shared Yahoo 1D 分时 viewBox geometry (holdings + sectors). */
const INTRADAY_VB = {
  width: 360,
  height: 188,
  padL: 6,
  padR: 30,
  padTop: 8,
  padBottom: 18,
};

/** Shared day/month/quarter candle geometry (holdings + sectors). */
const CANDLE_VB = {
  width: 360,
  height: 168,
  padL: 6,
  padR: 30,
  padTop: 8,
  padBottom: 10,
};

function formatBeijingCrosshairTime(ts) {
  const d = new Date(Number(ts) * 1000);
  if (Number.isNaN(d.getTime())) return "—";
  const parts = new Intl.DateTimeFormat("en-US", {
    timeZone: "Asia/Shanghai",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hourCycle: "h23",
  }).formatToParts(d);
  const get = (type) => parts.find((p) => p.type === type)?.value || "";
  let hour = get("hour");
  if (hour === "24") hour = "00";
  return `${get("month")}/${get("day")} ${hour}:${get("minute")} (北京)`;
}

/**
 * Build hit-test model for 分时 (same filter/axis as the SVG renderer).
 * Shared by holdings + sectors charts.
 */
function buildIntradayHitModel(
  points,
  { viewStart = 0, viewEnd = null, previousClose = null } = {}
) {
  const { width, height, padL, padR, padTop, padBottom } = INTRADAY_VB;
  const plotW = width - padL - padR;
  const plotH = height - padTop - padBottom;
  let view = (points || [])
    .filter((p) => p && Number.isFinite(Number(p.v ?? p.c)) && p.t != null)
    .map((p) => ({ ...p, _mins: etParts(p.t).mins }))
    .filter(
      (p) => p._mins >= YAHOO_DAY_START_MINS && p._mins <= YAHOO_DAY_END_MINS
    )
    .sort((a, b) => a._mins - b._mins || Number(a.t) - Number(b.t));
  const end = viewEnd == null ? view.length : Math.min(view.length, viewEnd);
  const start = clamp(viewStart, 0, Math.max(0, end));
  if (!(start === 0 && end >= view.length)) {
    view = view.slice(start, end);
  }
  if (view.length < 2) return null;

  const prev =
    previousClose != null && Number.isFinite(Number(previousClose))
      ? Number(previousClose)
      : null;
  const vals = view.map((p) => Number(p.v ?? p.c));
  let min = Math.min(...vals);
  let max = Math.max(...vals);
  if (prev != null) {
    min = Math.min(min, prev);
    max = Math.max(max, prev);
  }
  const pad = (max - min) * 0.06 || Math.abs(max) * 0.002 || 0.01;
  min -= pad;
  max += pad;
  const span = max - min || 1;
  const yOf = (v) => padTop + (1 - (v - min) / span) * plotH;
  const xOfMins = (mins) =>
    padL +
    (clamp(mins, YAHOO_DAY_START_MINS, YAHOO_DAY_END_MINS) -
      YAHOO_DAY_START_MINS) /
      YAHOO_DAY_SPAN_MINS *
      plotW;

  const samples = view.map((p) => {
    const price = Number(p.v ?? p.c);
    return {
      t: Number(p.t),
      price,
      mins: p._mins,
      x: xOfMins(p._mins),
      y: yOf(price),
    };
  });

  return {
    width,
    height,
    padL,
    padR,
    padTop,
    padBottom,
    plotW,
    plotH,
    min,
    max,
    prev,
    yOf,
    xOfMins,
    samples,
  };
}

/**
 * Index-futures 主连 1D: chronological X on Beijing 06:00→05:00 axis.
 * Do not reuse equity ET clock mapping (that draws the diagonal slash).
 */
function buildFuturesHitModel(
  points,
  {
    viewStart = 0,
    viewEnd = null,
    previousClose = null,
    cycleStart = null,
    cycleEnd = null,
  } = {}
) {
  const { width, height, padL, padR, padTop, padBottom } = INTRADAY_VB;
  const plotW = width - padL - padR;
  const plotH = height - padTop - padBottom;
  let view = (points || [])
    .filter((p) => p && Number.isFinite(Number(p.v ?? p.c)) && p.t != null)
    .map((p) => ({ ...p, t: Number(p.t), v: Number(p.v ?? p.c) }))
    .sort((a, b) => a.t - b.t);
  const bounds = futuresCycleBounds(view, cycleStart, cycleEnd);
  if (!bounds) return null;
  const { start, end } = bounds;
  view = view.filter((p) => p.t >= start && p.t <= end);
  const sliceEnd = viewEnd == null ? view.length : Math.min(view.length, viewEnd);
  const sliceStart = clamp(viewStart, 0, Math.max(0, sliceEnd));
  if (!(sliceStart === 0 && sliceEnd >= view.length)) {
    view = view.slice(sliceStart, sliceEnd);
  }
  if (view.length < 2) return null;

  const prev =
    previousClose != null && Number.isFinite(Number(previousClose))
      ? Number(previousClose)
      : null;
  const vals = view.map((p) => p.v);
  let min = Math.min(...vals);
  let max = Math.max(...vals);
  if (prev != null) {
    min = Math.min(min, prev);
    max = Math.max(max, prev);
  }
  const pad = (max - min) * 0.06 || Math.abs(max) * 0.002 || 0.01;
  min -= pad;
  max += pad;
  const span = max - min || 1;
  const axisSpan = Math.max(1, end - start);
  const yOf = (v) => padTop + (1 - (v - min) / span) * plotH;
  const xOfT = (t) =>
    padL + (clamp(Number(t), start, end) - start) / axisSpan * plotW;

  const samples = view.map((p) => ({
    t: p.t,
    price: p.v,
    mins: bjParts(p.t).mins,
    x: xOfT(p.t),
    y: yOf(p.v),
  }));

  return {
    width,
    height,
    padL,
    padR,
    padTop,
    padBottom,
    plotW,
    plotH,
    min,
    max,
    prev,
    yOf,
    xOfT,
    samples,
    cycleStart: start,
    cycleEnd: end,
  };
}

function renderFuturesIntradaySvg(
  points,
  {
    up = true,
    viewStart = 0,
    viewEnd = null,
    previousClose = null,
    cycleStart = null,
    cycleEnd = null,
  } = {}
) {
  const model = buildFuturesHitModel(points, {
    viewStart,
    viewEnd,
    previousClose,
    cycleStart,
    cycleEnd,
  });
  const { width, height, padL, padTop, padBottom, padR } = INTRADAY_VB;
  const plotW = width - padL - padR;
  const plotH = height - padTop - padBottom;
  if (!model) {
    return {
      html: `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="暂无走势"><text x="16" y="96" fill="${themeMutedFill()}" font-size="13">暂无分时数据</text></svg>`,
      hit: null,
    };
  }

  const { prev, min, max, yOf, xOfT, samples, cycleStart: start } = model;
  const coords = samples.map((s) => [s.x, s.y]);
  const stroke = up ? TAPE_UP : TAPE_DOWN;
  const fill = up ? TAPE_UP_SOFT : TAPE_DOWN_SOFT;
  const muted = themeMutedFill();

  const tickTs = FUTURES_BJ_TICK_HOURS.map((h) => {
    // Offset from session open (06:00): wrap past midnight for 02:00 / 05:00.
    let hoursFromOpen = h - 6;
    if (hoursFromOpen < 0) hoursFromOpen += 24;
    return { h, t: start + hoursFromOpen * 3600 };
  });

  const timeLabels = tickTs
    .map(({ h, t }) => {
      const x = xOfT(t);
      return `<text x="${x.toFixed(1)}" y="${(height - 4).toFixed(
        1
      )}" text-anchor="middle" fill="${muted}" font-size="6.2">${escapeHtml(
        formatBjClockLabel(h)
      )}</text>`;
    })
    .join("");

  const priceTicks = [max, (max + min) / 2, min]
    .map((v, i) => {
      const y = yOf(v);
      const anchor = i === 0 ? "hanging" : i === 2 ? "auto" : "middle";
      return `<text x="${(width - 1.5).toFixed(1)}" y="${y.toFixed(
        1
      )}" text-anchor="end" dominant-baseline="${anchor}" fill="${muted}" font-size="6.4">${escapeHtml(
        formatPriceTick(v)
      )}</text>`;
    })
    .join("");

  const prevLine =
    prev != null
      ? `<line x1="${padL}" y1="${yOf(prev).toFixed(2)}" x2="${(
          padL + plotW
        ).toFixed(2)}" y2="${yOf(prev).toFixed(
          2
        )}" stroke="rgba(251,146,60,0.85)" stroke-width="1" stroke-dasharray="4 3"></line>
        <text x="${(padL + 3).toFixed(1)}" y="${(yOf(prev) - 2.5).toFixed(
          1
        )}" fill="${muted}" font-size="6.2">昨收 ${escapeHtml(
          formatPriceTick(prev)
        )}</text>`
      : "";

  const line = coords
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`)
    .join(" ");
  const area = `${line} L${coords[coords.length - 1][0].toFixed(2)},${(
    padTop + plotH
  ).toFixed(2)} L${coords[0][0].toFixed(2)},${(padTop + plotH).toFixed(2)} Z`;

  const last = coords[coords.length - 1];
  const tip = `<circle class="intraday-tip" cx="${last[0].toFixed(
    2
  )}" cy="${last[1].toFixed(
    2
  )}" r="0.9" fill="${stroke}" vector-effect="non-scaling-stroke"></circle>`;

  const html = `
    <svg class="session-intraday-svg futures-intraday-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="指数期货主连分时">
      ${prevLine}
      <path class="intraday-area" d="${area}" fill="${fill}"></path>
      <path class="intraday-line" d="${line}" fill="none" stroke="${stroke}" stroke-width="0.6" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"></path>
      ${tip}
      <g class="intraday-crosshair" visibility="hidden">
        <line class="ch-v" x1="0" y1="${padTop}" x2="0" y2="${(
          padTop + plotH
        ).toFixed(1)}" stroke="rgba(148,163,184,0.85)" stroke-width="1" vector-effect="non-scaling-stroke"></line>
        <line class="ch-h" x1="${padL}" y1="0" x2="${(padL + plotW).toFixed(
          1
        )}" y2="0" stroke="rgba(148,163,184,0.55)" stroke-width="1" stroke-dasharray="3 3" vector-effect="non-scaling-stroke"></line>
        <circle class="ch-dot" cx="0" cy="0" r="1.35" fill="${stroke}" stroke="#fff" stroke-width="0.6" vector-effect="non-scaling-stroke"></circle>
      </g>
      ${timeLabels}
      ${priceTicks}
    </svg>
  `;
  return { html, hit: model };
}

/**
 * Yahoo 1D-style 分时 (盘前→盘中→盘后), shared by holdings + sectors.
 * Fixed ET 04:00–20:00 axis with clock labels and previous-close guide.
 */
function renderSessionIntradaySvg(
  points,
  {
    up = true,
    viewStart = 0,
    viewEnd = null,
    sessions = null,
    previousClose = null,
    cycleStart = null,
  } = {}
) {
  void sessions;
  void cycleStart;
  const model = buildIntradayHitModel(points, {
    viewStart,
    viewEnd,
    previousClose,
  });
  const { width, height, padL, padTop, padBottom, padR } = INTRADAY_VB;
  const plotW = width - padL - padR;
  const plotH = height - padTop - padBottom;
  if (!model) {
    return {
      html: `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="暂无走势"><text x="16" y="96" fill="${themeMutedFill()}" font-size="13">暂无分时数据</text></svg>`,
      hit: null,
    };
  }

  const { prev, min, max, yOf, xOfMins, samples } = model;
  const coords = samples.map((s) => [s.x, s.y]);
  const stroke = up ? TAPE_UP : TAPE_DOWN;
  const fill = up ? TAPE_UP_SOFT : TAPE_DOWN_SOFT;
  const muted = themeMutedFill();
  // Yahoo-style extended-hours bands (avoid red/green so they never clash with tape).
  const PRE_OPEN = 9 * 60 + 30;
  const POST_OPEN = 16 * 60;
  const xPre0 = xOfMins(YAHOO_DAY_START_MINS);
  const xPre1 = xOfMins(PRE_OPEN);
  const xPost0 = xOfMins(POST_OPEN);
  const xPost1 = xOfMins(YAHOO_DAY_END_MINS);
  const preW = Math.max(0, xPre1 - xPre0);
  const postW = Math.max(0, xPost1 - xPost0);
  // Pale flat bands only (no grain) — painted before the tape so they sit behind.
  const sessionBands = `
    <g class="session-bands" aria-hidden="true">
      <rect class="band-pre" x="${xPre0.toFixed(2)}" y="${padTop}" width="${preW.toFixed(
        2
      )}" height="${plotH.toFixed(2)}"></rect>
      <rect class="band-post" x="${xPost0.toFixed(2)}" y="${padTop}" width="${postW.toFixed(
        2
      )}" height="${plotH.toFixed(2)}"></rect>
    </g>`;

  const timeLabels = YAHOO_TIME_TICKS.map((mins) => {
    const x = xOfMins(mins);
    return `<text x="${x.toFixed(1)}" y="${(height - 4).toFixed(
      1
    )}" text-anchor="middle" fill="${muted}" font-size="6.2">${escapeHtml(
      formatEtClockLabel(mins)
    )}</text>`;
  }).join("");

  // Park price labels at the far right so the plot can use a narrower padR.
  const priceTicks = [max, (max + min) / 2, min].map((v, i) => {
    const y = yOf(v);
    const anchor = i === 0 ? "hanging" : i === 2 ? "auto" : "middle";
    return `<text x="${(width - 1.5).toFixed(1)}" y="${y.toFixed(
      1
    )}" text-anchor="end" dominant-baseline="${anchor}" fill="${muted}" font-size="6.4">${escapeHtml(
      formatPriceTick(v)
    )}</text>`;
  }).join("");

  const prevLine =
    prev != null
      ? `<line x1="${padL}" y1="${yOf(prev).toFixed(2)}" x2="${(
          padL + plotW
        ).toFixed(2)}" y2="${yOf(prev).toFixed(
          2
        )}" stroke="rgba(148,163,184,0.75)" stroke-width="1" stroke-dasharray="4 3"></line>
        <text x="${(padL + 3).toFixed(1)}" y="${(yOf(prev) - 2.5).toFixed(
          1
        )}" fill="${muted}" font-size="6.2">昨收 ${escapeHtml(
          formatPriceTick(prev)
        )}</text>`
      : "";

  const line = coords
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`)
    .join(" ");
  const area = `${line} L${coords[coords.length - 1][0].toFixed(2)},${(
    padTop + plotH
  ).toFixed(2)} L${coords[0][0].toFixed(2)},${(padTop + plotH).toFixed(2)} Z`;

  const last = coords[coords.length - 1];
  const tip = `<circle class="intraday-tip" cx="${last[0].toFixed(
    2
  )}" cy="${last[1].toFixed(
    2
  )}" r="0.9" fill="${stroke}" vector-effect="non-scaling-stroke"></circle>`;

  const html = `
    <svg class="session-intraday-svg yahoo-intraday-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="Yahoo 1D 分时">
      ${sessionBands}
      ${prevLine}
      <path class="intraday-area" d="${area}" fill="${fill}"></path>
      <path class="intraday-line" d="${line}" fill="none" stroke="${stroke}" stroke-width="0.6" stroke-linecap="round" stroke-linejoin="round" vector-effect="non-scaling-stroke"></path>
      ${tip}
      <g class="intraday-crosshair" visibility="hidden">
        <line class="ch-v" x1="0" y1="${padTop}" x2="0" y2="${(
          padTop + plotH
        ).toFixed(1)}" stroke="rgba(148,163,184,0.85)" stroke-width="1" vector-effect="non-scaling-stroke"></line>
        <line class="ch-h" x1="${padL}" y1="0" x2="${(padL + plotW).toFixed(
          1
        )}" y2="0" stroke="rgba(148,163,184,0.55)" stroke-width="1" stroke-dasharray="3 3" vector-effect="non-scaling-stroke"></line>
        <circle class="ch-dot" cx="0" cy="0" r="1.35" fill="${stroke}" stroke="#fff" stroke-width="0.6" vector-effect="non-scaling-stroke"></circle>
      </g>
      ${timeLabels}
      ${priceTicks}
    </svg>
  `;
  return { html, hit: model };
}

function sanitizeCandleBars(points) {
  const bars = (points || []).filter((p) => {
    if (!p) return false;
    const o = Number(p.o);
    const h = Number(p.h);
    const l = Number(p.l);
    const c = Number(p.c);
    if (![o, h, l, c].every((n) => Number.isFinite(n) && n > 0)) return false;
    if (h < l || o > h * 1.05 || c > h * 1.05 || o < l * 0.95 || c < l * 0.95) {
      return false;
    }
    return true;
  });
  if (bars.length < 8) return bars;
  const closes = bars.map((b) => Number(b.c)).sort((a, b) => a - b);
  const median = closes[Math.floor(closes.length / 2)] || 0;
  if (!(median > 0)) return bars;
  const floor = median * 0.08;
  const ceil = median * 40;
  return bars.filter((b) => {
    const h = Number(b.h);
    const l = Number(b.l);
    return l >= floor && h <= ceil;
  });
}

function renderCandleSvg(
  points,
  { showMa = false, viewStart = 0, viewEnd = null } = {}
) {
  const { width, height, padL, padR, padTop, padBottom } = CANDLE_VB;
  const plotW = width - padL - padR;
  const plotH = height - padTop - padBottom;
  const muted = themeMutedFill();
  const bars = sanitizeCandleBars(points);
  if (bars.length < 2) {
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="暂无K线"><text x="16" y="78" fill="${muted}" font-size="11">暂无K线数据</text></svg>`;
  }
  const end = viewEnd == null ? bars.length : Math.min(bars.length, viewEnd);
  const start = clamp(viewStart, 0, Math.max(0, end));
  const viewBars = bars.slice(start, end);
  if (viewBars.length < 2) {
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="暂无K线"><text x="16" y="78" fill="${muted}" font-size="11">暂无K线数据</text></svg>`;
  }

  const closes = bars.map((b) => Number(b.c));
  const maLines = showMa
    ? MA_PERIODS.map((m) => ({
        ...m,
        values: smaSeries(closes, m.n).slice(start, end),
      })).filter((m) => m.values.some((v) => v != null))
    : [];

  const highs = viewBars.map((b) => Number(b.h));
  const lows = viewBars.map((b) => Number(b.l));
  const maVals = maLines.flatMap((m) => m.values.filter((v) => v != null));
  const min = Math.min(...lows, ...(maVals.length ? maVals : [Infinity]));
  const max = Math.max(...highs, ...(maVals.length ? maVals : [-Infinity]));
  const span = max - min || 1;
  const slot = plotW / viewBars.length;
  const bodyW = Math.max(1.8, Math.min(8, slot * 0.68));
  const wickW = Math.max(1.2, Math.min(2.2, bodyW * 0.45));
  const yOf = (price) => padTop + (1 - (price - min) / span) * plotH;

  const shapes = viewBars
    .map((b, i) => {
      const o = Number(b.o);
      const h = Number(b.h);
      const l = Number(b.l);
      const c = Number(b.c);
      const up = c >= o;
      const color = up ? TAPE_UP : TAPE_DOWN;
      const x = padL + i * slot + slot / 2;
      const yHigh = yOf(h);
      const yLow = yOf(l);
      const yOpen = yOf(o);
      const yClose = yOf(c);
      const top = Math.min(yOpen, yClose);
      const bodyH = Math.max(1.4, Math.abs(yClose - yOpen));
      return `
        <line x1="${x.toFixed(2)}" y1="${yHigh.toFixed(2)}" x2="${x.toFixed(
          2
        )}" y2="${yLow.toFixed(2)}" stroke="${color}" stroke-width="${wickW.toFixed(
          2
        )}"></line>
        <rect x="${(x - bodyW / 2).toFixed(2)}" y="${top.toFixed(
          2
        )}" width="${bodyW.toFixed(2)}" height="${bodyH.toFixed(
          2
        )}" fill="${color}"></rect>
      `;
    })
    .join("");

  const maPaths = maLines
    .map((m) => {
      let d = "";
      let started = false;
      m.values.forEach((v, i) => {
        if (v == null || Number.isNaN(v)) {
          started = false;
          return;
        }
        const x = padL + i * slot + slot / 2;
        const y = yOf(v);
        d += `${started ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)} `;
        started = true;
      });
      if (!d) return "";
      return `<path d="${d.trim()}" fill="none" stroke="${
        m.color
      }" stroke-width="1.2" stroke-linecap="round" stroke-linejoin="round" opacity="0.9"></path>`;
    })
    .join("");

  const priceTicks = [max, (max + min) / 2, min].map((v, i) => {
    const y = yOf(v);
    const anchor = i === 0 ? "hanging" : i === 2 ? "auto" : "middle";
    return `<text x="${(width - 1.5).toFixed(1)}" y="${y.toFixed(
      1
    )}" text-anchor="end" dominant-baseline="${anchor}" fill="${muted}" font-size="6.4">${escapeHtml(
      formatPriceTick(v)
    )}</text>`;
  }).join("");

  return `
    <svg class="candle-ohlc-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="K线柱状图 红涨绿跌${
      showMa ? " 含均线" : ""
    }">
      ${shapes}
      ${maPaths}
      ${priceTicks}
    </svg>
  `;
}

function candleChartHtml(points, tf, zoom = null) {
  const showMa = MA_CHART_TFS.has(tf);
  const svg = renderCandleSvg(points, {
    showMa,
    viewStart: zoom?.start ?? 0,
    viewEnd: zoom ? zoom.start + zoom.count : null,
  });
  if (!showMa) return svg;
  const closes = (points || [])
    .map((p) => Number(p?.c))
    .filter((v) => !Number.isNaN(v));
  const active = MA_PERIODS.filter((m) => closes.length >= m.n);
  return `${svg}${maLegendHtml(active.length ? active : MA_PERIODS)}`;
}

function paintZoomableChart(key) {
  const meta = chartZoomData.get(key);
  if (!meta?.root) return;
  const { points, tf, kind, up, root } = meta;
  const len = meta.len;
  const z = ensureChartZoom(key, meta.scope, len, tf, kind);
  const stage = root.querySelector(".chart-zoom-stage");
  const zoomRoot = root.querySelector(".chart-zoom");
  const resetBtn = root.querySelector('[data-zoom-act="reset"]');
  if (!stage) return;
  const full = defaultChartZoom(len, tf, kind);
  const zoomed = z.count < len || z.start !== full.start;
  if (resetBtn) resetBtn.classList.toggle("is-hidden", !zoomed);
  const liveBtn = root.querySelector('[data-zoom-act="live-refresh"]');
  if (liveBtn) liveBtn.classList.toggle("is-hidden", tf !== "intraday");
  if (zoomRoot) zoomRoot.classList.toggle("is-zoomed", zoomed);
  root.querySelectorAll(":scope > .ma-legend").forEach((el) => el.remove());
  // 分时 always uses the session line renderer, even if a stale kind says candle.
  // Never index-slice 分时 — that clipped session tips off the canvas.
  if (tf === "intraday") {
    const linePts = toLineSparkPoints(points);
    const pts = linePts.length ? linePts : points;
    const isFutures =
      meta.axis === "futures_bj" || String(key || "").startsWith("us-fut-");
    const drawn = isFutures
      ? renderFuturesIntradaySvg(pts, {
          up,
          viewStart: 0,
          viewEnd: null,
          previousClose: meta.previousClose,
          cycleStart: meta.cycleStart,
          cycleEnd: meta.cycleEnd,
        })
      : renderSessionIntradaySvg(pts, {
          up,
          viewStart: 0,
          viewEnd: null,
          sessions: meta.sessions,
          previousClose: meta.previousClose,
          cycleStart: meta.cycleStart,
        });
    stage.innerHTML = drawn.html;
    meta.intradayHit = drawn.hit;
    hideIntradayCrosshair(key);
  } else if (kind === "candle") {
    meta.intradayHit = null;
    hideIntradayCrosshair(key);
    // Keep SVG inside the zoom stage; park MA legend as a sibling so it cannot
    // overflow/paint over 个股财报 below when the chart card is height-clipped.
    stage.innerHTML = candleChartHtml(points, tf, z).replace(
      /<div class="ma-legend"[\s\S]*?<\/div>\s*$/,
      ""
    );
    const active = MA_PERIODS.filter((m) => (points || []).length >= m.n);
    if (zoomRoot) {
      zoomRoot.insertAdjacentHTML(
        "afterend",
        maLegendHtml(active.length ? active : MA_PERIODS)
      );
    }
  } else {
    meta.intradayHit = null;
    hideIntradayCrosshair(key);
    stage.innerHTML = renderChartSvg(points, {
      up,
      viewStart: z.start,
      viewEnd: z.start + z.count,
    });
  }
}

function nearestIntradaySample(hit, svgX) {
  const samples = hit?.samples || [];
  if (!samples.length) return null;
  let best = samples[0];
  let bestDist = Math.abs(samples[0].x - svgX);
  for (let i = 1; i < samples.length; i += 1) {
    const d = Math.abs(samples[i].x - svgX);
    if (d < bestDist) {
      best = samples[i];
      bestDist = d;
    }
  }
  return best;
}

function hideIntradayCrosshair(key) {
  const meta = chartZoomData.get(key);
  const root = meta?.root;
  if (!root) return;
  const g = root.querySelector(".intraday-crosshair");
  if (g) g.setAttribute("visibility", "hidden");
  const tip = root.querySelector(".chart-crosshair-tip");
  if (tip) {
    tip.classList.add("is-hidden");
    tip.innerHTML = "";
  }
}

function ensureIntradayCrosshairTip(zoomRoot) {
  if (!zoomRoot) return null;
  let tip = zoomRoot.querySelector(".chart-crosshair-tip");
  if (!tip) {
    tip = document.createElement("div");
    tip.className = "chart-crosshair-tip is-hidden";
    tip.setAttribute("aria-live", "polite");
    zoomRoot.appendChild(tip);
  }
  return tip;
}

function showIntradayCrosshair(key, clientX, clientY) {
  const meta = chartZoomData.get(key);
  if (!meta || meta.tf !== "intraday" || !meta.intradayHit) {
    hideIntradayCrosshair(key);
    return;
  }
  const root = meta.root;
  const svg = root?.querySelector("svg.session-intraday-svg");
  const zoomRoot = root?.querySelector(".chart-zoom");
  const hit = meta.intradayHit;
  if (!svg || !zoomRoot) return;

  const rect = svg.getBoundingClientRect();
  if (!(rect.width > 0) || !(rect.height > 0)) return;
  const svgX = ((clientX - rect.left) / rect.width) * hit.width;
  const sample = nearestIntradaySample(hit, svgX);
  if (!sample) {
    hideIntradayCrosshair(key);
    return;
  }

  const g = svg.querySelector(".intraday-crosshair");
  const v = g?.querySelector(".ch-v");
  const h = g?.querySelector(".ch-h");
  const dot = g?.querySelector(".ch-dot");
  if (g && v && h && dot) {
    g.setAttribute("visibility", "visible");
    v.setAttribute("x1", sample.x.toFixed(2));
    v.setAttribute("x2", sample.x.toFixed(2));
    h.setAttribute("y1", sample.y.toFixed(2));
    h.setAttribute("y2", sample.y.toFixed(2));
    dot.setAttribute("cx", sample.x.toFixed(2));
    dot.setAttribute("cy", sample.y.toFixed(2));
  }

  const tip = ensureIntradayCrosshairTip(zoomRoot);
  if (!tip) return;
  const prev = hit.prev;
  const change =
    prev != null && Number.isFinite(prev) ? sample.price - prev : null;
  const changePct =
    change != null && prev ? (change / prev) * 100 : null;
  const delta = formatDelta(change);
  const tipCls = pctClass(changePct);
  tip.innerHTML = `
    <div class="cht-time">${escapeHtml(formatBeijingCrosshairTime(sample.t))}</div>
    <div class="cht-grid">
      <div><span>价格</span><strong class="${tipCls}">${escapeHtml(
        formatNumber(sample.price, "")
      )}</strong></div>
      <div><span>涨跌额</span><strong class="${delta.cls}">${escapeHtml(
        delta.text
      )}</strong></div>
      <div><span>涨跌幅</span><strong class="${tipCls}">${escapeHtml(
        pctText(changePct)
      )}</strong></div>
    </div>
  `;
  tip.classList.remove("is-hidden");

  // Keep tip inside the chart: prefer above the finger/cursor, flip if needed.
  const zr = zoomRoot.getBoundingClientRect();
  const localX = clientX - zr.left;
  const localY = clientY - zr.top;
  const tipW = tip.offsetWidth || 168;
  const tipH = tip.offsetHeight || 72;
  let left = localX - tipW / 2;
  let top = localY - tipH - 14;
  left = clamp(left, 6, Math.max(6, zr.width - tipW - 6));
  if (top < 6) top = Math.min(localY + 18, Math.max(6, zr.height - tipH - 6));
  tip.style.left = `${left}px`;
  tip.style.top = `${top}px`;
}

function bindIntradayCrosshair(zoomRoot, key) {
  if (!zoomRoot || zoomRoot.dataset.crosshairBound === "1") return;
  zoomRoot.dataset.crosshairBound = "1";
  ensureIntradayCrosshairTip(zoomRoot);
  let activePointer = null;

  const onMove = (event) => {
    if (event.pointerType === "touch" && activePointer == null) return;
    if (activePointer != null && event.pointerId !== activePointer) return;
    // Ignore multi-touch pinch gestures.
    if (event.pointerType === "touch" && zoomRoot._pulsePointers > 1) {
      hideIntradayCrosshair(key);
      return;
    }
    const meta = chartZoomData.get(key);
    if (!meta || meta.tf !== "intraday") {
      hideIntradayCrosshair(key);
      return;
    }
    showIntradayCrosshair(key, event.clientX, event.clientY);
  };

  zoomRoot.addEventListener("pointerdown", (event) => {
    if (event.target.closest("[data-zoom-act]")) return;
    zoomRoot._pulsePointers = (zoomRoot._pulsePointers || 0) + 1;
    if (event.pointerType === "touch") {
      activePointer = event.pointerId;
      try {
        zoomRoot.setPointerCapture(event.pointerId);
      } catch {
        /* ignore */
      }
      showIntradayCrosshair(key, event.clientX, event.clientY);
    }
  });
  zoomRoot.addEventListener("pointermove", onMove);
  zoomRoot.addEventListener("pointerup", (event) => {
    zoomRoot._pulsePointers = Math.max(0, (zoomRoot._pulsePointers || 1) - 1);
    if (event.pointerId === activePointer) {
      activePointer = null;
      hideIntradayCrosshair(key);
    }
  });
  zoomRoot.addEventListener("pointercancel", (event) => {
    zoomRoot._pulsePointers = Math.max(0, (zoomRoot._pulsePointers || 1) - 1);
    if (event.pointerId === activePointer) activePointer = null;
    hideIntradayCrosshair(key);
  });
  zoomRoot.addEventListener("pointerleave", () => {
    if (activePointer == null) hideIntradayCrosshair(key);
  });
}

function bindZoomableChart(
  canvasEl,
  {
    key,
    scope,
    points,
    tf,
    kind,
    up,
    sessions = null,
    previousClose = null,
    cycleStart = null,
    cycleEnd = null,
    axis = null,
  }
) {
  if (!canvasEl) return;
  const list = points || [];
  const len = list.length;
  const prev = chartZoomData.get(key);
  const sameShell =
    prev?.root === canvasEl &&
    prev?.scope === scope &&
    Boolean(canvasEl.querySelector(".chart-zoom-stage"));
  chartZoomData.set(key, {
    root: canvasEl,
    points: list,
    tf,
    kind,
    up,
    scope,
    len,
    sessions,
    previousClose,
    cycleStart,
    cycleEnd,
    axis,
  });
  ensureChartZoom(key, scope, len, tf, kind);
  if (sameShell) {
    paintZoomableChart(key);
    bindIntradayCrosshair(canvasEl.querySelector(".chart-zoom"), key);
    return;
  }
  const z = state.chartZoom[key];
  const full = defaultChartZoom(len, tf, kind);
  const zoomed = z.count < len || z.start !== full.start;
  canvasEl.innerHTML = `
    <div class="chart-zoom" data-zoom-key="${escapeHtml(key)}" tabindex="0" aria-label="可缩放图表：触控板捏合或使用上方缩放按钮">
      ${chartZoomControlsHtml(zoomed, { showLiveRefresh: tf === "intraday" })}
      <div class="chart-zoom-stage"></div>
      <div class="chart-crosshair-tip is-hidden" aria-live="polite"></div>
    </div>
  `;
  paintZoomableChart(key);

  const zoomRoot = canvasEl.querySelector(".chart-zoom");
  if (!zoomRoot) return;
  bindIntradayCrosshair(zoomRoot, key);

  zoomRoot.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-zoom-act]");
    if (!btn || !zoomRoot.contains(btn)) return;
    const act = btn.getAttribute("data-zoom-act");
    if (act === "in") zoomChartWindow(key, CHART_ZOOM_STEP, 0.85);
    else if (act === "out") zoomChartWindow(key, 1 / CHART_ZOOM_STEP, 0.85);
    else if (act === "reset") zoomChartWindow(key, 1);
    else if (act === "live-refresh") {
      event.preventDefault();
      void refreshChartLive(key);
    }
  });

  zoomRoot.addEventListener(
    "wheel",
    (event) => {
      const absX = Math.abs(event.deltaX);
      const absY = Math.abs(event.deltaY);
      // Trackpad pinch → ctrl/meta + wheel (Chrome/Safari/Firefox on macOS).
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault();
        event.stopPropagation();
        const rect = zoomRoot.getBoundingClientRect();
        const pivot =
          rect.width > 0 ? clamp((event.clientX - rect.left) / rect.width, 0, 1) : 0.85;
        const intensity = Math.exp(-event.deltaY * 0.01);
        zoomChartWindow(key, intensity, pivot);
        return;
      }
      const z = normalizeChartZoom(state.chartZoom[key], chartZoomData.get(key)?.len || 0);
      const metaNow = chartZoomData.get(key);
      if (!metaNow || z.count >= metaNow.len) return;
      if (absX > absY && absX > 2) {
        event.preventDefault();
        event.stopPropagation();
        const step = Math.max(1, Math.round(z.count * 0.04));
        panChartWindow(key, event.deltaX > 0 ? step : -step);
      }
    },
    { passive: false }
  );

  // Safari legacy gesture events (pinch).
  let gestureScale = 1;
  zoomRoot.addEventListener(
    "gesturestart",
    (event) => {
      event.preventDefault();
      gestureScale = 1;
    },
    { passive: false }
  );
  zoomRoot.addEventListener(
    "gesturechange",
    (event) => {
      event.preventDefault();
      const next = Number(event.scale) || 1;
      const factor = next / gestureScale;
      gestureScale = next;
      if (!Number.isFinite(factor) || Math.abs(factor - 1) < 0.01) return;
      const rect = zoomRoot.getBoundingClientRect();
      const pivot =
        rect.width > 0 ? clamp((event.clientX - rect.left) / rect.width, 0, 1) : 0.85;
      zoomChartWindow(key, factor, pivot);
    },
    { passive: false }
  );
}

function activeMarketTf(data) {
  let tf = state.marketTf || data?.default_tf || "intraday";
  if (tf === "h24") tf = "intraday";
  const known = (data?.timeframes || []).map((t) => t.id);
  if (known.length && !known.includes(tf)) return data.default_tf || known[0];
  return tf;
}

function tfMeta(data, tfId) {
  return (data?.timeframes || []).find((t) => t.id === tfId) || {
    id: tfId,
    label: tfId,
    blurb: "",
  };
}

function renderMarketCharts(data) {
  if (!els.chartGrid) return;
  const tf = activeMarketTf(data);
  const meta = tfMeta(data, tf);
  const charts =
    (data?.charts_by_tf && data.charts_by_tf[tf]) ||
    data?.charts ||
    [];

  if (els.chartTfNote) {
    els.chartTfNote.textContent = meta.blurb || meta.label || "";
  }

  if (els.tfFilters) {
    els.tfFilters.querySelectorAll("[data-tf]").forEach((btn) => {
      const on = btn.getAttribute("data-tf") === tf;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
  }

  if (!charts.length) {
    els.chartGrid.innerHTML =
      '<p class="empty">该周期暂无走势数据，请稍后刷新或切换其他周期。</p>';
    return;
  }

  els.chartGrid.innerHTML = charts
    .map((chart) => {
      const pct = chart.change_pct;
      const up = !(typeof pct === "number" && pct < 0);
      const pctText =
        typeof pct === "number"
          ? `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`
          : "—";
      const kind = chart.chart || meta.chart || (tf === "intraday" ? "line" : "candle");
      const svg =
        kind === "candle"
          ? candleChartHtml(chart.points || [], tf)
          : renderChartSvg(chart.points || [], { up });
      const chgCls = up ? "up" : "down";
      return `
        <article class="chart-card">
          <div class="chart-head">
            <h3>${escapeHtml(chart.label || chart.short || "")}</h3>
            <span class="range chg ${chgCls}">${escapeHtml(
              meta.label || ""
            )} · 区间 ${pctText}</span>
          </div>
          <div class="chart-canvas">${svg}</div>
          <div class="chart-foot">${escapeHtml(chart.blurb || meta.blurb || "")}</div>
        </article>
      `;
    })
    .join("");
}

function renderMarkets(markets) {
  const data = markets || {};
  state.markets = data;
  if (!state.marketTf || state.marketTf === "h24") {
    state.marketTf = data.default_tf || "intraday";
  }
  const indices = data.indices || [];
  const tf = activeMarketTf(data);

  if (els.marketsBlurb) {
    els.marketsBlurb.textContent = data.source
      ? `来源 ${data.source} · 分时含盘前盘后；日/周/月/年为K线（红涨绿跌，延迟报价）`
      : "分时 · 日 / 周 / 月 / 年 K 线（红涨绿跌）";
  }

  if (els.indexGrid) {
    if (!indices.length) {
      els.indexGrid.innerHTML =
        '<p class="empty">暂时无法读取指数报价，请稍后刷新。</p>';
    } else {
      els.indexGrid.innerHTML = indices
        .map((row) => {
          const pct = row.change_pct;
          const cls =
            pct == null || Number.isNaN(pct) ? "" : pct >= 0 ? "up" : "down";
          const pctText =
            pct == null || Number.isNaN(pct)
              ? "—"
              : `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
          const chg =
            row.change == null || Number.isNaN(row.change)
              ? ""
              : ` · ${row.change >= 0 ? "+" : ""}${Number(row.change).toFixed(
                  row.unit === "%" ? 3 : 2
                )}`;
          const rawSpark =
            row.series?.[tf]?.points ||
            row.series?.intraday?.points ||
            row.series?.day?.points ||
            row.points ||
            [];
          const sparkPoints = rawSpark.map((p) =>
            p && p.c != null && p.v == null ? { t: p.t, v: p.c } : p
          );
          const path = sparklinePath(sparkPoints);
          const stroke = cls === "down" ? TAPE_DOWN : TAPE_UP;
          return `
            <a class="index-card" href="${escapeHtml(
              row.url || "#"
            )}" target="_blank" rel="noopener noreferrer">
              <div class="label">${escapeHtml(row.label || "")}</div>
              <span class="short">${escapeHtml(row.short || "")}</span>
              <div class="value">${formatNumber(row.price, row.unit || "")}</div>
              <div class="chg ${cls}">${pctText}${chg}</div>
              ${
                path
                  ? `<svg class="mini-spark" viewBox="0 0 120 36" preserveAspectRatio="none" aria-hidden="true"><path d="${path}" fill="none" stroke="${stroke}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path></svg>`
                  : ""
              }
            </a>
          `;
        })
        .join("");
    }
  }

  renderMarketCharts(data);
}

function miniCandleSvg(points, { width = 140, height = 42 } = {}) {
  const bars = (points || []).filter(
    (p) => p && [p.o, p.h, p.l, p.c].every((n) => n != null && !Number.isNaN(Number(n)))
  );
  if (bars.length < 2) return "";
  const highs = bars.map((b) => Number(b.h));
  const lows = bars.map((b) => Number(b.l));
  const min = Math.min(...lows);
  const max = Math.max(...highs);
  const span = max - min || 1;
  const padY = 2;
  const slot = width / bars.length;
  const bodyW = Math.max(1.2, Math.min(4.5, slot * 0.55));
  const yOf = (price) => padY + (1 - (price - min) / span) * (height - padY * 2);
  const shapes = bars
    .map((b, i) => {
      const o = Number(b.o);
      const h = Number(b.h);
      const l = Number(b.l);
      const c = Number(b.c);
      const up = c >= o;
      const color = up ? TAPE_UP : TAPE_DOWN;
      const x = i * slot + slot / 2;
      const top = Math.min(yOf(o), yOf(c));
      const bodyH = Math.max(1, Math.abs(yOf(c) - yOf(o)));
      return `<line x1="${x.toFixed(1)}" y1="${yOf(h).toFixed(1)}" x2="${x.toFixed(
        1
      )}" y2="${yOf(l).toFixed(1)}" stroke="${color}" stroke-width="1"></line>
      <rect x="${(x - bodyW / 2).toFixed(1)}" y="${top.toFixed(1)}" width="${bodyW.toFixed(
        1
      )}" height="${bodyH.toFixed(1)}" fill="${color}"></rect>`;
    })
    .join("");
  return `<svg class="spark" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" aria-hidden="true">${shapes}</svg>`;
}

function pctSparkBar(pct) {
  if (typeof pct !== "number" || Number.isNaN(pct)) {
    return `<span class="empty">—</span>`;
  }
  const up = pct >= 0;
  const color = up ? TAPE_UP : TAPE_DOWN;
  const track = "rgba(128,128,128,0.22)";
  const mid = 60;
  const mag = Math.max(4, Math.min(52, Math.abs(pct) * 10));
  const x = up ? mid : mid - mag;
  return `<svg class="spark spark-pct" viewBox="0 0 120 30" preserveAspectRatio="none" aria-hidden="true">
    <line x1="60" y1="4" x2="60" y2="26" stroke="${track}" stroke-width="1"/>
    <rect x="8" y="12" width="104" height="6" rx="3" fill="${track}"/>
    <rect x="${x}" y="12" width="${mag}" height="6" rx="3" fill="${color}"/>
  </svg>`;
}

function toLineSparkPoints(raw) {
  return (raw || [])
    .map((p) => {
      if (!p) return null;
      // Candle bars store volume in `v` — prefer close for line sparks
      const isCandle =
        p.c != null && (p.o != null || p.h != null || p.l != null);
      const v = isCandle ? Number(p.c) : Number(p.v ?? p.c);
      if (Number.isNaN(v)) return null;
      const row = { t: p.t, v };
      if (p.session) row.session = p.session;
      return row;
    })
    .filter(Boolean);
}

function holdingSparkSvg(holding, tf) {
  const want = tf || "intraday";
  // List column always paints a line spark (never mini-candles / pct bars).
  // Only use true intraday series — do not borrow day OHLC from `points`
  // (that made some rows look like short bars / different shapes).
  if (want === "intraday") {
    const sparkPoints = toLineSparkPoints(
      holding?.series?.intraday?.points || []
    );
    const pct =
      holding?.series?.intraday?.change_pct != null
        ? holding.series.intraday.change_pct
        : sparkPoints.length >= 2
          ? ((sparkPoints[sparkPoints.length - 1].v - sparkPoints[0].v) /
              Math.abs(sparkPoints[0].v || 1)) *
            100
          : holding?.change_pct;
    const up = !(typeof pct === "number" && pct < 0);
    const path = sparklinePath(sparkPoints, 120, 30, 2);
    if (!path) {
      return `<svg class="spark spark-empty" viewBox="0 0 120 30" preserveAspectRatio="none" aria-hidden="true"></svg>`;
    }
    const stroke = up ? TAPE_UP : TAPE_DOWN;
    return `<svg class="spark" viewBox="0 0 120 30" preserveAspectRatio="none" aria-hidden="true"><path d="${path}" fill="none" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path></svg>`;
  }

  const series = holding?.series?.[want];
  const points = series?.points || holding?.points || [];
  const kind = series?.chart || "candle";
  const pct =
    series?.change_pct != null
      ? series.change_pct
      : holdingTfPct(holding, want) != null
        ? holdingTfPct(holding, want)
        : holding?.change_pct;
  const up = !(typeof pct === "number" && pct < 0);
  if (kind === "candle") {
    return (
      miniCandleSvg(points, { width: 120, height: 30 }) ||
      `<svg class="spark spark-empty" viewBox="0 0 120 30" preserveAspectRatio="none" aria-hidden="true"></svg>`
    );
  }
  const sparkPoints = toLineSparkPoints(points);
  const path = sparklinePath(sparkPoints, 120, 30, 2);
  if (!path) {
    return `<svg class="spark spark-empty" viewBox="0 0 120 30" preserveAspectRatio="none" aria-hidden="true"></svg>`;
  }
  const stroke = up ? TAPE_UP : TAPE_DOWN;
  return `<svg class="spark" viewBox="0 0 120 30" preserveAspectRatio="none" aria-hidden="true"><path d="${path}" fill="none" stroke="${stroke}" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"></path></svg>`;
}

function holdingTfPct(holding, tf) {
  const series = holding?.series?.[tf];
  const pct = series?.change_pct != null ? series.change_pct : holding?.change_pct;
  return typeof pct === "number" && !Number.isNaN(pct) ? pct : null;
}

function sortedHoldings(holdings, tf) {
  const { key, dir } = state.portfolioSort || { key: "change_pct", dir: "desc" };
  const mul = dir === "asc" ? 1 : -1;
  return [...(holdings || [])].sort((a, b) => {
    let av;
    let bv;
    if (key === "price") {
      av = a.price;
      bv = b.price;
    } else {
      av = holdingTfPct(a, tf);
      bv = holdingTfPct(b, tf);
    }
    if (av == null && bv == null) return 0;
    if (av == null) return 1;
    if (bv == null) return -1;
    if (av === bv) return String(a.symbol).localeCompare(String(b.symbol));
    return av > bv ? mul : -mul;
  });
}

function updatePortfolioSortMarks() {
  if (!els.portfolioListHead) return;
  const { key, dir } = state.portfolioSort || {};
  els.portfolioListHead.querySelectorAll("[data-psort]").forEach((btn) => {
    const on = btn.getAttribute("data-psort") === key;
    btn.classList.toggle("is-active", on);
    const mark = btn.querySelector(".sort-mark");
    if (mark) mark.textContent = on ? (dir === "asc" ? "↑" : "↓") : "";
  });
}

function seriesStats(points, kind) {
  const bars =
    kind === "candle" ? sanitizeCandleBars(points) : (points || []).filter(Boolean);
  if (!bars.length) {
    return { open: null, high: null, low: null, last: null, volume: null };
  }
  if (kind === "candle") {
    const opens = bars.map((b) => Number(b.o)).filter((n) => !Number.isNaN(n));
    const highs = bars.map((b) => Number(b.h)).filter((n) => !Number.isNaN(n));
    const lows = bars.map((b) => Number(b.l)).filter((n) => !Number.isNaN(n));
    const closes = bars.map((b) => Number(b.c)).filter((n) => !Number.isNaN(n));
    const vols = bars
      .map((b) => Number(b.v))
      .filter((n) => !Number.isNaN(n) && n != null);
    return {
      open: opens[0] ?? null,
      high: highs.length ? Math.max(...highs) : null,
      low: lows.length ? Math.min(...lows) : null,
      last: closes[closes.length - 1] ?? null,
      volume: vols.length ? vols.reduce((s, n) => s + n, 0) : null,
    };
  }
  const vals = bars
    .map((b) => Number(b.v != null ? b.v : b.c))
    .filter((n) => !Number.isNaN(n));
  if (!vals.length) {
    return { open: null, high: null, low: null, last: null, volume: null };
  }
  return {
    open: vals[0],
    high: Math.max(...vals),
    low: Math.min(...vals),
    last: vals[vals.length - 1],
    volume: null,
  };
}

function formatCompact(n) {
  if (n == null || Number.isNaN(Number(n))) return "—";
  const v = Number(n);
  const abs = Math.abs(v);
  if (abs >= 1e9) return `${(v / 1e9).toFixed(2)}B`;
  if (abs >= 1e6) return `${(v / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${(v / 1e3).toFixed(1)}K`;
  return formatNumber(v, "");
}

function boardFromHolding(holding) {
  if (!holding) return null;
  return {
    symbol: holding.symbol,
    label: holding.label || holding.name || holding.symbol,
    price: holding.price,
    change: holding.change,
    change_pct: holding.change_pct,
    unit: holding.unit || "",
    series: holding.series || {},
    points: holding.points || [],
  };
}

function activePortfolioBoard(data) {
  const previewSym = state.portfolioPreview;
  if (previewSym) {
    const hit = (data?.holdings || []).find((h) => h.symbol === previewSym);
    if (hit) return { board: boardFromHolding(hit), preview: true };
  }
  if (data?.selected_board) {
    return { board: data.selected_board, preview: false };
  }
  const selected = data?.selected;
  const hit = (data?.holdings || []).find((h) => h.symbol === selected);
  if (hit) return { board: boardFromHolding(hit), preview: false };
  const first = (data?.holdings || [])[0];
  return first
    ? { board: boardFromHolding(first), preview: false }
    : { board: null, preview: false };
}

function renderPortfolioChart() {
  const data = state.portfolio || {};
  const tf = state.portfolioTf || data.default_tf || "intraday";
  const meta =
    (data.timeframes || []).find((t) => t.id === tf) || {
      id: tf,
      label: tf,
      blurb: "",
      chart: tf === "intraday" ? "line" : "candle",
    };

  if (els.portfolioTfNote) {
    els.portfolioTfNote.textContent = holdingsCountNote(data, meta);
  }
  if (els.portfolioTfFilters) {
    els.portfolioTfFilters.querySelectorAll("[data-ptf]").forEach((btn) => {
      const on = btn.getAttribute("data-ptf") === tf;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
  }
  if (!els.portfolioChart) return;

  const { board, preview } = activePortfolioBoard(data);
  if (!board) {
    els.portfolioChart.classList.add("is-empty");
    els.portfolioChart.classList.remove("is-preview");
    els.portfolioChart.innerHTML =
      '<p class="chart-placeholder">添加持仓后，中间将显示分时 / K 线详情</p>';
    return;
  }

  // Same series resolution as sectors desk — one paint path for list spark + chart
  const pick = {
    ...board,
    name: board.label || board.name || board.symbol,
  };
  const resolved = resolveSectorChartSeries(pick, tf);
  const series = resolved.series;
  const points = resolved.points;
  const kind = resolved.kind;

  if (points.length < 2) {
    const tfLabel =
      { intraday: "分时", day: "日图", month: "月图", quarter: "季图" }[tf] ||
      "走势";
    els.portfolioChart.classList.remove("is-empty");
    els.portfolioChart.classList.toggle("is-preview", Boolean(preview));
    els.portfolioChart.innerHTML = `
      <div class="chart-head">
        <h3>${escapeHtml(pick.name || "")} · ${escapeHtml(
          pick.symbol || ""
        )}${preview ? '<span class="preview-tag">预览</span>' : ""}</h3>
      </div>
      ${deskStatsBlockHtml(pick, { open: null, high: null, low: null })}
      <p class="chart-placeholder">暂无${escapeHtml(
        tfLabel
      )}数据 · 点右上角刷新重试</p>
    `;
    return;
  }

  const zoomWin = defaultChartZoom(points.length, tf, kind);
  const viewPoints = points.slice(zoomWin.start, zoomWin.start + zoomWin.count);
  const pct =
    series?.change_pct != null && kind === "line"
      ? series.change_pct
      : viewPoints.length >= 2
        ? kind === "candle"
          ? ((Number(viewPoints[viewPoints.length - 1].c) -
              Number(viewPoints[0].o ?? viewPoints[0].c)) /
              Math.abs(Number(viewPoints[0].o ?? viewPoints[0].c) || 1)) *
            100
          : ((Number(
              viewPoints[viewPoints.length - 1].v ??
                viewPoints[viewPoints.length - 1].c
            ) -
              Number(viewPoints[0].v ?? viewPoints[0].c)) /
              Math.abs(Number(viewPoints[0].v ?? viewPoints[0].c) || 1)) *
            100
        : series?.change_pct != null
          ? series.change_pct
          : pick.change_pct;
  const up = !(typeof pct === "number" && pct < 0);
  const stats = seriesStats(viewPoints.length ? viewPoints : points, kind);
  const maNote = MA_CHART_TFS.has(tf) ? " · 含均线" : "";
  const sessionNote =
    tf === "intraday" ? " · Yahoo 1D 分时（美东时间）" : "";

  els.portfolioChart.classList.remove("is-empty");
  els.portfolioChart.classList.toggle("is-preview", Boolean(preview));
  els.portfolioChart.innerHTML = `
    <div class="chart-head">
      <h3>${escapeHtml(pick.name || "")} · ${escapeHtml(pick.symbol || "")}${
        pick.is_wave ? '<span class="hot-tag">涨势</span>' : ""
      }${preview ? '<span class="preview-tag">预览</span>' : ""}</h3>
    </div>
    ${deskStatsBlockHtml(pick, stats)}
    <div class="chart-canvas" data-zoom-host="portfolio"></div>
    <div class="chart-foot">红涨绿跌${maNote}${sessionNote} · ${escapeHtml(
      pick.sector_label || "持仓"
    )}</div>
  `;
  bindZoomableChart(els.portfolioChart.querySelector("[data-zoom-host]"), {
    key: "portfolio",
    scope: `${pick.symbol || ""}:${tf}`,
    points,
    tf,
    kind,
    up,
    sessions: series?.sessions || null,
    previousClose: series?.previous_close ?? null,
    cycleStart: series?.cycle_start ?? null,
  });
}

function holdingsCountNote(data, meta) {
  const n = (data?.holdings || []).length;
  if (!n) return "打开「管理持仓」添加代码；支持导出 / 导入备份";
  const waveN = (data?.holdings || []).filter((h) => h.is_wave).length;
  return `${n} 只持仓 · ${waveN} 只涨势 · ${meta?.label || "分时"} · 点选看走势 · ↑↓ 切换`;
}

function renderPortfolio(data) {
  state.portfolio = data || null;
  const holdings = data?.holdings || [];
  const selected =
    data?.selected || data?.selected_symbol || holdings[0]?.symbol || "";
  const selectedBoard =
    data?.selected_board ||
    holdings.find((h) => h.symbol === selected) ||
    null;
  const tf = state.portfolioTf || data?.default_tf || "intraday";
  const meta =
    (data?.timeframes || []).find((t) => t.id === tf) || {
      id: tf,
      label: tf,
    };

  if (els.portfolioBlurb) {
    els.portfolioBlurb.textContent =
      data?.note ||
      `自定义股票 · 云端同步 · 最多 ${data?.max_holdings || 20} 只 · 红涨绿跌`;
  }

  const titleEl = document.getElementById("portfolio-picks-title");
  if (titleEl) titleEl.textContent = "我的持仓";

  if (els.holdingRail) {
    if (!holdings.length) {
      els.holdingRail.innerHTML =
        '<p class="empty">还没有持仓，点右上角「管理持仓」添加美股代码。</p>';
    } else {
      const rows = sortedHoldings(holdings, "intraday");
      els.holdingRail.innerHTML = rows
        .map((h) => {
          // List tape matches sectors: day % + 24h spark (not desk TF)
          const pct = h.change_pct;
          const on = h.symbol === selected;
          const sparkSrc =
            on && selectedBoard?.series?.intraday?.points?.length >= 2
              ? selectedBoard
              : h;
          return `
            <div class="holding-row sector-pick-row ${
              on ? "is-active" : ""
            } ${pctClass(pct)}" data-holding="${escapeHtml(
              h.symbol
            )}" data-symbol="${escapeHtml(h.symbol)}" role="option" aria-selected="${
              on ? "true" : "false"
            }">
              <button type="button" class="sector-pick-main" data-holding="${escapeHtml(
                h.symbol
              )}" data-symbol="${escapeHtml(h.symbol)}">
                <span class="meta">
                  <span class="nm">${escapeHtml(h.name || h.label || h.symbol)}${
                    h.is_wave
                      ? '<span class="hot-tag">涨势</span>'
                      : h.is_strong
                        ? '<span class="hot-tag">强</span>'
                        : ""
                  }</span>
                  <span class="sym">${escapeHtml(h.symbol)} · ${escapeHtml(
                    h.sector_label || "持仓"
                  )} · 月 ${escapeHtml(pctText(h.month_change_pct))}</span>
                </span>
                <span class="spark-wrap">${holdingSparkSvg(
                  sparkSrc,
                  "intraday"
                )}</span>
                ${listQuoteHtml(h)}
              </button>
              <button
                type="button"
                class="sector-hold-btn is-held"
                data-hold-symbol="${escapeHtml(h.symbol)}"
                data-hold-name="${escapeHtml(h.name || "")}"
                data-hold-action="remove"
                title="从持仓移除 ${escapeHtml(h.symbol)}"
                aria-label="从持仓移除 ${escapeHtml(h.symbol)}"
              >−</button>
            </div>
          `;
        })
        .join("");
      els.holdingRail
        .querySelectorAll(".sector-hold-btn[data-hold-symbol]")
        .forEach((btn) => {
          btn.addEventListener("click", (event) => {
            event.preventDefault();
            event.stopPropagation();
            const sym = btn.getAttribute("data-hold-symbol") || "";
            if (!sym) return;
            if (!confirm(`确定从持仓移除 ${sym}？`)) return;
            toggleSectorHolding(sym);
          });
        });
    }
  }
  if (els.portfolioTfNote) {
    els.portfolioTfNote.textContent = holdingsCountNote(data, meta);
  }
  renderPortfolioChart();
  renderPortfolioFocus(data);
}

function cachePortfolioBoard(board) {
  const sym = String(board?.symbol || "").toUpperCase();
  if (!sym || !board) return;
  if (!state.portfolioBoardCache) state.portfolioBoardCache = {};
  if (pickHasChart(board) || (board.series?.intraday?.points || []).length >= 2) {
    state.portfolioBoardCache[sym] = board;
  }
}

function applyPortfolioSelectionLocal(symbol) {
  const data = state.portfolio;
  if (!data) return null;
  const holdings = data.holdings || [];
  const hit = holdings.find((h) => h.symbol === symbol);
  if (!hit) return null;
  const cached = state.portfolioBoardCache?.[symbol];
  const board =
    cached && (pickHasChart(cached) || (cached.series?.intraday?.points || []).length >= 2)
      ? { ...hit, ...cached, symbol }
      : hit;
  const nextHoldings = holdings.map((h) =>
    h.symbol === symbol ? { ...h, ...board, symbol } : h
  );
  state.portfolio = {
    ...data,
    holdings: nextHoldings,
    selected: symbol,
    selected_symbol: symbol,
    selected_board: board,
    board,
    selected_earnings: board.earnings || data.selected_earnings || null,
    value_chain: board.value_chain || data.value_chain || null,
  };
  state.portfolioPreview = null;
  return state.portfolio;
}

function mergePortfolioSelectResponse(symbol, res) {
  const rawBoard = res?.selected_board || res?.board || res?.portfolio?.selected_board;
  const prevBoard =
    state.portfolio?.selected_board?.symbol === symbol
      ? state.portfolio.selected_board
      : state.portfolioBoardCache?.[symbol] ||
        (state.portfolio?.holdings || []).find((h) => h.symbol === symbol);
  const board = mergeListQuoteFields(
    mergePickPreserveIntraday(rawBoard, prevBoard),
    prevBoard
  );
  if (board) cachePortfolioBoard(board);
  if (res?.portfolio?.holdings) {
    for (const h of res.portfolio.holdings) cachePortfolioBoard(h);
  }
  if (state.portfolio?.selected !== symbol) return;
  if (board) {
    const holdings = (state.portfolio.holdings || []).map((h) =>
      h.symbol === symbol
        ? mergePickPreserveIntraday({ ...h, ...board, symbol }, h)
        : h
    );
    state.portfolio = {
      ...state.portfolio,
      holdings,
      selected: symbol,
      selected_symbol: symbol,
      selected_board: board,
      board,
      selected_earnings: res.selected_earnings || board.earnings || null,
      value_chain: res.value_chain || board.value_chain || null,
    };
    // Chart + focus only — avoid rebuilding the whole holdings list on every /select.
    if (els.holdingRail?.querySelector(`[data-holding="${symbol}"]`)) {
      paintPortfolioSelection();
      refreshActiveRowQuote(els.holdingRail, board, "data-holding");
    } else {
      renderPortfolio(state.portfolio);
    }
    persistPageDataCache();
    return;
  }
  if (res?.portfolio) {
    state.portfolio = res.portfolio;
    for (const h of res.portfolio.holdings || []) cachePortfolioBoard(h);
    renderPortfolio(state.portfolio);
    persistPageDataCache();
  }
}

async function selectPortfolioSymbol(symbol, { quiet = false } = {}) {
  const sym = String(symbol || "").trim().toUpperCase();
  if (!sym) return;
  // Only skip network when day/month candles already exist.
  // Intraday-only boards still need /select to unlock 日/月/季.
  if (
    sym === state.portfolio?.selected &&
    pickHasChart(state.portfolio?.selected_board)
  ) {
    state.portfolioPreview = null;
    paintPortfolioSelection();
    if (PAGE === "desk") loadHoldingIntel({ symbol: sym, soft: true });
    return;
  }
  // Paint instantly from local list / board cache — never block the UI on /select.
  const painted = applyPortfolioSelectionLocal(sym);
  if (painted) {
    paintPortfolioSelection();
    setStatus(`已切换 ${painted.selected_board?.name || sym}`);
    if (PAGE === "desk") loadHoldingIntel({ symbol: sym, soft: true });
  }
  // Coalesce rapid clicks — only the latest symbol hits the network.
  state.portfolioSelectPending = sym;
  if (state.portfolioSelectBusy) return;
  state.portfolioSelectBusy = true;
  try {
    while (state.portfolioSelectPending) {
      const target = state.portfolioSelectPending;
      state.portfolioSelectPending = null;
      try {
        const data = await portfolioPost("/api/portfolio/select", {
          symbol: target,
        });
        if (state.portfolioSelectPending) continue;
        mergePortfolioSelectResponse(target, data);
      } catch (err) {
        if (!quiet && !state.portfolioSelectPending && els.portfolioBlurb) {
          els.portfolioBlurb.textContent = `详情刷新失败：${err.message || err}`;
        }
      }
    }
  } finally {
    state.portfolioSelectBusy = false;
  }
}

async function ensurePortfolioSelection(data) {
  const holdings = data?.holdings || [];
  if (!holdings.length) return data;
  const selected = data.selected;
  const hasBoard = Boolean(data.selected_board);
  const valid = selected && holdings.some((h) => h.symbol === selected);
  if (valid && hasBoard) return data;
  const target = (valid && selected) || holdings[0].symbol;
  // Already have a valid selection — fill a local board stub so add/remove
  // never hangs on a second /select round-trip while quotes are still loading.
  if (valid && !hasBoard) {
    return {
      ...data,
      selected: target,
      selected_board: boardFromHolding(
        holdings.find((h) => h.symbol === target) || holdings[0]
      ),
    };
  }
  try {
    const res = await portfolioPost("/api/portfolio/select", { symbol: target });
    if (res?.portfolio) return res.portfolio;
    if (res?.selected_board) {
      const board = res.selected_board;
      cachePortfolioBoard(board);
      return {
        ...data,
        selected: target,
        selected_symbol: target,
        selected_board: board,
        board,
        selected_earnings: res.selected_earnings || board.earnings,
        value_chain: res.value_chain || board.value_chain,
        holdings: holdings.map((h) =>
          h.symbol === target ? { ...h, ...board, symbol: target } : h
        ),
      };
    }
    return data;
  } catch {
    return {
      ...data,
      selected: target,
      selected_board: boardFromHolding(
        holdings.find((h) => h.symbol === target) || holdings[0]
      ),
    };
  }
}

async function loadPortfolio({ refresh = false } = {}) {
  if (PAGE === "desk" && !AUTHED) return null;
  try {
    const res = await fetch(`/api/portfolio${refresh ? "?refresh=true" : ""}`, {
      credentials: "same-origin",
    });
    if (res.status === 401) {
      if (PAGE === "desk") {
        setStatus("请先登录查看个人持仓");
      }
      return null;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    let data = await res.json();
    data = await ensurePortfolioSelection(data);
    // Preserve 分时 across quiet refreshes that return day/month without intraday.
    if (state.portfolio?.holdings?.length && data?.holdings?.length) {
      const prevBySym = Object.fromEntries(
        state.portfolio.holdings.map((h) => [h.symbol, h])
      );
      data.holdings = data.holdings.map((h) =>
        mergeListQuoteFields(
          mergePickPreserveIntraday(h, prevBySym[h.symbol]),
          prevBySym[h.symbol]
        )
      );
      if (data.selected_board) {
        const prevBoard =
          state.portfolio.selected_board?.symbol === data.selected
            ? state.portfolio.selected_board
            : prevBySym[data.selected];
        data.selected_board = mergeListQuoteFields(
          mergePickPreserveIntraday(data.selected_board, prevBoard),
          prevBoard
        );
        data.board = data.selected_board;
      }
    }
    syncHoldingSymbolsFromPortfolio(data);
    for (const h of data.holdings || []) cachePortfolioBoard(h);
    if (data.selected_board) cachePortfolioBoard(data.selected_board);
    renderPortfolio(data);
    persistPageDataCache();
    try {
      localStorage.setItem(
        "pulse_portfolio_backup",
        JSON.stringify({
          holdings: (data.holdings || []).map((h) => ({
            symbol: h.symbol,
            name: h.name,
            note: h.note,
          })),
          selected: data.selected || "",
          saved_at: Date.now(),
        })
      );
    } catch {
      /* ignore */
    }
  } catch (err) {
    if (els.portfolioBlurb) {
      els.portfolioBlurb.textContent = `持仓加载失败：${err.message || err}`;
    }
  }
}

async function portfolioPost(path, body) {
  const res = await fetch(path, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  const detailMsg = (() => {
    const detail = data?.detail;
    if (typeof detail === "string") return detail;
    if (Array.isArray(detail)) {
      return detail
        .map((d) => (typeof d === "string" ? d : d?.msg || ""))
        .filter(Boolean)
        .join("；");
    }
    return "";
  })();
  if (res.status === 401) {
    window.location.href = "/login";
    throw new Error(detailMsg || "请先登录");
  }
  if (!res.ok) throw new Error(detailMsg || `HTTP ${res.status}`);
  return data;
}

function syncHoldingSymbolsFromPortfolio(data) {
  const symbols = (data?.holdings || [])
    .map((h) => String(h.symbol || "").toUpperCase())
    .filter(Boolean);
  state.holdingSymbols = new Set(symbols);
  state._holdingSymbolsAt = Date.now();
  if (data) state.portfolio = data;
  return state.holdingSymbols;
}

function isInHoldings(symbol) {
  const sym = String(symbol || "").toUpperCase();
  if (!sym) return false;
  if (state.holdingSymbols) return state.holdingSymbols.has(sym);
  return (state.portfolio?.holdings || []).some((h) => h.symbol === sym);
}

async function refreshHoldingSymbols({ force = false } = {}) {
  if (!AUTHED) {
    state.holdingSymbols = new Set();
    return state.holdingSymbols;
  }
  if (
    !force &&
    state.holdingSymbols instanceof Set &&
    state._holdingSymbolsAt &&
    Date.now() - state._holdingSymbolsAt < 60_000
  ) {
    return state.holdingSymbols;
  }
  try {
    // Symbols-only — never block sectors/map on full portfolio quote builds.
    const res = await fetch("/api/portfolio/symbols", {
      credentials: "same-origin",
    });
    if (res.status === 401) {
      state.holdingSymbols = new Set();
      return state.holdingSymbols;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    const symbols = (data?.symbols || [])
      .map((s) => String(s || "").toUpperCase())
      .filter(Boolean);
    state.holdingSymbols = new Set(symbols);
    state._holdingSymbolsAt = Date.now();
    return state.holdingSymbols;
  } catch {
    try {
      const res = await fetch("/api/portfolio", { credentials: "same-origin" });
      if (res.ok) {
        const data = await res.json();
        syncHoldingSymbolsFromPortfolio(data);
        state._holdingSymbolsAt = Date.now();
        return state.holdingSymbols;
      }
    } catch {
      /* ignore */
    }
    if (!state.holdingSymbols) state.holdingSymbols = new Set();
    return state.holdingSymbols;
  }
}

function paintHoldingToggle(sym, held) {
  const symbol = String(sym || "").toUpperCase();
  if (!symbol) return;
  document
    .querySelectorAll(`.sector-hold-btn[data-hold-symbol="${symbol}"]`)
    .forEach((btn) => {
      btn.classList.toggle("is-held", held);
      btn.setAttribute("data-hold-action", held ? "remove" : "add");
      btn.textContent = held ? "−" : "+";
      const title = held ? `从持仓移除 ${symbol}` : `加入持仓 ${symbol}`;
      btn.title = title;
      btn.setAttribute("aria-label", title);
    });
  document
    .querySelectorAll(
      `.sector-pick-row[data-symbol="${symbol}"], .holding-row[data-holding="${symbol}"], .chains-co-row[data-symbol="${symbol}"]`
    )
    .forEach((row) => {
      row.classList.toggle("in-holding", held);
      const nm = row.querySelector(".meta .nm");
      if (!nm) return;
      const tag = nm.querySelector(".hold-tag");
      if (held && !tag) {
        nm.insertAdjacentHTML(
          "beforeend",
          '<span class="hold-tag">持仓</span>'
        );
      } else if (!held && tag) {
        tag.remove();
      }
    });
}

async function toggleSectorHolding(symbol, name = "") {
  const sym = String(symbol || "").trim().toUpperCase();
  if (!sym) return;
  if (!AUTHED) {
    window.location.href = `/login?next=${encodeURIComponent(
      location.pathname + location.search
    )}`;
    return;
  }
  if (!state.holdingToggleBusySyms) state.holdingToggleBusySyms = new Set();
  if (state.holdingToggleBusySyms.has(sym)) return;
  state.holdingToggleBusySyms.add(sym);
  const held = isInHoldings(sym);
  // Optimistic UI — flip +/− immediately, don't wait on network.
  if (!state.holdingSymbols) state.holdingSymbols = new Set();
  if (held) state.holdingSymbols.delete(sym);
  else state.holdingSymbols.add(sym);
  paintHoldingToggle(sym, !held);
  try {
    const data = held
      ? await portfolioPost("/api/portfolio/remove", { symbol: sym })
      : await portfolioPost("/api/portfolio/add", {
          symbol: sym,
          name: name || "",
        });
    syncHoldingSymbolsFromPortfolio(data.portfolio);
    paintHoldingToggle(sym, isInHoldings(sym));
    if (PAGE === "desk") {
      // Soft refresh quotes in background — list already updated if present.
      loadPortfolio({ refresh: false });
    }
    setStatus(
      held
        ? `已从持仓移除 ${sym}`
        : `已加入持仓 ${data.resolved?.name || name || sym}（${sym}）`
    );
  } catch (err) {
    // Revert optimistic flip
    if (held) state.holdingSymbols.add(sym);
    else state.holdingSymbols.delete(sym);
    paintHoldingToggle(sym, held);
    setStatus(`${held ? "移除" : "加入"}失败：${err.message || err}`);
  } finally {
    state.holdingToggleBusySyms.delete(sym);
  }
}

function renderAgenda(events, nextFomc) {
  if (!els.agenda) return;
  if (nextFomc && els.agendaBlurb) {
    const sep = nextFomc.sep ? "，含点阵图/SEP" : "";
    const mood = nextFomc.sentiment_label
      ? ` · 会前评判 ${nextFomc.sentiment_label}`
      : "";
    els.agendaBlurb.textContent = `下一场 ${nextFomc.label}：${nextFomc.end}${sep}（还有 ${nextFomc.days_until} 天）${mood}`;
  }

  if (!events?.length) {
    els.agenda.innerHTML = '<p class="empty">近期暂无已录入的日程节点。</p>';
    return;
  }

  els.agenda.innerHTML = events
    .map((ev) => {
      const watch = (ev.watch_points || []).slice(0, 3).join(" / ");
      const inner = `
        <div class="agenda-when">
          <span>${ev.date}</span>
          <span>${daysLabel(ev.days_until)}</span>
        </div>
        <div class="agenda-title-row">
          <h3>${escapeHtml(ev.title)}</h3>
          <span class="verdict-badge verdict-${ev.sentiment || "neutral"}">${escapeHtml(
            ev.sentiment_label || "中性"
          )}</span>
        </div>
        <p class="agenda-note">${escapeHtml(ev.note || ev.subtitle || "")}</p>
        <p class="agenda-bear"><strong>利空情景：</strong>${escapeHtml(
          ev.bear_case || "数据/表态超预期偏鹰时压制风险资产。"
        )}</p>
        <p class="agenda-bull"><strong>利多情景：</strong>${escapeHtml(
          ev.bull_case || "数据/表态偏鸽时提振风险偏好。"
        )}</p>
        <p class="agenda-logic">${escapeHtml(ev.sentiment_logic || ev.pre_reason || "")}</p>
        ${watch ? `<p class="agenda-watch">关注：${escapeHtml(watch)}</p>` : ""}
        <span class="kind-pill ${ev.kind}">${KIND_LABELS[ev.kind] || ev.kind}</span>
      `;
      const cls = `agenda-card is-${ev.sentiment || "neutral"}`;
      if (ev.url) {
        return `<a class="${cls}" href="${ev.url}" target="_blank" rel="noopener noreferrer">${inner}</a>`;
      }
      return `<div class="${cls}">${inner}</div>`;
    })
    .join("");
}

function renderDigest(digest) {
  if (!els.digest) return;
  if (!digest?.summary) {
    els.digest.textContent = "暂无主题简报";
    return;
  }
  els.digest.textContent = digest.summary;
}

function listLinks(rows) {
  if (!rows?.length) return "<li>暂无</li>";
  return rows
    .map((row) => {
      const title = escapeHtml(row.title || "");
      if (row.url) {
        return `<li><a href="${row.url}" target="_blank" rel="noopener noreferrer">[${escapeHtml(
          row.label || ""
        )}] ${title}</a></li>`;
      }
      return `<li>[${escapeHtml(row.label || "")}] ${title}</li>`;
    })
    .join("");
}

function renderMood(summary) {
  if (!els.moodBoard) return;
  if (!summary) {
    els.moodBoard.innerHTML = '<p class="empty">暂无情绪统计</p>';
    return;
  }
  if (els.moodBlurb) {
    els.moodBlurb.textContent = summary.blurb || "对近端情报做美股风险偏好启发式打分";
  }
  const counts = summary.counts || {};
  els.moodBoard.innerHTML = `
    <div class="mood-card ${summary.tilt || "neutral"}">
      <h3>综合倾向</h3>
      <p class="tilt">${escapeHtml(summary.tilt_zh || "中性")}</p>
      <p>均分 ${Number(summary.avg_score || 0).toFixed(2)} · 利多 ${counts.bullish || 0} / 利空 ${counts.bearish || 0} / 中性 ${counts.neutral || 0}</p>
    </div>
    <div class="mood-card bullish">
      <h3>利多头条</h3>
      <ul>${listLinks(summary.top_bullish)}</ul>
    </div>
    <div class="mood-card bearish">
      <h3>利空头条</h3>
      <ul>${listLinks(summary.top_bearish)}</ul>
    </div>
  `;
}

function fillSettingsForm(settings) {
  if (!settings || !els.cfgWebhook) return;
  els.cfgWebhook.value = settings.webhook_url || "";
  if (els.cfgFormat) els.cfgFormat.value = settings.webhook_format || "auto";
  if (els.cfgInterval) {
    els.cfgInterval.value = String(settings.push_interval_minutes ?? 15);
  }
  if (els.cfgTimes) els.cfgTimes.value = (settings.push_times || []).join(",");
  if (els.cfgTz) els.cfgTz.value = settings.push_timezone || "Asia/Shanghai";
  if (els.cfgEnabled) els.cfgEnabled.checked = Boolean(settings.push_enabled);
  if (els.cfgKeywords) {
    els.cfgKeywords.value = (settings.watch_keywords || []).join(",");
  }
}

function renderPush(push) {
  if (!els.pushStatus) return;
  if (!push) {
    els.pushStatus.textContent = "暂无推送状态";
    return;
  }
  const settings = push.settings || {};
  fillSettingsForm(settings);

  const channels = [];
  if (push.webhook_configured) {
    channels.push(`Webhook(${push.webhook_format || settings.resolved_webhook_format || "auto"})`);
  }
  if (push.email_configured) channels.push("邮件");
  const channelText = channels.length ? channels.join(" + ") : "未配置";
  const last = push.last || {};
  let lastText = "尚未推送";
  if (last.at) {
    const when = new Date(last.at * 1000).toLocaleString("zh-CN");
    lastText = last.ok
      ? `成功于 ${when}（${(last.channels || []).join("/") || "channel"}）`
      : `失败于 ${when}：${last.error || "未知错误"}`;
  }
  const interval = Number(push.interval_minutes || settings.push_interval_minutes || 0);
  const intervalText = interval > 0 ? `每 ${interval} 分钟` : "未设置间隔";
  const extraTimes = (push.times || []).join("、");
  if (els.pushBlurb) {
    els.pushBlurb.textContent = push.enabled
      ? `已启用定时推送：${intervalText}${extraTimes ? `；额外定点 ${extraTimes}` : ""}（${push.timezone}）`
      : "定时推送未启用：勾选并保存后生效";
  }
  els.pushStatus.innerHTML = `
    <div><strong>渠道</strong>：${escapeHtml(channelText)}</div>
    <div><strong>间隔</strong>：${escapeHtml(intervalText)} · ${escapeHtml(push.timezone || "")}</div>
    <div><strong>额外定点</strong>：${escapeHtml(extraTimes || "无")}</div>
    <div><strong>盯盘词</strong>：${escapeHtml((push.watch_keywords || []).join("、") || "未设置")}</div>
    <div><strong>最近一次</strong>：${escapeHtml(lastText)}</div>
  `;
  if (els.pushTest) {
    els.pushTest.disabled = !push.webhook_configured && !push.email_configured;
  }
}

/** English title primary; Chinese below at one smaller size. */
function newsTitleParts(item) {
  const en = String(item?.title || "").trim();
  const zhRaw = String(item?.title_zh || "").trim();
  const zh = zhRaw && zhRaw !== en ? zhRaw : "";
  return { en: en || zhRaw, zh };
}

/** Card mood class — 红多 / 绿空 / 灰中性. */
function newsMoodClass(item) {
  const s = item?.sentiment;
  if (s === "bullish") return "is-bullish";
  if (s === "bearish") return "is-bearish";
  return "is-neutral";
}

function newsTitleBlockHtml(item, { heading = "h3", href = null } = {}) {
  const { en, zh } = newsTitleParts(item);
  if (!en && !zh) return "";
  const zhTag = heading === "span" ? "span" : "p";
  const enBody = href
    ? `<a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">${escapeHtml(
        en
      )}</a>`
    : escapeHtml(en);
  return `
    <${heading} class="news-title-en">${enBody}</${heading}>
    ${
      zh
        ? `<${zhTag} class="news-title-zh">${escapeHtml(zh)}</${zhTag}>`
        : ""
    }
  `;
}

function holdingIntelCardHtml(item) {
  const matches = (item.holding_matches || []).join(" · ");
  const logic =
    item.sentiment_logic ||
    item.brief_zh ||
    item.summary ||
    "";
  return `
    <a class="holding-intel-card ${newsMoodClass(
      item
    )}" href="${escapeHtml(item.url || "#")}" target="_blank" rel="noopener noreferrer">
      <div class="holding-intel-meta">
        ${verdictBadge(item)}
        ${
          matches
            ? `<span class="chip holding">${escapeHtml(matches)}</span>`
            : ""
        }
        <span>${escapeHtml(item.source || "")}</span>
        <span>${escapeHtml(relativeTime(item.published))}</span>
      </div>
      ${newsTitleBlockHtml(item)}
      ${logic ? `<p class="logic">${escapeHtml(logic)}</p>` : ""}
    </a>
  `;
}

function renderHoldingIntelChips(container, symbols, selected, { total = 0 } = {}) {
  if (!container) return;
  const rows = symbols || [];
  if (!rows.length) {
    container.innerHTML = "";
    return;
  }
  const allActive = !selected;
  container.innerHTML = [
    `<button type="button" class="holding-chip ${
      allActive ? "is-active" : ""
    }" data-holding-filter="">全部<span class="n">${total}</span></button>`,
    ...rows.map(
      (row) => `<button type="button" class="holding-chip ${
        selected === row.symbol ? "is-active" : ""
      }" data-holding-filter="${escapeHtml(row.symbol)}">${escapeHtml(
        row.symbol
      )}<span class="n">${row.count || 0}</span></button>`
    ),
  ].join("");
}

function renderHoldingIntel(data) {
  state.holdingIntel = data || null;
  const symbols = data?.symbols || [];
  const selected = data?.selected || state.holdingFilter || "";
  const items = data?.items || [];
  const total = data?.total ?? items.length;

  if (els.holdingIntelBlurb) {
    if (!(data?.holdings || symbols).length && !(state.portfolio?.holdings || []).length) {
      els.holdingIntelBlurb.textContent = "添加持仓后，这里会自动关联相关情报";
    } else if (!total) {
      els.holdingIntelBlurb.textContent =
        "暂无命中持仓代码 / 备注名的情报，可稍后再刷新";
    } else {
      els.holdingIntelBlurb.textContent = `已关联 ${total} 条 · 利空优先 · 点击芯片可按标的筛选`;
    }
  }

  renderHoldingIntelChips(els.holdingIntelChips, symbols, selected, { total });

  if (els.holdingIntelAllLink) {
    const qs = selected
      ? `holdings=1&holding=${encodeURIComponent(selected)}`
      : "holdings=1";
    els.holdingIntelAllLink.href = `/intel?${qs}`;
  }

  if (!els.holdingIntelList) return;
  if (!(state.portfolio?.holdings || []).length && !(data?.holdings || []).length) {
    els.holdingIntelList.innerHTML =
      '<p class="empty">还没有持仓。添加代码后，信息流会自动映射到这里。</p>';
    return;
  }
  if (!items.length) {
    els.holdingIntelList.innerHTML =
      '<p class="empty">当前筛选下暂无持仓相关情报。</p>';
    return;
  }
  els.holdingIntelList.innerHTML = items.map(holdingIntelCardHtml).join("");
}

async function loadHoldingIntel({ refresh = false, symbol, soft = false } = {}) {
  if (!els.holdingIntelList && !els.holdingIntelChips) return null;
  if (!AUTHED) return null;
  const filter =
    symbol !== undefined ? symbol || "" : state.holdingFilter || "";
  state.holdingFilter = filter;
  // Soft switch: keep previous intel visible while the next filter loads.
  if (!soft && els.holdingIntelList) {
    els.holdingIntelList.innerHTML =
      '<p class="empty">同步持仓相关情报…</p>';
  }
  try {
    const params = new URLSearchParams();
    if (refresh) params.set("refresh", "true");
    if (filter) params.set("symbol", filter);
    params.set("limit", "20");
    const res = await fetch(`/api/portfolio/intel?${params.toString()}`, {
      credentials: "same-origin",
    });
    if (res.status === 401) {
      if (els.holdingIntelList) {
        els.holdingIntelList.innerHTML =
          '<p class="empty">登录后可查看持仓关联情报。</p>';
      }
      return null;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderHoldingIntel(data);
    return data;
  } catch (err) {
    if (els.holdingIntelBlurb) {
      els.holdingIntelBlurb.textContent = `持仓情报加载失败：${err.message || err}`;
    }
    if (els.holdingIntelList) {
      els.holdingIntelList.innerHTML =
        '<p class="empty">持仓情报暂时不可用，请稍后刷新。</p>';
    }
    return null;
  }
}

function renderWatchHits(hits) {
  if (!els.watchHits) return;
  if (!hits?.length) {
    els.watchHits.hidden = true;
    els.watchHits.innerHTML = "";
    return;
  }
  els.watchHits.hidden = false;
  els.watchHits.innerHTML = `
    <h3>盯盘命中 ${hits.length}</h3>
    <div class="watch-hit-list">
      ${hits
        .slice(0, 8)
        .map((item) => {
          const keys = (item.watch_matches || []).join(",");
          return `
            <a class="watch-hit-card ${newsMoodClass(
              item
            )}" href="${item.url}" target="_blank" rel="noopener noreferrer">
              <div class="watch-hit-meta">
                <span class="chip ${item.sentiment || "neutral"}">${escapeHtml(
                  item.sentiment_label || "中性"
                )}</span>
                <span class="chip watch">盯盘:${escapeHtml(keys)}</span>
              </div>
              ${newsTitleBlockHtml(item, { heading: "p" })}
            </a>
          `;
        })
        .join("")}
    </div>
  `;
}

function verdictBadge(item) {
  const sentiment = item.sentiment || "neutral";
  const label = item.sentiment_label || "中性";
  const strong = item.sentiment_strength === "强";
  const title = item.sentiment_logic || item.sentiment_reason || "";
  return `<span class="verdict-badge verdict-${sentiment} ${strong ? "is-strong" : ""}" title="${escapeHtml(
    title
  )}">${escapeHtml(label)}</span>`;
}

function spotlightCardHtml(item) {
  const factors = (item.sentiment_factors || []).join("、");
  const metaBits = [
    item.source || "",
    item.published ? formatClock(item.published) : "",
  ].filter(Boolean);
  const logic =
    item.sentiment_logic || item.sentiment_reason || item.brief_zh || "";
  return `
    <a class="spotlight-card ${newsMoodClass(item)}" href="${
      item.url || "#"
    }" target="_blank" rel="noopener noreferrer">
      ${verdictBadge(item)}
      ${newsTitleBlockHtml(item)}
      ${logic ? `<p class="news-logic">${escapeHtml(logic)}</p>` : ""}
      ${factors ? `<p class="news-logic">因子：${escapeHtml(factors)}</p>` : ""}
      ${
        metaBits.length
          ? `<p class="war-card-meta">${escapeHtml(metaBits.join(" · "))}</p>`
          : ""
      }
    </a>
  `;
}

function renderSpotlight(rows) {
  if (!els.spotlight) return;
  if (!rows?.length) {
    els.spotlight.innerHTML = '<p class="empty">当前暂无识别出的利空/偏空头条。</p>';
    if (els.spotlightBlurb) els.spotlightBlurb.textContent = "暂无强利空样本";
    return;
  }
  if (els.spotlightBlurb) {
    els.spotlightBlurb.textContent = `共 ${rows.length} 条重点利空/偏空（按得分从低到高）`;
  }
  els.spotlight.innerHTML = rows.map((item) => spotlightCardHtml(item)).join("");
}

function renderWarLatest(container, rows, emptyText) {
  if (!container) return;
  if (!rows?.length) {
    container.innerHTML = `<p class="empty">${escapeHtml(emptyText)}</p>`;
    return;
  }
  container.innerHTML = rows
    .slice(0, 5)
    .map((item) => spotlightCardHtml(item))
    .join("");
}

function renderWarDesk(desk) {
  const data = desk || {};
  const columns = data.columns || {};
  const usIran = columns.us_iran || {};
  const ukraine = columns.ukraine || {};
  const analyses = data.bearish_analysis || [];

  if (els.warDeskBlurb) {
    const nIran = usIran.counts?.total || 0;
    const nUa = ukraine.counts?.total || 0;
    els.warDeskBlurb.textContent =
      data.updated_hint ||
      `美伊 ${nIran} 条 · 俄乌 ${nUa} 条 · 与情报流同源`;
  }

  renderWarLatest(
    els.warLatestUsIran,
    usIran.latest || [],
    "暂无美伊冲突相关最新进展。"
  );
  renderWarLatest(
    els.warLatestUkraine,
    ukraine.latest || [],
    "暂无俄乌战争相关最新进展。"
  );

  if (!els.warBearishGrid) return;
  if (!analyses.length) {
    els.warBearishGrid.innerHTML =
      '<p class="empty">暂无冲突利空分析样本。</p>';
    return;
  }

  if (els.warBearishBlurb) {
    const totalBear = analyses.reduce(
      (sum, row) => sum + (row.counts?.bearish || 0),
      0
    );
    els.warBearishBlurb.textContent = `两线合计利空 ${totalBear} 条 · 按压制强度拆解`;
  }

  els.warBearishGrid.innerHTML = analyses
    .map((row) => {
      const counts = row.counts || {};
      const factors = (row.top_factors || []).slice(0, 4).join("、");
      const score =
        typeof row.avg_score === "number" ? row.avg_score.toFixed(2) : "0.00";
      const q = row.query || row.label || "";
      const spot = (row.spotlight || [])
        .slice(0, 2)
        .map((item) => spotlightCardHtml(item))
        .join("");
      return `
        <article class="war-analysis-card">
          <div class="war-analysis-head">
            <h3>${escapeHtml(row.label || "")}</h3>
            <button type="button" class="btn ghost btn-compact war-filter-link" data-war-q="${escapeHtml(
              q
            )}">在情报流查看</button>
          </div>
          <div class="brief-meta-row">
            <span class="brief-chip bias-bearish">利空 ${counts.bearish || 0}</span>
            <span class="brief-chip">利多 ${counts.bullish || 0}</span>
            <span class="brief-chip score">均分 ${escapeHtml(score)}</span>
            <span class="brief-chip">样本 ${counts.total || 0}</span>
          </div>
          <p class="war-assessment">${escapeHtml(row.assessment || "")}</p>
          ${
            factors
              ? `<p class="war-factors">核心利空因子：${escapeHtml(factors)}</p>`
              : ""
          }
          <div class="spotlight-list war-analysis-spot">${
            spot || '<p class="empty">暂无强利空头条</p>'
          }</div>
        </article>
      `;
    })
    .join("");

  els.warBearishGrid.querySelectorAll(".war-filter-link").forEach((btn) => {
    btn.addEventListener("click", () => {
      const q = btn.getAttribute("data-war-q") || "";
      if (els.searchInput) els.searchInput.value = q;
      state.q = q;
      state.category = "all";
      state.sentiment = "all";
      document
        .querySelectorAll("#filters .filter")
        .forEach((el) =>
          el.classList.toggle("is-active", el.dataset.category === "all")
        );
      document
        .querySelectorAll("#sentiment-filters .filter[data-sentiment]")
        .forEach((el) =>
          el.classList.toggle("is-active", el.dataset.sentiment === "all")
        );
      document.getElementById("feed")?.scrollIntoView({ behavior: "smooth" });
      loadIntel();
    });
  });
}

function formatClock(iso) {
  if (!iso) return "时间未知";
  const ts = Date.parse(iso);
  if (Number.isNaN(ts)) return "时间未知";
  return new Date(ts).toLocaleString("zh-CN", {
    month: "numeric",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

function renderLiveBriefing(brief) {
  const data = brief || {};
  const direction = data.direction || {};
  const counts = data.counts || {};
  const windowHours = data.window_hours || 12;
  const overview =
    data.overview ||
    data.summary ||
    "近几小时公开源更新偏少，暂未形成可概述的主线事件。";
  const assessment =
    data.assessment || "样本不足，暂不做利空强弱结论。";
  const change = direction.change || "steady";
  const bias = direction.bias || "neutral";
  const score =
    typeof direction.score === "number" ? direction.score.toFixed(2) : "0.00";
  const delta =
    typeof direction.delta === "number"
      ? `${direction.delta >= 0 ? "+" : ""}${direction.delta.toFixed(2)}`
      : "0.00";

  const bulletHtml = (data.event_bullets || [])
    .slice(0, 4)
    .map((b, idx) => {
      const title = b.title_zh || b.title || "";
      const meta =
        b.kind === "event" && (b.count || 1) >= 2
          ? ` · ${b.count} 条相关`
          : b.theme
            ? ` · ${b.theme}`
            : "";
      return `<li><span class="bullet-idx">${idx + 1}</span>${escapeHtml(
        title
      )}<span class="bullet-meta">${escapeHtml(meta)}</span></li>`;
    })
    .join("");

  if (els.liveBriefPin) {
    els.liveBriefPin.innerHTML = `
      <div class="brief-kicker">
        <span class="label">近 ${escapeHtml(String(windowHours))} 小时利空速评</span>
        <span class="brief-chip">更新 ${counts.total || 0} 条</span>
      </div>
      <div class="brief-block">
        <p class="brief-block-label">事件概述</p>
        <p class="brief-summary">${escapeHtml(overview)}</p>
        ${
          bulletHtml
            ? `<ol class="brief-bullets">${bulletHtml}</ol>`
            : ""
        }
      </div>
      <div class="brief-block assessment">
        <p class="brief-block-label">利空评判</p>
        <div class="brief-meta-row" style="margin-bottom:0.45rem">
          <span class="brief-chip change-${escapeHtml(change)}">${escapeHtml(
            direction.change_zh || "动向待定"
          )}</span>
          <span class="brief-chip bias-${escapeHtml(bias)}">${escapeHtml(
            direction.bias_zh || "中性观望"
          )}</span>
          <span class="brief-chip score">均分 ${escapeHtml(score)} · Δ ${escapeHtml(
            delta
          )}</span>
          <span class="brief-chip">利空 ${counts.bearish || 0} / 利多 ${
            counts.bullish || 0
          }</span>
        </div>
        <p class="brief-summary assessment-text">${escapeHtml(assessment)}</p>
      </div>
    `;
  }

  if (els.liveBriefRail) {
    const factors = (data.top_factors || [])
      .slice(0, 5)
      .map((f) => `<li>${escapeHtml(f)}</li>`)
      .join("");
    const drivers = (data.drivers || [])
      .map((d) => {
        const href = d.url || "#";
        const mood = newsMoodClass(d);
        return `
          <li class="driver-item ${mood}">
            <a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">
              ${newsTitleBlockHtml(d, { heading: "span" })}
            </a>
            <div class="driver-meta">
              <span class="chip ${d.sentiment || "neutral"}">${escapeHtml(
                d.sentiment_label || "中性"
              )}</span>
              <span>${escapeHtml(d.source || "")}</span>
              <span>${escapeHtml(formatClock(d.published))}</span>
            </div>
            ${
              d.logic
                ? `<p class="driver-logic">${escapeHtml(d.logic)}</p>`
                : ""
            }
          </li>
        `;
      })
      .join("");

    els.liveBriefRail.innerHTML = `
      <div class="rail-head">
        <h2>近时速评</h2>
        <p>近 ${escapeHtml(String(windowHours))} 小时 · 先概述事件，再做利空评判</p>
      </div>
      <p class="rail-block-title">事件概述</p>
      <p class="rail-summary">${escapeHtml(overview)}</p>
      ${
        bulletHtml
          ? `<ol class="brief-bullets rail-bullets">${bulletHtml}</ol>`
          : ""
      }
      <p class="rail-block-title">利空评判</p>
      <div class="brief-meta-row" style="margin-bottom:0.55rem">
        <span class="brief-chip change-${escapeHtml(change)}">${escapeHtml(
          direction.change_zh || "持平"
        )}</span>
        <span class="brief-chip bias-${escapeHtml(bias)}">${escapeHtml(
          direction.bias_zh || "中性"
        )}</span>
      </div>
      <p class="rail-summary">${escapeHtml(assessment)}</p>
      <p class="rail-block-title">核心利空因子</p>
      <ul class="factor-list">${
        factors || "<li>暂无集中因子</li>"
      }</ul>
      <p class="rail-block-title">最强压制线索</p>
      <ul class="driver-list">${
        drivers || "<li class='driver-title'>暂无显著利空头条</li>"
      }</ul>
    `;
  }
}

function renderBriefStrip(data) {
  if (!els.briefGrid) return;
  const mood = data.sentiment_summary || {};
  const counts = mood.counts || {};
  const timeline = data.timeline || [];
  const today = timeline[0] || {};
  const threads = data.event_threads || [];
  const next = data.next_fomc;
  const watch = (data.watch_hits || []).length;

  if (els.briefBlurb) {
    els.briefBlurb.textContent = mood.blurb || "时间线、事件线与情绪一页看清";
  }

  const fomcText = next
    ? `${next.end || ""} · ${next.days_until ?? "—"} 天`
    : "暂无";
  els.briefGrid.innerHTML = `
    <div class="brief-card">
      <div class="label">${escapeHtml(today.label || "今日")}情报</div>
      <div class="value">${today.count || 0}</div>
      <div class="note">利空 ${today.bearish || 0} · 利多 ${today.bullish || 0}</div>
    </div>
    <div class="brief-card bearish">
      <div class="label">近端利空</div>
      <div class="value">${counts.bearish || 0}</div>
      <div class="note">综合倾向：${escapeHtml(mood.tilt_zh || "中性")}</div>
    </div>
    <div class="brief-card">
      <div class="label">事件线</div>
      <div class="value">${threads.length}</div>
      <div class="note">盯盘命中 ${watch} · 可点开追踪</div>
    </div>
    <div class="brief-card">
      <div class="label">下一场 FOMC</div>
      <div class="value" style="font-size:1.15rem;margin-top:0.7rem">${escapeHtml(
        next?.label ? "决议" : "—"
      )}</div>
      <div class="note">${escapeHtml(fomcText)}</div>
    </div>
  `;
}

function renderEventThreads(threads) {
  if (!els.eventRail) return;
  const rows = threads || [];
  if (!rows.length) {
    els.eventRail.innerHTML =
      '<p class="empty">当前还没有识别到可串联的同一事件（至少 2 条相关报道）。</p>';
    if (els.eventsBlurb) els.eventsBlurb.textContent = "暂无多源事件线";
    return;
  }
  if (els.eventsBlurb) {
    els.eventsBlurb.textContent = `已串联 ${rows.length} 条事件线，点击可查看完整时间线`;
  }
  els.eventRail.innerHTML = rows
    .map((event) => {
      const keys = (event.keywords || [])
        .slice(0, 4)
        .map((k) => `<span class="key-chip">${escapeHtml(k)}</span>`)
        .join("");
      return `
        <button type="button" class="event-card ${newsMoodClass(
          event
        )}" data-open-event="${escapeHtml(event.id)}">
          <div class="event-card-top">
            <span class="chip ${event.sentiment || "neutral"}">${escapeHtml(
              event.sentiment_label || "中性"
            )}</span>
            <span>${event.count} 条报道</span>
          </div>
          ${newsTitleBlockHtml(event)}
          <p class="event-en">${escapeHtml(formatClock(event.first_seen))} → ${escapeHtml(
            formatClock(event.last_seen)
          )}</p>
          <div class="event-keys">${keys}</div>
        </button>
      `;
    })
    .join("");
}

function renderDayTimeline(timeline) {
  if (!els.dayTimeline) return;
  const days = timeline || [];
  if (!days.length) {
    els.dayTimeline.innerHTML = '<p class="empty">暂无时间线数据</p>';
    return;
  }
  if (els.timelineBlurb) {
    els.timelineBlurb.textContent = `覆盖 ${days.length} 天 · 共 ${days.reduce(
      (n, d) => n + (d.count || 0),
      0
    )} 条`;
  }
  els.dayTimeline.innerHTML = days
    .map((day, index) => {
      const items = (day.items || [])
        .slice(0, 8)
        .map((item) => {
          const eventBtn =
            item.event_id && item.event_count > 1
              ? `<button type="button" class="event-link" data-open-event="${escapeHtml(
                  item.event_id
                )}">同事件 ${item.event_count}</button>`
              : "";
          return `
            <div class="day-item ${newsMoodClass(item)}">
              <div class="day-item-top">
                <span class="chip ${item.sentiment || "neutral"}">${escapeHtml(
                  item.sentiment_label || "中性"
                )}</span>
                <span>${escapeHtml(item.source || "")}</span>
                <time datetime="${item.published || ""}">${relativeTime(item.published)}</time>
                ${eventBtn}
              </div>
              ${newsTitleBlockHtml(item, { heading: "p", href: item.url || "#" })}
            </div>
          `;
        })
        .join("");
      const tone = index === 0 ? "today" : `tone-${(index - 1) % 4}`;
      return `
        <div class="day-bucket is-${tone}">
          <div class="day-bucket-head">
            <h3>${escapeHtml(day.label)} · ${escapeHtml(day.date)}</h3>
            <span>${day.count} 条 · 利空 ${day.bearish || 0} · 利多 ${day.bullish || 0}</span>
          </div>
          ${items}
        </div>
      `;
    })
    .join("");
}

function openEventDrawer(event) {
  if (!event || !els.eventDrawer) return;
  const titleZh = event.title_zh || event.title || "事件详情";
  els.eventDrawerTitle.textContent = titleZh;
  const keys = (event.keywords || []).join("、") || "综合";
  els.eventDrawerMeta.innerHTML = `
    <div>情绪：${escapeHtml(event.sentiment_label || "中性")}（${Number(
      event.sentiment_score || 0
    ).toFixed(2)}）</div>
    <div>关键词：${escapeHtml(keys)}</div>
    <div>时间跨度：${escapeHtml(formatClock(event.first_seen))} → ${escapeHtml(
      formatClock(event.last_seen)
    )} · ${event.count || 0} 条</div>
    <div>来源：${escapeHtml((event.sources || []).join("、") || "—")}</div>
  `;
  els.eventDrawerTimeline.innerHTML = (event.timeline || [])
    .map((node) => {
      const zh = node.title_zh || node.title || "";
      const en = node.title || "";
      const showEn = en && en !== zh;
      return `
        <li>
          <div class="when">${escapeHtml(formatClock(node.published))} · ${escapeHtml(
            node.source || ""
          )} · ${escapeHtml(node.sentiment_label || "中性")}</div>
          <p class="zh"><a href="${node.url}" target="_blank" rel="noopener noreferrer">${escapeHtml(
            zh
          )}</a></p>
          ${showEn ? `<p class="en">${escapeHtml(en)}</p>` : ""}
        </li>
      `;
    })
    .join("");
  els.eventDrawer.hidden = false;
  document.body.style.overflow = "hidden";
}

function closeEventDrawer() {
  if (!els.eventDrawer) return;
  els.eventDrawer.hidden = true;
  document.body.style.overflow = "";
}

async function openEventById(eventId) {
  if (!eventId) return;
  let event = state.eventsById[eventId];
  if (!event) {
    try {
      const res = await fetch(`/api/events/${encodeURIComponent(eventId)}`);
      if (res.ok) {
        const data = await res.json();
        event = data.event;
        if (event) state.eventsById[event.id] = event;
      }
    } catch (err) {
      console.error(err);
    }
  }
  if (event) openEventDrawer(event);
}

function renderFeed(items) {
  if (!els.feed) return;
  if (!items?.length) {
    els.feed.innerHTML =
      '<p class="empty">这个分类下暂时没有匹配结果，试试换个关键词或分类。</p>';
    return;
  }
  els.feed.innerHTML = items
    .map((item) => {
      const watchChip = item.watch_hit
        ? `<span class="chip watch">盯盘:${escapeHtml((item.watch_matches || []).join(","))}</span>`
        : "";
      const holdingChip = item.holding_hit
        ? `<span class="chip holding">持仓:${escapeHtml(
            (item.holding_matches || []).join(",")
          )}</span>`
        : "";
      const factors = (item.sentiment_factors || []).join("、") || "暂无强因子";
      const logic =
        item.sentiment_logic ||
        `结论：${item.sentiment_label || "中性"}（${Number(item.sentiment_score || 0).toFixed(2)}）`;
      const eventBtn =
        item.event_id && item.event_count > 1
          ? `<button type="button" class="event-link" data-open-event="${escapeHtml(
              item.event_id
            )}">同事件 ${item.event_count} 条</button>`
          : "";
      return `
      <article class="story ${item.watch_hit ? "is-watch" : ""} ${item.holding_hit ? "is-holding" : ""} ${newsMoodClass(item)}">
        <div class="story-top">
          <span class="chip ${item.category}">${categoryName(item.category)}</span>
          ${watchChip}
          ${holdingChip}
          ${item.theme ? `<span class="chip policy">${escapeHtml(item.theme)}</span>` : ""}
          <span>${escapeHtml(item.source)}</span>
          <span>·</span>
          <time datetime="${item.published || ""}">${relativeTime(item.published)}</time>
          ${eventBtn}
        </div>
        <div class="story-title-block">
          ${verdictBadge(item)}
          ${newsTitleBlockHtml(item, { href: item.url || "#" })}
        </div>
        <div class="story-verdict ${item.sentiment || "neutral"}">
          <p class="story-verdict-label">
            <strong>利多/利空评判：${escapeHtml(item.sentiment_label || "中性")}</strong>
            <span>得分 ${Number(item.sentiment_score || 0).toFixed(2)}</span>
          </p>
          <p class="story-verdict-factors">因子：${escapeHtml(factors)}</p>
          <p class="story-verdict-logic">逻辑：${escapeHtml(logic)}</p>
        </div>
        ${item.brief_zh ? `<p class="story-brief">${escapeHtml(item.brief_zh)}</p>` : ""}
        ${item.summary ? `<p class="story-summary">${escapeHtml(item.summary)}</p>` : ""}
      </article>
    `;
    })
    .join("");
}

function categoryName(key) {
  const map = {
    markets: "市场",
    fed: "美联储",
    treasury: "国债",
    policy: "政策监管",
    politics: "时政地缘",
  };
  return map[key] || key;
}

function escapeHtml(text) {
  return String(text)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function setStatus(text) {
  if (els.status) els.status.textContent = text;
}

async function loadMarketsDesk({ force = false } = {}) {
  setStatus(force ? "正在刷新市场…" : "同步指数与读数…");
  if (els.refresh) els.refresh.disabled = true;
  try {
    const res = await fetch(`/api/markets${force ? "?refresh=true" : ""}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderMarkets(data.markets);
    renderIndicators(data.indicators);
    renderAgenda(data.calendar, data.next_fomc);
    const when = data.fetched_at
      ? new Date(data.fetched_at * 1000).toLocaleTimeString("zh-CN", {
          hour: "2-digit",
          minute: "2-digit",
        })
      : "";
    const cacheNote = data.cached ? "缓存" : "实时";
    const errNote = data.errors?.length ? ` · ${data.errors.length} 条提示` : "";
    setStatus(`${cacheNote}市场 ${when}${errNote}`);
  } catch (err) {
    console.error(err);
    setStatus("市场同步失败，请稍后重试");
  } finally {
    if (els.refresh) els.refresh.disabled = false;
  }
}

function syncHoldingsFilterUi() {
  if (els.filterHoldings) {
    els.filterHoldings.classList.toggle("is-active", state.holdingsOnly);
    els.filterHoldings.setAttribute(
      "aria-selected",
      state.holdingsOnly ? "true" : "false"
    );
  }
  if (els.intelHoldingChips) {
    const symbols = state.holdingIntel?.symbols || [];
    const show = state.holdingsOnly && symbols.length;
    els.intelHoldingChips.hidden = !show;
    if (show) {
      renderHoldingIntelChips(
        els.intelHoldingChips,
        symbols,
        state.holdingFilter,
        { total: state.holdingIntel?.total || 0 }
      );
    }
  }
}

async function loadIntel({ force = false } = {}) {
  const params = new URLSearchParams({
    category: state.category,
    sentiment: state.sentiment,
    sort: state.sort,
    q: state.q,
  });
  if (state.watchOnly) params.set("watch_only", "true");
  if (state.holdingsOnly) params.set("holdings_only", "true");
  if (state.holdingFilter) params.set("holding", state.holdingFilter);
  if (force) params.set("refresh", "true");

  setStatus(force ? "正在强制刷新…" : "同步情报源中…");
  if (els.refresh) els.refresh.disabled = true;

  try {
    const res = await fetch(`/api/intel?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();

    const allEvents = [
      ...(data.event_threads || []),
      ...(data.events || []),
    ];
    state.eventsById = {};
    for (const event of allEvents) {
      if (event?.id) state.eventsById[event.id] = event;
    }

    if (PAGE === "markets") {
      renderMarkets(data.markets);
      renderIndicators(data.indicators);
      renderAgenda(data.calendar, data.next_fomc);
    } else {
      renderMood(data.sentiment_summary);
      renderLiveBriefing(data.live_briefing);
      renderSpotlight(data.bearish_spotlight);
      renderWarDesk(data.war_desk);
      renderBriefStrip(data);
      renderEventThreads(data.event_threads);
      renderDayTimeline(data.timeline);
      renderWatchHits(data.watch_hits);
      renderFeed(data.items);
      renderDigest(data.digest);
      if (PAGE === "settings") renderPush(data.push);
    }

    if (data.holding_intel) {
      state.holdingIntel = data.holding_intel;
    }
    syncHoldingsFilterUi();

    const sortNote =
      state.sort === "bearish" ? " · 利空优先" : state.sort === "bullish" ? " · 利多优先" : " · 最新优先";
    const holdNote = state.holdingsOnly
      ? state.holdingFilter
        ? ` · 持仓 ${state.holdingFilter}`
        : " · 仅持仓相关"
      : "";
    if (els.blurb) {
      els.blurb.textContent =
        (CATEGORY_LABELS[state.category] || CATEGORY_LABELS.all) +
        sortNote +
        holdNote;
    }

    const when = data.fetched_at
      ? new Date(data.fetched_at * 1000).toLocaleTimeString("zh-CN", {
          hour: "2-digit",
          minute: "2-digit",
        })
      : "";
    const cacheNote = data.cached ? "缓存" : "实时";
    const errNote = data.errors?.length ? ` · ${data.errors.length} 个源暂不可用` : "";
    const watchNote = data.watch_hits?.length ? ` · 盯盘 ${data.watch_hits.length}` : "";
    setStatus(`${cacheNote}更新 ${when} · ${data.count} 条${watchNote}${errNote}`);
  } catch (err) {
    console.error(err);
    setStatus("同步失败，请检查网络后重试");
    if (els.feed) {
      els.feed.innerHTML =
        '<p class="error-note">情报流加载失败。确认服务已启动，并可以访问外网 RSS / FRED。</p>';
    }
  } finally {
    if (els.refresh) els.refresh.disabled = false;
  }
}

async function loadSettingsPage() {
  setStatus("读取配置…");
  try {
    const [settingsRes, pushRes] = await Promise.all([
      fetch("/api/settings"),
      fetch("/api/push/status"),
    ]);
    const settings = settingsRes.ok ? await settingsRes.json() : null;
    const push = pushRes.ok ? await pushRes.json() : null;
    if (settings) fillSettingsForm(settings);
    if (push) renderPush(push);
    else if (settings) renderPush({ settings, ...push });
    setStatus("设置已加载");
  } catch (err) {
    setStatus(`设置读取失败：${err.message || err}`);
  }
}

els.tfFilters?.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-tf]");
  if (!btn) return;
  state.marketTf = btn.dataset.tf;
  if (state.markets) {
    renderMarkets(state.markets);
  }
});

els.portfolioTfFilters?.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-ptf]");
  if (!btn) return;
  const tf = btn.dataset.ptf;
  if (!tf || tf === state.portfolioTf) return;
  state.portfolioTf = tf;
  // TF switch is chart-only — list sparks stay on day tape.
  renderPortfolioChart();
  persistPageDataCache();
  if (tf === "intraday") {
    refreshActiveIntraday({ force: false });
  } else if (!pickHasTfSeries(state.portfolio?.selected_board, tf)) {
    ensureMultiTfChartUpgrade();
  }
});

els.portfolioManageBtn?.addEventListener("click", () => {
  if (!els.portfolioManage || !els.portfolioManageBtn) return;
  const open = els.portfolioManage.hasAttribute("hidden");
  if (open) {
    els.portfolioManage.removeAttribute("hidden");
    els.portfolioManageBtn.classList.add("is-open");
    els.portfolioManageBtn.setAttribute("aria-expanded", "true");
    els.portfolioSymbol?.focus();
  } else {
    els.portfolioManage.setAttribute("hidden", "");
    els.portfolioManageBtn.classList.remove("is-open");
    els.portfolioManageBtn.setAttribute("aria-expanded", "false");
  }
});

els.portfolioListHead?.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-psort]");
  if (!btn || !state.portfolio) return;
  const key = btn.getAttribute("data-psort");
  if (!key) return;
  if (state.portfolioSort.key === key) {
    state.portfolioSort.dir =
      state.portfolioSort.dir === "desc" ? "asc" : "desc";
  } else {
    state.portfolioSort = { key, dir: "desc" };
  }
  renderPortfolio(state.portfolio);
});

els.holdingRail?.addEventListener("click", async (event) => {
  const btn = event.target.closest("[data-holding]");
  if (!btn) return;
  const symbol = btn.getAttribute("data-holding");
  await selectPortfolioSymbol(symbol);
});

function syncHoldingPreviewClasses() {
  if (!els.holdingRail) return;
  const selected = state.portfolio?.selected || "";
  const preview = state.portfolioPreview;
  els.holdingRail.querySelectorAll("[data-holding]").forEach((row) => {
    const sym = row.getAttribute("data-holding");
    row.classList.toggle("is-preview", Boolean(preview && sym === preview && sym !== selected));
  });
}

els.holdingRail?.addEventListener("mouseover", (event) => {
  const btn = event.target.closest("[data-holding]");
  if (!btn || !state.portfolio) return;
  const symbol = btn.getAttribute("data-holding");
  if (!symbol || symbol === state.portfolioPreview) return;
  state.portfolioPreview = symbol;
  syncHoldingPreviewClasses();
  renderPortfolioChart();
});

els.holdingRail?.addEventListener("mouseleave", () => {
  if (!state.portfolioPreview) return;
  state.portfolioPreview = null;
  syncHoldingPreviewClasses();
  renderPortfolioChart();
});

document.addEventListener("keydown", (event) => {
  if (PAGE !== "desk") return;
  if (event.metaKey || event.ctrlKey || event.altKey) return;
  const tag = (event.target?.tagName || "").toLowerCase();
  if (tag === "input" || tag === "textarea" || event.target?.isContentEditable) {
    return;
  }
  const holdings = state.portfolio?.holdings || [];
  if (!holdings.length) return;

  if (event.key >= "1" && event.key <= "5") {
    const tf = PORTFOLIO_TF_KEYS[Number(event.key) - 1];
    if (!tf) return;
    event.preventDefault();
    state.portfolioTf = tf;
    renderPortfolioChart();
    persistPageDataCache();
    if (tf === "intraday") refreshActiveIntraday({ force: false });
    else if (!pickHasTfSeries(state.portfolio?.selected_board, tf)) {
      ensureMultiTfChartUpgrade();
    }
    return;
  }

  if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
  const tf = state.portfolioTf || "intraday";
  const rows = sortedHoldings(holdings, tf);
  if (!rows.length) return;
  const current =
    state.portfolioPreview || state.portfolio?.selected || rows[0].symbol;
  const idx = Math.max(
    0,
    rows.findIndex((h) => h.symbol === current)
  );
  const next =
    event.key === "ArrowDown"
      ? rows[Math.min(rows.length - 1, idx + 1)]
      : rows[Math.max(0, idx - 1)];
  if (!next) return;
  event.preventDefault();
  selectPortfolioSymbol(next.symbol, { quiet: true });
  const el = els.holdingRail?.querySelector(`[data-holding="${next.symbol}"]`);
  el?.scrollIntoView({ block: "nearest" });
});

els.portfolioAddForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const symbol = (els.portfolioSymbol?.value || "").trim();
  const name = (els.portfolioName?.value || "").trim();
  if (!symbol) {
    setStatus("请先输入美股代码或中文名");
    return;
  }
  const submitBtn = els.portfolioAddForm.querySelector('button[type="submit"]');
  if (submitBtn) submitBtn.disabled = true;
  setStatus(`正在添加 ${symbol}…`);
  try {
    const data = await portfolioPost("/api/portfolio/add", { symbol, name });
    if (els.portfolioSymbol) els.portfolioSymbol.value = "";
    if (els.portfolioName) els.portfolioName.value = "";
    if (els.portfolioLookupHint) {
      els.portfolioLookupHint.hidden = true;
      els.portfolioLookupHint.textContent = "";
    }
    state.portfolioTf = "intraday";
    state.portfolioPreview = null;
    const portfolio = await ensurePortfolioSelection(data.portfolio);
    syncHoldingSymbolsFromPortfolio(portfolio);
    renderPortfolio(portfolio);
    const resolved = data.resolved || {};
    const label = resolved.symbol
      ? `${resolved.name || resolved.symbol}（${resolved.symbol}）`
      : symbol;
    if (els.portfolioBlurb) {
      els.portfolioBlurb.textContent = `已添加 ${label}`;
    }
    setStatus(`已加入持仓 ${label}`);
    // Upgrade stub quotes in the background without blocking the add UX.
    loadPortfolio({ refresh: false });
  } catch (err) {
    if (els.portfolioBlurb) {
      els.portfolioBlurb.textContent = `添加失败：${err.message || err}`;
    }
    setStatus(`添加失败：${err.message || err}`);
  } finally {
    if (submitBtn) submitBtn.disabled = false;
  }
});

let portfolioLookupTimer = 0;
async function refreshPortfolioLookup(q) {
  if (!els.portfolioSymbolSuggest && !els.portfolioLookupHint) return;
  const query = (q || "").trim();
  if (!query) {
    if (els.portfolioSymbolSuggest) els.portfolioSymbolSuggest.innerHTML = "";
    if (els.portfolioLookupHint) {
      els.portfolioLookupHint.hidden = true;
      els.portfolioLookupHint.textContent = "";
    }
    return;
  }
  try {
    const res = await fetch(
      `/api/portfolio/lookup?q=${encodeURIComponent(query)}&limit=8`
    );
    if (!res.ok) return;
    const data = await res.json();
    const suggestions = data.suggestions || [];
    if (els.portfolioSymbolSuggest) {
      els.portfolioSymbolSuggest.innerHTML = suggestions
        .map((row) => {
          const label = row.label || `${row.name || ""} · ${row.symbol || ""}`;
          // Prefer filling the Chinese/name query path when user typed CJK
          const value = /[\u4e00-\u9fff]/.test(query)
            ? row.name || row.symbol
            : row.symbol;
          return `<option value="${escapeHtml(value)}" label="${escapeHtml(
            label
          )}"></option>`;
        })
        .join("");
    }
    if (els.portfolioLookupHint) {
      const hit = data.resolved;
      if (hit?.symbol) {
        els.portfolioLookupHint.hidden = false;
        els.portfolioLookupHint.textContent = `将添加：${hit.name || hit.symbol}（${hit.symbol}）`;
      } else if (suggestions.length) {
        els.portfolioLookupHint.hidden = false;
        els.portfolioLookupHint.textContent = `候选 ${suggestions
          .slice(0, 3)
          .map((s) => s.symbol)
          .join(" / ")}`;
      } else {
        els.portfolioLookupHint.hidden = true;
        els.portfolioLookupHint.textContent = "";
      }
    }
  } catch {
    /* ignore lookup errors */
  }
}

els.portfolioSymbol?.addEventListener("input", () => {
  clearTimeout(portfolioLookupTimer);
  portfolioLookupTimer = setTimeout(() => {
    refreshPortfolioLookup(els.portfolioSymbol?.value || "");
  }, 180);
});

els.portfolioRemove?.addEventListener("click", async () => {
  const symbol = state.portfolio?.selected;
  if (!symbol) return;
  if (!confirm(`确定删除持仓 ${symbol}？`)) return;
  try {
    const data = await portfolioPost("/api/portfolio/remove", { symbol });
    state.portfolioPreview = null;
    const portfolio = await ensurePortfolioSelection(data.portfolio);
    syncHoldingSymbolsFromPortfolio(portfolio);
    renderPortfolio(portfolio);
  } catch (err) {
    if (els.portfolioBlurb) {
      els.portfolioBlurb.textContent = `删除失败：${err.message || err}`;
    }
  }
});

els.portfolioRefresh?.addEventListener("click", () => loadPortfolio({ refresh: true }));

els.portfolioExport?.addEventListener("click", async () => {
  try {
    const res = await fetch("/api/portfolio/export");
    const data = await res.json();
    const blob = new Blob([JSON.stringify(data.portfolio || {}, null, 2)], {
      type: "application/json",
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "pulse-portfolio.json";
    a.click();
    URL.revokeObjectURL(url);
  } catch (err) {
    if (els.portfolioBlurb) {
      els.portfolioBlurb.textContent = `导出失败：${err.message || err}`;
    }
  }
});

els.portfolioImport?.addEventListener("change", async (event) => {
  const file = event.target.files?.[0];
  if (!file) return;
  try {
    const text = await file.text();
    const parsed = JSON.parse(text);
    const holdings = parsed.holdings || parsed.portfolio?.holdings || [];
    const selected = parsed.selected || parsed.portfolio?.selected || "";
    const res = await fetch("/api/portfolio", {
      method: "PUT",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ holdings, selected }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    state.portfolioPreview = null;
    const portfolio = await ensurePortfolioSelection(data.portfolio);
    renderPortfolio(portfolio);
  } catch (err) {
    if (els.portfolioBlurb) {
      els.portfolioBlurb.textContent = `导入失败：${err.message || err}`;
    }
  } finally {
    event.target.value = "";
  }
});

els.filters?.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-category]");
  if (!btn) return;
  state.category = btn.dataset.category;
  for (const el of els.filters.querySelectorAll(".filter")) {
    const active = el === btn;
    el.classList.toggle("is-active", active);
    el.setAttribute("aria-selected", active ? "true" : "false");
  }
  loadIntel();
});

els.sortFilters?.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-sort]");
  if (!btn) return;
  state.sort = btn.dataset.sort;
  for (const el of els.sortFilters.querySelectorAll(".filter")) {
    const active = el === btn;
    el.classList.toggle("is-active", active);
    el.setAttribute("aria-selected", active ? "true" : "false");
  }
  loadIntel();
});

els.sentimentFilters?.addEventListener("click", (event) => {
  const watchBtn = event.target.closest("[data-watch]");
  if (watchBtn) {
    state.watchOnly = !state.watchOnly;
    watchBtn.classList.toggle("is-active", state.watchOnly);
    watchBtn.setAttribute("aria-selected", state.watchOnly ? "true" : "false");
    loadIntel();
    return;
  }

  const holdingsBtn = event.target.closest("[data-holdings]");
  if (holdingsBtn) {
    state.holdingsOnly = !state.holdingsOnly;
    if (!state.holdingsOnly) state.holdingFilter = "";
    syncHoldingsFilterUi();
    loadIntel();
    return;
  }

  const btn = event.target.closest("[data-sentiment]");
  if (!btn) return;
  state.sentiment = btn.dataset.sentiment;
  for (const el of els.sentimentFilters.querySelectorAll("[data-sentiment]")) {
    const active = el === btn;
    el.classList.toggle("is-active", active);
    el.setAttribute("aria-selected", active ? "true" : "false");
  }
  loadIntel();
});

els.holdingIntelChips?.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-holding-filter]");
  if (!btn) return;
  const symbol = btn.getAttribute("data-holding-filter") || "";
  loadHoldingIntel({ symbol });
});

els.intelHoldingChips?.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-holding-filter]");
  if (!btn) return;
  state.holdingsOnly = true;
  state.holdingFilter = btn.getAttribute("data-holding-filter") || "";
  syncHoldingsFilterUi();
  loadIntel();
});

els.holdingIntelRefresh?.addEventListener("click", () =>
  loadHoldingIntel({ refresh: true, symbol: state.holdingFilter || "" })
);

els.searchForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  state.q = (els.searchInput?.value || "").trim();
  loadIntel();
});

let searchTimer;
els.searchInput?.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.q = (els.searchInput?.value || "").trim();
    loadIntel();
  }, 320);
});

els.refresh?.addEventListener("click", () => {
  if (PAGE === "markets") loadMarketsDesk({ force: true });
  else loadIntel({ force: true });
});

els.saveSettings?.addEventListener("click", async () => {
  if (!els.saveSettings || !els.cfgWebhook) return;
  els.saveSettings.disabled = true;
  if (els.pushStatus) els.pushStatus.textContent = "正在保存设置…";
  try {
    const body = {
      webhook_url: els.cfgWebhook.value.trim(),
      webhook_format: els.cfgFormat?.value || "auto",
      push_interval_minutes: Number(els.cfgInterval?.value || 15),
      push_times: els.cfgTimes?.value || "",
      push_timezone: (els.cfgTz?.value || "").trim() || "Asia/Shanghai",
      push_enabled: Boolean(els.cfgEnabled?.checked),
      watch_keywords: els.cfgKeywords?.value || "",
    };
    const res = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    renderPush(data.push);
    if (els.pushStatus) {
      els.pushStatus.innerHTML =
        `<div><strong>已保存</strong>到本地配置。${els.pushStatus.innerHTML}</div>`;
    }
    setStatus("设置已保存");
  } catch (err) {
    if (els.pushStatus) {
      els.pushStatus.textContent = `保存失败：${err.message || err}`;
    }
  } finally {
    els.saveSettings.disabled = false;
  }
});

els.pushTest?.addEventListener("click", async () => {
  if (!els.pushTest) return;
  els.pushTest.disabled = true;
  if (els.pushStatus) els.pushStatus.textContent = "正在发送测试推送…";
  try {
    const headers = { "Content-Type": "application/json" };
    const secret = window.localStorage.getItem("PULSE_PUSH_SECRET");
    if (secret) headers["X-Pulse-Secret"] = secret;
    const res = await fetch("/api/push/test", { method: "POST", headers });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    if (els.pushStatus) {
      els.pushStatus.textContent = data.ok
        ? `测试推送成功：${(data.channels || []).join(", ")}`
        : `推送失败：${data.error || "未知错误"}`;
    }
    await loadSettingsPage();
  } catch (err) {
    if (els.pushStatus) {
      els.pushStatus.textContent = `推送失败：${err.message || err}`;
    }
  } finally {
    els.pushTest.disabled = false;
  }
});

function renderShareStatus(data) {
  const tip = document.getElementById("access-tip");
  const urlEl = document.getElementById("share-url");
  const startBtn = document.getElementById("btn-share-start");
  const stopBtn = document.getElementById("btn-share-stop");
  const copyBtn = document.getElementById("btn-share-copy");
  if (!tip || !urlEl) return;

  const publicUrl = data.public || data.url || data.share?.url;
  const phone = (data.phone || data.lan || [])[0];
  const running = Boolean(publicUrl || data.running || data.share?.running);

  if (phone) {
    tip.innerHTML = `局域网（同一 Wi-Fi）：<a href="${escapeHtml(phone)}">${escapeHtml(
      phone
    )}</a>`;
  } else {
    tip.textContent = data.tip || "局域网需同一 Wi-Fi";
  }

  if (publicUrl) {
    urlEl.hidden = false;
    urlEl.innerHTML = `公网分享（任意网络手机/电脑）：<a href="${escapeHtml(
      publicUrl
    )}" target="_blank" rel="noopener noreferrer">${escapeHtml(
      publicUrl
    )}</a><span class="note">本机服务需保持运行；重启后链接会变化</span>`;
    if (startBtn) startBtn.textContent = "公网已开启";
    if (startBtn) startBtn.disabled = true;
    if (stopBtn) stopBtn.hidden = false;
    if (copyBtn) {
      copyBtn.hidden = false;
      copyBtn.dataset.url = publicUrl;
    }
  } else {
    urlEl.hidden = true;
    urlEl.innerHTML = "";
    if (startBtn) {
      startBtn.textContent = running ? "生成链接中…" : "开启公网分享";
      startBtn.disabled = running;
    }
    if (stopBtn) stopBtn.hidden = !running;
    if (copyBtn) copyBtn.hidden = true;
    if (data.error || data.share?.error) {
      urlEl.hidden = false;
      urlEl.innerHTML = `<span class="note">开启失败：${escapeHtml(
        data.error || data.share.error
      )}</span>`;
    }
  }
}

async function loadAccessTip() {
  try {
    const res = await fetch("/api/access");
    if (!res.ok) return;
    const data = await res.json();
    renderShareStatus(data);
  } catch {
    /* ignore */
  }
}

async function startPublicShare() {
  const startBtn = document.getElementById("btn-share-start");
  const urlEl = document.getElementById("share-url");
  if (startBtn) {
    startBtn.disabled = true;
    startBtn.textContent = "正在开通公网…";
  }
  if (urlEl) {
    urlEl.hidden = false;
    urlEl.innerHTML = `<span class="note">正在连接 Cloudflare 临时隧道，约需数秒…</span>`;
  }
  try {
    const res = await fetch("/api/share/start", { method: "POST" });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    renderShareStatus(data);
    if (!data.url) {
      // Poll a few times while tunnel negotiates
      for (let i = 0; i < 12 && !data.url; i += 1) {
        await new Promise((r) => setTimeout(r, 1000));
        const st = await fetch("/api/share").then((r) => r.json());
        renderShareStatus(st);
        if (st.url) break;
      }
    }
  } catch (err) {
    if (urlEl) {
      urlEl.hidden = false;
      urlEl.innerHTML = `<span class="note">开启失败：${escapeHtml(
        err.message || String(err)
      )}</span>`;
    }
    if (startBtn) {
      startBtn.disabled = false;
      startBtn.textContent = "开启公网分享";
    }
  }
}

document.getElementById("btn-share-start")?.addEventListener("click", startPublicShare);
document.getElementById("btn-share-stop")?.addEventListener("click", async () => {
  await fetch("/api/share/stop", { method: "POST" });
  loadAccessTip();
});
document.getElementById("btn-share-copy")?.addEventListener("click", async (event) => {
  const btn = event.currentTarget;
  const url = btn?.dataset?.url;
  if (!url) return;
  try {
    await navigator.clipboard.writeText(url);
    btn.textContent = "已复制";
    setTimeout(() => {
      btn.textContent = "复制链接";
    }, 1500);
  } catch {
    btn.textContent = "复制失败";
  }
});

document.addEventListener("click", (event) => {
  const btn = event.target.closest("[data-open-event]");
  if (btn) {
    event.preventDefault();
    openEventById(btn.getAttribute("data-open-event"));
    return;
  }
  if (event.target === els.eventDrawer) {
    closeEventDrawer();
  }
});

els.eventDrawerClose?.addEventListener("click", closeEventDrawer);
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape") closeEventDrawer();
});

function readIntelQueryFlags() {
  if (PAGE !== "intel") return;
  const params = new URLSearchParams(window.location.search);
  if (params.get("holdings") === "1" || params.get("holdings_only") === "1") {
    state.holdingsOnly = true;
  }
  const holding = (params.get("holding") || "").trim().toUpperCase();
  if (holding) {
    state.holdingsOnly = true;
    state.holdingFilter = holding;
  }
  syncHoldingsFilterUi();
}

function setAuthMode(mode) {
  const next = mode === "register" ? "register" : "login";
  const modeInput = document.getElementById("auth-mode");
  const submitBtn = document.getElementById("auth-submit");
  const errorEl = document.getElementById("auth-error");
  const displayWrap = document.getElementById("auth-display-wrap");
  const passwordInput = document.getElementById("auth-password");
  document.querySelectorAll("[data-auth-tab]").forEach((el) => {
    const on = (el.getAttribute("data-auth-tab") || "") === next;
    el.classList.toggle("is-active", on);
    el.setAttribute("aria-selected", on ? "true" : "false");
  });
  if (modeInput) modeInput.value = next;
  if (displayWrap) {
    displayWrap.hidden = next !== "register";
    displayWrap.style.display = next === "register" ? "" : "none";
  }
  if (passwordInput) {
    passwordInput.autocomplete =
      next === "register" ? "new-password" : "current-password";
  }
  if (submitBtn) submitBtn.textContent = next === "register" ? "注册并登录" : "登录";
  if (errorEl) {
    errorEl.hidden = true;
    errorEl.textContent = "";
  }
}

function bindAuthPage() {
  const form = document.getElementById("auth-form");
  if (!form) return;
  const modeInput = document.getElementById("auth-mode");
  const submitBtn = document.getElementById("auth-submit");
  const errorEl = document.getElementById("auth-error");

  // Honor /login?mode=register and keep display-name field truly hidden on login
  const initialMode =
    new URLSearchParams(window.location.search).get("mode") === "register"
      ? "register"
      : modeInput?.value || "login";
  setAuthMode(initialMode);

  document.querySelectorAll("[data-auth-tab]").forEach((btn) => {
    btn.addEventListener("click", () => {
      setAuthMode(btn.getAttribute("data-auth-tab") || "login");
    });
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const mode = modeInput?.value || "login";
    const username = document.getElementById("auth-username")?.value.trim() || "";
    const password = document.getElementById("auth-password")?.value || "";
    const display_name = document.getElementById("auth-display")?.value.trim() || "";
    if (submitBtn) submitBtn.disabled = true;
    if (errorEl) {
      errorEl.hidden = true;
      errorEl.textContent = "";
    }
    try {
      const res = await fetch(
        mode === "register" ? "/api/auth/register" : "/api/auth/login",
        {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ username, password, display_name }),
        }
      );
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        const detail = data?.detail;
        let msg = `HTTP ${res.status}`;
        if (typeof detail === "string") msg = detail;
        else if (Array.isArray(detail)) {
          msg = detail
            .map((d) => (typeof d === "string" ? d : d?.msg || JSON.stringify(d)))
            .filter(Boolean)
            .join("；");
        } else if (detail && typeof detail === "object" && detail.msg) {
          msg = String(detail.msg);
        }
        throw new Error(msg || `请求失败（${res.status}）`);
      }
      let next = new URLSearchParams(window.location.search).get("next") || "/";
      if (!next.startsWith("/")) next = "/";
      // Bust any stale document cache from older service workers
      const join = next.includes("?") ? "&" : "?";
      window.location.href = `${next}${join}_auth=${Date.now()}`;
    } catch (err) {
      if (errorEl) {
        errorEl.hidden = false;
        errorEl.style.display = "";
        errorEl.textContent = err.message || String(err);
      }
      setStatus(`登录失败：${err.message || err}`);
    } finally {
      if (submitBtn) submitBtn.disabled = false;
    }
  });
}

document.getElementById("btn-logout")?.addEventListener("click", async () => {
  try {
    await fetch("/api/auth/logout", {
      method: "POST",
      credentials: "same-origin",
    });
  } finally {
    window.location.href = "/login";
  }
});

function pctClass(pct) {
  if (typeof pct !== "number" || Number.isNaN(pct)) return "";
  return pct > 0 ? "up" : pct < 0 ? "down" : "";
}

function pctText(pct) {
  const n = Number(pct);
  if (pct == null || !Number.isFinite(n)) return "—";
  return `${n >= 0 ? "+" : ""}${n.toFixed(2)}%`;
}

/** Shared desk stats: 现价/开高低/月涨幅 + 收盘% + 时段实时% (holdings + sectors). */
function deskStatsBlockHtml(pick, stats) {
  const closePct = pick?.change_pct;
  const sessionLabel = String(pick?.session_label || "").trim() || "实时";
  const rtPct = pick?.rt_change_pct;
  const priceCls = pctClass(closePct);
  return `
    <div class="portfolio-stats" aria-label="区间读数">
      <span class="stat-cell">
        <span class="k">现价</span>
        <span class="v ${priceCls}" data-desk-price>${escapeHtml(
          pick?.price == null ? "—" : formatNumber(pick.price, "")
        )}</span>
      </span>
      <span class="stat-cell">
        <span class="k">开</span>
        <span class="v">${escapeHtml(
          stats?.open == null ? "—" : formatNumber(stats.open, "")
        )}</span>
      </span>
      <span class="stat-cell">
        <span class="k">高</span>
        <span class="v up">${escapeHtml(
          stats?.high == null ? "—" : formatNumber(stats.high, "")
        )}</span>
      </span>
      <span class="stat-cell">
        <span class="k">低</span>
        <span class="v down">${escapeHtml(
          stats?.low == null ? "—" : formatNumber(stats.low, "")
        )}</span>
      </span>
      <span class="stat-cell">
        <span class="k">月涨幅</span>
        <span class="v ${pctClass(pick?.month_change_pct)}">${escapeHtml(
          pctText(pick?.month_change_pct)
        )}</span>
      </span>
    </div>
    <div class="desk-chg-row" aria-label="收盘与时段涨跌">
      <span class="desk-close-chg ${pctClass(closePct)}" data-desk-close-chg>收盘: ${escapeHtml(
        pctText(closePct)
      )}</span>
      <span class="desk-session-chg ${pctClass(rtPct)}" data-desk-session-chg data-session-label="${escapeHtml(
        sessionLabel
      )}">${escapeHtml(sessionLabel)}: ${escapeHtml(pctText(rtPct))}</span>
    </div>
  `;
}

/** Shared holdings/sectors list quote: 收盘涨跌幅 + 实时涨跌幅 + 时段. */
function listQuoteHtml(pick) {
  const closePct = pick?.change_pct;
  const rtPct =
    pick?.rt_change_pct != null ? pick.rt_change_pct : null;
  const sessionLabel = String(pick?.session_label || "").trim();
  const price =
    pick?.price == null ? "—" : formatNumber(pick.price, "");
  const rtPrice =
    pick?.rt_price == null ? "" : formatNumber(pick.rt_price, "");
  const showRt =
    rtPct != null || pick?.rt_price != null || Boolean(sessionLabel);
  return `
    <span class="quote">
      <span class="quote-main">
        <span class="price ${pctClass(closePct)}">${escapeHtml(price)}</span>
        <span class="chg chg-close ${pctClass(closePct)}" title="收盘涨跌幅">${escapeHtml(
          pctText(closePct)
        )}</span>
      </span>
      ${
        showRt
          ? `<span class="quote-rt" title="实时涨跌幅">
        <span class="rt-price ${pctClass(rtPct)}">${escapeHtml(
          rtPrice || "—"
        )}</span>
        <span class="rt-chg ${pctClass(rtPct)}">${escapeHtml(
          pctText(rtPct)
        )}${
          sessionLabel
            ? `<span class="session-tag">${escapeHtml(sessionLabel)}</span>`
            : ""
        }</span>
      </span>`
          : ""
      }
    </span>
  `;
}

function mergeListQuoteFields(next, prev) {
  if (!next) return prev || next;
  if (!prev) return next;
  const out = { ...next };
  const nextSid = String(out.session || "");
  const prevSid = String(prev.session || "");
  // Never carry RT across session boundaries (夜盘→盘前 was showing stale %).
  const sameSession = nextSid && prevSid && nextSid === prevSid;
  if (nextSid === "night") {
    const prevOvernight = Boolean(prev.overnight);
    const nextOvernight = Boolean(out.overnight);
    if (!nextOvernight) {
      if (prevOvernight && sameSession) {
        for (const key of ["rt_price", "rt_change", "rt_change_pct"]) {
          if (out[key] == null && prev[key] != null) out[key] = prev[key];
        }
        out.overnight = true;
      } else {
        delete out.rt_price;
        delete out.rt_change;
        delete out.rt_change_pct;
        delete out.overnight;
      }
    }
  } else if (sameSession) {
    for (const key of ["rt_price", "rt_change", "rt_change_pct"]) {
      if (out[key] == null && prev[key] != null) out[key] = prev[key];
    }
    delete out.overnight;
  } else {
    // Session flipped (e.g. 夜盘→盘前): drop prior RT unless next brought fresh.
    if (out.rt_price == null) {
      delete out.rt_price;
      delete out.rt_change;
      delete out.rt_change_pct;
    }
    delete out.overnight;
  }
  for (const key of [
    "price",
    "change",
    "change_pct",
    "session",
    "session_label",
  ]) {
    if (out[key] == null && prev[key] != null) out[key] = prev[key];
  }
  return out;
}

function renderAiDesk(aiDesk) {
  const data = aiDesk || {};
  const analysis = data.analysis || {};
  const counts = analysis.counts || {};
  const score =
    typeof analysis.avg_score === "number"
      ? analysis.avg_score.toFixed(2)
      : "0.00";
  const factors = (analysis.top_factors || []).slice(0, 4).join("、");
  const label = data.label || "热点板块";
  if (els.hotDeskTitle) els.hotDeskTitle.textContent = "热点利空";
  if (els.aiDeskBlurb) {
    els.aiDeskBlurb.textContent =
      data.blurb ||
      `${label} · 样本 ${counts.total || 0} · 利空 ${counts.bearish || 0}`;
  }
  if (els.aiAnalysisCard) {
    const q = label;
    els.aiAnalysisCard.innerHTML = `
      <div class="war-analysis-head">
        <h3>${escapeHtml(label)}</h3>
        <a class="btn ghost btn-compact" href="/intel?q=${encodeURIComponent(
          q
        )}">情报流</a>
      </div>
      <div class="brief-meta-row">
        <span class="brief-chip bias-bearish">利空 ${counts.bearish || 0}</span>
        <span class="brief-chip score">均分 ${escapeHtml(score)}</span>
        <span class="brief-chip">样本 ${counts.total || 0}</span>
      </div>
      <p class="war-assessment">${escapeHtml(analysis.assessment || "暂无评判")}</p>
      ${
        factors
          ? `<p class="war-factors">因子：${escapeHtml(factors)}</p>`
          : ""
      }
    `;
  }
  if (els.aiNewsList) {
    const rows = data.latest?.length ? data.latest : data.spotlight || [];
    if (!rows.length) {
      els.aiNewsList.innerHTML = '<p class="empty">暂无该热点相关新闻。</p>';
    } else {
      els.aiNewsList.innerHTML = rows
        .slice(0, 4)
        .map((item) => spotlightCardHtml(item))
        .join("");
    }
  }
}

function renderSectorNewsFeed(data) {
  const news = data?.sector_news || [];
  const label =
    data?.active_sector?.label || data?.active_sector_id || "当前板块";
  const q = data?.active_sector?.topic_id || label;
  if (els.sectorNewsBlurb) {
    els.sectorNewsBlurb.textContent = news.length
      ? `${label} · Google News · ${news.length} 条最新`
      : `${label} · Google News · 暂无最新`;
  }
  if (els.sectorNewsLink) {
    els.sectorNewsLink.href = `/intel?q=${encodeURIComponent(q)}`;
  }
  if (!els.sectorNewsList) return;
  els.sectorNewsList.innerHTML = news.length
    ? news.slice(0, 8).map((item) => spotlightCardHtml(item)).join("")
    : '<p class="empty">暂无该板块最新新闻。</p>';
}

function renderSymbolNewsFeed(data) {
  const pick = data?.selected_pick;
  const news =
    data?.symbol_news ||
    pick?.symbol_news ||
    [];
  const sym = data?.selected_symbol || pick?.symbol || "";
  const name = pick?.name || sym;
  if (els.symbolNewsBlurb) {
    if (!sym) {
      els.symbolNewsBlurb.textContent = "点选个股后汇总最新消息";
    } else if (!news.length) {
      els.symbolNewsBlurb.textContent = `${name} · Google News · 暂无最新`;
    } else {
      els.symbolNewsBlurb.textContent = `${name} · Google News · ${news.length} 条最新`;
    }
  }
  if (els.symbolNewsLink) {
    els.symbolNewsLink.href = sym
      ? `/intel?q=${encodeURIComponent(sym)}`
      : "/intel";
  }
  if (!els.symbolNewsList) return;
  if (!sym) {
    els.symbolNewsList.innerHTML =
      '<p class="empty">选择个股后显示相关新闻</p>';
    return;
  }
  els.symbolNewsList.innerHTML = news.length
    ? news.slice(0, 8).map((item) => spotlightCardHtml(item)).join("")
    : `<p class="empty">暂无 ${escapeHtml(
        sym
      )} 最新消息 · <a href="/intel?q=${encodeURIComponent(sym)}">去情报流搜索</a></p>`;
  requestAnimationFrame(() => syncSectorsDeskHeights());
}

function heatColor(pct) {
  if (pct == null || Number.isNaN(Number(pct))) {
    return "color-mix(in srgb, var(--panel-2, #243041) 88%, #6b7c90)";
  }
  const t = clamp(Number(pct) / 3.5, -1, 1);
  if (t >= 0) {
    const a = 0.22 + t * 0.78;
    return `color-mix(in srgb, ${TAPE_UP} ${Math.round(a * 100)}%, #2a3340)`;
  }
  const a = 0.22 + -t * 0.78;
  return `color-mix(in srgb, ${TAPE_DOWN} ${Math.round(a * 100)}%, #2a3340)`;
}

function layoutTreemap(nodes, x, y, w, h, out) {
  const items = (nodes || []).filter((n) => n && n.value > 0);
  if (!items.length || w < 1 || h < 1) return;
  if (items.length === 1) {
    out.push({ ...items[0], x, y, w, h });
    return;
  }
  const total = items.reduce((s, n) => s + n.value, 0) || 1;
  let acc = 0;
  let split = 1;
  for (let i = 0; i < items.length; i += 1) {
    acc += items[i].value;
    if (acc >= total * 0.5) {
      split = Math.max(1, Math.min(items.length - 1, i + 1));
      break;
    }
  }
  const left = items.slice(0, split);
  const right = items.slice(split);
  const leftSum = left.reduce((s, n) => s + n.value, 0);
  const ratio = leftSum / total;
  if (w >= h) {
    const lw = w * ratio;
    layoutTreemap(left, x, y, lw, h, out);
    layoutTreemap(right, x + lw, y, w - lw, h, out);
  } else {
    const lh = h * ratio;
    layoutTreemap(left, x, y, w, lh, out);
    layoutTreemap(right, x, y + lh, w, h - lh, out);
  }
}

/** Clamp treemap labels to real pixel boxes after layout (fixes phone overflow). */
function fitSectorMapLabels() {
  const stage = els.sectorMapCanvas?.querySelector(".sector-map-stage");
  if (!stage) return;
  stage.querySelectorAll(".map-stock").forEach((el) => {
    const w = el.clientWidth;
    const h = el.clientHeight;
    el.classList.toggle("is-tiny", w < 40 || h < 26);
    el.classList.toggle("is-compact", w < 62 || h < 38);
    el.classList.toggle("is-roomy", w >= 86 && h >= 50);
    const nm = el.querySelector(".nm");
    if (nm && (w < 72 || h < 44)) nm.hidden = true;
    const pct = el.querySelector(".pct");
    if (pct && (w < 30 || h < 20)) pct.hidden = true;
  });
  stage.querySelectorAll(".map-group-label").forEach((el) => {
    const host = el.parentElement;
    if (!host) return;
    if (host.clientWidth < 52 || host.clientHeight < 36) {
      el.hidden = true;
      host.querySelector(".map-group-body")?.classList.remove("has-label");
    }
  });
  stage.querySelectorAll(".map-sector-label").forEach((el) => {
    const host = el.parentElement;
    if (!host) return;
    if (host.clientWidth < 64 || host.clientHeight < 48) {
      el.hidden = true;
      host.querySelector(".map-sector-body")?.classList.remove("has-label");
    }
  });
}

function renderSectorMap(map) {
  if (!els.sectorMapCanvas) return;
  const sectors = map?.sectors || [];
  const stats = map?.stats || {};
  if (els.sectorMapBlurb) {
    if (!sectors.length) {
      els.sectorMapBlurb.textContent = "全板块涨跌图暂不可用，稍后刷新";
    } else {
      const bits = [
        `已覆盖 ${stats.quoted || 0}/${stats.symbols || 0} 只龙头`,
        typeof stats.up === "number" ? `涨 ${stats.up}` : "",
        typeof stats.down === "number" ? `跌 ${stats.down}` : "",
        map?.cached ? "缓存" : "",
      ].filter(Boolean);
      els.sectorMapBlurb.textContent = `${bits.join(" · ")} · 点击板块或个股下钻`;
    }
  }
  if (!sectors.length) {
    els.sectorMapCanvas.innerHTML =
      '<p class="empty">暂无全板块数据，请点击刷新重试。</p>';
    return;
  }

  const narrow =
    typeof window !== "undefined" &&
    (window.matchMedia("(max-width: 720px)").matches ||
      document.documentElement.classList.contains("pulse-native-app"));
  const width = 1000;
  const height = narrow ? 640 : 520;
  const sectorNodes = sectors.map((s) => ({
    ...s,
    value: Math.max(0.5, Number(s.weight) || 1),
  }));
  const sectorRects = [];
  layoutTreemap(sectorNodes, 0, 0, width, height, sectorRects);

  const gap = 1.1;
  const html = sectorRects
    .map((sec) => {
      const sx = sec.x + gap;
      const sy = sec.y + gap;
      const sw = Math.max(1, sec.w - gap * 2);
      const sh = Math.max(1, sec.h - gap * 2);
      const showHead = narrow ? sh > 72 && sw > 86 : sh > 64 && sw > 70;
      const innerW = Math.max(1, sw - 2);
      const innerH = Math.max(1, sh - (showHead ? 17 : 2));
      const groups = (sec.groups || []).map((g) => ({
        ...g,
        value: Math.max(0.4, Number(g.weight) || 1),
      }));
      const groupRects = [];
      layoutTreemap(groups, 0, 0, innerW, innerH, groupRects);
      const groupsHtml = groupRects
        .map((grp) => {
          const showGHead = narrow
            ? grp.h > 52 && grp.w > 64
            : grp.h > 42 && grp.w > 50;
          const bodyW = Math.max(1, grp.w - 1);
          const bodyH = Math.max(1, grp.h - (showGHead ? 13 : 1));
          const stocks = (grp.children || []).map((c) => ({
            ...c,
            value: Math.max(0.3, Number(c.weight) || 1),
          }));
          const stockRects = [];
          layoutTreemap(stocks, 0, 0, bodyW, bodyH, stockRects);
          const stocksHtml = stockRects
            .map((st) => {
              // Phone: ticker + % only — company names overflow tiny cells.
              const showName = narrow
                ? false
                : st.w / bodyW > 0.28 && st.h / bodyH > 0.34;
              const showPct = narrow
                ? st.w > 28 && st.h > 22
                : st.w / bodyW > 0.18 && st.h / bodyH > 0.22;
              const pct = st.change_pct;
              const cls =
                pct == null || Number.isNaN(Number(pct))
                  ? ""
                  : Number(pct) >= 0
                    ? "up"
                    : "down";
              return `
                <button type="button" class="map-stock ${cls}"
                  style="left:${((st.x / bodyW) * 100).toFixed(3)}%;top:${(
                    (st.y / bodyH) *
                    100
                  ).toFixed(3)}%;width:${((Math.max(0, st.w - 0.6) / bodyW) * 100).toFixed(
                    3
                  )}%;height:${((Math.max(0, st.h - 0.6) / bodyH) * 100).toFixed(
                    3
                  )}%;background:${heatColor(pct)}"
                  data-symbol="${escapeHtml(st.symbol || "")}"
                  data-desk="${escapeHtml(sec.desk_id || sec.id || "")}"
                  title="${escapeHtml(st.name || st.symbol || "")} ${escapeHtml(
                    pctText(pct)
                  )}">
                  <span class="sym">${escapeHtml(st.symbol || "")}</span>
                  ${
                    showName
                      ? `<span class="nm">${escapeHtml(st.name || "")}</span>`
                      : ""
                  }
                  ${
                    showPct
                      ? `<span class="pct">${escapeHtml(pctText(pct))}</span>`
                      : ""
                  }
                </button>
              `;
            })
            .join("");
          return `
            <div class="map-group" style="left:${((grp.x / innerW) * 100).toFixed(
              3
            )}%;top:${((grp.y / innerH) * 100).toFixed(3)}%;width:${(
              (Math.max(0, grp.w - 0.5) / innerW) *
              100
            ).toFixed(3)}%;height:${((Math.max(0, grp.h - 0.5) / innerH) * 100).toFixed(
              3
            )}%">
              ${
                showGHead
                  ? `<div class="map-group-label">${escapeHtml(
                      grp.label || ""
                    )}</div>`
                  : ""
              }
              <div class="map-group-body${
                showGHead ? " has-label" : ""
              }">${stocksHtml}</div>
            </div>
          `;
        })
        .join("");
      return `
        <div class="map-sector" style="left:${((sx / width) * 100).toFixed(
          3
        )}%;top:${((sy / height) * 100).toFixed(3)}%;width:${((sw / width) * 100).toFixed(
          3
        )}%;height:${((sh / height) * 100).toFixed(3)}%;--sector-tint:${heatColor(
          sec.change_pct
        )}">
          ${
            showHead
              ? `<button type="button" class="map-sector-label" data-desk="${escapeHtml(
                  sec.desk_id || sec.id || ""
                )}" title="${escapeHtml(sec.label || "")} ${escapeHtml(
                  pctText(sec.change_pct)
                )}">${escapeHtml(sec.label || "")}<span>${escapeHtml(
                  pctText(sec.change_pct)
                )}</span></button>`
              : ""
          }
          <div class="map-sector-body${showHead ? " has-label" : ""}">${groupsHtml}</div>
        </div>
      `;
    })
    .join("");

  els.sectorMapCanvas.innerHTML = `<div class="sector-map-stage${
    narrow ? " is-narrow" : ""
  }">${html}</div>`;
  requestAnimationFrame(() => {
    fitSectorMapLabels();
    requestAnimationFrame(fitSectorMapLabels);
  });

  els.sectorMapCanvas.querySelectorAll("[data-desk].map-sector-label").forEach((btn) => {
    btn.addEventListener("click", () => {
      openSectorDesk(btn.getAttribute("data-desk"), { scroll: true });
    });
  });
  els.sectorMapCanvas.querySelectorAll(".map-stock[data-symbol]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const sym = (btn.getAttribute("data-symbol") || "").toUpperCase();
      const desk = btn.getAttribute("data-desk") || "";
      if (!sym) return;
      if (desk && desk !== state.sectorId) {
        state.sectorId = desk;
        state.sectorSymbol = sym;
        loadSectorDesk().finally(() => {
          els.sectorsDesk?.scrollIntoView({ behavior: "smooth", block: "start" });
        });
        return;
      }
      selectSectorSymbol(sym);
      els.sectorsDesk?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  });
}

async function loadSectorMap({ force = false } = {}) {
  if (PAGE !== "sectors" || !els.sectorMapCanvas) return null;
  if (force) {
    els.sectorMapCanvas.innerHTML = '<p class="empty">刷新全板块涨跌图…</p>';
  }
  try {
    const params = force ? "?refresh=true" : "";
    const res = await fetch(`/api/sectors/map${params}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderSectorMap(data);
    return data;
  } catch (err) {
    if (els.sectorMapBlurb) {
      els.sectorMapBlurb.textContent = `涨跌图加载失败：${err.message || err}`;
    }
    els.sectorMapCanvas.innerHTML =
      '<p class="empty">全板块涨跌图加载失败，请稍后刷新。</p>';
    return null;
  }
}

function syncSectorQuery() {
  if (PAGE !== "sectors" || typeof history === "undefined" || !history.replaceState) {
    return;
  }
  const params = new URLSearchParams(location.search);
  if (state.sectorId) params.set("sector", state.sectorId);
  else params.delete("sector");
  if (state.sectorSymbol) params.set("symbol", state.sectorSymbol);
  else params.delete("symbol");
  const qs = params.toString();
  const next = `${location.pathname}${qs ? `?${qs}` : ""}${location.hash || ""}`;
  if (next !== `${location.pathname}${location.search}${location.hash || ""}`) {
    history.replaceState(null, "", next);
  }
}

function sectorCacheGet(id) {
  const row = state.sectorCache?.[id];
  if (!row?.data) return null;
  // Keep optimistic sector paint warm across tab switches / hover.
  if (Date.now() - Number(row.at || 0) > 120_000) return null;
  return row.data;
}

function sectorCachePut(id, data) {
  if (!id || !data) return;
  state.sectorCache[id] = { at: Date.now(), data };
}

function pickHasChart(pick) {
  const series = pick?.series || {};
  const day = series.day?.points || [];
  const month = series.month?.points || [];
  // Require multi-TF desk chart — list sparklines alone are not enough
  return day.length >= 2 || month.length >= 2;
}

function pickHasIntraday(pick) {
  return (pick?.series?.intraday?.points || []).length >= 2;
}

function deskChartReady(pick) {
  return pickHasChart(pick) || pickHasIntraday(pick);
}

function pickHasTfSeries(pick, tf) {
  const want = tf || "intraday";
  if (want === "intraday") return pickHasIntraday(pick);
  return (pick?.series?.[want]?.points || []).length >= 2;
}

/** Background-fetch day/month/quarter when the board only has 分时. */
function ensureMultiTfChartUpgrade({ force = false } = {}) {
  if (PAGE === "desk") {
    const board = state.portfolio?.selected_board;
    const sym = state.portfolio?.selected || board?.symbol || "";
    if (!sym || (pickHasChart(board) && !force)) return;
    // Coalesce through the same /select path as symbol clicks.
    selectPortfolioSymbol(sym, { quiet: true });
    return;
  }
  if (PAGE === "sectors") {
    const pick = state.sectors?.selected_pick;
    if (pickHasChart(pick) && !force) return;
    loadSectorDesk({ force });
  }
}

function markActiveListRow(listEl, symbol, attr = "data-symbol") {
  if (!listEl) return;
  const sym = String(symbol || "").toUpperCase();
  listEl.querySelectorAll(".holding-row, .sector-pick-row").forEach((row) => {
    const rowSym = (
      row.getAttribute(attr) ||
      row.getAttribute("data-holding") ||
      row.getAttribute("data-symbol") ||
      ""
    ).toUpperCase();
    const on = Boolean(sym && rowSym === sym);
    row.classList.toggle("is-active", on);
    row.setAttribute("aria-selected", on ? "true" : "false");
  });
}

function refreshActiveRowQuote(listEl, pick, attr = "data-symbol") {
  if (!listEl || !pick?.symbol) return;
  const row = listEl.querySelector(
    `[${attr}="${String(pick.symbol).toUpperCase()}"]`
  );
  if (!row) return;
  const spark = row.querySelector(".spark-wrap");
  if (spark && pickHasIntraday(pick)) {
    spark.innerHTML = holdingSparkSvg(pick, "intraday");
  }
  const quote = row.querySelector(".quote");
  if (quote) quote.outerHTML = listQuoteHtml(pick);
  const pct = pick.change_pct;
  row.classList.toggle("up", pctClass(pct) === "up");
  row.classList.toggle("down", pctClass(pct) === "down");
}

function paintPortfolioSelection() {
  markActiveListRow(els.holdingRail, state.portfolio?.selected, "data-holding");
  syncHoldingPreviewClasses();
  renderPortfolioChart();
  renderPortfolioFocus(state.portfolio);
}

function paintSectorSelection() {
  const data = state.sectors || {};
  markActiveListRow(
    els.sectorPickList,
    data.selected_symbol || state.sectorSymbol,
    "data-symbol"
  );
  renderSectorPickChart();
  renderSectorNewsFeed(data);
  renderSymbolNewsFeed(data);
  renderEarningsCalendar(data);
  renderValueChain(data?.value_chain || data?.selected_pick?.value_chain);
  scheduleSectorsDeskHeightSync();
}

function updateDeskChartQuote(
  root,
  { pct, price, rtPct, sessionLabel } = {}
) {
  if (!root) return;
  // Legacy top-right badge (removed from markup; keep safe if cached HTML remains).
  const range = root.querySelector(".chart-head .range");
  if (range) range.hidden = true;
  const priceV = root.querySelector("[data-desk-price]");
  if (priceV && price != null) {
    priceV.className = `v ${pctClass(pct)}`;
    priceV.textContent = formatNumber(price, "");
  }
  const closeEl = root.querySelector("[data-desk-close-chg]");
  if (closeEl && pct != null) {
    closeEl.className = `desk-close-chg ${pctClass(pct)}`;
    closeEl.textContent = `收盘: ${pctText(pct)}`;
  }
  const sessEl = root.querySelector("[data-desk-session-chg]");
  if (sessEl) {
    const label =
      String(sessionLabel || sessEl.getAttribute("data-session-label") || "").trim() ||
      "实时";
    sessEl.setAttribute("data-session-label", label);
    const hasRt = rtPct != null && Number.isFinite(Number(rtPct));
    sessEl.className = `desk-session-chg ${hasRt ? pctClass(rtPct) : ""}`;
    sessEl.textContent = `${label}: ${hasRt ? pctText(rtPct) : "—"}`;
  }
}

function patchZoomableIntraday(key, series, pick) {
  const points = series?.points || [];
  if (points.length < 2) return false;
  const meta = chartZoomData.get(key);
  if (!meta?.root?.querySelector(".chart-zoom-stage") || meta.tf !== "intraday") {
    return false;
  }
  const pct =
    series?.change_pct != null ? series.change_pct : pick?.change_pct;
  const up = !(typeof pct === "number" && pct < 0);
  meta.points = points;
  meta.len = points.length;
  meta.up = up;
  meta.sessions = series?.sessions || null;
  meta.previousClose = series?.previous_close ?? null;
  meta.cycleStart = series?.cycle_start ?? null;
  paintZoomableChart(key);
  return true;
}

function applyIntradaySnapshot(sym, snap) {
  const symbol = String(sym || "").toUpperCase();
  const intra = snap?.series?.intraday;
  if (!symbol || !intra?.points?.length) return;
  // Poll updates 实时价/涨跌; keep 收盘涨跌幅 (change_pct) from the day quote.
  // Prefer backend session-aware rt_*; never clone full-day % into 夜盘/盘后/盘前.
  const sid = String(snap.session || "");
  const rtPatch = {
    series: { intraday: intra },
  };
  if (snap.session_label) {
    rtPatch.session = snap.session;
    rtPatch.session_label = snap.session_label;
  }
  const hasExplicitRt =
    snap.rt_price != null || snap.rt_change != null || snap.rt_change_pct != null;
  if (hasExplicitRt) {
    if (snap.rt_price != null) rtPatch.rt_price = snap.rt_price;
    if (snap.rt_change != null) rtPatch.rt_change = snap.rt_change;
    if (snap.rt_change_pct != null) rtPatch.rt_change_pct = snap.rt_change_pct;
    if (sid === "night") rtPatch.overnight = true;
  } else if (sid === "night") {
    // No true Overnight on this snap — clear 盘后 leftovers.
    rtPatch.rt_price = null;
    rtPatch.rt_change = null;
    rtPatch.rt_change_pct = null;
    rtPatch.overnight = false;
  } else if (sid === "regular") {
    rtPatch.rt_price = snap.price;
    rtPatch.rt_change = snap.change;
    rtPatch.rt_change_pct = snap.change_pct;
  } else if (sid === "pre" || sid === "post") {
    // Legacy snapshot without rt_*: only adopt when distinct from day line.
    const dayBoard =
      PAGE === "desk"
        ? state.portfolio?.selected_board
        : state.sectors?.selected_pick;
    const dayPx = dayBoard?.price;
    const dayPct = dayBoard?.change_pct;
    const samePx =
      snap.price != null &&
      dayPx != null &&
      Math.abs(Number(snap.price) - Number(dayPx)) < 1e-6;
    const samePct =
      snap.change_pct != null &&
      dayPct != null &&
      Math.abs(Number(snap.change_pct) - Number(dayPct)) < 1e-6;
    if (!(samePx && samePct)) {
      rtPatch.rt_price = snap.price;
      rtPatch.rt_change = snap.change;
      rtPatch.rt_change_pct = snap.change_pct;
    }
  }

  if (PAGE === "desk" && state.portfolio) {
    const board = state.portfolio.selected_board;
    if (board?.symbol === symbol) {
      const nextBoard = mergePickPreserveIntraday(
        {
          ...board,
          ...rtPatch,
          series: { ...(board.series || {}), intraday: intra },
          symbol,
        },
        board
      );
      state.portfolio.selected_board = nextBoard;
      state.portfolio.board = nextBoard;
      state.portfolio.holdings = (state.portfolio.holdings || []).map((h) =>
        h.symbol === symbol
          ? mergePickPreserveIntraday({ ...h, ...nextBoard, symbol }, h)
          : h
      );
      cachePortfolioBoard(nextBoard);
      refreshActiveRowQuote(els.holdingRail, nextBoard, "data-holding");
      if (
        state.portfolioTf === "intraday" &&
        !state.portfolioPreview &&
        state.portfolio.selected === symbol
      ) {
        if (!patchZoomableIntraday("portfolio", intra, nextBoard)) {
          renderPortfolioChart();
        } else {
          updateDeskChartQuote(els.portfolioChart, {
            pct: nextBoard.change_pct,
            price: nextBoard.price,
            rtPct: nextBoard.rt_change_pct,
            sessionLabel: nextBoard.session_label,
          });
        }
      }
    }
  }

  if (PAGE === "sectors" && state.sectors) {
    const pick = state.sectors.selected_pick;
    if (pick?.symbol === symbol) {
      const nextPick = mergePickPreserveIntraday(
        {
          ...pick,
          ...rtPatch,
          series: { ...(pick.series || {}), intraday: intra },
          symbol,
        },
        pick
      );
      state.sectors.selected_pick = nextPick;
      state.sectors.picks = (state.sectors.picks || []).map((p) =>
        p.symbol === symbol
          ? mergePickPreserveIntraday({ ...p, ...nextPick, symbol }, p)
          : p
      );
      refreshActiveRowQuote(els.sectorPickList, nextPick, "data-symbol");
      if (state.sectorTf === "intraday" && state.sectorSymbol === symbol) {
        if (!patchZoomableIntraday("sector", intra, nextPick)) {
          renderSectorPickChart();
        } else {
          updateDeskChartQuote(els.sectorPickChart, {
            pct: nextPick.change_pct,
            price: nextPick.price,
            rtPct: nextPick.rt_change_pct,
            sessionLabel: nextPick.session_label,
          });
        }
      }
    }
  }
}

async function refreshActiveIntraday({ force = false } = {}) {
  if (PAGE !== "desk" && PAGE !== "sectors") return;
  const tf = PAGE === "desk" ? state.portfolioTf : state.sectorTf;
  if (tf !== "intraday") return;
  const sym =
    PAGE === "desk"
      ? state.portfolioPreview || state.portfolio?.selected || ""
      : state.sectorSymbol || state.sectors?.selected_symbol || "";
  // Auto-poll skips when busy; manual 刷新 bypasses as a backup.
  if (!sym || (state.intradayPollBusy && !force)) return;
  state.intradayPollBusy = true;
  try {
    const url = `/api/quote/intraday?symbol=${encodeURIComponent(sym)}${
      force ? "&refresh=true" : ""
    }`;
    const res = await fetch(url, { credentials: "same-origin" });
    if (!res.ok) return;
    const snap = await res.json();
    // Drop stale replies if the user already switched symbols.
    const current =
      PAGE === "desk"
        ? state.portfolioPreview || state.portfolio?.selected || ""
        : state.sectorSymbol || "";
    if (String(current).toUpperCase() !== String(sym).toUpperCase()) return;
    applyIntradaySnapshot(sym, snap);
  } catch {
    /* quiet poll */
  } finally {
    state.intradayPollBusy = false;
  }
}

/** Keep a prior 分时 series when a refresh brings day/month but empty intraday. */
function mergePickPreserveIntraday(next, prev) {
  if (!next) return prev || next;
  if (!prev || !pickHasIntraday(prev)) return next;
  // Always prefer a fresh tape when present — denser-but-stale prior sessions
  // (e.g. yesterday 盘后) must not block today's shorter 盘前 line.
  if (pickHasIntraday(next)) return next;
  return {
    ...next,
    series: {
      ...(next.series || {}),
      intraday: prev.series.intraday,
    },
    points:
      (prev.series.intraday.points || []).length >= 2
        ? prev.series.intraday.points.slice(-64)
        : next.points,
  };
}

function openSectorDesk(id, { scroll = true } = {}) {
  const sectorId = (id || "").trim().toLowerCase();
  if (!sectorId) return;
  const same = sectorId === state.sectorId;
  state.sectorId = sectorId;
  if (!same) state.sectorSymbol = "";
  syncSectorQuery();

  // Optimistic: paint cached desk immediately while a refresh runs in background
  const cached = sectorCacheGet(sectorId);
  if (cached && (!same || !state.sectors)) {
    renderSectorDesk(cached);
  } else if (!same && els.sectorPickList) {
    els.sectorPickList.innerHTML = '<p class="empty">加载成分股…</p>';
    if (els.sectorPicksTitle) {
      const label =
        (state.sectors?.sectors || []).find((s) => s.id === sectorId)?.label ||
        sectorId;
      els.sectorPicksTitle.textContent = `${label} · 成分`;
    }
  }

  const load =
    same && state.sectors && pickHasChart(state.sectors.selected_pick)
      ? Promise.resolve(state.sectors)
      : loadSectorDesk();
  Promise.resolve(load).finally(() => {
    if (scroll && els.sectorsDesk) {
      els.sectorsDesk.scrollIntoView({ behavior: "smooth", block: "start" });
    }
  });
}

function prefetchSectorDesk(id) {
  const sectorId = (id || "").trim().toLowerCase();
  if (!sectorId || sectorCacheGet(sectorId)) return;
  const params = new URLSearchParams({ sector: sectorId });
  fetch(`/api/sectors?${params.toString()}`)
    .then((res) => (res.ok ? res.json() : null))
    .then((data) => {
      if (data) sectorCachePut(sectorId, data);
    })
    .catch(() => {});
}

function renderSectorEtfs(sectors) {
  if (!els.sectorEtfGrid) return;
  const rows = sectors || [];
  if (!rows.length) {
    els.sectorEtfGrid.innerHTML = '<p class="empty">暂无板块行情。</p>';
    return;
  }
  if (els.hotSectorsBlurb) {
    const hot = rows.filter((r) => r.is_hot).map((r) => r.label).slice(0, 3);
    const active = rows.find((r) => r.id === state.sectorId);
    const count = active?.pick_count || active?.universe?.length || active?.picks?.length || 0;
    els.hotSectorsBlurb.textContent = active
      ? `${active.label} · ${count} 只成分 · 点卡片进入下方走势台`
      : hot.length
        ? `当前热点 ${hot.join(" · ")} · 点选板块查看全部成分股`
        : "点选板块 → 左侧成分股 → 中间分时 / K 线";
  }
  els.sectorEtfGrid.innerHTML = rows
    .map((row) => {
      const pct = row.change_pct;
      const month = row.month_change_pct;
      const up = !(typeof pct === "number" && pct < 0);
      const active = row.id === state.sectorId;
      const spark = sparklinePath(row.points || [], 54, 18, 1);
      const stroke = up ? TAPE_UP : TAPE_DOWN;
      const preview = row.pick_preview || row.universe || row.picks || [];
      const count = row.pick_count || preview.length || 0;
      const tickers = preview
        .slice(0, 5)
        .map((sym) => `<span class="chip-ticker">${escapeHtml(sym)}</span>`)
        .join("");
      const more =
        count > 5 ? `<span class="chip-ticker">+${count - 5}</span>` : "";
      return `
        <button type="button" class="sector-chip ${active ? "is-active" : ""} ${
          row.is_hot ? "is-hot" : ""
        }" data-sector="${escapeHtml(row.id)}" aria-pressed="${
          active ? "true" : "false"
        }" title="查看 ${escapeHtml(row.label)} 全部成分股走势">
          <span class="chip-name">${escapeHtml(row.label)}${
            row.is_wave
              ? '<span class="hot-tag">涨势</span>'
              : row.is_hot
                ? '<span class="hot-tag">热</span>'
                : ""
          }</span>
          <span class="chip-count">${count || "—"} 只</span>
          <p class="chip-blurb">${escapeHtml(
            row.blurb || `${row.symbol || ""} 板块代理`
          )}</p>
          <span class="chip-tickers">${tickers}${more}</span>
          <span class="chip-meta">
            <span>
              <span class="chg ${pctClass(pct)}">${escapeHtml(pctText(pct))}</span>
              <span>月 ${escapeHtml(pctText(month))}</span>
            </span>
            ${
              spark
                ? `<span class="chip-spark" aria-hidden="true"><svg viewBox="0 0 54 18" preserveAspectRatio="none"><path d="${spark}" fill="none" stroke="${stroke}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"></path></svg></span>`
                : ""
            }
          </span>
        </button>
      `;
    })
    .join("");

  els.sectorEtfGrid.querySelectorAll("[data-sector]").forEach((btn) => {
    btn.addEventListener("click", () => {
      openSectorDesk(btn.getAttribute("data-sector"), { scroll: true });
    });
    btn.addEventListener("pointerenter", () => {
      const id = btn.getAttribute("data-sector");
      if (!id) return;
      clearTimeout(state.sectorPrefetchTimer);
      state.sectorPrefetchTimer = setTimeout(() => prefetchSectorDesk(id), 120);
    });
  });
}

function formatEarningsWhen(row) {
  if (!row) return "日期待定";
  if (typeof row.days_to_earnings === "number") {
    if (row.days_to_earnings < 0) return `已过 ${Math.abs(row.days_to_earnings)} 天`;
    if (row.days_to_earnings === 0) return "今天";
    if (row.days_to_earnings <= 7) return `${row.days_to_earnings} 天后`;
    return row.next_earnings_label || `${row.days_to_earnings} 天后`;
  }
  return row.next_earnings_label || "日期待定";
}

function renderEarningsCalendar(data, { onSelect } = {}) {
  if (!els.earningsList) return;
  const rows = data?.earnings_calendar || [];
  const selected = data?.selected_symbol || data?.selected || "";
  if (els.earningsBlurb) {
    const soon = rows.filter(
      (r) => typeof r.days_to_earnings === "number" && r.days_to_earnings <= 14
    ).length;
    const onDesk = PAGE === "desk";
    els.earningsBlurb.textContent = soon
      ? `${soon} 只 14 日内临近财报`
      : onDesk
        ? "当前持仓财报窗口"
        : "关注观察名单财报窗口";
  }
  if (!rows.length) {
    els.earningsList.innerHTML =
      PAGE === "desk"
        ? '<p class="empty">暂无持仓财报日期 · <a href="/earnings">看全美股日历</a></p>'
        : '<p class="empty">暂无观察名单财报 · <a href="/earnings">看全美股日历</a></p>';
    return;
  }
  els.earningsList.innerHTML = rows
    .slice(0, 5)
    .map((row) => {
      const soon =
        typeof row.days_to_earnings === "number" && row.days_to_earnings <= 14;
      const expect = row.expect_eps ?? row.eps_avg;
      const metaBits = [
        row.name || "",
        expect != null ? `预期 ${formatEps(expect)}` : "",
        row.yoy_pct != null ? `同比 ${formatSignedPct(row.yoy_pct)}` : "",
      ].filter(Boolean);
      return `
        <button type="button" class="earnings-item ${
          row.symbol === selected ? "is-active" : ""
        } ${soon ? "is-soon" : ""}" data-symbol="${escapeHtml(row.symbol)}">
          <span class="sym">${escapeHtml(row.symbol)}</span>
          <span class="when">${escapeHtml(formatEarningsWhen(row))}</span>
          <span class="meta">${escapeHtml(metaBits.join(" · "))}</span>
        </button>
      `;
    })
    .join("");
  const pickFn =
    typeof onSelect === "function"
      ? onSelect
      : PAGE === "desk"
        ? (sym) => selectPortfolioSymbol(sym)
        : (sym) => selectSectorSymbol(sym);
  els.earningsList.querySelectorAll("[data-symbol]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const sym = btn.getAttribute("data-symbol") || "";
      pickFn(sym);
    });
  });
}

function renderPortfolioFocus(data) {
  if (PAGE !== "desk") return;
  const holdings = data?.holdings || [];
  const selected = data?.selected || data?.selected_symbol || "";
  const pick =
    data?.selected_board ||
    holdings.find((h) => h.symbol === selected) ||
    holdings[0] ||
    null;
  renderStockEarnings(data?.selected_earnings || pick?.earnings, pick);
  renderMoveAnalysis(pick);
  renderValueChain(data?.value_chain || pick?.value_chain);
  renderEarningsCalendar({
    earnings_calendar: data?.earnings_calendar || [],
    selected_symbol: selected,
  });
}

function renderMonthPanel(pick) {
  if (!els.monthChart) return;
  if (!pick) {
    els.monthChart.innerHTML = '<p class="empty">选择个股后显示月图</p>';
    return;
  }
  const series = pick.series?.month;
  const points = series?.points || [];
  const pct = series?.change_pct != null ? series.change_pct : pick.month_change_pct;
  const up = !(typeof pct === "number" && pct < 0);
  const svg = points.length
    ? candleChartHtml(points, "month")
    : '<p class="empty">暂无月线</p>';
  if (els.monthPanelBlurb) {
    els.monthPanelBlurb.textContent = pick.is_wave
      ? "一轮涨势进行中"
      : "月线对照涨势 · 含均线";
  }
  els.monthChart.innerHTML = `
    <div class="month-head">
      <strong>${escapeHtml(pick.symbol || "")}</strong>
      <span class="chg ${pctClass(pct)}">${escapeHtml(pctText(pct))}</span>
    </div>
    <div class="chart-canvas">${svg}</div>
  `;
}

function formatEps(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  const n = Number(value);
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(2)}`;
}

function formatSignedPct(value) {
  if (value == null || Number.isNaN(Number(value))) return "—";
  const n = Number(value);
  const sign = n > 0 ? "+" : "";
  return `${sign}${n.toFixed(1)}%`;
}

function renderStockEarnings(earn, pick) {
  if (!els.stockEarnings) return;
  if (!pick) {
    els.stockEarnings.innerHTML =
      '<p class="empty">选择个股后显示财报对照</p>';
    return;
  }
  const data = earn || pick.earnings || {};
  const hasCore =
    data.next_earnings_label ||
    data.prev_earnings_label ||
    data.expect_eps != null ||
    data.eps_avg != null ||
    data.last_eps_actual != null;
  if (!hasCore) {
    // Fall back to sector earnings calendar row for this symbol if present
    const cal = (state.sectors?.earnings_calendar || []).find(
      (r) => (r.symbol || "").toUpperCase() === (pick.symbol || "").toUpperCase()
    );
    if (cal && (cal.next_earnings_label || cal.days_to_earnings != null)) {
      renderStockEarnings(
        {
          next_earnings_label: cal.next_earnings_label,
          days_to_earnings: cal.days_to_earnings,
          expect_eps: cal.expect_eps ?? cal.eps_avg ?? cal.next_eps_estimate,
          eps_avg: cal.eps_avg ?? cal.expect_eps,
          last_eps_actual: cal.last_eps_actual,
          last_eps_estimate: cal.last_eps_estimate,
          beat_pct: cal.beat_pct,
          analyst_count: cal.analyst_count,
        },
        pick
      );
      return;
    }
    els.stockEarnings.innerHTML = `
      <div class="stock-earnings-head">
        <p class="move-kicker">个股财报</p>
        <h3>${escapeHtml(pick.name || pick.symbol || "")} · ${escapeHtml(
          pick.symbol || ""
        )}</h3>
      </div>
      <div class="earn-date-row">
        <div>
          <span class="k">下一发布日</span>
          <strong>待日历同步</strong>
        </div>
        <div>
          <span class="k">上次实际</span>
          <strong>—</strong>
        </div>
      </div>
      <p class="empty compact">完整 EPS 明细稍后补齐 · <a href="/earnings?q=${encodeURIComponent(
        pick.symbol || ""
      )}">打开财报日历</a></p>
    `;
    return;
  }
  const expect = data.expect_eps ?? data.eps_avg ?? data.next_eps_estimate;
  const nextLabel = data.next_earnings_label || "待定";
  const prevLabel = data.prev_earnings_label || "—";
  const when =
    typeof data.days_to_earnings === "number"
      ? formatEarningsWhen(data)
      : "";
  const beat = data.beat_pct;
  const beatCls =
    beat == null ? "" : beat >= 0 ? "up" : "down";
  els.stockEarnings.innerHTML = `
    <div class="stock-earnings-head">
      <div>
        <p class="move-kicker">个股财报</p>
        <h3>${escapeHtml(pick.name || "")} · ${escapeHtml(pick.symbol || "")}</h3>
      </div>
      ${
        when
          ? `<span class="earn-when">${escapeHtml(when)}</span>`
          : ""
      }
    </div>
    <div class="earn-date-row">
      <div>
        <span class="k">下一发布日</span>
        <strong>${escapeHtml(nextLabel)}</strong>
      </div>
      <div>
        <span class="k">上一发布日</span>
        <strong>${escapeHtml(prevLabel)}</strong>
      </div>
    </div>
    <div class="earn-metrics">
      <div>
        <span class="k">市场预期 EPS</span>
        <strong>${escapeHtml(formatEps(expect))}</strong>
        <span class="sub">${
          data.analyst_count != null
            ? `${escapeHtml(String(data.analyst_count))} 家机构`
            : data.next_eps_low != null && data.next_eps_high != null
              ? `区间 ${escapeHtml(formatEps(data.next_eps_low))} ~ ${escapeHtml(
                  formatEps(data.next_eps_high)
                )}`
              : "共识预期"
        }</span>
      </div>
      <div>
        <span class="k">上次实际</span>
        <strong class="${beatCls}">${escapeHtml(
          formatEps(data.last_eps_actual)
        )}</strong>
        <span class="sub">预期 ${escapeHtml(
          formatEps(data.last_eps_estimate)
        )}${
          beat != null
            ? ` · ${beat >= 0 ? "超预期" : "低于预期"} ${escapeHtml(
                formatSignedPct(beat)
              )}`
            : ""
        }</span>
      </div>
      <div>
        <span class="k">同比 YoY</span>
        <strong class="${pctClass(data.yoy_pct)}">${escapeHtml(
          formatSignedPct(data.yoy_pct)
        )}</strong>
        <span class="sub">预期同比 ${escapeHtml(
          formatSignedPct(data.expect_yoy_pct)
        )}</span>
      </div>
      <div>
        <span class="k">环比 QoQ</span>
        <strong class="${pctClass(data.qoq_pct)}">${escapeHtml(
          formatSignedPct(data.qoq_pct)
        )}</strong>
        <span class="sub">上季 ${escapeHtml(
          formatEps(data.prev_eps_actual)
        )}</span>
      </div>
    </div>
  `;
}

function renderMoveAnalysis(pick) {
  if (!els.moveAnalysis) return;
  if (!pick) {
    els.moveAnalysis.innerHTML =
      '<p class="empty">选择个股后显示涨跌解读</p>';
    return;
  }
  const analysis = pick.move_analysis || {};
  const bias = analysis.bias || "neutral";
  const factors = analysis.factors || [];
  const sector = pick.sector_label || "";
  els.moveAnalysis.innerHTML = `
    <div class="move-analysis-head">
      <div>
        <p class="move-kicker">涨跌解读</p>
        <h3>${escapeHtml(pick.name || pick.symbol || "")} · ${escapeHtml(
          pick.symbol || ""
        )}</h3>
      </div>
      <span class="move-bias bias-${escapeHtml(bias)}">${escapeHtml(
        analysis.bias_zh || "中性"
      )}</span>
    </div>
    <p class="move-sector">所属板块 · ${escapeHtml(sector || "未标注")}${
      pick.vs_sector_pct != null
        ? ` · 相对板块 ${escapeHtml(pctText(pick.vs_sector_pct))}`
        : ""
    }</p>
    <p class="move-summary">${escapeHtml(
      analysis.summary || "暂无解读"
    )}</p>
    ${
      factors.length
        ? `<ul class="move-factors">${factors
            .map((f) => `<li>${escapeHtml(f)}</li>`)
            .join("")}</ul>`
        : ""
    }
  `;
}

function resolveSectorChartSeries(pick, preferredTf) {
  const seriesMap = pick?.series || {};
  const want = preferredTf || "intraday";

  // 分时 must always be a session line — never fall back to day/month candles
  // (that painted a 柱状图 while the 分时 tab stayed selected).
  if (want === "intraday") {
    const preferred = seriesMap.intraday;
    const raw = preferred?.points || [];
    const points = toLineSparkPoints(raw);
    if (points.length >= 2) {
      return {
        tf: "intraday",
        series: {
          ...(preferred || {}),
          chart: "line",
          points: preferred?.points || points,
          session_labels: SESSION_LABEL_ORDER,
          previous_close:
            preferred?.previous_close ?? pick?.previous_close ?? null,
        },
        points,
        kind: "line",
      };
    }
    return {
      tf: "intraday",
      series: preferred || null,
      points: [],
      kind: "line",
    };
  }

  const preferred = seriesMap[want];
  const preferredRaw = preferred?.points || [];
  const preferredPoints = sanitizeCandleBars(preferredRaw);
  if (preferredPoints.length >= 2) {
    return {
      tf: want,
      series: preferred || { chart: "candle", points: preferredRaw },
      points: preferredPoints,
      kind: "candle",
    };
  }
  return { tf: want, series: preferred || null, points: [], kind: "candle" };
}

function renderSectorPickChart() {
  if (!els.sectorPickChart) return;
  const data = state.sectors || {};
  const pick = data.selected_pick;
  let tf = state.sectorTf || "intraday";
  if (els.sectorTfFilters) {
    els.sectorTfFilters.querySelectorAll("[data-stf]").forEach((btn) => {
      const on = btn.getAttribute("data-stf") === tf;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
  }
  if (!pick) {
    els.sectorPickChart.innerHTML =
      '<p class="chart-placeholder">点左侧个股，显示分时 / K 线</p>';
    renderMonthPanel(null);
    renderStockEarnings(null, null);
    renderMoveAnalysis(null);
    renderSymbolNewsFeed(data);
    return;
  }
  const resolved = resolveSectorChartSeries(pick, tf);
  const series = resolved.series;
  const points = resolved.points;
  const kind = resolved.kind;
  if (points.length < 2) {
    const tfLabel =
      { intraday: "分时", day: "日图", month: "月图", quarter: "季图" }[tf] ||
      "走势";
    els.sectorPickChart.innerHTML = `
      <div class="chart-head">
        <h3>${escapeHtml(pick.name || pick.label || "")} · ${escapeHtml(
          pick.symbol || ""
        )}</h3>
      </div>
      ${deskStatsBlockHtml(pick, { open: null, high: null, low: null })}
      <p class="chart-placeholder">暂无${escapeHtml(
        tfLabel
      )}数据 · 点右上角刷新重试</p>
    `;
    renderMonthPanel(pick);
    renderStockEarnings(data.selected_earnings || pick.earnings, pick);
    renderMoveAnalysis(pick);
    return;
  }
  const zoomWin = defaultChartZoom(points.length, tf, kind);
  const viewPoints = points.slice(zoomWin.start, zoomWin.start + zoomWin.count);
  const pct =
    series?.change_pct != null && kind === "line"
      ? series.change_pct
      : viewPoints.length >= 2
        ? kind === "candle"
          ? ((Number(viewPoints[viewPoints.length - 1].c) -
              Number(viewPoints[0].o ?? viewPoints[0].c)) /
              Math.abs(Number(viewPoints[0].o ?? viewPoints[0].c) || 1)) *
            100
          : ((Number(
              viewPoints[viewPoints.length - 1].v ??
                viewPoints[viewPoints.length - 1].c
            ) -
              Number(viewPoints[0].v ?? viewPoints[0].c)) /
              Math.abs(Number(viewPoints[0].v ?? viewPoints[0].c) || 1)) *
            100
        : series?.change_pct != null
          ? series.change_pct
          : pick.change_pct;
  const up = !(typeof pct === "number" && pct < 0);
  const stats = seriesStats(viewPoints.length ? viewPoints : points, kind);
  const earn = data.selected_earnings || pick.earnings || {};
  const earnNote = earn.next_earnings_label
    ? ` · 财报 ${earn.next_earnings_label}${
        typeof earn.days_to_earnings === "number"
          ? `（${formatEarningsWhen(earn)}）`
          : ""
      }`
    : "";
  const maNote = MA_CHART_TFS.has(tf) ? " · 含均线" : "";
  const sessionNote =
    tf === "intraday" ? " · Yahoo 1D 分时（美东时间）" : "";
  els.sectorPickChart.innerHTML = `
    <div class="chart-head">
      <h3>${escapeHtml(pick.name || pick.label || "")} · ${escapeHtml(
        pick.symbol || ""
      )}${pick.is_wave ? '<span class="hot-tag">涨势</span>' : ""}</h3>
    </div>
    ${deskStatsBlockHtml(pick, stats)}
    <div class="chart-canvas" data-zoom-host="sector"></div>
    <div class="chart-foot">红涨绿跌${maNote}${sessionNote} · 所属 ${escapeHtml(
      pick.sector_label || "板块"
    )}${escapeHtml(earnNote)}</div>
  `;
  bindZoomableChart(els.sectorPickChart.querySelector("[data-zoom-host]"), {
    key: "sector",
    scope: `${pick.symbol || ""}:${tf}`,
    points,
    tf,
    kind,
    up,
    sessions: series?.sessions || null,
    previousClose: series?.previous_close ?? null,
    cycleStart: series?.cycle_start ?? null,
  });
  renderMonthPanel(pick);
  renderStockEarnings(data.selected_earnings || pick.earnings, pick);
  renderMoveAnalysis(pick);
}

function renderValueChain(vc) {
  if (!els.valueChainBody) return;
  const data = vc || {};
  if (!data.symbol) {
    els.valueChainBody.innerHTML =
      '<p class="empty">选择个股后显示业务背景与产业链位置</p>';
    return;
  }
  if (els.valueChainBlurb) {
    els.valueChainBlurb.textContent = `${data.name || data.symbol} · 主营 / 产业 / 上下游`;
  }
  const chips = (items) =>
    (items || []).length
      ? `<div class="vc-chips">${items
          .map((x) => `<span class="vc-chip">${escapeHtml(x)}</span>`)
          .join("")}</div>`
      : "<p class='empty'>暂无</p>";
  els.valueChainBody.innerHTML = `
    <div class="vc-block">
      <p class="vc-kicker">${escapeHtml(data.symbol)} · ${escapeHtml(
        data.name || ""
      )}</p>
      <p>${escapeHtml(data.business || "")}</p>
    </div>
    <div class="vc-block">
      <h3>位置</h3>
      <p>${escapeHtml(
        [data.industry, data.chain_position].filter(Boolean).join(" · ")
      )}</p>
    </div>
    <div class="vc-block">
      <h3>上游</h3>
      ${chips(data.upstream)}
    </div>
    <div class="vc-block">
      <h3>下游</h3>
      ${chips(data.downstream)}
    </div>
    <div class="vc-block">
      <h3>风险</h3>
      ${chips(data.bear_risks)}
    </div>
  `;
}

function renderSectorPicks(data) {
  const picks = data?.picks || [];
  const selected = data?.selected_symbol || state.sectorSymbol || "";
  const selectedPick = data?.selected_pick || null;
  const sector = data?.active_sector || {};
  const tf = state.sectorTf || "intraday";
  const waveN = (data?.wave_leaders || picks.filter((p) => p.is_wave)).length;
  if (els.sectorPicksTitle) {
    els.sectorPicksTitle.textContent = sector.label
      ? `${sector.label} · 成分`
      : "板块成分";
  }
  if (els.sectorPicksBlurb) {
    els.sectorPicksBlurb.textContent = `${picks.length} 只成分 · ${waveN} 只一轮涨势 · 点选看走势 · +/− 管持仓`;
  }
  if (els.sectorPickList) {
    if (!picks.length) {
      els.sectorPickList.innerHTML = '<p class="empty">暂无该板块成分股。</p>';
    } else {
      els.sectorPickList.innerHTML = picks
        .map((pick) => {
          // List tape is always day % + 24h spark — independent of desk TF tabs
          const pct = pick.change_pct;
          const on = pick.symbol === selected;
          // Selected row must share the same intraday series as the middle chart
          const sparkSrc =
            on && selectedPick?.series?.intraday?.points?.length >= 2
              ? selectedPick
              : pick;
          const held = isInHoldings(pick.symbol);
          return `
            <div class="holding-row sector-pick-row ${
              on ? "is-active" : ""
            } ${held ? "in-holding" : ""} ${pctClass(pct)}" data-symbol="${escapeHtml(
              pick.symbol
            )}" role="option" aria-selected="${on ? "true" : "false"}">
              <button type="button" class="sector-pick-main" data-symbol="${escapeHtml(
                pick.symbol
              )}">
                <span class="meta">
                  <span class="nm">${escapeHtml(pick.name || pick.symbol)}${
                    pick.is_wave
                      ? '<span class="hot-tag">涨势</span>'
                      : pick.is_strong
                        ? '<span class="hot-tag">强</span>'
                        : ""
                  }${
                    held ? '<span class="hold-tag">持仓</span>' : ""
                  }</span>
                  <span class="sym">${escapeHtml(pick.symbol)} · ${escapeHtml(
                    pick.sector_label || "板块"
                  )} · 月 ${escapeHtml(pctText(pick.month_change_pct))}</span>
                </span>
                <span class="spark-wrap">${holdingSparkSvg(sparkSrc, "intraday")}</span>
                ${listQuoteHtml(pick)}
              </button>
              <button
                type="button"
                class="sector-hold-btn ${held ? "is-held" : ""}"
                data-hold-symbol="${escapeHtml(pick.symbol)}"
                data-hold-name="${escapeHtml(pick.name || "")}"
                data-hold-action="${held ? "remove" : "add"}"
                title="${held ? `从持仓移除 ${pick.symbol}` : `加入持仓 ${pick.symbol}`}"
                aria-label="${held ? `从持仓移除 ${pick.symbol}` : `加入持仓 ${pick.symbol}`}"
              >${held ? "−" : "+"}</button>
            </div>
          `;
        })
        .join("");
      els.sectorPickList.querySelectorAll(".sector-pick-main[data-symbol]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const sym = btn.getAttribute("data-symbol") || "";
          selectSectorSymbol(sym);
        });
      });
      els.sectorPickList.querySelectorAll(".sector-hold-btn").forEach((btn) => {
        btn.addEventListener("click", (event) => {
          event.preventDefault();
          event.stopPropagation();
          const sym = btn.getAttribute("data-hold-symbol") || "";
          const name = btn.getAttribute("data-hold-name") || "";
          const action = btn.getAttribute("data-hold-action") || "add";
          if (action === "remove") {
            if (!confirm(`确定从持仓移除 ${sym}？`)) return;
          }
          toggleSectorHolding(sym, name);
        });
      });
    }
  }

  renderSectorNewsFeed(data);
  renderSymbolNewsFeed(data);

  renderSectorPickChart();
  renderEarningsCalendar(data);
  renderValueChain(data?.value_chain || data?.selected_pick?.value_chain);
  scheduleSectorsDeskHeightSync();
}

function syncSectorsDeskHeights() {
  const desk = els.sectorsDesk;
  if (!desk || PAGE !== "sectors") return;
  const center = desk.querySelector(".sectors-chart-sticky");
  const left = desk.querySelector(".sectors-list-pane");
  const right = desk.querySelector(".sectors-intel-pane");
  if (!center) return;

  const clear = () => {
    desk.style.removeProperty("--sectors-center-h");
    if (left) {
      left.style.removeProperty("height");
      left.style.removeProperty("max-height");
    }
    if (right) {
      right.style.removeProperty("height");
      right.style.removeProperty("max-height");
    }
  };

  // Below the 3-col breakpoint, panes stack — clear the lock.
  if (window.matchMedia("(max-width: 1180px)").matches) {
    clear();
    return;
  }

  // Measure center without L/R height locks affecting layout
  const prevLeftH = left?.style.height || "";
  const prevRightH = right?.style.height || "";
  if (left) {
    left.style.height = "auto";
    left.style.maxHeight = "none";
  }
  if (right) {
    right.style.height = "auto";
    right.style.maxHeight = "none";
  }
  desk.style.removeProperty("--sectors-center-h");

  const h = Math.ceil(center.getBoundingClientRect().height);
  if (h < 120) {
    if (left && prevLeftH) left.style.height = prevLeftH;
    if (right && prevRightH) right.style.height = prevRightH;
    return;
  }

  const px = `${h}px`;
  desk.style.setProperty("--sectors-center-h", px);
  if (left) {
    left.style.height = px;
    left.style.maxHeight = px;
  }
  if (right) {
    right.style.height = px;
    right.style.maxHeight = px;
  }
}

function scheduleSectorsDeskHeightSync() {
  if (PAGE !== "sectors") return;
  requestAnimationFrame(() => {
    syncSectorsDeskHeights();
    requestAnimationFrame(syncSectorsDeskHeights);
  });
}

function selectSectorSymbol(sym) {
  const symbol = (sym || "").trim().toUpperCase();
  if (!symbol) return;
  const data = state.sectors;
  const pick = (data?.picks || []).find((p) => p.symbol === symbol);
  if (!data || !pick) {
    state.sectorSymbol = symbol;
    syncSectorQuery();
    loadSectorDesk();
    return;
  }
  const already =
    symbol === state.sectorSymbol && pickHasChart(data.selected_pick);
  // Always paint locally first — never wait on network / rebuild the whole list.
  state.sectorSymbol = symbol;
  data.selected_symbol = symbol;
  data.selected_pick = pick;
  data.selected_earnings = pick.earnings || null;
  data.value_chain = pick.value_chain || data.value_chain;
  data.symbol_news = pick.symbol_news || [];
  syncSectorQuery();
  paintSectorSelection();
  refreshActiveRowQuote(els.sectorPickList, pick, "data-symbol");
  setStatus(`已切换 ${pick.name || symbol} · ${pick.sector_label || ""}`);
  persistPageDataCache();
  if (already || pickHasChart(pick)) {
    if (state.sectorTf === "intraday") refreshActiveIntraday({ force: false });
    return;
  }
  // Has 分时 but missing 日/月/季 — still upgrade in background.
  if (state.sectorTf === "intraday") refreshActiveIntraday({ force: false });
  loadSectorDesk();
}

function renderSectorDesk(data) {
  state.sectors = data || null;
  if (data?.active_sector_id) state.sectorId = data.active_sector_id;
  if (data?.selected_symbol) state.sectorSymbol = data.selected_symbol;
  renderAiDesk(data?.hot_desk || data?.ai_desk);
  renderSectorEtfs(data?.sectors || []);
  renderSectorPicks(data);
}

async function loadSectorDesk({ force = false } = {}) {
  if (PAGE !== "sectors") return null;
  const params = new URLSearchParams();
  if (state.sectorId) params.set("sector", state.sectorId);
  if (state.sectorSymbol) params.set("symbol", state.sectorSymbol);
  if (force) params.set("refresh", "true");
  setStatus(force ? "强制刷新板块…" : "同步板块行情与情报…");
  if (els.sectorsRefresh) els.sectorsRefresh.disabled = true;
  // Map is independent — never let it delay the constituent list / chart.
  const mapPromise = loadSectorMap({ force }).catch(() => null);
  try {
    const res = await fetch(`/api/sectors?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data?.active_sector_id) sectorCachePut(data.active_sector_id, data);
    // Keep previously upgraded picks / 分时 when the new payload is still lite
    // or arrives with day/month candles but an empty intraday series.
    if (state.sectors?.picks?.length && data?.picks?.length) {
      const prevBySym = Object.fromEntries(
        state.sectors.picks.map((p) => [p.symbol, p])
      );
      const prevSelected = state.sectors.selected_pick;
      data.picks = data.picks.map((p) => {
        const prev = prevBySym[p.symbol];
        if (!prev) return p;
        if (!pickHasChart(p) && pickHasChart(prev)) {
          return mergeListQuoteFields(
            mergePickPreserveIntraday(
              {
                ...p,
                series: { ...(p.series || {}), ...prev.series },
                points: prev.points?.length ? prev.points : p.points,
                lite: false,
              },
              prev
            ),
            prev
          );
        }
        return mergeListQuoteFields(mergePickPreserveIntraday(p, prev), prev);
      });
      if (data.selected_symbol) {
        const fromList = data.picks.find(
          (p) => p.symbol === data.selected_symbol
        );
        const prevSel =
          prevSelected?.symbol === data.selected_symbol
            ? prevSelected
            : prevBySym[data.selected_symbol];
        const merged = mergeListQuoteFields(
          mergePickPreserveIntraday(fromList || data.selected_pick, prevSel),
          prevSel
        );
        if (merged) data.selected_pick = merged;
      }
    }
    renderSectorDesk(data);
    syncSectorQuery();
    persistPageDataCache();
    const hot = (data.hot_sectors || []).map((s) => s.label).slice(0, 2).join("、");
    const n = (data.picks || []).length;
    setStatus(
      `板块已更新${data.cached ? "（缓存）" : ""}${
        data.active_sector?.label ? ` · ${data.active_sector.label}` : ""
      }${n ? ` · ${n} 只成分` : ""}${hot ? ` · 热点 ${hot}` : ""}`
    );
    // Don't await map — paint desk immediately; map fills when ready.
    void mapPromise;
    return data;
  } catch (err) {
    setStatus(`板块加载失败：${err.message || err}`);
    void mapPromise;
    return null;
  } finally {
    if (els.sectorsRefresh) els.sectorsRefresh.disabled = false;
  }
}

function usStripSparkHtml(row) {
  const pts = (row?.points || [])
    .map((p) => Number(p?.v ?? p?.c))
    .filter((n) => Number.isFinite(n));
  if (pts.length < 2) return "";
  const w = 56;
  const h = 28;
  const min = Math.min(...pts);
  const max = Math.max(...pts);
  const span = max - min || 1;
  const step = (w - 2) / (pts.length - 1);
  const d = pts
    .map((v, i) => {
      const x = 1 + i * step;
      const y = 1 + (1 - (v - min) / span) * (h - 2);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");
  const up = pts[pts.length - 1] >= pts[0];
  const stroke = up ? TAPE_UP : TAPE_DOWN;
  return `<svg class="us-strip-spark" viewBox="0 0 ${w} ${h}" preserveAspectRatio="none" aria-hidden="true"><path d="${d}" fill="none" stroke="${stroke}" stroke-width="1.2" vector-effect="non-scaling-stroke"></path></svg>`;
}

function renderUsMarketsStrip(strip) {
  if (!els.usMarketsStrip) return;
  const rows = strip || [];
  if (!rows.length) {
    els.usMarketsStrip.innerHTML = '<p class="empty">暂无美国市场行情</p>';
    return;
  }
  els.usMarketsStrip.innerHTML = rows
    .map((row) => {
      const pct = row.change_pct;
      const cls = pctClass(pct);
      return `
        <article class="us-strip-card ${cls}" data-us-sym="${escapeHtml(
          row.symbol || ""
        )}">
          <div class="us-strip-meta">
            <span class="us-strip-name">${escapeHtml(row.label || row.short || "")}</span>
            <span class="us-strip-price ${cls}">${escapeHtml(
              row.price == null ? "—" : formatNumber(row.price, "")
            )}</span>
            <span class="us-strip-chg ${cls}">${escapeHtml(pctText(pct))}</span>
          </div>
          ${usStripSparkHtml(row)}
        </article>
      `;
    })
    .join("");
}

function renderUsFuturesCharts() {
  if (!els.usFuturesGrid) return;
  const data = state.usMarkets || {};
  const futures = data.futures || [];
  const tf = state.usFuturesTf || "intraday";
  if (els.usFuturesTfFilters) {
    els.usFuturesTfFilters.querySelectorAll("[data-uftf]").forEach((btn) => {
      const on = btn.getAttribute("data-uftf") === tf;
      btn.classList.toggle("is-active", on);
      btn.setAttribute("aria-selected", on ? "true" : "false");
    });
  }
  if (!futures.length) {
    els.usFuturesGrid.innerHTML = '<p class="empty">暂无指数期货走势</p>';
    return;
  }
  els.usFuturesGrid.innerHTML = futures
    .map((fut) => {
      const id = String(fut.id || fut.symbol || "").toLowerCase();
      const resolved = resolveSectorChartSeries(fut, tf);
      const series = resolved.series;
      const points = resolved.points;
      const kind = resolved.kind;
      const pct =
        series?.change_pct != null
          ? series.change_pct
          : fut.change_pct;
      const up = !(typeof pct === "number" && pct < 0);
      return `
        <article class="us-futures-card" data-fut-id="${escapeHtml(id)}">
          <div class="us-futures-card-head">
            <div>
              <h3>${escapeHtml(fut.short || fut.label || fut.symbol || "")}</h3>
              <p class="us-futures-sub">${escapeHtml(fut.label || "")} · ${escapeHtml(
                fut.symbol || ""
              )}</p>
            </div>
            <div class="us-futures-quote">
              <span class="us-futures-price ${up ? "up" : "down"}">${escapeHtml(
                fut.price == null ? "—" : formatNumber(fut.price, "")
              )}</span>
              <span class="us-futures-chg ${up ? "up" : "down"}">${escapeHtml(
                pctText(pct)
              )}</span>
            </div>
          </div>
          <div class="chart-canvas us-futures-canvas" data-zoom-host="us-fut-${escapeHtml(
            id
          )}" data-fut-key="${escapeHtml(id)}"></div>
          ${
            points.length < 2
              ? `<p class="chart-placeholder">暂无${escapeHtml(
                  { intraday: "分时", day: "日图", month: "月图", quarter: "季图" }[
                    tf
                  ] || "走势"
                )}数据</p>`
              : ""
          }
        </article>
      `;
    })
    .join("");

  futures.forEach((fut) => {
    const id = String(fut.id || fut.symbol || "").toLowerCase();
    const host = els.usFuturesGrid.querySelector(`[data-fut-key="${id}"]`);
    if (!host) return;
    const resolved = resolveSectorChartSeries(fut, tf);
    const points = resolved.points;
    if (points.length < 2) return;
    const series = resolved.series;
    const kind = resolved.kind;
    const pct =
      series?.change_pct != null ? series.change_pct : fut.change_pct;
    const up = !(typeof pct === "number" && pct < 0);
    bindZoomableChart(host, {
      key: `us-fut-${id}`,
      scope: `${fut.symbol || id}:${tf}`,
      points,
      tf,
      kind,
      up,
      sessions: series?.sessions || null,
      previousClose: series?.previous_close ?? fut.previous_close ?? null,
      cycleStart: series?.cycle_start ?? null,
      cycleEnd: series?.cycle_end ?? null,
      axis: series?.axis || (tf === "intraday" ? "futures_bj" : null),
    });
  });
}

function renderUsMarketsDesk(data) {
  state.usMarkets = data || null;
  if (els.usMarketsBlurb) {
    const n = (data?.futures || []).length;
    const src = data?.source || "Yahoo";
    els.usMarketsBlurb.textContent = `${src}${
      data?.cached ? " · 缓存" : ""
    }${n ? ` · ${n} 条期货主连` : ""}`;
  }
  renderUsMarketsStrip(data?.strip || []);
  renderUsFuturesCharts();
}

async function loadUsMarketsDesk({ force = false } = {}) {
  if (PAGE !== "sectors") return null;
  if (state.usMarketsPollBusy && !force) return null;
  state.usMarketsPollBusy = true;
  try {
    const res = await fetch(
      `/api/us-markets${force ? "?refresh=true" : ""}`
    );
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderUsMarketsDesk(data);
    return data;
  } catch (err) {
    if (els.usMarketsBlurb) {
      els.usMarketsBlurb.textContent = `美国市场加载失败：${err.message || err}`;
    }
    if (els.usMarketsStrip) {
      els.usMarketsStrip.innerHTML = `<p class="empty">加载失败：${escapeHtml(
        String(err.message || err)
      )}</p>`;
    }
    return null;
  } finally {
    state.usMarketsPollBusy = false;
  }
}

function bindUsMarketsDesk() {
  if (PAGE !== "sectors") return;
  els.usFuturesTfFilters?.querySelectorAll("[data-uftf]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tf = btn.getAttribute("data-uftf");
      if (!tf || tf === state.usFuturesTf) return;
      state.usFuturesTf = tf;
      renderUsFuturesCharts();
    });
  });
}

function bindSectorDesk() {
  if (PAGE !== "sectors") return;
  bindUsMarketsDesk();
  els.sectorsRefresh?.addEventListener("click", () => {
    loadSectorDesk({ force: true });
    loadUsMarketsDesk({ force: true });
  });
  els.sectorTfFilters?.querySelectorAll("[data-stf]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tf = btn.getAttribute("data-stf");
      if (!tf || tf === state.sectorTf) return;
      state.sectorTf = tf;
      // Same as holdings: TF switch paints the middle chart only.
      renderSectorPickChart();
      persistPageDataCache();
      if (tf === "intraday") {
        refreshActiveIntraday({ force: false });
      } else if (!pickHasTfSeries(state.sectors?.selected_pick, tf)) {
        ensureMultiTfChartUpgrade();
      }
    });
  });
  const desk = els.sectorsDesk;
  const center = desk?.querySelector(".sectors-chart-sticky");
  if (center && typeof ResizeObserver !== "undefined") {
    const ro = new ResizeObserver(() => syncSectorsDeskHeights());
    ro.observe(center);
  }
  window.addEventListener("resize", () => scheduleSectorsDeskHeightSync());
  scheduleSectorsDeskHeightSync();
}

/** Unify earnings date labels to YYYY-MM-DD (handles M/D/YYYY from Nasdaq). */
function formatEarningsDateIso(raw) {
  const text = String(raw || "").trim();
  if (!text || text === "—" || text === "-") return "—";
  if (/^\d{4}-\d{2}-\d{2}$/.test(text)) return text;
  const mdy = text.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  if (mdy) {
    const mm = String(Number(mdy[1])).padStart(2, "0");
    const dd = String(Number(mdy[2])).padStart(2, "0");
    return `${mdy[3]}-${mm}-${dd}`;
  }
  return text;
}

function formatCapShort(text) {
  if (!text || text === "—" || text === "N/A") return "—";
  const raw = String(text).replace(/[$,]/g, "");
  const n = Number(raw);
  if (!Number.isFinite(n)) return String(text);
  if (n >= 1e12) return `${(n / 1e12).toFixed(2)}T`;
  if (n >= 1e9) return `${(n / 1e9).toFixed(1)}B`;
  if (n >= 1e6) return `${(n / 1e6).toFixed(0)}M`;
  return String(text);
}

function renderEarningsDesk(data) {
  state.earnings = data || null;
  if (data?.selected_date) state.earningsDate = data.selected_date;
  if (data?.session) state.earningsSession = data.session;

  const dates = data?.dates || [];
  const items = data?.items || [];
  const focusWatch = data?.focus_watch || [];
  const selectedFocus = data?.selected_focus || [];
  const selected = data?.selected_date || state.earningsDate || "";

  if (els.earningsPageBlurb) {
    const total = dates.reduce((s, d) => s + (d.count || 0), 0);
    const win =
      data?.window_start && data?.window_end
        ? `${data.window_start.slice(5)} → ${data.window_end.slice(5)}`
        : `近 ${dates.length} 日`;
    els.earningsPageBlurb.textContent = `一个月窗口 ${win} · 共 ${total} 家申报 · 重点关注 ${
      data?.focus_count ?? focusWatch.length
    } 只 · 当日 ${data?.count ?? items.length} 家`;
  }

  if (els.earningsDateTabs) {
    els.earningsDateTabs.innerHTML = dates
      .map((d) => {
        const on = d.date === selected;
        const focusN = d.focus_count || 0;
        return `
          <button type="button" class="earnings-date-tab ${on ? "is-active" : ""} ${
            d.is_today ? "is-today" : ""
          } ${d.is_weekend ? "is-weekend" : ""} ${
            focusN ? "has-focus" : ""
          }" data-date="${escapeHtml(d.date)}" role="tab" aria-selected="${
            on ? "true" : "false"
          }">
            <span class="dow">周${escapeHtml(d.weekday)}</span>
            <span class="dom">${escapeHtml(d.label)}</span>
            <span class="cnt">${d.count || 0}${
              focusN ? `<em>·${focusN}重点</em>` : ""
            }</span>
          </button>
        `;
      })
      .join("");
    els.earningsDateTabs.querySelectorAll("[data-date]").forEach((btn) => {
      btn.addEventListener("click", () => {
        const date = btn.getAttribute("data-date") || "";
        if (!date || date === state.earningsDate) return;
        state.earningsDate = date;
        loadEarningsDesk();
      });
    });
  }

  els.earningsSessionFilters?.querySelectorAll("[data-esession]").forEach((btn) => {
    const key = btn.getAttribute("data-esession") || "all";
    const on = key === (state.earningsSession || "all");
    btn.classList.toggle("is-active", on);
    btn.setAttribute("aria-selected", on ? "true" : "false");
  });

  if (els.earningsQ && document.activeElement !== els.earningsQ) {
    els.earningsQ.value = state.earningsQ || data?.q || "";
  }

  const focusTarget = els.earningsFocus || els.earningsMega;
  if (focusTarget) {
    if (!focusWatch.length) {
      focusTarget.innerHTML =
        '<p class="empty compact">本月窗口暂无重点关注标的（或已被筛选过滤）</p>';
    } else {
      const dayFocusNote = selectedFocus.length
        ? `当日重点 ${selectedFocus.length} 只`
        : "点日期可筛选当日列表";
      focusTarget.innerHTML = `
        <div class="earnings-focus-head">
          <div>
            <h2>本月重点关注</h2>
            <p>大市值 / 核心标的 / 预期同比异动 · ${escapeHtml(dayFocusNote)}</p>
          </div>
          <span class="earnings-focus-count">${focusWatch.length} 只</span>
        </div>
        <div class="earnings-focus-grid">
          ${focusWatch
            .map((row) => {
              const onDay = row.date === selected;
              const reasons = (row.focus_reasons || []).slice(0, 3).join(" · ");
              return `
              <button type="button" class="earnings-focus-card ${
                onDay ? "is-today-report" : ""
              }" data-focus-date="${escapeHtml(row.date || "")}" data-symbol="${escapeHtml(
                row.symbol || ""
              )}">
                <span class="top">
                  <span class="sym">${escapeHtml(row.symbol)}</span>
                  <span class="when">
                    <span class="when-date">${escapeHtml(row.date || "")}</span>
                    <span class="when-session">${escapeHtml(row.time_zh || "")}</span>
                  </span>
                </span>
                <span class="name">${escapeHtml(row.name || "")}</span>
                <span class="cap">预期 ${escapeHtml(
                  row.eps_forecast_text || "—"
                )} · 同比 ${escapeHtml(formatSignedPct(row.yoy_pct))}</span>
                <span class="why">${escapeHtml(reasons || "重点跟踪")}</span>
              </button>
            `;
            })
            .join("")}
        </div>
      `;
      focusTarget.querySelectorAll("[data-focus-date]").forEach((btn) => {
        btn.addEventListener("click", () => {
          const date = btn.getAttribute("data-focus-date") || "";
          if (!date) return;
          if (date !== state.earningsDate) {
            state.earningsDate = date;
            loadEarningsDesk();
          }
        });
      });
    }
  }

  if (els.earningsTableTitle) {
    const tab = dates.find((d) => d.date === selected);
    const focusN = items.filter((r) => r.is_focus).length;
    els.earningsTableTitle.textContent = tab
      ? `${tab.label} 周${tab.weekday} · 全部申报`
      : "当日全部";
    if (els.earningsTableBlurb) {
      els.earningsTableBlurb.textContent = focusN
        ? `重点 ${focusN} 只置顶 · 市场预期 / 同比 / 发布日`
        : "市场预期 · 上年对照 · 同比 · 发布日";
    }
  }
  if (els.earningsCount) {
    const focusN = items.filter((r) => r.is_focus).length;
    els.earningsCount.textContent = focusN
      ? `${items.length} 家 · ${focusN} 重点`
      : `${items.length} 家`;
  }

  if (els.earningsTable) {
    if (!items.length) {
      els.earningsTable.innerHTML =
        '<p class="empty">该日暂无匹配申报，可切换日期或清空筛选。</p>';
    } else {
      els.earningsTable.innerHTML = `
        <div class="earnings-row head" aria-hidden="true">
          <span>代码</span><span>公司</span><span>时段</span><span>下一发布日</span><span>上年发布日</span><span>市场预期</span><span>上年EPS</span><span>同比</span><span>市值</span>
        </div>
        ${items
          .map((row) => {
            const focus = Boolean(row.is_focus);
            const nextDate = formatEarningsDateIso(
              row.next_earnings_label || row.date || "—"
            );
            const prevDate = formatEarningsDateIso(
              row.prev_earnings_label || row.last_year_report_date || "—"
            );
            return `
          <a class="earnings-row ${focus ? "is-focus" : ""}" href="${escapeHtml(
            row.url || `https://finance.yahoo.com/quote/${row.symbol}/`
          )}" target="_blank" rel="noopener noreferrer">
            <span class="sym">${escapeHtml(row.symbol)}${
              focus ? '<em class="focus-tag">重点</em>' : ""
            }</span>
            <span class="name">${escapeHtml(row.name || "")}</span>
            <span class="session session-${escapeHtml(
              (row.time || "").replace("time-", "")
            )}">${escapeHtml(row.time_zh || "—")}</span>
            <span class="date">${escapeHtml(nextDate)}</span>
            <span class="date muted">${escapeHtml(prevDate)}</span>
            <span class="eps">${escapeHtml(row.eps_forecast_text || "—")}</span>
            <span class="eps muted">${escapeHtml(row.last_year_eps_text || "—")}</span>
            <span class="yoy ${pctClass(row.yoy_pct)}">${escapeHtml(
              formatSignedPct(row.yoy_pct)
            )}</span>
            <span class="cap">${escapeHtml(formatCapShort(row.market_cap_text))}</span>
          </a>
        `;
          })
          .join("")}
      `;
    }
  }
}

async function loadEarningsDesk({ force = false } = {}) {
  if (PAGE !== "earnings") return null;
  const params = new URLSearchParams();
  params.set("days", "31");
  if (state.earningsDate) params.set("date", state.earningsDate);
  if (state.earningsSession && state.earningsSession !== "all") {
    params.set("session", state.earningsSession);
  }
  if (state.earningsQ) params.set("q", state.earningsQ);
  if (force) params.set("refresh", "true");
  setStatus(force ? "强制刷新近一个月财报…" : "同步近一个月财报日历…");
  if (els.earningsRefresh) els.earningsRefresh.disabled = true;
  try {
    const res = await fetch(`/api/earnings?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderEarningsDesk(data);
    const errN = (data.errors || []).length;
    setStatus(
      `财报已更新${data.cached ? "（缓存）" : ""} · ${data.window_start || ""}→${
        data.window_end || ""
      } · 当日 ${data.count || 0} · 重点 ${data.focus_count || 0}${
        errN ? ` · ${errN} 条拉取警告` : ""
      }`
    );
    return data;
  } catch (err) {
    setStatus(`财报日历加载失败：${err.message || err}`);
    return null;
  } finally {
    if (els.earningsRefresh) els.earningsRefresh.disabled = false;
  }
}

function bindEarningsDesk() {
  if (PAGE !== "earnings") return;
  els.earningsRefresh?.addEventListener("click", () =>
    loadEarningsDesk({ force: true })
  );
  els.earningsSessionFilters?.querySelectorAll("[data-esession]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const key = btn.getAttribute("data-esession") || "all";
      if (key === state.earningsSession) return;
      state.earningsSession = key;
      loadEarningsDesk();
    });
  });
  let qTimer = 0;
  els.earningsQ?.addEventListener("input", () => {
    state.earningsQ = els.earningsQ.value.trim();
    window.clearTimeout(qTimer);
    qTimer = window.setTimeout(() => loadEarningsDesk(), 280);
  });
  els.earningsQ?.addEventListener("keydown", (ev) => {
    if (ev.key === "Enter") {
      ev.preventDefault();
      state.earningsQ = els.earningsQ.value.trim();
      loadEarningsDesk();
    }
  });
}

function clearPageTimers() {
  while (pageTimers.length) {
    clearInterval(pageTimers.pop());
  }
}

function trackPageInterval(fn, ms) {
  const id = window.setInterval(fn, ms);
  pageTimers.push(id);
  return id;
}

function pageDataKey(page = PAGE) {
  return `pulse_data:${page}`;
}

function persistPageDataCache() {
  try {
    if (PAGE === "desk" && state.portfolio) {
      for (const h of state.portfolio.holdings || []) cachePortfolioBoard(h);
      if (state.portfolio.selected_board) {
        cachePortfolioBoard(state.portfolio.selected_board);
      }
      sessionStorage.setItem(
        pageDataKey("desk"),
        JSON.stringify({
          at: Date.now(),
          portfolio: state.portfolio,
          portfolioTf: state.portfolioTf,
          boardCache: state.portfolioBoardCache || {},
          holdingFilter: state.holdingFilter || "",
        })
      );
    }
    if (PAGE === "sectors" && state.sectors) {
      sessionStorage.setItem(
        pageDataKey("sectors"),
        JSON.stringify({
          at: Date.now(),
          sectors: state.sectors,
          sectorId: state.sectorId,
          sectorSymbol: state.sectorSymbol,
          sectorTf: state.sectorTf,
          sectorCache: state.sectorCache || {},
          usMarkets: state.usMarkets || null,
          usFuturesTf: state.usFuturesTf || "intraday",
        })
      );
    }
    if (PAGE === "markets" && state.markets) {
      sessionStorage.setItem(
        pageDataKey("markets"),
        JSON.stringify({
          at: Date.now(),
          markets: state.markets,
          marketTf: state.marketTf,
        })
      );
    }
  } catch {
    /* quota / private mode */
  }
}

function readPageDataCache(page = PAGE) {
  try {
    const raw = sessionStorage.getItem(pageDataKey(page));
    if (!raw) return null;
    const row = JSON.parse(raw);
    if (!row || Date.now() - Number(row.at || 0) > PAGE_DATA_TTL_MS) return null;
    return row;
  } catch {
    return null;
  }
}

function paintFromPageDataCache(page = PAGE) {
  const row = readPageDataCache(page);
  if (!row) return false;
  if (page === "desk" && row.portfolio) {
    state.portfolio = row.portfolio;
    if (row.portfolioTf) state.portfolioTf = row.portfolioTf;
    if (row.boardCache) state.portfolioBoardCache = row.boardCache;
    if (row.holdingFilter != null) state.holdingFilter = row.holdingFilter;
    renderPortfolio(row.portfolio);
    return true;
  }
  if (page === "sectors" && row.sectors) {
    state.sectors = row.sectors;
    if (row.sectorId) state.sectorId = row.sectorId;
    if (row.sectorSymbol) state.sectorSymbol = row.sectorSymbol;
    if (row.sectorTf) state.sectorTf = row.sectorTf;
    if (row.sectorCache) state.sectorCache = row.sectorCache;
    renderSectorDesk(row.sectors);
    if (row.usMarkets) {
      if (row.usFuturesTf) state.usFuturesTf = row.usFuturesTf;
      renderUsMarketsDesk(row.usMarkets);
    }
    return true;
  }
  if (page === "markets" && row.markets) {
    state.markets = row.markets;
    if (row.marketTf) state.marketTf = row.marketTf;
    renderMarkets(row.markets);
    return true;
  }
  return false;
}

function syncChainsQuery() {
  const params = new URLSearchParams();
  if (state.chainQ) params.set("q", state.chainQ);
  if (state.chainId) params.set("chain", state.chainId);
  const qs = params.toString();
  const next = qs ? `/chains?${qs}` : "/chains";
  if (`${location.pathname}${location.search}` !== next) {
    history.replaceState({}, "", next);
  }
}

function renderChainsSuggest(catalog) {
  if (!els.chainsSuggest) return;
  const list = catalog || [];
  els.chainsSuggest.innerHTML = list
    .map(
      (c) =>
        `<button type="button" class="chains-suggest-chip" data-chain-id="${escapeHtml(
          c.id
        )}" data-chain-q="${escapeHtml(c.label)}">${escapeHtml(
          c.label
        )}</button>`
    )
    .join("");
}

function chainsCompanyRowHtml(c) {
  const sym = String(c.symbol || "").toUpperCase();
  const held = isInHoldings(sym);
  const sector = c.sector || "technology";
  const core = Boolean(c.core);
  return `
    <div class="chains-co-row ${held ? "in-holding" : ""} ${
      core ? "is-core" : ""
    }" data-symbol="${escapeHtml(sym)}">
      <a class="chains-co-main" href="/sectors?sector=${encodeURIComponent(
        sector
      )}&symbol=${encodeURIComponent(sym)}">
        <span class="chains-co-name">${escapeHtml(c.name || sym)}</span>
        <span class="chains-co-sym-wrap">
          <span class="chains-co-sym">${escapeHtml(sym)}</span>
          ${
            core
              ? '<span class="chains-co-core-tag" title="核心标的">核心</span>'
              : ""
          }
        </span>
        ${
          c.note
            ? `<span class="chains-co-note">${escapeHtml(c.note)}</span>`
            : ""
        }
      </a>
      <button
        type="button"
        class="sector-hold-btn ${held ? "is-held" : ""}"
        data-hold-symbol="${escapeHtml(sym)}"
        data-hold-name="${escapeHtml(c.name || "")}"
        data-hold-action="${held ? "remove" : "add"}"
        title="${held ? `从持仓移除 ${sym}` : `加入持仓 ${sym}`}"
        aria-label="${held ? `从持仓移除 ${sym}` : `加入持仓 ${sym}`}"
      >${held ? "−" : "+"}</button>
    </div>
  `;
}

function sortChainCompanies(list) {
  return (list || [])
    .slice()
    .sort((a, b) => {
      const ac = a?.core ? 0 : 1;
      const bc = b?.core ? 0 : 1;
      if (ac !== bc) return ac - bc;
      return String(a?.symbol || "").localeCompare(String(b?.symbol || ""));
    });
}

function chainsMindmapStages(chain) {
  const flow = Array.isArray(chain.top_flow) ? chain.top_flow : [];
  const defaults = [
    { id: "support", label: "上游支撑", tone: "support" },
    { id: "core", label: "中游核心", tone: "core" },
    { id: "downstream", label: "下游应用", tone: "app" },
  ];
  const stages = (flow.length ? flow : defaults).map((stage, idx) => ({
    id: stage.id || defaults[idx]?.id || `stage_${idx}`,
    label: stage.label || defaults[idx]?.label || "环节",
    tone: stage.tone || defaults[idx]?.tone || "core",
    panels: [],
  }));
  const byTone = { support: 0, core: 1, app: 2 };
  const fallbackIdx = (tone) =>
    byTone[tone] != null ? Math.min(byTone[tone], stages.length - 1) : 1;

  for (const panel of chain.panels || []) {
    const tone = panel.tone || "core";
    let idx = stages.findIndex((s) => s.tone === tone || s.id === tone);
    if (idx < 0) idx = fallbackIdx(tone);
    stages[idx].panels.push(panel);
  }
  // Prefer branch node labels when a stage has no panels yet.
  for (const branch of chain.branches || []) {
    const tone = branch.tone || "core";
    let idx = stages.findIndex(
      (s) => s.tone === tone || s.id === branch.parent || s.id === tone
    );
    if (idx < 0 || stages[idx].panels.length) continue;
    for (const node of branch.nodes || []) {
      stages[idx].panels.push({
        id: node.id,
        label: node.label || node.id,
        tone,
        _virtual: true,
      });
    }
  }
  return stages.filter((s) => s.panels.length);
}

function chainsMmLeafHtml(panel, tone) {
  const id = panel.id || "";
  const tag = panel._virtual ? "span" : "button";
  const attrs = panel._virtual
    ? ""
    : ` type="button" data-panel-id="${escapeHtml(id)}"`;
  return `<${tag} class="chains-mm-leaf tone-${escapeHtml(tone)}"${attrs}>${escapeHtml(
    panel.label || id
  )}</${tag}>`;
}

function chainsMmStageBlock(stage, side) {
  if (!stage) return '<div class="chains-mm-stage is-empty"></div>';
  const leaves = (stage.panels || [])
    .map((p) => chainsMmLeafHtml(p, stage.tone))
    .join("");
  return `
    <div class="chains-mm-stage side-${escapeHtml(side)} tone-${escapeHtml(
      stage.tone
    )}" data-tone="${escapeHtml(stage.tone)}" data-side="${escapeHtml(side)}">
      <div class="chains-mm-stage-label">${escapeHtml(stage.label)}</div>
      <div class="chains-mm-leaves">${leaves}</div>
    </div>`;
}

function renderChainsMindmap(chain) {
  if (!els.chainsMindmap) return;
  const stages = chainsMindmapStages(chain);
  const rootLabel = (chain.label || "产业链").replace(/产业链$/, "") || "产业链";
  const left =
    stages.find((s) => s.tone === "support") ||
    stages.find((s) => /support|upstream|上游|材料/.test(`${s.id}${s.label}`));
  const right =
    stages.find((s) => s.tone === "app") ||
    stages.find((s) => /app|downstream|下游|应用|补能|出行/.test(`${s.id}${s.label}`));
  const bottom =
    stages.find((s) => s.tone === "core") ||
    stages.find((s) => s !== left && s !== right) ||
    stages[0];
  // Any leftover stages append under bottom so nothing is dropped.
  const extras = stages.filter(
    (s) => s && s !== left && s !== right && s !== bottom
  );

  els.chainsMindmap.innerHTML = `
    <div class="chains-mm-shell is-lr">
      <svg class="chains-mm-links" aria-hidden="true"></svg>
      <div class="chains-mm-lr">
        <div class="chains-mm-rail left">${chainsMmStageBlock(left, "left")}</div>
        <div class="chains-mm-center">
          <div class="chains-mm-root">
            <span class="chains-mm-root-kicker">产业逻辑脑图</span>
            <strong>${escapeHtml(rootLabel)}</strong>
          </div>
          ${chainsMmStageBlock(bottom, "bottom")}
          ${extras.map((s) => chainsMmStageBlock(s, "bottom")).join("")}
        </div>
        <div class="chains-mm-rail right">${chainsMmStageBlock(right, "right")}</div>
      </div>
    </div>`;

  els.chainsMindmap.querySelectorAll("[data-panel-id]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const id = btn.getAttribute("data-panel-id");
      const target = id && document.getElementById(`chain-panel-${id}`);
      if (!target) return;
      target.scrollIntoView({ behavior: "smooth", block: "nearest" });
      target.classList.add("is-flash");
      window.setTimeout(() => target.classList.remove("is-flash"), 1200);
    });
  });

  requestAnimationFrame(() => {
    drawChainsMindmapLinks();
    requestAnimationFrame(() => drawChainsMindmapLinks());
  });
}

function drawChainsMindmapLinks() {
  const shell = els.chainsMindmap?.querySelector(".chains-mm-shell");
  const svg = els.chainsMindmap?.querySelector(".chains-mm-links");
  const root = els.chainsMindmap?.querySelector(".chains-mm-root");
  if (!shell || !svg || !root) return;
  if (window.matchMedia("(max-width: 900px)").matches) {
    svg.innerHTML = "";
    return;
  }
  const shellBox = shell.getBoundingClientRect();
  const rootBox = root.getBoundingClientRect();
  const w = Math.max(1, shell.clientWidth);
  const h = Math.max(1, shell.clientHeight);
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.setAttribute("width", String(w));
  svg.setAttribute("height", String(h));

  const rx = rootBox.left + rootBox.width / 2 - shellBox.left;
  const ry = rootBox.top + rootBox.height / 2 - shellBox.top;
  const paths = [];

  els.chainsMindmap.querySelectorAll(".chains-mm-stage:not(.is-empty)").forEach((stage) => {
    const side = stage.dataset.side || "bottom";
    const label = stage.querySelector(".chains-mm-stage-label");
    if (!label) return;
    const lb = label.getBoundingClientRect();
    const lx = lb.left + lb.width / 2 - shellBox.left;
    const ly = lb.top + lb.height / 2 - shellBox.top;
    const tone = stage.dataset.tone || "core";

    let x0 = rx;
    let y0 = ry;
    if (side === "left") {
      x0 = rootBox.left - shellBox.left;
      y0 = ry;
    } else if (side === "right") {
      x0 = rootBox.right - shellBox.left;
      y0 = ry;
    } else {
      x0 = rx;
      y0 = rootBox.bottom - shellBox.top;
    }

    const c1x =
      side === "left" ? x0 - Math.abs(x0 - lx) * 0.35 : side === "right" ? x0 + Math.abs(lx - x0) * 0.35 : x0;
    const c1y = side === "bottom" ? y0 + Math.abs(ly - y0) * 0.35 : y0;
    const c2x =
      side === "left" ? lx + Math.abs(x0 - lx) * 0.35 : side === "right" ? lx - Math.abs(lx - x0) * 0.35 : lx;
    const c2y = side === "bottom" ? ly - Math.abs(ly - y0) * 0.35 : ly;
    paths.push(
      `<path class="chains-mm-link tone-${tone}" d="M ${x0} ${y0} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${lx} ${ly}" fill="none" />`
    );

    stage.querySelectorAll(".chains-mm-leaf").forEach((leaf) => {
      const fb = leaf.getBoundingClientRect();
      const fx = fb.left + fb.width / 2 - shellBox.left;
      const fy = fb.top + fb.height / 2 - shellBox.top;
      let sx = lx;
      let sy = ly;
      if (side === "left") {
        sx = lb.left - shellBox.left;
        sy = ly;
      } else if (side === "right") {
        sx = lb.right - shellBox.left;
        sy = ly;
      } else {
        sx = lx;
        sy = lb.bottom - shellBox.top;
      }
      const mx = (sx + fx) / 2;
      const my = (sy + fy) / 2;
      paths.push(
        `<path class="chains-mm-link soft tone-${tone}" d="M ${sx} ${sy} Q ${mx} ${my}, ${fx} ${fy}" fill="none" />`
      );
    });
  });
  svg.innerHTML = paths.join("");
}

function renderChainsPanorama(chain) {
  if (!els.chainsPanels) return;
  renderChainsMindmap(chain);

  els.chainsPanels.innerHTML = (chain.panels || [])
    .map((panel) => {
      const cos = sortChainCompanies(panel.companies || []);
      const coreN = cos.filter((c) => c.core).length;
      return `
        <article class="chains-panel tone-${escapeHtml(panel.tone || "core")}" id="chain-panel-${escapeHtml(
          panel.id
        )}">
          <header class="chains-panel-head">
            <h3>${escapeHtml(panel.label || "")}</h3>
            <p>${escapeHtml(
              panel.blurb || ""
            )}${
              cos.length
                ? `${panel.blurb ? " · " : ""}${cos.length} 只${
                    coreN ? ` · 核心 ${coreN}` : ""
                  }`
                : ""
            }</p>
          </header>
          <div class="chains-panel-list" tabindex="0" aria-label="${escapeHtml(
            panel.label || "股票列表"
          )}可滚动">
            ${
              cos.length
                ? cos.map(chainsCompanyRowHtml).join("")
                : '<p class="empty">暂无美股映射</p>'
            }
          </div>
        </article>`;
    })
    .join("");

  els.chainsPanels.querySelectorAll(".sector-hold-btn").forEach((btn) => {
    btn.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const sym = btn.getAttribute("data-hold-symbol") || "";
      const name = btn.getAttribute("data-hold-name") || "";
      const action = btn.getAttribute("data-hold-action") || "add";
      if (action === "remove") {
        if (!confirm(`确定从持仓移除 ${sym}？`)) return;
      }
      toggleSectorHolding(sym, name);
    });
  });
  // Keep wheel/trackpad scroll inside panel lists without growing the card.
  els.chainsPanels.querySelectorAll(".chains-panel-list").forEach((list) => {
    list.addEventListener(
      "wheel",
      (event) => {
        if (list.scrollHeight <= list.clientHeight + 1) return;
        const dy = event.deltaY;
        const top = list.scrollTop;
        const max = list.scrollHeight - list.clientHeight;
        const atTop = top <= 0 && dy < 0;
        const atBottom = top >= max - 1 && dy > 0;
        if (!atTop && !atBottom) {
          event.stopPropagation();
        }
      },
      { passive: true }
    );
  });

  if (!window.__chainsMindmapResizeBound) {
    window.__chainsMindmapResizeBound = true;
    window.addEventListener("resize", () => {
      if (els.chainsMindmap && !els.chainsMap?.classList.contains("is-hidden")) {
        drawChainsMindmapLinks();
      }
    });
  }
}

function renderChainsDesk(data) {
  if (!data) return;
  state.chains = data;
  state.chainQ = data.q || state.chainQ || "";
  state.chainId = data.matched ? data.chain?.id || "" : "";
  if (els.chainsQ && state.chainQ && els.chainsQ.value !== state.chainQ) {
    els.chainsQ.value = state.chainQ;
  }
  renderChainsSuggest(data.catalog || []);

  const matched = Boolean(data.matched && data.chain);
  if (els.chainsEmpty) {
    els.chainsEmpty.classList.toggle("is-hidden", matched);
    if (!matched) {
      const title = els.chainsEmpty.querySelector(".chains-empty-title");
      const text = els.chainsEmpty.querySelector(".chains-empty-text");
      if (title) {
        title.textContent = data.q ? "未匹配到产业链" : "从搜索开始";
      }
      if (text) {
        text.textContent =
          data.message ||
          "输入行业关键词后，将生成全产业链逻辑图，并列出对应美股。";
      }
    }
  }
  if (els.chainsMap) els.chainsMap.classList.toggle("is-hidden", !matched);

  if (matched) {
    const chain = data.chain;
    if (els.chainsMapTitle) els.chainsMapTitle.textContent = chain.label || "产业链";
    if (els.chainsMapBlurb) {
      els.chainsMapBlurb.textContent = chain.blurb || "";
    }
    if (els.chainsBlurb) {
      els.chainsBlurb.textContent =
        chain.blurb ||
        "输入行业关键词，生成上下游逻辑图，并标注美股代码；可一键加入持仓。";
    }
    renderChainsPanorama(chain);
    setStatus(
      data.generated
        ? `${chain.label} · 已按关键词自动生成`
        : `${chain.label} · 全景逻辑图已生成`
    );
  } else {
    setStatus(data.message || "输入行业关键词生成产业链");
  }
  syncChainsQuery();
}

async function loadChainsDesk({ q, chain } = {}) {
  if (PAGE !== "chains") return null;
  const query = q ?? state.chainQ;
  const chainId = chain ?? state.chainId;
  if (query) {
    setStatus(`正在根据「${query}」生成全产业链逻辑图…`);
    if (els.chainsEmpty) {
      els.chainsEmpty.classList.remove("is-hidden");
      const title = els.chainsEmpty.querySelector(".chains-empty-title");
      const text = els.chainsEmpty.querySelector(".chains-empty-text");
      if (title) title.textContent = "正在生成…";
      if (text) {
        text.textContent =
          "正在组合上下游环节并检索相关美股，通常几秒内完成。";
      }
    }
    if (els.chainsMap) els.chainsMap.classList.add("is-hidden");
  }
  try {
    const params = new URLSearchParams();
    if (query) params.set("q", query);
    if (chainId) params.set("chain", chainId);
    const res = await fetch(`/api/chains?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderChainsDesk(data);
    return data;
  } catch (err) {
    setStatus(`产业链加载失败：${err.message || err}`);
    if (els.chainsEmpty) {
      els.chainsEmpty.classList.remove("is-hidden");
      const text = els.chainsEmpty.querySelector(".chains-empty-text");
      if (text) text.textContent = `加载失败：${err.message || err}`;
    }
    if (els.chainsMap) els.chainsMap.classList.add("is-hidden");
    return null;
  }
}

function bindChainsDesk() {
  if (PAGE !== "chains" || state.chainsBound) return;
  state.chainsBound = true;
  els.chainsSearch?.addEventListener("submit", (event) => {
    event.preventDefault();
    state.chainQ = (els.chainsQ?.value || "").trim();
    state.chainId = "";
    void loadChainsDesk({ q: state.chainQ, chain: "" });
  });
  els.chainsSuggest?.addEventListener("click", (event) => {
    const chip = event.target.closest("[data-chain-id]");
    if (!chip) return;
    const id = chip.getAttribute("data-chain-id") || "";
    const label = chip.getAttribute("data-chain-q") || "";
    state.chainId = id;
    state.chainQ = label;
    if (els.chainsQ) els.chainsQ.value = label;
    void loadChainsDesk({ q: label, chain: id });
  });
}

function bootPage() {
  clearPageTimers();
  if (PAGE === "login") {
    bindAuthPage();
    setStatus("登录后查看个人持仓");
    return;
  }
  if (PAGE === "desk") {
    if (!AUTHED) {
      setStatus("未登录 · 持仓需登录后查看");
      return;
    }
    const painted = paintFromPageDataCache("desk");
    if (painted) {
      restoreScrollPosition();
      setStatus("已恢复持仓缓存 · 后台刷新中…");
    }
    loadPortfolio().then(() => {
      const selected = state.portfolio?.selected || "";
      loadHoldingIntel({ symbol: selected || "", soft: painted });
      persistPageDataCache();
      if (state.portfolioTf === "intraday") refreshActiveIntraday();
      // Prefetch 日/月/季 so TF tabs work without a hard refresh.
      if (!pickHasChart(state.portfolio?.selected_board)) {
        ensureMultiTfChartUpgrade();
      }
    });
    // Soft list refresh — force=true was making buttons feel stuck every 90s.
    trackPageInterval(() => {
      loadPortfolio({ refresh: false });
      loadHoldingIntel({
        symbol: state.holdingFilter || state.portfolio?.selected || "",
        soft: true,
      });
    }, 90 * 1000);
    // Fastest practical 分时 poll (backend snap TTL ~0.75s).
    trackPageInterval(() => refreshActiveIntraday(), 500);
  } else if (PAGE === "markets") {
    const painted = paintFromPageDataCache("markets");
    if (painted) restoreScrollPosition();
    loadMarketsDesk();
    // Markets board TTL ~2s; avoid force so FRED isn't hammered.
    trackPageInterval(() => loadMarketsDesk({ force: false }), 2000);
  } else if (PAGE === "sectors") {
    const params = new URLSearchParams(location.search);
    const qSector = (params.get("sector") || "").trim().toLowerCase();
    const qSymbol = (params.get("symbol") || "").trim().toUpperCase();
    if (qSector) state.sectorId = qSector;
    if (qSymbol) state.sectorSymbol = qSymbol;
    const painted = paintFromPageDataCache("sectors");
    if (painted) {
      restoreScrollPosition();
      setStatus("已恢复板块缓存 · 后台刷新中…");
    }
    bindSectorDesk();
    // Parallel: desk / US markets / hold-tags — never wait on full portfolio quotes.
    void loadUsMarketsDesk().then(() => persistPageDataCache());
    void refreshHoldingSymbols().then(() => {
      if (state.sectors) renderSectorPicks(state.sectors);
    });
    void loadSectorDesk().then(() => {
      if (state.sectorTf === "intraday") refreshActiveIntraday();
      if (!pickHasChart(state.sectors?.selected_pick)) {
        ensureMultiTfChartUpgrade();
      }
      persistPageDataCache();
    });
    trackPageInterval(() => loadSectorDesk(), 90 * 1000);
    // Futures 分时 + strip: match stock 分时 cadence (~0.5s).
    trackPageInterval(() => {
      if ((state.usFuturesTf || "intraday") === "intraday") {
        loadUsMarketsDesk({ force: true });
      }
    }, 500);
    trackPageInterval(() => {
      if ((state.usFuturesTf || "intraday") !== "intraday") {
        loadUsMarketsDesk({ force: false });
      }
    }, 60 * 1000);
    trackPageInterval(() => refreshHoldingSymbols({ force: true }), 120 * 1000);
    trackPageInterval(() => refreshActiveIntraday(), 500);
  } else if (PAGE === "earnings") {
    bindEarningsDesk();
    loadEarningsDesk();
    trackPageInterval(() => loadEarningsDesk(), 5 * 60 * 1000);
  } else if (PAGE === "intel") {
    readIntelQueryFlags();
    loadIntel();
    trackPageInterval(() => loadIntel(), 5 * 60 * 1000);
  } else if (PAGE === "chains") {
    const params = new URLSearchParams(location.search);
    const qText = (params.get("q") || "").trim();
    const qChain = (params.get("chain") || "").trim();
    if (qText) state.chainQ = qText;
    if (qChain) state.chainId = qChain;
    if (els.chainsQ && qText) els.chainsQ.value = qText;
    bindChainsDesk();
    void refreshHoldingSymbols().then(() => loadChainsDesk());
  } else if (PAGE === "settings") {
    loadSettingsPage();
    loadAccessTip();
  }
}

/** Persist / restore scroll per route so tab switches don't jump to top. */
function scrollStorageKey(pathname = location.pathname, hash = location.hash) {
  return `pulse_scroll:${pathname}${hash || ""}`;
}

function saveScrollPosition() {
  try {
    sessionStorage.setItem(
      scrollStorageKey(),
      String(window.scrollY || window.pageYOffset || 0)
    );
  } catch {
    /* ignore quota / private mode */
  }
}

function restoreScrollPosition() {
  let raw = null;
  try {
    raw = sessionStorage.getItem(scrollStorageKey());
  } catch {
    return;
  }
  const html = document.documentElement;
  const prevBehavior = html.style.scrollBehavior;
  html.style.scrollBehavior = "auto";
  const finish = () => {
    html.style.scrollBehavior = prevBehavior;
  };
  if (raw == null) {
    if (location.hash === "#holding-intel") {
      document.getElementById("holding-intel")?.scrollIntoView({ block: "start" });
    }
    setTimeout(finish, 50);
    return;
  }
  const y = Number(raw);
  if (!Number.isFinite(y)) {
    finish();
    return;
  }
  const apply = () => window.scrollTo(0, y);
  requestAnimationFrame(() => requestAnimationFrame(apply));
  setTimeout(apply, 100);
  setTimeout(() => {
    apply();
    finish();
  }, 350);
}

function navCycleRoutes() {
  const settingsHref = AUTHED ? "/settings" : "/login";
  return [
    {
      id: "desk",
      href: "/",
      match: (p) => p === "/",
    },
    {
      id: "markets",
      href: "/markets",
      match: (p) => p === "/markets",
    },
    {
      id: "sectors",
      href: "/sectors",
      match: (p) => p === "/sectors",
    },
    {
      id: "earnings",
      href: "/earnings",
      match: (p) => p === "/earnings",
    },
    {
      id: "intel",
      href: "/intel",
      match: (p) => p === "/intel",
    },
    {
      id: AUTHED ? "settings" : "login",
      href: settingsHref,
      match: (p) => p === "/settings" || p === "/login",
    },
  ];
}

function currentNavIndex() {
  const routes = navCycleRoutes();
  const path = location.pathname;
  const hash = location.hash || "";
  const idx = routes.findIndex((r) => r.match(path, hash));
  return idx >= 0 ? idx : 0;
}

function syncNavActive() {
  const routes = navCycleRoutes();
  const idx = currentNavIndex();
  const activeId = routes[idx]?.id;
  document.querySelectorAll("[data-nav-cycle] a[data-nav]").forEach((a) => {
    a.classList.toggle("is-active", a.dataset.nav === activeId);
  });
}

function navigateToHref(href) {
  const url = new URL(href, location.origin);
  const samePath = url.pathname === location.pathname;

  // Snapshot desk/sectors data before leaving so the next visit paints instantly.
  persistPageDataCache();
  saveScrollPosition();

  if (samePath) {
    if (url.hash) {
      history.pushState(null, "", `${url.pathname}${url.hash}`);
      syncNavActive();
      restoreScrollPosition();
      return;
    }
    if (location.hash) {
      history.pushState(null, "", url.pathname);
      syncNavActive();
      restoreScrollPosition();
      return;
    }
    restoreScrollPosition();
    return;
  }

  location.href = `${url.pathname}${url.search || ""}${url.hash || ""}`;
}

function cycleNav(delta) {
  if (PAGE === "login") return;
  const routes = navCycleRoutes();
  if (!routes.length) return;
  const next = (currentNavIndex() + delta + routes.length) % routes.length;
  navigateToHref(routes[next].href);
}

function isEditableTarget(el) {
  if (!el || !(el instanceof Element)) return false;
  if (el.closest("input, textarea, select, [contenteditable='true']")) return true;
  return false;
}

function canConsumeHorizontalScroll(el, dir) {
  let node = el instanceof Element ? el : null;
  while (node && node !== document.documentElement) {
    const style = getComputedStyle(node);
    const ox = style.overflowX;
    if (
      (ox === "auto" || ox === "scroll" || ox === "overlay") &&
      node.scrollWidth > node.clientWidth + 1
    ) {
      if (dir > 0 && node.scrollLeft + node.clientWidth < node.scrollWidth - 1) {
        return true;
      }
      if (dir < 0 && node.scrollLeft > 1) return true;
    }
    node = node.parentElement;
  }
  return false;
}

function bindStickyNavChrome() {
  syncNavActive();
  restoreScrollPosition();

  document.querySelectorAll("[data-nav-cycle] a[data-nav]").forEach((a) => {
    a.addEventListener("click", (event) => {
      const href = a.getAttribute("href");
      if (!href) return;
      event.preventDefault();
      navigateToHref(href);
    });
  });

  window.addEventListener("pagehide", () => {
    persistPageDataCache();
    saveScrollPosition();
  });
  window.addEventListener("beforeunload", () => {
    persistPageDataCache();
    saveScrollPosition();
  });
  let scrollSaveTimer = 0;
  window.addEventListener(
    "scroll",
    () => {
      clearTimeout(scrollSaveTimer);
      scrollSaveTimer = window.setTimeout(saveScrollPosition, 120);
    },
    { passive: true }
  );
  window.addEventListener("hashchange", () => {
    syncNavActive();
    restoreScrollPosition();
  });
  window.addEventListener("popstate", () => {
    syncNavActive();
    restoreScrollPosition();
  });

  /* Horizontal swipe / trackpad sideways nav disabled — use top/bottom tab bar. */
}

const THEME_MODE_KEY = "pulse_theme_mode";
const THEME_MODE_LABELS = {
  auto: "自动",
  light: "白天",
  dark: "夜晚",
};

function readThemeMode() {
  try {
    const mode = localStorage.getItem(THEME_MODE_KEY) || "auto";
    return mode === "light" || mode === "dark" || mode === "auto" ? mode : "auto";
  } catch {
    return "auto";
  }
}

function resolveTheme(mode = readThemeMode()) {
  if (mode === "light" || mode === "dark") return mode;
  const hour = new Date().getHours();
  return hour >= 6 && hour < 18 ? "light" : "dark";
}

function applyTheme(mode = readThemeMode(), { announce = false } = {}) {
  const nextMode = mode === "light" || mode === "dark" || mode === "auto" ? mode : "auto";
  const theme = resolveTheme(nextMode);
  document.documentElement.setAttribute("data-theme", theme);
  document.documentElement.setAttribute("data-theme-mode", nextMode);
  try {
    localStorage.setItem(THEME_MODE_KEY, nextMode);
  } catch {
    /* ignore */
  }

  const metaColor = document.getElementById("meta-theme-color");
  if (metaColor) {
    metaColor.setAttribute(
      "content",
      theme === "dark" ? "#0a0e14" : "#102033"
    );
  }
  const statusBar = document.getElementById("meta-status-bar");
  if (statusBar) {
    statusBar.setAttribute(
      "content",
      theme === "dark" ? "black-translucent" : "default"
    );
  }

  const label = document.getElementById("theme-label");
  if (label) label.textContent = THEME_MODE_LABELS[nextMode] || "自动";

  const btn = document.getElementById("btn-theme");
  if (btn) {
    btn.setAttribute(
      "aria-label",
      `当前主题：${THEME_MODE_LABELS[nextMode]}，点击切换`
    );
    btn.title = `主题：${THEME_MODE_LABELS[nextMode]}（点击切换 自动/白天/夜晚）`;
  }

  document.querySelectorAll("[data-theme-mode]").forEach((el) => {
    const active = el.dataset.themeMode === nextMode;
    el.classList.toggle("is-active", active);
    el.setAttribute("aria-pressed", active ? "true" : "false");
  });

  if (announce) {
    setStatus(`已切换为${THEME_MODE_LABELS[nextMode]}主题`);
  }

  window.dispatchEvent(
    new CustomEvent("pulse-theme-change", {
      detail: { mode: nextMode, theme },
    })
  );
}

function cycleThemeMode() {
  const order = ["auto", "light", "dark"];
  const current = readThemeMode();
  const next = order[(order.indexOf(current) + 1) % order.length];
  applyTheme(next, { announce: true });
}

function refreshThemeBoundViews() {
  if (PAGE === "markets" && state.markets) renderMarkets(state.markets);
  if (PAGE === "desk" && state.portfolio) {
    renderPortfolio(state.portfolio);
    renderPortfolioChart();
  }
}

function scheduleAutoThemeRefresh() {
  const now = new Date();
  const next = new Date(now);
  const hour = now.getHours();
  if (hour < 6) {
    next.setHours(6, 0, 0, 0);
  } else if (hour < 18) {
    next.setHours(18, 0, 0, 0);
  } else {
    next.setDate(next.getDate() + 1);
    next.setHours(6, 0, 0, 0);
  }
  const delay = Math.max(5_000, next.getTime() - now.getTime() + 250);
  window.setTimeout(() => {
    if (readThemeMode() === "auto") applyTheme("auto");
    scheduleAutoThemeRefresh();
  }, delay);
}

function bindThemeChrome() {
  applyTheme(readThemeMode());
  document.getElementById("btn-theme")?.addEventListener("click", () => {
    cycleThemeMode();
  });
  document.querySelectorAll("[data-theme-mode]").forEach((el) => {
    el.addEventListener("click", () => {
      applyTheme(el.dataset.themeMode || "auto", { announce: true });
    });
  });
  window.addEventListener("pulse-theme-change", refreshThemeBoundViews);
  scheduleAutoThemeRefresh();
}

bootPage();
bindStickyNavChrome();
bindThemeChrome();
