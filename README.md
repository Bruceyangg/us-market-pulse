# Pulse Desk · 美股情报台

搜集并呈现最新美股相关情报：市场动态、时政地缘、政策监管、美联储与国债。

## 功能

- **情报流**：聚合美联储、财政部、SEC、白宫、CNBC、MarketWatch 等公开 RSS
- **分类筛选**：市场 / 美联储 / 国债 / 政策监管 / 时政地缘
- **交易台读数**：FRED 公开序列（联邦基金利率、2Y/10Y/30Y 国债、利差、VIX）
- **政策日程**：FOMC 决议、会议纪要、CPI/NFP 等关键节点
- **中文简报**：基于标题主题的中文要点 + 术语提示；并提炼近端主题摘要
- **利多/利空评判**：对每条情报做美股风险偏好启发式打分，并汇总近端情绪
- **定时推送**：按设定时刻推送 Webhook / 邮件简报（也可手动测试或 cron）
- **搜索与刷新**：关键词过滤，支持强制刷新（默认 5 分钟缓存）

## 快速开始

```bash
cd us-market-pulse
uv sync
uv run us-market-pulse
```

电脑浏览器打开 [http://127.0.0.1:8765](http://127.0.0.1:8765)

### 手机访问（同一 Wi-Fi）

服务默认监听 `0.0.0.0:8765`。手机连与电脑相同的 Wi-Fi 后，打开：

```text
http://<电脑局域网IP>:8765
```

启动时终端会打印 Phone 地址；页面底部也会显示。若打不开，检查 macOS「系统设置 → 网络 → 防火墙」是否拦截了 Python/uvicorn。

### 公网分享（任意网络手机/电脑）

**想电脑关机后大家仍能用：部署到云（推荐 Render 免费档）**

仓库已公开：https://github.com/Bruceyangg/us-market-pulse  

一键部署（Render 免费档）：  
https://render.com/deploy?repo=https://github.com/Bruceyangg/us-market-pulse  

用 GitHub 登录 Render → 选 Free → Apply/Deploy。完成后会得到固定网址（如 `https://pulse-desk.onrender.com`）。

说明：Render 免费档闲置后可能休眠，第一次打开偶发要等十几秒。

**临时分享（需本机开着）：** 页面底部点 **开启公网分享**，或：

```bash
uv run pulse-share
```

会生成 `https://xxxx.trycloudflare.com`；本机服务需保持运行，重启后链接会变。

或：

```bash
uv run uvicorn us_market_pulse.app:app --host 0.0.0.0 --reload --port 8765
```

## 定时推送与盯盘

推荐在网页 **推送与盯盘** 面板直接填写并保存（写入 `data/settings.json`）：

- Webhook：支持 **Server酱 / 钉钉 / 飞书 / 企业微信 / Discord**（可自动识别）
- 默认 **每 15 分钟** 推送一次（`push_interval_minutes`，可改）
- 盯盘关键词：命中后会在页面高亮，并进入推送简报的「盯盘命中」区块

也可使用环境变量（优先级高于本地文件），见 `.env.example`。

```bash
uv run pulse-push                 # 立即推送一次
curl -X POST http://127.0.0.1:8765/api/push/test
```

若设置了 `PULSE_PUSH_SECRET`，测试接口需带请求头 `X-Pulse-Secret`。

## API

- `GET /api/intel?category=fed&sentiment=bullish&q=rate&refresh=false`
- `GET /api/push/status`
- `POST /api/push/test`
- `GET /api/health`

## 说明

内容来自公开 RSS 与 FRED CSV；利多/利空为规则引擎启发式判断，仅供研究参考，不构成投资建议。部分源可能因网络或对方站点限制暂时不可用，页面状态栏会提示失败源数量。
