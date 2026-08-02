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
};

const els = {
  status: document.getElementById("status-line"),
  indicators: document.getElementById("indicator-grid"),
  indexGrid: document.getElementById("index-grid"),
  chartGrid: document.getElementById("chart-grid"),
  marketsBlurb: document.getElementById("markets-blurb"),
  chartTfNote: document.getElementById("chart-tf-note"),
  tfFilters: document.getElementById("tf-filters"),
  portfolioBlurb: document.getElementById("portfolio-blurb"),
  holdingRail: document.getElementById("holding-rail"),
  portfolioChart: document.getElementById("portfolio-chart"),
  portfolioTfFilters: document.getElementById("portfolio-tf-filters"),
  portfolioTfNote: document.getElementById("portfolio-tf-note"),
  portfolioAddForm: document.getElementById("portfolio-add-form"),
  portfolioSymbol: document.getElementById("portfolio-symbol"),
  portfolioName: document.getElementById("portfolio-name"),
  portfolioRemove: document.getElementById("btn-portfolio-remove"),
  portfolioRefresh: document.getElementById("btn-portfolio-refresh"),
  portfolioExport: document.getElementById("btn-portfolio-export"),
  portfolioImport: document.getElementById("portfolio-import"),
  agenda: document.getElementById("agenda-rail"),
  agendaBlurb: document.getElementById("agenda-blurb"),
  digest: document.getElementById("digest-line"),
  moodBoard: document.getElementById("mood-board"),
  moodBlurb: document.getElementById("mood-blurb"),
  spotlight: document.getElementById("spotlight-list"),
  spotlightBlurb: document.getElementById("spotlight-blurb"),
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
  const vals = (points || []).map((p) => Number(p.v)).filter((v) => !Number.isNaN(v));
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

function renderChartSvg(points, { up = true } = {}) {
  const width = 320;
  const height = 140;
  const padX = 8;
  const padY = 12;
  const vals = (points || [])
    .map((p) => Number(p.v ?? p.c))
    .filter((v) => !Number.isNaN(v));
  if (vals.length < 2) {
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="暂无走势"><text x="16" y="72" fill="#3a4d63" font-size="13">暂无走势数据</text></svg>`;
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

function renderCandleSvg(points) {
  const width = 320;
  const height = 150;
  const padX = 8;
  const padY = 10;
  const bars = (points || []).filter(
    (p) =>
      p &&
      [p.o, p.h, p.l, p.c].every((n) => n != null && !Number.isNaN(Number(n)))
  );
  if (bars.length < 2) {
    return `<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="暂无K线"><text x="16" y="78" fill="#3a4d63" font-size="13">暂无K线数据</text></svg>`;
  }
  const highs = bars.map((b) => Number(b.h));
  const lows = bars.map((b) => Number(b.l));
  const min = Math.min(...lows);
  const max = Math.max(...highs);
  const span = max - min || 1;
  const slot = (width - padX * 2) / bars.length;
  const bodyW = Math.max(1.5, Math.min(7, slot * 0.62));
  const yOf = (price) => padY + (1 - (price - min) / span) * (height - padY * 2);

  const shapes = bars
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
      const bodyH = Math.max(1.2, Math.abs(yClose - yOpen));
      return `
        <line x1="${x.toFixed(2)}" y1="${yHigh.toFixed(2)}" x2="${x.toFixed(
          2
        )}" y2="${yLow.toFixed(2)}" stroke="${color}" stroke-width="1.2"></line>
        <rect x="${(x - bodyW / 2).toFixed(2)}" y="${top.toFixed(
          2
        )}" width="${bodyW.toFixed(2)}" height="${bodyH.toFixed(
          2
        )}" fill="${color}"></rect>
      `;
    })
    .join("");

  return `
    <svg viewBox="0 0 ${width} ${height}" preserveAspectRatio="none" role="img" aria-label="K线柱状图 红涨绿跌">
      ${shapes}
    </svg>
  `;
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
          ? renderCandleSvg(chart.points || [])
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
          ${svg}
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

function holdingSparkSvg(holding, tf) {
  const series = holding?.series?.[tf];
  const points = series?.points || holding?.points || [];
  const kind = series?.chart || (tf === "intraday" ? "line" : "candle");
  const pct =
    series?.change_pct != null ? series.change_pct : holding?.change_pct;
  const up = !(typeof pct === "number" && pct < 0);
  if (kind === "candle") {
    return miniCandleSvg(points) || `<span class="empty">暂无</span>`;
  }
  const sparkPoints = points.map((p) =>
    p && p.c != null && p.v == null ? { t: p.t, v: p.c } : p
  );
  const path = sparklinePath(sparkPoints, 140, 42, 2);
  if (!path) return `<span class="empty">暂无</span>`;
  const stroke = up ? TAPE_UP : TAPE_DOWN;
  return `<svg class="spark" viewBox="0 0 140 42" preserveAspectRatio="none" aria-hidden="true"><path d="${path}" fill="none" stroke="${stroke}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"></path></svg>`;
}

function renderPortfolioChart() {
  const data = state.portfolio || {};
  const board = data.selected_board;
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
  if (!board) {
    els.portfolioChart.classList.add("is-empty");
    els.portfolioChart.innerHTML =
      '<p class="chart-placeholder">点击左侧持仓，在此查看分时 / K 线详情</p>';
    return;
  }
  const series = board.series?.[tf];
  const points = series?.points || [];
  const pct = series?.change_pct;
  const up = !(typeof pct === "number" && pct < 0);
  const pctText =
    typeof pct === "number" ? `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%` : "—";
  const kind = series?.chart || meta.chart || (tf === "intraday" ? "line" : "candle");
  const svg =
    kind === "candle"
      ? renderCandleSvg(points)
      : renderChartSvg(points, { up });
  els.portfolioChart.classList.remove("is-empty");
  els.portfolioChart.innerHTML = `
    <div class="chart-head">
      <h3>${escapeHtml(board.label || board.symbol || "")} · ${escapeHtml(
        board.symbol || ""
      )}</h3>
      <span class="range chg ${up ? "up" : "down"}">${escapeHtml(
        meta.label || ""
      )} · 区间 ${pctText}</span>
    </div>
    ${svg}
    <div class="chart-foot">${escapeHtml(series?.blurb || meta.blurb || "")} · 现价 ${formatNumber(
      board.price,
      board.unit || ""
    )}</div>
  `;
}

function holdingsCountNote(data, meta) {
  const n = (data?.holdings || []).length;
  if (!n) return "添加持仓后，这里会同时显示全部走势";
  return `全部 ${n} 只持仓 · ${meta?.label || ""}（红涨绿跌）`;
}

function renderPortfolio(data) {
  state.portfolio = data || null;
  const holdings = data?.holdings || [];
  const selected = data?.selected || "";
  const tf = state.portfolioTf || data?.default_tf || "intraday";
  const meta =
    (data?.timeframes || []).find((t) => t.id === tf) || {
      id: tf,
      label: tf,
    };

  if (els.portfolioBlurb) {
    els.portfolioBlurb.textContent =
      data?.note ||
      `自定义股票 · 云端同步 · 最多 ${data?.max_holdings || 20} 只`;
  }

  if (els.holdingRail) {
    if (!holdings.length) {
      els.holdingRail.innerHTML =
        '<p class="empty">还没有持仓，先添加一只美股代码。</p>';
    } else {
      els.holdingRail.innerHTML = holdings
        .map((h) => {
          const series = h.series?.[tf];
          const pct =
            series?.change_pct != null ? series.change_pct : h.change_pct;
          const cls =
            pct == null || Number.isNaN(pct) ? "" : pct >= 0 ? "up" : "down";
          const pctText =
            pct == null || Number.isNaN(pct)
              ? "—"
              : `${pct >= 0 ? "+" : ""}${pct.toFixed(2)}%`;
          return `
            <button type="button" class="holding-row ${
              h.symbol === selected ? "is-active" : ""
            }" data-holding="${escapeHtml(h.symbol)}">
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
}

