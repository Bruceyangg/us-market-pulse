"""Industry-chain desk: keyword → full panorama map with US tickers."""

from __future__ import annotations

from typing import Any


def _co(
    symbol: str,
    name: str,
    *,
    note: str = "",
    sector: str = "technology",
) -> dict[str, Any]:
    return {
        "symbol": symbol.upper(),
        "name": name,
        "note": note,
        "sector": sector,
    }


def _panel(
    pid: str,
    label: str,
    *,
    tone: str,
    branch: str,
    companies: list[dict[str, Any]],
    blurb: str = "",
) -> dict[str, Any]:
    return {
        "id": pid,
        "label": label,
        "tone": tone,
        "branch": branch,
        "blurb": blurb,
        "companies": companies,
    }


SEMICONDUCTOR: dict[str, Any] = {
    "id": "semiconductor",
    "label": "半导体产业链",
    "keywords": [
        "半导体",
        "芯片",
        "晶圆",
        "光刻",
        "集成电路",
        "IC",
        "semiconductor",
        "chip",
        "foundry",
        "fabless",
        "台积电",
        "英伟达",
        "ASML",
    ],
    "blurb": "支撑产业 → 设计 / 制造 / 封测 → 下游应用，定位美股在链上的位置。",
    "top_flow": [
        {"id": "support", "label": "半导体支撑产业", "tone": "support"},
        {"id": "core", "label": "半导体行业", "tone": "core"},
        {"id": "downstream", "label": "下游应用", "tone": "app"},
    ],
    "branches": [
        {
            "parent": "support",
            "tone": "support",
            "nodes": [
                {"id": "materials", "label": "半导体材料"},
                {"id": "equipment", "label": "半导体设备"},
            ],
        },
        {
            "parent": "core",
            "tone": "core",
            "nodes": [
                {"id": "discrete", "label": "分立器件"},
                {"id": "ic", "label": "集成电路"},
            ],
            "pipeline": [
                {"id": "ic_design", "label": "设计"},
                {"id": "ic_fab", "label": "制造"},
                {"id": "osat", "label": "封测"},
            ],
        },
        {
            "parent": "downstream",
            "tone": "app",
            "nodes": [
                {"id": "pc", "label": "PC"},
                {"id": "comms", "label": "通信"},
                {"id": "consumer", "label": "消费电子"},
                {"id": "auto", "label": "汽车电子"},
                {"id": "industrial", "label": "工业医疗"},
                {"id": "iot", "label": "物联网"},
                {"id": "energy", "label": "新能源"},
            ],
        },
    ],
    "panels": [
        _panel(
            "target",
            "靶材",
            tone="support",
            branch="materials",
            blurb="溅射靶材等关键耗材",
            companies=[
                _co("HON", "霍尼韦尔", note="特种材料"),
                _co("DD", "杜邦", note="电子材料"),
                _co("FCX", "自由港麦克莫兰", note="铜等基础材料", sector="materials"),
            ],
        ),
        _panel(
            "mask",
            "光掩膜 / 基板",
            tone="support",
            branch="materials",
            companies=[
                _co("GLW", "康宁", note="特种玻璃 / 基板"),
                _co("TSM", "台积电", note="先进掩膜协同"),
                _co("AAPL", "苹果", note="终端需求拉动"),
            ],
        ),
        _panel(
            "wafer",
            "硅片 / 晶圆",
            tone="support",
            branch="materials",
            companies=[
                _co("ENTG", "Entegris", note="高纯材料与晶圆处理"),
                _co("TSM", "台积电", note="晶圆代工消耗"),
                _co("INTC", "英特尔", note="IDM 自用硅片"),
            ],
        ),
        _panel(
            "resist",
            "光刻胶 / 显影",
            tone="support",
            branch="materials",
            companies=[
                _co("DD", "杜邦", note="光刻相关材料"),
                _co("EMN", "伊士曼化工", note="特种化学", sector="materials"),
                _co("ASML", "阿斯麦", note="光刻工艺协同"),
            ],
        ),
        _panel(
            "equip_process",
            "工艺制造设备",
            tone="support",
            branch="equipment",
            companies=[
                _co("ASML", "阿斯麦", note="EUV / DUV 光刻"),
                _co("AMAT", "应用材料", note="沉积 / 刻蚀 / CMP"),
                _co("LRCX", "拉姆研究", note="刻蚀与沉积"),
                _co("TOELY", "东京电子", note="涂胶显影 / 刻蚀"),
            ],
        ),
        _panel(
            "equip_metrology",
            "检测 / 测试设备",
            tone="support",
            branch="equipment",
            companies=[
                _co("KLAC", "科磊", note="过程控制与量测"),
                _co("TER", "泰瑞达", note="自动测试设备"),
                _co("AMAT", "应用材料", note="量测集成"),
            ],
        ),
        _panel(
            "discrete",
            "分立器件",
            tone="core",
            branch="discrete",
            companies=[
                _co("ON", "安森美", note="功率与传感"),
                _co("TXN", "德州仪器", note="模拟与嵌入式"),
                _co("NXPI", "恩智浦", note="汽车 / 工业 MCU"),
                _co("STM", "意法半导体", note="功率 / MCU"),
                _co("IFNNY", "英飞凌", note="功率器件"),
            ],
        ),
        _panel(
            "ic_design",
            "IC 设计",
            tone="core",
            branch="ic",
            companies=[
                _co("NVDA", "英伟达", note="GPU / AI 加速"),
                _co("AMD", "超威", note="CPU / GPU"),
                _co("AVGO", "博通", note="定制 ASIC / 连接"),
                _co("QCOM", "高通", note="移动 SoC / 射频"),
                _co("MRVL", "美满电子", note="数据中心 / 连接"),
                _co("ARM", "Arm", note="CPU IP"),
                _co("TXN", "德州仪器", note="模拟芯片"),
                _co("ADI", "亚德诺", note="高性能模拟"),
                _co("MU", "美光", note="存储"),
            ],
        ),
        _panel(
            "ic_fab",
            "IC 制造",
            tone="core",
            branch="ic",
            companies=[
                _co("TSM", "台积电", note="先进制程代工"),
                _co("INTC", "英特尔", note="IDM + 代工"),
                _co("GFS", "格芯", note="特色工艺"),
                _co("UMC", "联电", note="成熟制程"),
            ],
        ),
        _panel(
            "osat",
            "IC 封测",
            tone="core",
            branch="ic",
            companies=[
                _co("ASX", "日月光", note="封测龙头"),
                _co("AMKR", "Amkor", note="先进封装"),
            ],
        ),
        _panel(
            "pc",
            "PC / 计算",
            tone="app",
            branch="pc",
            companies=[
                _co("AAPL", "苹果", note="Mac / 自研芯片"),
                _co("MSFT", "微软", note="云与 PC"),
                _co("AMZN", "亚马逊", note="AWS 算力"),
                _co("GOOGL", "谷歌", note="云 / TPU"),
                _co("SMCI", "超微电脑", note="AI 服务器"),
                _co("DELL", "戴尔", note="企业计算"),
            ],
        ),
        _panel(
            "comms",
            "通信",
            tone="app",
            branch="comms",
            companies=[
                _co("AAPL", "苹果", note="智能手机"),
                _co("QCOM", "高通", note="基带 / 射频"),
                _co("AVGO", "博通", note="网络芯片"),
                _co("SWKS", "思佳讯", note="射频前端"),
                _co("ANET", "Arista", note="数据中心网络"),
            ],
        ),
        _panel(
            "consumer",
            "消费电子",
            tone="app",
            branch="consumer",
            companies=[
                _co("AAPL", "苹果", note="消费电子旗舰"),
                _co("SONY", "索尼", note="影像传感"),
                _co("QCOM", "高通", note="移动平台"),
            ],
        ),
        _panel(
            "auto",
            "汽车电子",
            tone="app",
            branch="auto",
            companies=[
                _co("TSLA", "特斯拉", note="电动车 / 自研芯片", sector="consumer"),
                _co("NXPI", "恩智浦", note="车规 MCU"),
                _co("ON", "安森美", note="车用功率"),
                _co("STM", "意法半导体", note="车用芯片"),
                _co("IFNNY", "英飞凌", note="车规功率"),
            ],
        ),
        _panel(
            "industrial",
            "工业 / 医疗",
            tone="app",
            branch="industrial",
            companies=[
                _co("TXN", "德州仪器", note="工业模拟"),
                _co("ADI", "亚德诺", note="工业 / 医疗信号链"),
                _co("ON", "安森美", note="工业功率"),
            ],
        ),
        _panel(
            "iot",
            "物联网 / 安防",
            tone="app",
            branch="iot",
            companies=[
                _co("QCOM", "高通", note="连接平台"),
                _co("MRVL", "美满电子", note="边缘连接"),
                _co("SWKS", "思佳讯", note="射频连接"),
            ],
        ),
        _panel(
            "energy",
            "新能源",
            tone="app",
            branch="energy",
            companies=[
                _co("ON", "安森美", note="功率器件"),
                _co("STM", "意法半导体", note="SiC / 功率"),
                _co("IFNNY", "英飞凌", note="SiC"),
                _co("TSLA", "特斯拉", note="储能与电动车", sector="consumer"),
            ],
        ),
    ],
}


