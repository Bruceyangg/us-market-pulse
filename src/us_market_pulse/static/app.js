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
  holdingToggleBusy: false,
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
  earnings: null,
  earningsDate: "",
  earningsSession: "all",
  earningsQ: "",
  chartZoom: {},
  chartZoomScope: {},
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
const PAGE = document.body?.dataset?.page || "desk";
const AUTHED = Boolean(document.getElementById("user-chip") || document.getElementById("btn-logout"));

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
  if (value == null || Number.isNaN(value)) return "—";
  const abs = Math.abs(value);
  const digits = abs >= 100 ? 1 : abs >= 10 ? 2 : 3;
  const text = value.toFixed(digits);
  return unit === "%" ? `${text}%` : text;
}

function formatDelta(delta) {
  if (delta == null || Number.isNaN(delta)) return { text: "—", cls: "" };
  const sign = delta > 0 ? "+" : "";
  const cls = delta > 0 ? "up" : delta < 0 ? "down" : "";
  return { text: `${sign}${delta.toFixed(3)}`, cls };
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
  if (state.chartZoomScope[key] !== scope) {
    state.chartZoomScope[key] = scope;
    state.chartZoom[key] = defaultChartZoom(len, tf, kind);
  }
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

function chartZoomControlsHtml(zoomed) {
  return `
    <div class="chart-zoom-controls" role="group" aria-label="图表缩放">
      <button type="button" class="chart-zoom-btn" data-zoom-act="out" title="缩小" aria-label="缩小">−</button>
      <button type="button" class="chart-zoom-btn" data-zoom-act="in" title="放大" aria-label="放大">+</button>
      <button type="button" class="chart-zoom-btn chart-zoom-reset${
        zoomed ? "" : " is-hidden"
      }" data-zoom-act="reset" title="重置" aria-label="重置缩放">1×</button>
    </div>
  `;
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
      <path d="${area}" fill="${fill}"></path>
      <path d="${line}" fill="none" stroke="${stroke}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"></path>
    </svg>
  `;
}

const SESSION_BAND_COLORS = {
  night: "rgba(88, 110, 140, 0.14)",
  pre: "rgba(196, 122, 22, 0.12)",
  regular: "rgba(15, 138, 106, 0.08)",
  post: "rgba(47, 111, 159, 0.12)",
};

const SESSION_LABELS = {
  night: "夜盘",
  pre: "盘前",
  regular: "盘中",
  post: "盘后",
};

function sessionIdFromTs(ts) {
  if (!ts) return "regular";
  try {
    const parts = new Intl.DateTimeFormat("en-US", {
      timeZone: "America/New_York",
      hour: "numeric",
      minute: "numeric",
      hour12: false,
    }).formatToParts(new Date(Number(ts) * 1000));
    const hour = Number(parts.find((p) => p.type === "hour")?.value || 0);
    const minute = Number(parts.find((p) => p.type === "minute")?.value || 0);
    const mins = hour * 60 + minute;
    if (mins >= 20 * 60 || mins < 4 * 60) return "night";
    if (mins < 9 * 60 + 30) return "pre";
    if (mins < 16 * 60) return "regular";
    return "post";
  } catch {
    return "regular";
  }
}

function ensurePointSessions(points) {
  return (points || []).map((p) => {
    if (!p) return p;
    if (p.session) return p;
    return { ...p, session: sessionIdFromTs(p.t) };
  });
}

function buildSessionSegmentsFromPoints(points) {
  const rows = ensurePointSessions(points);
  if (!rows.length) return [];
  const segs = [];
  let cur = rows[0]?.session || "regular";
  let start = 0;
  for (let i = 0; i < rows.length; i += 1) {
    const sid = rows[i]?.session || "regular";
    if (sid !== cur) {
      segs.push({ id: cur, label: SESSION_LABELS[cur] || cur, i0: start, i1: i - 1 });
      cur = sid;
      start = i;
    }
  }
  segs.push({
    id: cur,
    label: SESSION_LABELS[cur] || cur,
    i0: start,
    i1: rows.length - 1,
  });
  return segs;
}

/** Composite 分时: 夜盘 / 盘前 / 盘中 / 盘后 as one continuous line with session bands. */
function renderSessionIntradaySvg(
  points,
  {
    up = true,
    viewStart = 0,
    viewEnd = null,
    sessions = null,
    previousClose = null,
  } = {}
) {
  const width = 320;
  const height = 168;
  const padX = 8;
  const padTop = 18;
  const padBottom = 16;
  const plotH = height - padTop - padBottom;
  const raw = ensurePointSessions(
    (points || []).filter((p) => p && Number.isFinite(Number(p.v ?? p.c)))
  );
  const end = viewEnd == null ? raw.length : Math.min(raw.length, viewEnd);
  const start = clamp(viewStart, 0, Math.max(0, end));
  const view = raw.slice(start, end);
  if (view.length < 2) {
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="暂无走势"><text x="16" y="90" fill="${themeMutedFill()}" font-size="13">暂无分时数据</text></svg>`;
  }
  const vals = view.map((p) => Number(p.v ?? p.c));
  let min = Math.min(...vals);
  let max = Math.max(...vals);
  const prev =
    previousClose != null && Number.isFinite(Number(previousClose))
      ? Number(previousClose)
      : null;
  if (prev != null) {
    min = Math.min(min, prev);
    max = Math.max(max, prev);
  }
  const span = max - min || 1;
  const stepX = (width - padX * 2) / (view.length - 1);
  const yOf = (v) => padTop + (1 - (v - min) / span) * plotH;
  const coords = vals.map((v, i) => [padX + i * stepX, yOf(v)]);

  let segs = Array.isArray(sessions) && sessions.length
    ? sessions
        .map((s) => ({
          id: s.id,
          label: s.label || SESSION_LABELS[s.id] || s.id,
          i0: Math.max(0, (s.i0 ?? 0) - start),
          i1: Math.min(view.length - 1, (s.i1 ?? 0) - start),
        }))
        .filter((s) => s.i1 >= 0 && s.i0 < view.length && s.i1 >= s.i0)
    : buildSessionSegmentsFromPoints(view);

  if (!segs.length) {
    segs = [{ id: "regular", label: "盘中", i0: 0, i1: view.length - 1 }];
  }

  const bands = segs
    .map((s) => {
      const x0 = padX + s.i0 * stepX - stepX * 0.35;
      const x1 = padX + s.i1 * stepX + stepX * 0.35;
      const w = Math.max(2, x1 - x0);
      const fill = SESSION_BAND_COLORS[s.id] || "rgba(128,128,128,0.08)";
      const midX = x0 + w / 2;
      const label = escapeHtml(s.label || "");
      return `
        <rect x="${x0.toFixed(2)}" y="${padTop}" width="${w.toFixed(
          2
        )}" height="${plotH}" fill="${fill}"></rect>
        <text x="${midX.toFixed(2)}" y="${(padTop - 5).toFixed(
          1
        )}" text-anchor="middle" fill="${themeMutedFill()}" font-size="8.5" font-weight="600">${label}</text>
      `;
    })
    .join("");

  const dividers = segs
    .slice(1)
    .map((s) => {
      const x = padX + s.i0 * stepX;
      return `<line x1="${x.toFixed(2)}" y1="${padTop}" x2="${x.toFixed(
        2
      )}" y2="${(padTop + plotH).toFixed(
        2
      )}" stroke="rgba(148,163,184,0.35)" stroke-width="1" stroke-dasharray="3 3"></line>`;
    })
    .join("");

  const prevLine =
    prev != null
      ? `<line x1="${padX}" y1="${yOf(prev).toFixed(2)}" x2="${
          width - padX
        }" y2="${yOf(prev).toFixed(
          2
        )}" stroke="rgba(148,163,184,0.55)" stroke-width="1" stroke-dasharray="4 3"></line>`
      : "";

  const line = coords
    .map(([x, y], i) => `${i === 0 ? "M" : "L"}${x.toFixed(2)},${y.toFixed(2)}`)
    .join(" ");
  const area = `${line} L${coords[coords.length - 1][0].toFixed(2)},${(
    padTop + plotH
  ).toFixed(2)} L${coords[0][0].toFixed(2)},${(padTop + plotH).toFixed(2)} Z`;
  const stroke = up ? TAPE_UP : TAPE_DOWN;
  const fill = up ? TAPE_UP_SOFT : TAPE_DOWN_SOFT;

  const footLabels = segs
    .map((s) => {
      const midX = padX + ((s.i0 + s.i1) / 2) * stepX;
      return `<text x="${midX.toFixed(2)}" y="${(height - 4).toFixed(
        1
      )}" text-anchor="middle" fill="${themeMutedFill()}" font-size="7.5">${escapeHtml(
        s.label || ""
      )}</text>`;
    })
    .join("");

  return `
    <svg class="session-intraday-svg" viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="盘前盘中盘后夜盘一体分时">
      ${bands}
      ${dividers}
      ${prevLine}
      <path d="${area}" fill="${fill}"></path>
      <path d="${line}" fill="none" stroke="${stroke}" stroke-width="2.1" stroke-linecap="round" stroke-linejoin="round"></path>
      ${footLabels}
    </svg>
  `;
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
  const width = 320;
  const height = 150;
  const padX = 8;
  const padY = 10;
  const bars = sanitizeCandleBars(points);
  if (bars.length < 2) {
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="暂无K线"><text x="16" y="78" fill="${themeMutedFill()}" font-size="13">暂无K线数据</text></svg>`;
  }
  const end = viewEnd == null ? bars.length : Math.min(bars.length, viewEnd);
  const start = clamp(viewStart, 0, Math.max(0, end));
  const viewBars = bars.slice(start, end);
  if (viewBars.length < 2) {
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="暂无K线"><text x="16" y="78" fill="${themeMutedFill()}" font-size="13">暂无K线数据</text></svg>`;
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
  const slot = (width - padX * 2) / viewBars.length;
  const bodyW = Math.max(1.8, Math.min(8, slot * 0.68));
  const wickW = Math.max(1.2, Math.min(2.2, bodyW * 0.45));
  const yOf = (price) => padY + (1 - (price - min) / span) * (height - padY * 2);

  const shapes = viewBars
    .map((b, i) => {
      const o = Number(b.o);
      const h = Number(b.h);
      const l = Number(b.l);
      const c = Number(b.c);
      const up = c >= o;
      const color = up ? TAPE_UP : TAPE_DOWN;
      const x = padX + i * slot + slot / 2;
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
        const x = padX + i * slot + slot / 2;
        const y = yOf(v);
        d += `${started ? "L" : "M"}${x.toFixed(2)},${y.toFixed(2)} `;
        started = true;
      });
      if (!d) return "";
      return `<path d="${d.trim()}" fill="none" stroke="${
        m.color
      }" stroke-width="1.35" stroke-linecap="round" stroke-linejoin="round" opacity="0.92"></path>`;
    })
    .join("");

  return `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="K线柱状图 红涨绿跌${
      showMa ? " 含均线" : ""
    }">
      ${shapes}
      ${maPaths}
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
  if (zoomRoot) zoomRoot.classList.toggle("is-zoomed", zoomed);
  root.querySelectorAll(":scope > .ma-legend").forEach((el) => el.remove());
  if (kind === "candle") {
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
  } else if (tf === "intraday") {
    stage.innerHTML = renderSessionIntradaySvg(points, {
      up,
      viewStart: z.start,
      viewEnd: z.start + z.count,
      sessions: meta.sessions,
      previousClose: meta.previousClose,
    });
  } else {
    stage.innerHTML = renderChartSvg(points, {
      up,
      viewStart: z.start,
      viewEnd: z.start + z.count,
    });
  }
}

function bindZoomableChart(
  canvasEl,
  { key, scope, points, tf, kind, up, sessions = null, previousClose = null }
) {
  if (!canvasEl) return;
  const list = points || [];
  const len = list.length;
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
  });
  ensureChartZoom(key, scope, len, tf, kind);
  const z = state.chartZoom[key];
  const full = defaultChartZoom(len, tf, kind);
  const zoomed = z.count < len || z.start !== full.start;
  canvasEl.innerHTML = `
    <div class="chart-zoom" data-zoom-key="${escapeHtml(key)}" tabindex="0" aria-label="可缩放图表：触控板捏合或使用角落按钮">
      ${chartZoomControlsHtml(zoomed)}
      <div class="chart-zoom-stage"></div>
    </div>
  `;
  paintZoomableChart(key);

  const zoomRoot = canvasEl.querySelector(".chart-zoom");
  if (!zoomRoot) return;

  zoomRoot.addEventListener("click", (event) => {
    const btn = event.target.closest("[data-zoom-act]");
    if (!btn || !zoomRoot.contains(btn)) return;
    const act = btn.getAttribute("data-zoom-act");
    if (act === "in") zoomChartWindow(key, CHART_ZOOM_STEP, 0.85);
    else if (act === "out") zoomChartWindow(key, 1 / CHART_ZOOM_STEP, 0.85);
    else if (act === "reset") zoomChartWindow(key, 1);
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

function holdingSparkSvg(holding, tf) {
  const want = tf || "intraday";
  const series = holding?.series?.[want];
  // Sector list always prefers 24h points even if other TF series exist
  const points =
    want === "intraday"
      ? series?.points ||
        holding?.series?.intraday?.points ||
        holding?.points ||
        []
      : series?.points || holding?.points || [];
  const kind = series?.chart || (want === "intraday" ? "line" : "candle");
  // Color the spark from the same series used for the path (desk 分时),
  // not the day quote %, so left/middle intraday shapes stay consistent.
  const pct =
    want === "intraday"
      ? series?.change_pct != null
        ? series.change_pct
        : holding?.series?.intraday?.change_pct != null
          ? holding.series.intraday.change_pct
          : points.length >= 2
            ? ((Number(points[points.length - 1].v ?? points[points.length - 1].c) -
                Number(points[0].v ?? points[0].c)) /
                Math.abs(Number(points[0].v ?? points[0].c) || 1)) *
              100
            : holding?.change_pct
      : series?.change_pct != null
        ? series.change_pct
        : holdingTfPct(holding, want) != null
          ? holdingTfPct(holding, want)
          : holding?.change_pct;
  const up = !(typeof pct === "number" && pct < 0);
  if (kind === "candle") {
    return (
      miniCandleSvg(points, { width: 120, height: 30 }) || pctSparkBar(pct)
    );
  }
  const sparkPoints = points.map((p) => {
    if (!p) return p;
    if (p.c != null && (p.o != null || p.h != null || p.l != null)) {
      return { t: p.t, v: p.c };
    }
    if (p.c != null && p.v == null) return { t: p.t, v: p.c };
    return p;
  });
  const path = sparklinePath(sparkPoints, 120, 30, 2);
  if (!path) return pctSparkBar(pct);
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
      '<p class="chart-placeholder">添加持仓后，右侧将显示分时 / K 线详情</p>';
    return;
  }

  const series = board.series?.[tf];
  const points = series?.points || board.points || [];
  const pct =
    series?.change_pct != null ? series.change_pct : board.change_pct;
  const up = !(typeof pct === "number" && pct < 0);
  const pctText =
    typeof pct === "number" ? `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%` : "—";
  const kind =
    series?.chart || meta.chart || (tf === "intraday" ? "line" : "candle");
  const stats = seriesStats(points, kind);
  const price = board.price != null ? board.price : stats.last;

  els.portfolioChart.classList.remove("is-empty");
  els.portfolioChart.classList.toggle("is-preview", Boolean(preview));
  els.portfolioChart.innerHTML = `
    <div class="chart-head">
      <h3>${escapeHtml(board.label || board.symbol || "")} · ${escapeHtml(
        board.symbol || ""
      )}${preview ? '<span class="preview-tag">预览</span>' : ""}</h3>
      <span class="range chg ${up ? "up" : "down"}">${escapeHtml(
        meta.label || ""
      )} · 区间 ${pctText}</span>
    </div>
    <div class="portfolio-stats" aria-label="区间读数">
      <span><span class="k">现价</span><span class="v ${
        up ? "up" : "down"
      }">${escapeHtml(price == null ? "—" : formatNumber(price, ""))}</span></span>
      <span><span class="k">开</span><span class="v">${escapeHtml(
        stats.open == null ? "—" : formatNumber(stats.open, "")
      )}</span></span>
      <span><span class="k">高</span><span class="v up">${escapeHtml(
        stats.high == null ? "—" : formatNumber(stats.high, "")
      )}</span></span>
      <span><span class="k">低</span><span class="v down">${escapeHtml(
        stats.low == null ? "—" : formatNumber(stats.low, "")
      )}</span></span>
      <span><span class="k">量</span><span class="v">${escapeHtml(
        formatCompact(stats.volume)
      )}</span></span>
    </div>
    <div class="chart-canvas" data-zoom-host="portfolio"></div>
    <div class="chart-foot">${escapeHtml(
      series?.blurb || meta.blurb || ""
    )} · 红涨绿跌 · 延迟报价 · 捏合缩放</div>
  `;
  bindZoomableChart(els.portfolioChart.querySelector("[data-zoom-host]"), {
    key: "portfolio",
    scope: `${board.symbol || ""}:${tf}`,
    points,
    tf,
    kind,
    up,
    sessions: series?.sessions || null,
    previousClose: series?.previous_close ?? null,
  });
}

function holdingsCountNote(data, meta) {
  const n = (data?.holdings || []).length;
  if (!n) return "打开「管理持仓」添加代码；支持导出 / 导入备份";
  return `全部 ${n} 只 · ${meta?.label || ""} · 悬停预览 · 点击锁定 · ↑↓ 切换`;
}

function renderPortfolio(data) {
  state.portfolio = data || null;
  const holdings = data?.holdings || [];
  const selected = data?.selected || holdings[0]?.symbol || "";
  const tf = state.portfolioTf || data?.default_tf || "intraday";
  const meta =
    (data?.timeframes || []).find((t) => t.id === tf) || {
      id: tf,
      label: tf,
    };
  const previewSym = state.portfolioPreview;

  if (els.portfolioBlurb) {
    els.portfolioBlurb.textContent =
      data?.note ||
      `自定义股票 · 云端同步 · 最多 ${data?.max_holdings || 20} 只 · 红涨绿跌`;
  }

  updatePortfolioSortMarks();

  if (els.holdingRail) {
    if (!holdings.length) {
      els.holdingRail.innerHTML =
        '<p class="empty">还没有持仓，点右上角「管理持仓」添加美股代码。</p>';
    } else {
      const rows = sortedHoldings(holdings, tf);
      els.holdingRail.innerHTML = rows
        .map((h) => {
          const pct = holdingTfPct(h, tf);
          const cls =
            pct == null || Number.isNaN(pct) ? "" : pct >= 0 ? "up" : "down";
          const pctText =
            pct == null || Number.isNaN(pct)
              ? "—"
              : `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
          const active = h.symbol === selected ? "is-active" : "";
          const preview =
            previewSym && h.symbol === previewSym && h.symbol !== selected
              ? "is-preview"
              : "";
          return `
            <button type="button" class="holding-row ${cls} ${active} ${preview}" data-holding="${escapeHtml(
              h.symbol
            )}" role="option" aria-selected="${
              h.symbol === selected ? "true" : "false"
            }">
              <span class="meta">
                <span class="nm">${escapeHtml(h.name || h.label || h.symbol)}</span>
                <span class="sym">${escapeHtml(h.symbol)}</span>
              </span>
              <span class="spark-wrap">${holdingSparkSvg(h, tf)}</span>
              <span class="price ${cls}">${
                h.price == null ? "—" : formatNumber(h.price, "")
              }</span>
              <span class="chg ${cls}">${pctText}</span>
            </button>
          `;
        })
        .join("");
    }
  }
  if (els.portfolioTfNote) {
    els.portfolioTfNote.textContent = holdingsCountNote(data, meta);
  }
  renderPortfolioChart();
  renderPortfolioFocus(data);
}

