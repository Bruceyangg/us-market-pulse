#!/usr/bin/env node
/**
 * Pulse Desk design intro deck — characteristics + logic diagrams.
 */
const pptxgen = require("pptxgenjs");
const path = require("path");
const os = require("os");
const ShapeType = new pptxgen().ShapeType;

const OUT_DOCS = path.join(__dirname, "Pulse-Desk-网页设计介绍.pptx");
const OUT_DESKTOP = path.join(
  os.homedir(),
  "Desktop",
  "stock网页设计",
  "Pulse-Desk-网页设计介绍.pptx",
);
const OUT = OUT_DOCS;

// Trading-desk palette (红涨绿跌, not generic purple)
const C = {
  bg: "0A1018",
  bgSoft: "121A26",
  panel: "16202E",
  ink: "EEF3F8",
  soft: "9BB0C6",
  line: "2A3A4F",
  sky: "6AA8D4",
  up: "D92B2B",
  down: "2ECF9A",
  amber: "E0A34A",
  white: "FFFFFF",
};

function addBg(slide) {
  slide.addShape(ShapeType.rect, {
    x: 0, y: 0, w: 10, h: 5.625,
    fill: { color: C.bg },
  });
  // subtle top glow bar
  slide.addShape(ShapeType.rect, {
    x: 0, y: 0, w: 10, h: 0.06,
    fill: { color: C.sky },
  });
}

function footer(slide, n, total) {
  slide.addText("Pulse Desk · 设计特点与逻辑", {
    x: 0.4, y: 5.28, w: 7, h: 0.24,
    fontSize: 10, color: C.soft, fontFace: "Arial", margin: 0,
  });
  slide.addText(`${n} / ${total}`, {
    x: 8.4, y: 5.28, w: 1.2, h: 0.24,
    fontSize: 10, color: C.soft, fontFace: "Arial", align: "right", margin: 0,
  });
}

function sectionTitle(slide, title, sub) {
  slide.addText(title, {
    x: 0.45, y: 0.28, w: 9.1, h: 0.42,
    fontSize: 24, bold: true, color: C.ink, fontFace: "Arial", margin: 0,
  });
  if (sub) {
    slide.addText(sub, {
      x: 0.45, y: 0.7, w: 9.1, h: 0.3,
      fontSize: 12, color: C.soft, fontFace: "Arial", margin: 0,
    });
  }
}

function card(slide, x, y, w, h, opts = {}) {
  slide.addShape(ShapeType.roundRect, {
    x, y, w, h,
    fill: { color: opts.fill || C.panel },
    rectRadius: 0.1,
    line: { color: opts.line || C.line, width: 1 },
  });
}