AI_COMPUTE: dict[str, Any] = {
    "id": "ai_compute",
    "label": "AI 算力产业链",
    "keywords": [
        "AI",
        "人工智能",
        "算力",
        "大模型",
        "GPU",
        "数据中心",
        "英伟达",
        "云计算",
    ],
    "blurb": "芯片与设备 → 云基础设施 → 模型与应用层。",
    "top_flow": [
        {"id": "support", "label": "算力底座", "tone": "support"},
        {"id": "core", "label": "云与模型", "tone": "core"},
        {"id": "downstream", "label": "应用落地", "tone": "app"},
    ],
    "branches": [
        {
            "parent": "support",
            "tone": "support",
            "nodes": [
                {"id": "chips", "label": "AI 芯片"},
                {"id": "infra_hw", "label": "服务器 / 网络"},
            ],
        },
        {
            "parent": "core",
            "tone": "core",
            "nodes": [
                {"id": "cloud", "label": "云厂商"},
                {"id": "model", "label": "模型 / 平台"},
            ],
        },
        {
            "parent": "downstream",
            "tone": "app",
            "nodes": [
                {"id": "apps", "label": "企业应用"},
                {"id": "devices", "label": "终端入口"},
            ],
        },
    ],
    "panels": [
        _panel(
            "chips",
            "AI 芯片",
            tone="support",
            branch="chips",
            companies=[
                _co("NVDA", "英伟达", note="训练 / 推理 GPU"),
                _co("AMD", "超威", note="Instinct / CPU"),
                _co("AVGO", "博通", note="定制 ASIC"),
                _co("TSM", "台积电", note="先进制程代工"),
                _co("ASML", "阿斯麦", note="先进制程设备"),
                _co("MU", "美光", note="HBM / 存储"),
            ],
        ),
        _panel(
            "infra_hw",
            "服务器 / 网络",
            tone="support",
            branch="infra_hw",
            companies=[
                _co("SMCI", "超微电脑", note="AI 服务器"),
                _co("DELL", "戴尔", note="企业服务器"),
                _co("ANET", "Arista", note="数据中心网络"),
                _co("CSCO", "思科", note="网络设备"),
            ],
        ),
        _panel(
            "cloud",
            "云厂商",
            tone="core",
            branch="cloud",
            companies=[
                _co("MSFT", "微软", note="Azure / OpenAI"),
                _co("AMZN", "亚马逊", note="AWS"),
                _co("GOOGL", "谷歌", note="GCP / TPU"),
                _co("ORCL", "甲骨文", note="云数据库"),
            ],
        ),
        _panel(
            "model",
            "模型 / 平台",
            tone="core",
            branch="model",
            companies=[
                _co("MSFT", "微软", note="Copilot 生态"),
                _co("GOOGL", "谷歌", note="Gemini"),
                _co("META", "Meta", note="开源模型"),
                _co("PLTR", "Palantir", note="企业 AI 平台"),
                _co("SNOW", "Snowflake", note="数据云"),
            ],
        ),
        _panel(
            "apps",
            "企业应用",
            tone="app",
            branch="apps",
            companies=[
                _co("CRM", "Salesforce", note="Agentforce"),
                _co("NOW", "ServiceNow", note="工作流 AI"),
                _co("ADBE", "Adobe", note="创意生成"),
                _co("PATH", "UiPath", note="自动化"),
            ],
        ),
        _panel(
            "devices",
            "终端入口",
            tone="app",
            branch="devices",
            companies=[
                _co("AAPL", "苹果", note="端侧 AI"),
                _co("MSFT", "微软", note="Copilot+ PC"),
                _co("TSLA", "特斯拉", note="车端算力", sector="consumer"),
            ],
        ),
    ],
}