async function selectPortfolioSymbol(symbol, { quiet = false } = {}) {
  if (!symbol || state.portfolioSelectBusy) return;
  if (symbol === state.portfolio?.selected) {
    state.portfolioPreview = null;
    renderPortfolio(state.portfolio);
    if (PAGE === "desk") loadHoldingIntel({ symbol });
    return;
  }
  state.portfolioSelectBusy = true;
  try {
    const data = await portfolioPost("/api/portfolio/select", { symbol });
    state.portfolioPreview = null;
    renderPortfolio(data.portfolio);
    if (PAGE === "desk") loadHoldingIntel({ symbol });
  } catch (err) {
    if (!quiet && els.portfolioBlurb) {
      els.portfolioBlurb.textContent = `切换失败：${err.message || err}`;
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
    return res.portfolio || data;
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
    syncHoldingSymbolsFromPortfolio(data);
    renderPortfolio(data);
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
  if (state.holdingSymbols && !force && state.portfolio) {
    return state.holdingSymbols;
  }
  try {
    const res = await fetch("/api/portfolio", { credentials: "same-origin" });
    if (res.status === 401) {
      state.holdingSymbols = new Set();
      return state.holdingSymbols;
    }
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    return syncHoldingSymbolsFromPortfolio(data);
  } catch {
    if (!state.holdingSymbols) state.holdingSymbols = new Set();
    return state.holdingSymbols;
  }
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
  if (state.holdingToggleBusy) return;
  state.holdingToggleBusy = true;
  const held = isInHoldings(sym);
  try {
    const data = held
      ? await portfolioPost("/api/portfolio/remove", { symbol: sym })
      : await portfolioPost("/api/portfolio/add", {
          symbol: sym,
          name: name || "",
        });
    syncHoldingSymbolsFromPortfolio(data.portfolio);
    if (PAGE === "desk") {
      const portfolio = await ensurePortfolioSelection(data.portfolio);
      renderPortfolio(portfolio);
      loadPortfolio({ refresh: false });
    } else if (PAGE === "sectors") {
      renderSectorPicks(state.sectors || {});
    }
    setStatus(
      held
        ? `已从持仓移除 ${sym}`
        : `已加入持仓 ${data.resolved?.name || name || sym}（${sym}）`
    );
  } catch (err) {
    setStatus(`${held ? "移除" : "加入"}失败：${err.message || err}`);
  } finally {
    state.holdingToggleBusy = false;
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

function holdingIntelCardHtml(item) {
  const titleZh = item.title_zh || item.title || "";
  const titleEn = item.title || "";
  const showEn = titleEn && titleEn !== titleZh;
  const matches = (item.holding_matches || []).join(" · ");
  const isBearish = item.sentiment === "bearish";
  const isBullish = item.sentiment === "bullish";
  const logic =
    item.sentiment_logic ||
    item.brief_zh ||
    item.summary ||
    "";
  return `
    <a class="holding-intel-card ${isBearish ? "is-bearish" : ""} ${
      isBullish ? "is-bullish" : ""
    }" href="${escapeHtml(item.url || "#")}" target="_blank" rel="noopener noreferrer">
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
      <h3>${escapeHtml(titleZh)}</h3>
      ${showEn ? `<p class="en">${escapeHtml(titleEn)}</p>` : ""}
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

async function loadHoldingIntel({ refresh = false, symbol } = {}) {
  if (!els.holdingIntelList && !els.holdingIntelChips) return null;
  if (!AUTHED) return null;
  const filter =
    symbol !== undefined ? symbol || "" : state.holdingFilter || "";
  state.holdingFilter = filter;
  if (els.holdingIntelList) {
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
          const titleZh = item.title_zh || item.title || "";
          const titleEn = item.title || "";
          const showEn = titleEn && titleEn !== titleZh;
          return `
            <a class="watch-hit-card" href="${item.url}" target="_blank" rel="noopener noreferrer">
              <div class="watch-hit-meta">
                <span class="chip ${item.sentiment || "neutral"}">${escapeHtml(
                  item.sentiment_label || "中性"
                )}</span>
                <span class="chip watch">盯盘:${escapeHtml(keys)}</span>
              </div>
              <p class="watch-hit-zh">${escapeHtml(titleZh)}</p>
              ${showEn ? `<p class="watch-hit-en">${escapeHtml(titleEn)}</p>` : ""}
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
  const titleZh = item.title_zh || item.title || "";
  const titleEn = item.title || "";
  const showEn = titleEn && titleEn !== titleZh;
  const factors = (item.sentiment_factors || []).join("、");
  const metaBits = [
    item.source || "",
    item.published ? formatClock(item.published) : "",
  ].filter(Boolean);
  return `
    <a class="spotlight-card" href="${item.url || "#"}" target="_blank" rel="noopener noreferrer">
      ${verdictBadge(item)}
      <h3>${escapeHtml(titleZh)}</h3>
      ${showEn ? `<p class="story-title-en">${escapeHtml(titleEn)}</p>` : ""}
      <p>${escapeHtml(item.sentiment_logic || item.sentiment_reason || item.brief_zh || "")}</p>
      ${factors ? `<p>因子：${escapeHtml(factors)}</p>` : ""}
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
        const titleZh = d.title_zh || d.title || "";
        const titleEn = d.title || "";
        const showEn = titleEn && titleEn !== titleZh;
        const href = d.url || "#";
        return `
          <li>
            <a href="${escapeHtml(href)}" target="_blank" rel="noopener noreferrer">
              <span class="driver-title">${escapeHtml(titleZh)}</span>
              ${
                showEn
                  ? `<span class="driver-en">${escapeHtml(titleEn)}</span>`
                  : ""
              }
            </a>
            <div class="driver-meta">
              <span class="chip bearish">${escapeHtml(
                d.sentiment_label || "利空"
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
      const titleZh = event.title_zh || event.title || "";
      const titleEn = event.title || "";
      const showEn = titleEn && titleEn !== titleZh;
      const keys = (event.keywords || [])
        .slice(0, 4)
        .map((k) => `<span class="key-chip">${escapeHtml(k)}</span>`)
        .join("");
      return `
        <button type="button" class="event-card" data-open-event="${escapeHtml(event.id)}">
          <div class="event-card-top">
            <span class="chip ${event.sentiment || "neutral"}">${escapeHtml(
              event.sentiment_label || "中性"
            )}</span>
            <span>${event.count} 条报道</span>
          </div>
          <h3>${escapeHtml(titleZh)}</h3>
          ${showEn ? `<p class="event-en">${escapeHtml(titleEn)}</p>` : ""}
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
          const titleZh = item.title_zh || item.title || "";
          const titleEn = item.title || "";
          const showEn = titleEn && titleEn !== titleZh;
          const eventBtn =
            item.event_id && item.event_count > 1
              ? `<button type="button" class="event-link" data-open-event="${escapeHtml(
                  item.event_id
                )}">同事件 ${item.event_count}</button>`
              : "";
          return `
            <div class="day-item">
              <div class="day-item-top">
                <span class="chip ${item.sentiment || "neutral"}">${escapeHtml(
                  item.sentiment_label || "中性"
                )}</span>
                <span>${escapeHtml(item.source || "")}</span>
                <time datetime="${item.published || ""}">${relativeTime(item.published)}</time>
                ${eventBtn}
              </div>
              <a href="${item.url}" target="_blank" rel="noopener noreferrer">${escapeHtml(
                titleZh
              )}</a>
              ${showEn ? `<p class="en">${escapeHtml(titleEn)}</p>` : ""}
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
      const isBearish = item.sentiment === "bearish";
      const isBullish = item.sentiment === "bullish";
      const factors = (item.sentiment_factors || []).join("、") || "暂无强因子";
      const logic =
        item.sentiment_logic ||
        `结论：${item.sentiment_label || "中性"}（${Number(item.sentiment_score || 0).toFixed(2)}）`;
      const titleZh = item.title_zh || item.title || "";
      const eventBtn =
        item.event_id && item.event_count > 1
          ? `<button type="button" class="event-link" data-open-event="${escapeHtml(
              item.event_id
            )}">同事件 ${item.event_count} 条</button>`
          : "";
      return `
      <article class="story ${item.watch_hit ? "is-watch" : ""} ${item.holding_hit ? "is-holding" : ""} ${isBearish ? "is-bearish" : ""} ${isBullish ? "is-bullish" : ""}">
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
          <h3>
            <a href="${item.url}" target="_blank" rel="noopener noreferrer">${escapeHtml(titleZh)}</a>
          </h3>
          <p class="story-title-en">${escapeHtml(item.title || "")}</p>
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
  state.portfolioTf = btn.dataset.ptf;
  if (state.portfolio) renderPortfolio(state.portfolio);
  else renderPortfolioChart();
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
    renderPortfolio(state.portfolio);
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
  if (typeof pct !== "number" || Number.isNaN(pct)) return "—";
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
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
      ? `${label} · ${news.length} 条匹配`
      : `${label} · 暂无匹配`;
  }
  if (els.sectorNewsLink) {
    els.sectorNewsLink.href = `/intel?q=${encodeURIComponent(q)}`;
  }
  if (!els.sectorNewsList) return;
  els.sectorNewsList.innerHTML = news.length
    ? news.slice(0, 8).map((item) => spotlightCardHtml(item)).join("")
    : '<p class="empty">暂无该板块匹配新闻。</p>';
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
      els.symbolNewsBlurb.textContent = "点选个股后显示相关情报";
    } else if (!news.length) {
      els.symbolNewsBlurb.textContent = `${name} · 暂无命中标题/正文的情报`;
    } else {
      els.symbolNewsBlurb.textContent = `${name} · ${news.length} 条相关`;
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
    : `<p class="empty">暂无命中 ${escapeHtml(
        sym
      )} 的情报 · <a href="/intel?q=${encodeURIComponent(sym)}">去情报流搜索</a></p>`;
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

  const width = 1000;
  const height = 520;
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
      const showHead = sh > 64 && sw > 70;
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
          const showGHead = grp.h > 42 && grp.w > 50;
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
              const showName = st.w / bodyW > 0.28 && st.h / bodyH > 0.34;
              const showPct = st.w / bodyW > 0.18 && st.h / bodyH > 0.22;
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

  els.sectorMapCanvas.innerHTML = `<div class="sector-map-stage">${html}</div>`;

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
  if (Date.now() - Number(row.at || 0) > 45_000) return null;
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
  const preferred = seriesMap[want];
  const preferredKind =
    preferred?.chart || (want === "intraday" ? "line" : "candle");
  const preferredRaw =
    preferred?.points || (want === "intraday" ? pick?.points || [] : []);
  const preferredPoints =
    preferredKind === "candle"
      ? sanitizeCandleBars(preferredRaw)
      : (preferredRaw || []).filter(Boolean);
  if (preferredPoints.length >= 2) {
    return {
      tf: want,
      series: preferred || { chart: preferredKind, points: preferredRaw },
      points: preferredPoints,
      kind: preferredKind,
    };
  }
  // Candle tabs stay empty when missing — do not silently snap back to 分时.
  if (want !== "intraday") {
    return { tf: want, series: preferred || null, points: [], kind: "candle" };
  }
  // Intraday fallback: any available series so the desk still paints
  const order = ["intraday", "day", "month", "quarter"];
  for (const tf of order) {
    const series = seriesMap[tf];
    const raw = series?.points || (tf === "intraday" ? pick?.points || [] : []);
    const kind = series?.chart || (tf === "intraday" ? "line" : "candle");
    const points =
      kind === "candle" ? sanitizeCandleBars(raw) : (raw || []).filter(Boolean);
    if (points.length >= 2) {
      return { tf, series: series || { chart: kind, points: raw }, points, kind };
    }
  }
  return { tf: want, series: null, points: [], kind: "line" };
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
    tf === "intraday"
      ? ` · ${(series?.session_labels || []).length ? (series.session_labels || []).join("·") : "盘前·盘中·盘后·夜盘"}一体分时`
      : "";
  els.sectorPickChart.innerHTML = `
    <div class="chart-head">
      <h3>${escapeHtml(pick.name || pick.label || "")} · ${escapeHtml(
        pick.symbol || ""
      )}${pick.is_wave ? '<span class="hot-tag">涨势</span>' : ""}</h3>
      <span class="range chg ${up ? "up" : "down"}">${escapeHtml(
        pctText(pct)
      )}</span>
    </div>
    <div class="portfolio-stats" aria-label="区间读数">
      <span><span class="k">现价</span><span class="v ${up ? "up" : "down"}">${escapeHtml(
        pick.price == null ? "—" : formatNumber(pick.price, "")
      )}</span></span>
      <span><span class="k">开</span><span class="v">${escapeHtml(
        stats.open == null ? "—" : formatNumber(stats.open, "")
      )}</span></span>
      <span><span class="k">高</span><span class="v up">${escapeHtml(
        stats.high == null ? "—" : formatNumber(stats.high, "")
      )}</span></span>
      <span><span class="k">低</span><span class="v down">${escapeHtml(
        stats.low == null ? "—" : formatNumber(stats.low, "")
      )}</span></span>
      <span><span class="k">月涨幅</span><span class="v ${pctClass(
        pick.month_change_pct
      )}">${escapeHtml(pctText(pick.month_change_pct))}</span></span>
    </div>
    <div class="chart-canvas" data-zoom-host="sector"></div>
    <div class="chart-foot">红涨绿跌${maNote}${sessionNote} · 所属 ${escapeHtml(
      pick.sector_label || "板块"
    )}${escapeHtml(earnNote)} · 捏合缩放</div>
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
                <span class="quote">
                  <span class="price ${pctClass(pct)}">${escapeHtml(
                    pick.price == null ? "—" : formatNumber(pick.price, "")
                  )}</span>
                  <span class="chg ${pctClass(pct)}">${escapeHtml(pctText(pct))}</span>
                </span>
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
  if (!symbol || symbol === state.sectorSymbol) return;
  const data = state.sectors;
  const pick = (data?.picks || []).find((p) => p.symbol === symbol);
  // Instant local switch when full chart series already loaded
  if (data && pick && pickHasChart(pick)) {
    state.sectorSymbol = symbol;
    data.selected_symbol = symbol;
    data.selected_pick = pick;
    data.selected_earnings = pick.earnings || null;
    data.value_chain = pick.value_chain || data.value_chain;
    data.symbol_news = pick.symbol_news || [];
    syncSectorQuery();
    renderSectorPicks(data);
    setStatus(`已切换 ${pick.name || symbol} · ${pick.sector_label || ""}`);
    return;
  }
  state.sectorSymbol = symbol;
  syncSectorQuery();
  if (els.sectorPickChart) {
    els.sectorPickChart.innerHTML = '<p class="chart-placeholder">加载走势…</p>';
  }
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
  const mapPromise = loadSectorMap({ force });
  try {
    const res = await fetch(`/api/sectors?${params.toString()}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    if (data?.active_sector_id) sectorCachePut(data.active_sector_id, data);
    renderSectorDesk(data);
    syncSectorQuery();
    const hot = (data.hot_sectors || []).map((s) => s.label).slice(0, 2).join("、");
    const n = (data.picks || []).length;
    setStatus(
      `板块已更新${data.cached ? "（缓存）" : ""}${
        data.active_sector?.label ? ` · ${data.active_sector.label}` : ""
      }${n ? ` · ${n} 只成分` : ""}${hot ? ` · 热点 ${hot}` : ""}`
    );
    await mapPromise;
    return data;
  } catch (err) {
    setStatus(`板块加载失败：${err.message || err}`);
    await mapPromise;
    return null;
  } finally {
    if (els.sectorsRefresh) els.sectorsRefresh.disabled = false;
  }
}

function bindSectorDesk() {
  if (PAGE !== "sectors") return;
  els.sectorsRefresh?.addEventListener("click", () => loadSectorDesk({ force: true }));
  els.sectorTfFilters?.querySelectorAll("[data-stf]").forEach((btn) => {
    btn.addEventListener("click", () => {
      const tf = btn.getAttribute("data-stf");
      if (!tf || tf === state.sectorTf) return;
      state.sectorTf = tf;
      renderSectorPicks(state.sectors || {});
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
                  <span class="when">${escapeHtml(row.date || "")} · ${escapeHtml(
                    row.time_zh || ""
                  )}</span>
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

function bootPage() {
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
    loadPortfolio().then(() => {
      const selected = state.portfolio?.selected || "";
      loadHoldingIntel({ symbol: selected || "" });
    });
    setInterval(() => {
      loadPortfolio({ refresh: true });
      loadHoldingIntel({
        symbol: state.holdingFilter || state.portfolio?.selected || "",
      });
    }, 90 * 1000);
  } else if (PAGE === "markets") {
    loadMarketsDesk();
    setInterval(() => loadMarketsDesk(), 90 * 1000);
  } else if (PAGE === "sectors") {
    const params = new URLSearchParams(location.search);
    const qSector = (params.get("sector") || "").trim().toLowerCase();
    const qSymbol = (params.get("symbol") || "").trim().toUpperCase();
    if (qSector) state.sectorId = qSector;
    if (qSymbol) state.sectorSymbol = qSymbol;
    bindSectorDesk();
    refreshHoldingSymbols().finally(() => loadSectorDesk());
    setInterval(() => loadSectorDesk(), 90 * 1000);
  } else if (PAGE === "earnings") {
    bindEarningsDesk();
    loadEarningsDesk();
    setInterval(() => loadEarningsDesk(), 5 * 60 * 1000);
  } else if (PAGE === "intel") {
    readIntelQueryFlags();
    loadIntel();
    setInterval(() => loadIntel(), 5 * 60 * 1000);
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
  saveScrollPosition();
  const url = new URL(href, location.origin);
  const samePath = url.pathname === location.pathname;

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

  location.href = `${url.pathname}${url.hash || ""}`;
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

  window.addEventListener("pagehide", saveScrollPosition);
  window.addEventListener("beforeunload", saveScrollPosition);
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