async function main() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9";
  pres.author = "Pulse Desk";
  pres.title = "Pulse Desk 网页设计介绍";
  const TOTAL = 11;

  // 1 Cover
  {
    const s = pres.addSlide();
    addBg(s);
    s.addShape(ShapeType.ellipse, {
      x: 7.2, y: -0.8, w: 4.2, h: 4.2,
      fill: { color: "1A3048" },
    });
    s.addShape(ShapeType.ellipse, {
      x: -1.2, y: 3.2, w: 3.6, h: 3.6,
      fill: { color: "0F2A24" },
    });
    s.addText("US MARKET PULSE", {
      x: 0.6, y: 1.35, w: 8, h: 0.3,
      fontSize: 12, color: C.sky, fontFace: "Arial", bold: true,
      charSpacing: 4, margin: 0,
    });
    s.addText("Pulse Desk", {
      x: 0.6, y: 1.75, w: 8, h: 0.7,
      fontSize: 40, bold: true, color: C.ink, fontFace: "Arial", margin: 0,
    });
    s.addText("网页设计特点与逻辑图", {
      x: 0.6, y: 2.5, w: 8, h: 0.45,
      fontSize: 22, color: C.soft, fontFace: "Arial", margin: 0,
    });
    s.addText("红涨绿跌  ·  持仓≡板块  ·  Yahoo 1D 分时  ·  日/月/季后台升级  ·  1 秒刷新", {
      x: 0.6, y: 3.3, w: 8.5, h: 0.35,
      fontSize: 14, color: C.ink, fontFace: "Arial", margin: 0,
    });
    s.addShape(ShapeType.roundRect, {
      x: 0.6, y: 3.9, w: 1.15, h: 0.38,
      fill: { color: C.up }, rectRadius: 0.06,
    });
    s.addText("+7.85%", {
      x: 0.6, y: 3.9, w: 1.15, h: 0.38,
      fontSize: 12, bold: true, color: C.white, fontFace: "Arial",
      align: "center", valign: "middle", margin: 0,
    });
    s.addShape(ShapeType.roundRect, {
      x: 1.9, y: 3.9, w: 1.15, h: 0.38,
      fill: { color: C.down }, rectRadius: 0.06,
    });
    s.addText("-0.86%", {
      x: 1.9, y: 3.9, w: 1.15, h: 0.38,
      fontSize: 12, bold: true, color: C.white, fontFace: "Arial",
      align: "center", valign: "middle", margin: 0,
    });
    s.addText("https://us-market-pulse-6sqa.onrender.com", {
      x: 0.6, y: 4.7, w: 8, h: 0.28,
      fontSize: 12, color: C.sky, fontFace: "Arial", margin: 0,
    });
    s.addText("?v=20260806e15 · SW v98 · 2026-08-06", {
      x: 0.6, y: 5.05, w: 8, h: 0.25,
      fontSize: 11, color: C.soft, fontFace: "Arial", margin: 0,
    });
  }

  // 2 Positioning
  {
    const s = pres.addSlide();
    addBg(s);
    sectionTitle(s, "产品定位", "个人美股交易情报台 — 不是花哨仪表盘");
    footer(s, 2, TOTAL);
    const steps = [
      { n: "01", t: "点选个股", d: "持仓 / 板块成分一键切换" },
      { n: "02", t: "看分时 / K 线", d: "Yahoo 1D 盘前到盘后" },
      { n: "03", t: "读财报与产业链", d: "右侧情报同屏对照" },
      { n: "04", t: "+/− 管持仓", d: "即时反馈，不卡行情" },
    ];
    steps.forEach((it, i) => {
      const x = 0.45 + i * 2.35;
      card(s, x, 1.35, 2.2, 3.2);
      s.addText(it.n, {
        x: x + 0.18, y: 1.6, w: 1.8, h: 0.4,
        fontSize: 20, bold: true, color: C.sky, fontFace: "Arial", margin: 0,
      });
      s.addText(it.t, {
        x: x + 0.18, y: 2.3, w: 1.85, h: 0.55,
        fontSize: 16, bold: true, color: C.ink, fontFace: "Arial", margin: 0,
      });
      s.addText(it.d, {
        x: x + 0.18, y: 3.0, w: 1.85, h: 1.0,
        fontSize: 12, color: C.soft, fontFace: "Arial", margin: 0,
      });
    });
  }

  // 3 Principles
  {
    const s = pres.addSlide();
    addBg(s);
    sectionTitle(s, "六条设计硬原则", "修改产品时不可破坏");
    footer(s, 3, TOTAL);
    const items = [
      { t: "红涨绿跌", d: "A 股习惯配色 #D92B2B / #2ECF9A", c: C.up },
      { t: "持仓 ≡ 板块", d: "同一交易台、同一渲染与刷新路径", c: C.sky },
      { t: "Yahoo 1D 分时", d: "美东 04:00–20:00 + 昨收虚线", c: C.amber },
      { t: "先画后取", d: "乐观 UI，按钮不卡网络", c: C.down },
      { t: "一屏一焦点", d: "中间图是主舞台，TF 只重绘图", c: C.sky },
      { t: "源可降级", d: "CNBC → Yahoo → Nasdaq 回退", c: C.amber },
    ];
    items.forEach((it, i) => {
      const col = i % 3;
      const row = Math.floor(i / 3);
      const x = 0.45 + col * 3.15;
      const y = 1.25 + row * 1.85;
      card(s, x, y, 3.0, 1.65);
      s.addShape(ShapeType.rect, {
        x: x, y: y, w: 0.1, h: 1.65,
        fill: { color: it.c },
      });
      s.addText(it.t, {
        x: x + 0.28, y: y + 0.35, w: 2.5, h: 0.4,
        fontSize: 16, bold: true, color: C.ink, fontFace: "Arial", margin: 0,
      });
      s.addText(it.d, {
        x: x + 0.28, y: y + 0.85, w: 2.5, h: 0.5,
        fontSize: 12, color: C.soft, fontFace: "Arial", margin: 0,
      });
    });
  }

  // 4 IA
  {
    const s = pres.addSlide();
    addBg(s);
    sectionTitle(s, "信息架构", "顶栏导航 · 六大工作台");
    footer(s, 4, TOTAL);
    const pages = [
      { t: "持仓", d: "个人交易台", hot: true },
      { t: "市场", d: "指数与宏观" },
      { t: "板块", d: "热图+成分台", hot: true },
      { t: "财报", d: "日历筛选" },
      { t: "情报", d: "RSS / 战争台" },
      { t: "设置", d: "推送与账户" },
    ];
    pages.forEach((p, i) => {
      const x = 0.45 + i * 1.55;
      card(s, x, 1.4, 1.45, 1.7, { fill: p.hot ? "1A2A3A" : C.panel, line: p.hot ? C.sky : C.line });
      s.addText(p.t, {
        x: x + 0.08, y: 1.75, w: 1.3, h: 0.4,
        fontSize: 16, bold: true, color: C.ink, align: "center", fontFace: "Arial", margin: 0,
      });
      s.addText(p.d, {
        x: x + 0.08, y: 2.3, w: 1.3, h: 0.5,
        fontSize: 11, color: C.soft, align: "center", fontFace: "Arial", margin: 0,
      });
    });
    card(s, 0.45, 3.45, 9.1, 1.35);
    s.addText("技术栈", {
      x: 0.7, y: 3.65, w: 2, h: 0.3,
      fontSize: 12, bold: true, color: C.sky, fontFace: "Arial", margin: 0,
    });
    s.addText("FastAPI + Jinja2 页面壳  ·  原生 JS/CSS（单文件 app.js）  ·  Render 部署  ·  PWA / Service Worker", {
      x: 0.7, y: 4.05, w: 8.5, h: 0.45,
      fontSize: 14, color: C.ink, fontFace: "Arial", margin: 0,
    });
  }

  // 5 Three-pane desk
  {
    const s = pres.addSlide();
    addBg(s);
    sectionTitle(s, "交易台三栏布局", "持仓页与板块页共用同一套结构与逻辑");
    footer(s, 5, TOTAL);

    // left
    card(s, 0.4, 1.25, 2.7, 3.6);
    s.addText("左 · 列表", {
      x: 0.55, y: 1.4, w: 2.4, h: 0.32,
      fontSize: 13, bold: true, color: C.sky, fontFace: "Arial", margin: 0,
    });
    ["LRCX  收盘+7.85%", "实时 -0.86%  盘前", "AVGO  …", "MU  …"].forEach((t, i) => {
      s.addText(t, {
        x: 0.6, y: 1.95 + i * 0.55, w: 2.3, h: 0.4,
        fontSize: 12, color: i === 0 ? C.up : C.soft, fontFace: "Arial", margin: 0,
      });
    });

    // center
    card(s, 3.25, 1.25, 3.9, 3.6);
    s.addText("中 · 分时 / K 线", {
      x: 3.4, y: 1.4, w: 3.5, h: 0.32,
      fontSize: 13, bold: true, color: C.sky, fontFace: "Arial", margin: 0,
    });
    s.addText("分时  日  月  季", {
      x: 3.4, y: 1.8, w: 3.5, h: 0.28,
      fontSize: 11, color: C.soft, fontFace: "Arial", margin: 0,
    });
    // fake chart line
    s.addShape(ShapeType.roundRect, {
      x: 3.5, y: 2.3, w: 3.4, h: 1.55,
      fill: { color: C.bgSoft }, rectRadius: 0.08,
    });
    s.addText("Yahoo 1D  ·  ET 4AM–8PM  ·  昨收虚线", {
      x: 3.6, y: 2.9, w: 3.2, h: 0.35,
      fontSize: 11, color: C.ink, align: "center", fontFace: "Arial", margin: 0,
    });
    s.addText("下方：个股财报 · 涨跌解读", {
      x: 3.5, y: 4.15, w: 3.4, h: 0.35,
      fontSize: 12, color: C.soft, fontFace: "Arial", margin: 0,
    });

    // right
    card(s, 7.3, 1.25, 2.3, 3.6);
    s.addText("右 · 情报", {
      x: 7.45, y: 1.4, w: 2.0, h: 0.32,
      fontSize: 13, bold: true, color: C.sky, fontFace: "Arial", margin: 0,
    });
    ["业务与产业链", "热点利空", "板块信息流", "财报日历"].forEach((t, i) => {
      s.addText("·  " + t, {
        x: 7.5, y: 2.0 + i * 0.5, w: 1.9, h: 0.35,
        fontSize: 12, color: C.ink, fontFace: "Arial", margin: 0,
      });
    });
  }

  // 6 Dual quote
  {
    const s = pres.addSlide();
    addBg(s);
    sectionTitle(s, "双行报价设计", "收盘涨跌幅 + 实时涨跌幅 + 时段徽章");
    footer(s, 6, TOTAL);

    card(s, 0.5, 1.3, 5.4, 3.5);
    s.addText("列表右侧单元格", {
      x: 0.75, y: 1.5, w: 4.8, h: 0.3,
      fontSize: 12, color: C.sky, fontFace: "Arial", margin: 0,
    });
    s.addText("拉姆研究  LRCX", {
      x: 0.75, y: 1.95, w: 3, h: 0.35,
      fontSize: 16, bold: true, color: C.ink, fontFace: "Arial", margin: 0,
    });
    // close row
    s.addText("317.74", {
      x: 0.75, y: 2.5, w: 1.6, h: 0.4,
      fontSize: 20, bold: true, color: C.up, fontFace: "Arial", margin: 0,
    });
    s.addShape(ShapeType.roundRect, {
      x: 2.5, y: 2.5, w: 1.5, h: 0.42,
      fill: { color: C.up }, rectRadius: 0.06,
    });
    s.addText("+7.85%", {
      x: 2.5, y: 2.5, w: 1.5, h: 0.42,
      fontSize: 14, bold: true, color: C.white, align: "center", valign: "middle",
      fontFace: "Arial", margin: 0,
    });
    s.addText("收盘涨跌幅 · 大字 + 实心胶囊", {
      x: 0.75, y: 3.05, w: 4.8, h: 0.28,
      fontSize: 11, color: C.soft, fontFace: "Arial", margin: 0,
    });
    // rt row
    s.addText("315.00", {
      x: 0.75, y: 3.55, w: 1.4, h: 0.32,
      fontSize: 14, color: C.down, fontFace: "Arial", margin: 0,
    });
    s.addText("-0.86%", {
      x: 2.2, y: 3.55, w: 1.2, h: 0.32,
      fontSize: 14, color: C.down, fontFace: "Arial", margin: 0,
    });
    s.addShape(ShapeType.roundRect, {
      x: 3.5, y: 3.55, w: 0.85, h: 0.32,
      fill: { color: "2A3545" }, rectRadius: 0.04,
    });
    s.addText("盘前", {
      x: 3.5, y: 3.55, w: 0.85, h: 0.32,
      fontSize: 11, color: C.soft, align: "center", valign: "middle",
      fontFace: "Arial", margin: 0,
    });
    s.addText("实时涨跌幅 · 小字红/绿 + 盘前/盘中/盘后/夜盘", {
      x: 0.75, y: 4.1, w: 4.8, h: 0.3,
      fontSize: 11, color: C.soft, fontFace: "Arial", margin: 0,
    });

    card(s, 6.15, 1.3, 3.4, 3.5);
    s.addText("数据字段", {
      x: 6.4, y: 1.55, w: 2.9, h: 0.3,
      fontSize: 13, bold: true, color: C.sky, fontFace: "Arial", margin: 0,
    });
    const fields = [
      "price / change_pct",
      "rt_price / rt_change_pct",
      "session_label",
      "CNBC ExtendedMktQuote",
      "poll 只更新 rt_*",
    ];
    fields.forEach((t, i) => {
      s.addText("▸  " + t, {
        x: 6.4, y: 2.1 + i * 0.45, w: 2.9, h: 0.35,
        fontSize: 12, color: C.ink, fontFace: "Arial", margin: 0,
      });
    });
  }

  // 7 Chart
  {
    const s = pres.addSlide();
    addBg(s);
    sectionTitle(s, "分时图设计特点", "尽量贴近 Yahoo Finance 1D");
    footer(s, 7, TOTAL);
    const feats = [
      { t: "固定时间轴", d: "美东 04:00–20:00，不随首末点拉伸" },
      { t: "会话刻度", d: "开盘 9:30 / 收盘 16:00 等时钟标签" },
      { t: "昨收参考线", d: "previous_close 水平虚线" },
      { t: "1 秒自动刷新", d: "Nasdaq 优先快路径，补点不拆缩放" },
      { t: "多周期一致", d: "分时/日/月/季共用缩放壳；缺K线自动升级" },
      { t: "红涨绿跌线", d: "折线与 K 线实体统一配色" },
    ];
    feats.forEach((it, i) => {
      const col = i % 3;
      const row = Math.floor(i / 3);
      const x = 0.45 + col * 3.15;
      const y = 1.3 + row * 1.75;
      card(s, x, y, 3.0, 1.55);
      s.addText(it.t, {
        x: x + 0.2, y: y + 0.35, w: 2.6, h: 0.35,
        fontSize: 15, bold: true, color: C.ink, fontFace: "Arial", margin: 0,
      });
      s.addText(it.d, {
        x: x + 0.2, y: y + 0.85, w: 2.6, h: 0.45,
        fontSize: 12, color: C.soft, fontFace: "Arial", margin: 0,
      });
    });
  }

  // 8 System architecture
  {
    const s = pres.addSlide();
    addBg(s);
    sectionTitle(s, "系统逻辑总图", "浏览器 → API → 模块 → 外部行情源");
    footer(s, 8, TOTAL);

    const layers = [
      { y: 1.25, title: "浏览器", body: "Jinja 页面壳 · app.js state · SW 缓存 · 1s 分时 poll", c: C.sky },
      { y: 2.25, title: "FastAPI", body: "/api/portfolio*  /api/sectors  /api/quote/intraday  /api/markets…", c: C.amber },
      { y: 3.25, title: "领域模块", body: "portfolio · sectors · quotes · markets · feeds", c: C.down },
      { y: 4.25, title: "外部源", body: "CNBC 日报价 · Yahoo 图表 · Nasdaq 分时 · RSS / FRED", c: C.up },
    ];
    layers.forEach((L, i) => {
      card(s, 0.7, L.y, 8.6, 0.8);
      s.addShape(ShapeType.roundRect, {
        x: 0.85, y: L.y + 0.18, w: 1.5, h: 0.44,
        fill: { color: L.c }, rectRadius: 0.06,
      });
      s.addText(L.title, {
        x: 0.85, y: L.y + 0.18, w: 1.5, h: 0.44,
        fontSize: 12, bold: true, color: C.white, align: "center", valign: "middle",
        fontFace: "Arial", margin: 0,
      });
      s.addText(L.body, {
        x: 2.55, y: L.y + 0.22, w: 6.5, h: 0.4,
        fontSize: 13, color: C.ink, fontFace: "Arial", valign: "middle", margin: 0,
      });
      if (i < layers.length - 1) {
        s.addText("▼", {
          x: 4.7, y: L.y + 0.72, w: 0.5, h: 0.28,
          fontSize: 12, color: C.soft, align: "center", fontFace: "Arial", margin: 0,
        });
      }
    });
  }

  // 9 Key flows
  {
    const s = pres.addSlide();
    addBg(s);
    sectionTitle(s, "关键交互逻辑", "点选快路径 · 分时 1 秒 · 日/月/季升级");
    footer(s, 9, TOTAL);

    card(s, 0.4, 1.25, 4.55, 3.55);
    s.addText("A. 点选个股", {
      x: 0.6, y: 1.45, w: 4.1, h: 0.35,
      fontSize: 15, bold: true, color: C.sky, fontFace: "Arial", margin: 0,
    });
    const flowA = [
      "1  本地切换 selected / board cache",
      "2  paint：高亮 + 中图 + 右侧",
      "3  仅 pickHasChart 才跳过网络",
      "4  后台 /select 或 loadSectorDesk",
      "5  合并响应，保留分时与 K 线",
    ];
    flowA.forEach((t, i) => {
      s.addText(t, {
        x: 0.7, y: 2.0 + i * 0.45, w: 4.0, h: 0.4,
        fontSize: 13, color: C.ink, fontFace: "Arial", margin: 0,
      });
    });

    card(s, 5.15, 1.25, 4.45, 3.55);
    s.addText("B. 分时自动刷新", {
      x: 5.35, y: 1.45, w: 4.0, h: 0.35,
      fontSize: 15, bold: true, color: C.down, fontFace: "Arial", margin: 0,
    });
    const flowB = [
      "1  每 1s（仅分时 TF）",
      "2  GET /api/quote/intraday",
      "3  Nasdaq-first · TTL 1s",
      "4  只更新 rt_* + points",
      "5  patchZoomableIntraday",
    ];
    flowB.forEach((t, i) => {
      s.addText(t, {
        x: 5.45, y: 2.0 + i * 0.45, w: 4.0, h: 0.4,
        fontSize: 13, color: C.ink, fontFace: "Arial", margin: 0,
      });
    });
  }

  // 10 +/- and sources
  {
    const s = pres.addSlide();
    addBg(s);
    sectionTitle(s, "+/− 持仓与数据源", "按钮即时响应 · 源职责矩阵");
    footer(s, 10, TOTAL);

    card(s, 0.4, 1.25, 4.55, 3.55);
    s.addText("C. 板块「+」加入持仓", {
      x: 0.6, y: 1.45, w: 4.1, h: 0.35,
      fontSize: 15, bold: true, color: C.amber, fontFace: "Arial", margin: 0,
    });
    [
      "乐观翻转按钮 + → −",
      "POST /api/portfolio/add",
      "只保存 JSON，立即 stub 返回",
      "禁止等待完整行情构建",
      "失败则回滚按钮状态",
    ].forEach((t, i) => {
      s.addText((i + 1) + "  " + t, {
        x: 0.7, y: 2.0 + i * 0.45, w: 4.0, h: 0.4,
        fontSize: 13, color: C.ink, fontFace: "Arial", margin: 0,
      });
    });

    card(s, 5.15, 1.25, 4.45, 3.55);
    s.addText("数据源职责", {
      x: 5.35, y: 1.45, w: 4.0, h: 0.35,
      fontSize: 15, bold: true, color: C.sky, fontFace: "Arial", margin: 0,
    });
    const src = [
      { k: "CNBC", v: "批量日报价 + 扩展时段" },
      { k: "Yahoo", v: "K 线 / 1D 分时初始包" },
      { k: "Nasdaq", v: "1s 分时 · spark · 回退" },
      { k: "RSS", v: "情报流 / 战争台" },
      { k: "FRED", v: "宏观指标" },
    ];
    src.forEach((it, i) => {
      s.addText(it.k, {
        x: 5.45, y: 2.0 + i * 0.45, w: 1.3, h: 0.35,
        fontSize: 13, bold: true, color: C.amber, fontFace: "Arial", margin: 0,
      });
      s.addText(it.v, {
        x: 6.8, y: 2.0 + i * 0.45, w: 2.5, h: 0.35,
        fontSize: 13, color: C.ink, fontFace: "Arial", margin: 0,
      });
    });
  }

  // 11 Close
  {
    const s = pres.addSlide();
    addBg(s);
    s.addShape(ShapeType.ellipse, {
      x: -1.0, y: -1.0, w: 3.5, h: 3.5,
      fill: { color: "122030" },
    });
    s.addText("设计闭环", {
      x: 0.6, y: 1.5, w: 8.5, h: 0.55,
      fontSize: 28, bold: true, color: C.ink, fontFace: "Arial", margin: 0,
    });
    s.addText("同一视觉语言 · 同一交易台逻辑 · 同一分时刷新路径\n持仓与板块一致 · 快响应 · 可降级 · 可交接", {
      x: 0.6, y: 2.25, w: 8.5, h: 0.9,
      fontSize: 16, color: C.soft, fontFace: "Arial", margin: 0,
    });
    s.addText("在线体验", {
      x: 0.6, y: 3.4, w: 3, h: 0.3,
      fontSize: 12, color: C.sky, fontFace: "Arial", margin: 0,
    });
    s.addText("https://us-market-pulse-6sqa.onrender.com", {
      x: 0.6, y: 3.75, w: 8, h: 0.35,
      fontSize: 16, bold: true, color: C.ink, fontFace: "Arial", margin: 0,
    });
    s.addText("?v=20260806e15 · SW pulse-desk-shell-v98 · 2026-08-06", {
      x: 0.6, y: 4.15, w: 8.5, h: 0.28,
      fontSize: 12, color: C.sky, fontFace: "Arial", margin: 0,
    });
    s.addText("配套：设计手册 PDF/HTML/MD · 完整代码与注解 TXT · Desktop/stock网页设计", {
      x: 0.6, y: 4.5, w: 8.5, h: 0.3,
      fontSize: 12, color: C.soft, fontFace: "Arial", margin: 0,
    });
  }

  await pres.writeFile({ fileName: OUT });
  console.log("wrote", OUT);
  try {
    const fs = require("fs");
    fs.mkdirSync(path.dirname(OUT_DESKTOP), { recursive: true });
    fs.copyFileSync(OUT, OUT_DESKTOP);
    console.log("wrote", OUT_DESKTOP);
  } catch (err) {
    console.warn("desktop copy skipped:", err.message);
  }
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