async function loadPortfolio({ refresh = false } = {}) {
  try {
    const res = await fetch(`/api/portfolio${refresh ? "?refresh=true" : ""}`);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    renderPortfolio(data);
    // mirror for same-browser recovery
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
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

function renderAgenda(events, nextFomc) {
  if (nextFomc) {
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
  if (!summary) {
    els.moodBoard.innerHTML = '<p class="empty">暂无情绪统计</p>';
    return;
  }
  els.moodBlurb.textContent = summary.blurb || "对近端情报做美股风险偏好启发式打分";
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
  if (!settings) return;
  els.cfgWebhook.value = settings.webhook_url || "";
  els.cfgFormat.value = settings.webhook_format || "auto";
  if (els.cfgInterval) {
    els.cfgInterval.value = String(settings.push_interval_minutes ?? 15);
  }
  els.cfgTimes.value = (settings.push_times || []).join(",");
  els.cfgTz.value = settings.push_timezone || "Asia/Shanghai";
  els.cfgEnabled.checked = Boolean(settings.push_enabled);
  els.cfgKeywords.value = (settings.watch_keywords || []).join(",");
}

function renderPush(push) {
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
  els.pushBlurb.textContent = push.enabled
    ? `已启用定时推送：${intervalText}${extraTimes ? `；额外定点 ${extraTimes}` : ""}（${push.timezone}）`
    : "定时推送未启用：勾选并保存后生效";
  els.pushStatus.innerHTML = `
    <div><strong>渠道</strong>：${escapeHtml(channelText)}</div>
    <div><strong>间隔</strong>：${escapeHtml(intervalText)} · ${escapeHtml(push.timezone || "")}</div>
    <div><strong>额外定点</strong>：${escapeHtml(extraTimes || "无")}</div>
    <div><strong>盯盘词</strong>：${escapeHtml((push.watch_keywords || []).join("、") || "未设置")}</div>
    <div><strong>最近一次</strong>：${escapeHtml(lastText)}</div>
  `;
  els.pushTest.disabled = !push.webhook_configured && !push.email_configured;
}

function renderWatchHits(hits) {
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
  els.spotlight.innerHTML = rows
    .map((item) => {
      const titleZh = item.title_zh || item.title || "";
      const titleEn = item.title || "";
      const showEn = titleEn && titleEn !== titleZh;
      const factors = (item.sentiment_factors || []).join("、");
      return `
        <a class="spotlight-card" href="${item.url}" target="_blank" rel="noopener noreferrer">
          ${verdictBadge(item)}
          <h3>${escapeHtml(titleZh)}</h3>
          ${showEn ? `<p class="story-title-en">${escapeHtml(titleEn)}</p>` : ""}
          <p>${escapeHtml(item.sentiment_logic || item.sentiment_reason || "")}</p>
          ${factors ? `<p>因子：${escapeHtml(factors)}</p>` : ""}
        </a>
      `;
    })
    .join("");
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
    .map((day) => {
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
      return `
        <div class="day-bucket">
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
      <article class="story ${item.watch_hit ? "is-watch" : ""} ${isBearish ? "is-bearish" : ""} ${isBullish ? "is-bullish" : ""}">
        <div class="story-top">
          <span class="chip ${item.category}">${categoryName(item.category)}</span>
          ${watchChip}
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

async function loadIntel({ force = false } = {}) {
  const params = new URLSearchParams({
    category: state.category,
    sentiment: state.sentiment,
    sort: state.sort,
    q: state.q,
  });
  if (state.watchOnly) params.set("watch_only", "true");
  if (force) params.set("refresh", "true");

  els.status.textContent = force ? "正在强制刷新…" : "同步情报源中…";
  els.refresh.disabled = true;

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

    renderMarkets(data.markets);
    renderIndicators(data.indicators);
    renderAgenda(data.calendar, data.next_fomc);
    renderDigest(data.digest);
    renderMood(data.sentiment_summary);
    renderLiveBriefing(data.live_briefing);
    renderSpotlight(data.bearish_spotlight);
    renderBriefStrip(data);
    renderEventThreads(data.event_threads);
    renderDayTimeline(data.timeline);
    renderPush(data.push);
    renderWatchHits(data.watch_hits);
    renderFeed(data.items);
    const sortNote =
      state.sort === "bearish" ? " · 利空优先" : state.sort === "bullish" ? " · 利多优先" : " · 最新优先";
    els.blurb.textContent =
      (CATEGORY_LABELS[state.category] || CATEGORY_LABELS.all) + sortNote;

    const when = data.fetched_at
      ? new Date(data.fetched_at * 1000).toLocaleTimeString("zh-CN", {
          hour: "2-digit",
          minute: "2-digit",
        })
      : "";
    const cacheNote = data.cached ? "缓存" : "实时";
    const errNote = data.errors?.length ? ` · ${data.errors.length} 个源暂不可用` : "";
    const watchNote = data.watch_hits?.length ? ` · 盯盘 ${data.watch_hits.length}` : "";
    els.status.textContent = `${cacheNote}更新 ${when} · ${data.count} 条${watchNote}${errNote}`;
  } catch (err) {
    console.error(err);
    els.status.textContent = "同步失败，请检查网络后重试";
    els.feed.innerHTML =
      '<p class="error-note">情报流加载失败。确认服务已启动，并可以访问外网 RSS / FRED。</p>';
  } finally {
    els.refresh.disabled = false;
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

els.holdingRail?.addEventListener("click", async (event) => {
  const btn = event.target.closest("[data-holding]");
  if (!btn) return;
  const symbol = btn.getAttribute("data-holding");
  try {
    const data = await portfolioPost("/api/portfolio/select", { symbol });
    renderPortfolio(data.portfolio);
  } catch (err) {
    if (els.portfolioBlurb) {
      els.portfolioBlurb.textContent = `切换失败：${err.message || err}`;
    }
  }
});

els.portfolioAddForm?.addEventListener("submit", async (event) => {
  event.preventDefault();
  const symbol = (els.portfolioSymbol?.value || "").trim();
  const name = (els.portfolioName?.value || "").trim();
  if (!symbol) return;
  try {
    const data = await portfolioPost("/api/portfolio/add", { symbol, name });
    if (els.portfolioSymbol) els.portfolioSymbol.value = "";
    if (els.portfolioName) els.portfolioName.value = "";
    state.portfolioTf = "intraday";
    renderPortfolio(data.portfolio);
  } catch (err) {
    if (els.portfolioBlurb) {
      els.portfolioBlurb.textContent = `添加失败：${err.message || err}`;
    }
  }
});

els.portfolioRemove?.addEventListener("click", async () => {
  const symbol = state.portfolio?.selected;
  if (!symbol) return;
  if (!confirm(`确定删除持仓 ${symbol}？`)) return;
  try {
    const data = await portfolioPost("/api/portfolio/remove", { symbol });
    renderPortfolio(data.portfolio);
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
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ holdings, selected }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    renderPortfolio(data.portfolio);
  } catch (err) {
    if (els.portfolioBlurb) {
      els.portfolioBlurb.textContent = `导入失败：${err.message || err}`;
    }
  } finally {
    event.target.value = "";
  }
});

els.filters.addEventListener("click", (event) => {
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

els.sortFilters.addEventListener("click", (event) => {
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

els.sentimentFilters.addEventListener("click", (event) => {
  const watchBtn = event.target.closest("[data-watch]");
  if (watchBtn) {
    state.watchOnly = !state.watchOnly;
    watchBtn.classList.toggle("is-active", state.watchOnly);
    watchBtn.setAttribute("aria-selected", state.watchOnly ? "true" : "false");
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

els.searchForm.addEventListener("submit", (event) => {
  event.preventDefault();
  state.q = els.searchInput.value.trim();
  loadIntel();
});

let searchTimer;
els.searchInput.addEventListener("input", () => {
  clearTimeout(searchTimer);
  searchTimer = setTimeout(() => {
    state.q = els.searchInput.value.trim();
    loadIntel();
  }, 320);
});

els.refresh.addEventListener("click", () => loadIntel({ force: true }));

els.saveSettings.addEventListener("click", async () => {
  els.saveSettings.disabled = true;
  els.pushStatus.textContent = "正在保存设置…";
  try {
    const body = {
      webhook_url: els.cfgWebhook.value.trim(),
      webhook_format: els.cfgFormat.value,
      push_interval_minutes: Number(els.cfgInterval?.value || 15),
      push_times: els.cfgTimes.value,
      push_timezone: els.cfgTz.value.trim() || "Asia/Shanghai",
      push_enabled: els.cfgEnabled.checked,
      watch_keywords: els.cfgKeywords.value,
    };
    const res = await fetch("/api/settings", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
    renderPush(data.push);
    els.pushStatus.innerHTML =
      `<div><strong>已保存</strong>到本地配置。${els.pushStatus.innerHTML}</div>`;
    await loadIntel({ force: true });
  } catch (err) {
    els.pushStatus.textContent = `保存失败：${err.message || err}`;
  } finally {
    els.saveSettings.disabled = false;
  }
});

els.pushTest.addEventListener("click", async () => {
  els.pushTest.disabled = true;
  els.pushStatus.textContent = "正在发送测试推送…";
  try {
    const headers = { "Content-Type": "application/json" };
    const secret = window.localStorage.getItem("PULSE_PUSH_SECRET");
    if (secret) headers["X-Pulse-Secret"] = secret;
    const res = await fetch("/api/push/test", { method: "POST", headers });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      throw new Error(data.detail || `HTTP ${res.status}`);
    }
    els.pushStatus.textContent = data.ok
      ? `测试推送成功：${(data.channels || []).join(", ")}`
      : `推送失败：${data.error || "未知错误"}`;
    loadIntel();
  } catch (err) {
    els.pushStatus.textContent = `推送失败：${err.message || err}`;
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

loadIntel();
loadPortfolio();
loadAccessTip();
setInterval(() => loadIntel(), 5 * 60 * 1000);
setInterval(() => loadPortfolio({ refresh: true }), 90 * 1000);