EV_CHAIN: dict[str, Any] = {
    "id": "ev",
    "label": "新能源车产业链",
    "keywords": [
        "新能源",
        "电动车",
        "汽车",
        "锂电",
        "充电",
        "EV",
        "特斯拉",
        "电池",
    ],
    "blurb": "材料与电池 → 整车与零部件 → 充电与出行服务。",
    "top_flow": [
        {"id": "support", "label": "上游材料", "tone": "support"},
        {"id": "core", "label": "整车制造", "tone": "core"},
        {"id": "downstream", "label": "补能与出行", "tone": "app"},
    ],
    "branches": [
        {
            "parent": "support",
            "tone": "support",
            "nodes": [
                {"id": "battery", "label": "电池 / 材料"},
                {"id": "power", "label": "功率电子"},
            ],
        },
        {
            "parent": "core",
            "tone": "core",
            "nodes": [
                {"id": "oem", "label": "整车"},
                {"id": "auto_chip", "label": "车规芯片"},
            ],
        },
        {
            "parent": "downstream",
            "tone": "app",
            "nodes": [
                {"id": "charge", "label": "充电网络"},
                {"id": "mobility", "label": "出行服务"},
            ],
        },
    ],
    "panels": [
        _panel(
            "battery",
            "电池 / 材料",
            tone="support",
            branch="battery",
            companies=[
                _co("ALB", "雅保", note="锂", sector="materials"),
                _co("SQM", "智利化工", note="锂", sector="materials"),
                _co("FCX", "自由港", note="铜", sector="materials"),
                _co("TSLA", "特斯拉", note="4680 / 储能", sector="consumer"),
            ],
        ),
        _panel(
            "power",
            "功率电子",
            tone="support",
            branch="power",
            companies=[
                _co("ON", "安森美", note="SiC / 功率"),
                _co("IFNNY", "英飞凌", note="车规功率"),
                _co("STM", "意法半导体", note="SiC"),
                _co("TXN", "德州仪器", note="车用模拟"),
            ],
        ),
        _panel(
            "oem",
            "整车",
            tone="core",
            branch="oem",
            companies=[
                _co("TSLA", "特斯拉", note="纯电龙头", sector="consumer"),
                _co("F", "福特", note="电动化转型", sector="consumer"),
                _co("GM", "通用汽车", note="Ultium 平台", sector="consumer"),
                _co("RIVN", "Rivian", note="电动皮卡", sector="consumer"),
                _co("LI", "理想汽车", note="增程 / SUV", sector="consumer"),
                _co("NIO", "蔚来", note="高端纯电", sector="consumer"),
                _co("XPEV", "小鹏", note="智能驾驶", sector="consumer"),
            ],
        ),
        _panel(
            "auto_chip",
            "车规芯片",
            tone="core",
            branch="auto_chip",
            companies=[
                _co("NXPI", "恩智浦", note="车规 MCU"),
                _co("ON", "安森美", note="传感 / 功率"),
                _co("QCOM", "高通", note="座舱 / 智驾"),
                _co("NVDA", "英伟达", note="智驾算力"),
            ],
        ),
        _panel(
            "charge",
            "充电网络",
            tone="app",
            branch="charge",
            companies=[
                _co("TSLA", "特斯拉", note="超充网络", sector="consumer"),
                _co("CHPT", "ChargePoint", note="充电运营", sector="industrials"),
            ],
        ),
        _panel(
            "mobility",
            "出行服务",
            tone="app",
            branch="mobility",
            companies=[
                _co("UBER", "Uber", note="出行平台", sector="consumer"),
                _co("LYFT", "Lyft", note="出行平台", sector="consumer"),
            ],
        ),
    ],
}


CHAINS: list[dict[str, Any]] = [SEMICONDUCTOR, AI_COMPUTE, EV_CHAIN]


def list_chain_catalog() -> list[dict[str, str]]:
    return [
        {
            "id": c["id"],
            "label": c["label"],
            "blurb": c.get("blurb") or "",
            "hint": "、".join((c.get("keywords") or [])[:4]),
        }
        for c in CHAINS
    ]


def _norm(text: str) -> str:
    return (text or "").strip().lower()


def _score_chain(chain: dict[str, Any], q: str) -> int:
    if not q:
        return 0
    score = 0
    label = _norm(chain.get("label") or "")
    if q == label or q in label:
        score += 100
    for kw in chain.get("keywords") or []:
        k = _norm(kw)
        if not k:
            continue
        if q == k:
            score += 90
        elif q in k or k in q:
            score += 70
    # Company / panel soft match
    for panel in chain.get("panels") or []:
        if q in _norm(panel.get("label") or ""):
            score += 40
        for co in panel.get("companies") or []:
            if q == _norm(co.get("symbol") or "") or q in _norm(co.get("name") or ""):
                score += 55
    return score


def resolve_chain(q: str | None = None, chain_id: str | None = None) -> dict[str, Any] | None:
    if chain_id:
        found = next((c for c in CHAINS if c["id"] == chain_id), None)
        if found:
            return found
    query = _norm(q or "")
    if not query:
        return None
    ranked = sorted(
        (( _score_chain(c, query), c) for c in CHAINS),
        key=lambda x: x[0],
        reverse=True,
    )
    if ranked and ranked[0][0] > 0:
        return ranked[0][1]
    return None


def _public_chain(chain: dict[str, Any], *, q: str = "") -> dict[str, Any]:
    return {
        "id": chain["id"],
        "label": chain["label"],
        "blurb": chain.get("blurb") or "",
        "top_flow": chain.get("top_flow") or [],
        "branches": chain.get("branches") or [],
        "panels": chain.get("panels") or [],
        "q": q,
    }


def build_chains_desk(
    *,
    chain_id: str | None = None,
    q: str | None = None,
    node_id: str | None = None,  # kept for URL compat; unused in panorama mode
) -> dict[str, Any]:
    del node_id  # panorama mode does not focus a single node
    query = (q or "").strip()
    catalog = list_chain_catalog()
    chain = resolve_chain(query, chain_id)
    if not chain:
        return {
            "ok": True,
            "matched": False,
            "q": query,
            "catalog": catalog,
            "chain": None,
            "message": (
                "输入行业关键词生成全产业链逻辑图，例如：半导体、AI、新能源车"
                if not query
                else f"未匹配到「{query}」相关产业链，可试：半导体、AI、新能源车"
            ),
        }
    return {
        "ok": True,
        "matched": True,
        "q": query or chain["label"],
        "catalog": catalog,
        "chain": _public_chain(chain, q=query or chain["label"]),
        "message": "",
    }
