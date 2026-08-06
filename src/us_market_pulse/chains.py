"""Industry-chain desk: searchable semiconductor panorama (v1)."""

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


# Semiconductor panorama — US-listed / ADR-first for Pulse Desk.
SEMICONDUCTOR_NODES: list[dict[str, Any]] = [
    {
        "id": "materials",
        "label": "半导体材料",
        "short": "材料",
        "tone": "support",
        "stage": "support",
        "group": "materials",
        "aliases": ["材料", "靶材", "光刻胶", "硅片", "晶圆", "光掩膜", "materials"],
        "blurb": "硅片、光掩膜、光刻胶、靶材等上游耗材，决定先进制程良率与产能弹性。",
        "upstream": [],
        "downstream": ["equipment", "ic_design", "ic_fab"],
        "companies": [
            _co("HON", "霍尼韦尔", note="特种材料 / 靶材相关"),
            _co("DD", "杜邦", note="电子材料 / 光刻相关"),
            _co("GLW", "康宁", note="基板与特种玻璃"),
            _co("ENTG", "Entegris", note="高纯材料与晶圆处理"),
            _co("AMAT", "应用材料", note="材料沉积与工艺集成"),
        ],
    },
    {
        "id": "equipment",
        "label": "半导体设备",
        "short": "设备",
        "tone": "support",
        "stage": "support",
        "group": "equipment",
        "aliases": ["设备", "光刻", "刻蚀", "检测", "ASML", "equipment"],
        "blurb": "光刻、沉积、刻蚀、量测等核心设备，是先进制程扩产的瓶颈环节。",
        "upstream": ["materials"],
        "downstream": ["ic_fab", "osat"],
        "companies": [
            _co("ASML", "阿斯麦", note="EUV / DUV 光刻"),
            _co("AMAT", "应用材料", note="沉积 / 刻蚀 / CMP"),
            _co("LRCX", "拉姆研究", note="刻蚀与沉积"),
            _co("KLAC", "科磊", note="过程控制与量测"),
            _co("TER", "泰瑞达", note="测试设备"),
            _co("TOELY", "东京电子", note="涂胶显影 / 刻蚀（ADR）"),
        ],
    },
    {
        "id": "discrete",
        "label": "分立器件",
        "short": "分立",
        "tone": "core",
        "stage": "core",
        "group": "discrete",
        "aliases": ["分立", "功率", "MOSFET", "IGBT", "discrete"],
        "blurb": "功率半导体、传感器与光电器件，承接汽车、工业与新能源用电需求。",
        "upstream": ["materials", "equipment"],
        "downstream": ["auto", "industrial", "energy"],
        "companies": [
            _co("ON", "安森美", note="功率与传感"),
            _co("TXN", "德州仪器", note="模拟与嵌入式"),
            _co("NXPI", "恩智浦", note="汽车与工业 MCU"),
            _co("STM", "意法半导体", note="功率 / MCU"),
            _co("IFNNY", "英飞凌", note="功率器件（ADR）"),
        ],
    },
    {
        "id": "ic_design",
        "label": "IC 设计",
        "short": "设计",
        "tone": "core",
        "stage": "core",
        "group": "ic",
        "aliases": ["设计", "Fabless", "IC设计", "芯片设计", "design"],
        "blurb": "无晶圆设计厂定义架构与 IP，把算力、连接与模拟需求产品化。",
        "upstream": ["materials", "equipment"],
        "downstream": ["ic_fab", "osat", "pc", "comms", "consumer", "auto"],
        "companies": [
            _co("NVDA", "英伟达", note="GPU / AI 加速"),
            _co("AMD", "超威", note="CPU / GPU"),
            _co("AVGO", "博通", note="定制 ASIC / 连接"),
            _co("QCOM", "高通", note="移动 SoC / 射频"),
            _co("MRVL", "美满电子", note="数据中心 / 连接"),
            _co("ARM", "Arm", note="CPU IP"),
            _co("TXN", "德州仪器", note="模拟芯片"),
            _co("ADI", "亚德诺", note="高性能模拟"),
            _co("MU", "美光", note="存储设计+制造"),
        ],
    },
    {
        "id": "ic_fab",
        "label": "IC 制造",
        "short": "制造",
        "tone": "core",
        "stage": "core",
        "group": "ic",
        "aliases": ["制造", "晶圆代工", "Foundry", "fab", "代工"],
        "blurb": "晶圆代工与 IDM 制造，决定先进制程产能、良率与交期。",
        "upstream": ["materials", "equipment", "ic_design"],
        "downstream": ["osat", "pc", "comms", "consumer"],
        "companies": [
            _co("TSM", "台积电", note="先进制程代工龙头"),
            _co("INTC", "英特尔", note="IDM + 代工扩张"),
            _co("GFS", "格芯", note="特色工艺代工"),
            _co("UMC", "联电", note="成熟制程代工"),
            _co("SSNLF", "三星电子", note="存储 / 代工（场外）"),
        ],
    },
    {
        "id": "osat",
        "label": "IC 封测",
        "short": "封测",
        "tone": "core",
        "stage": "core",
        "group": "ic",
        "aliases": ["封测", "封装", "测试", "OSAT", "package"],
        "blurb": "先进封装与测试把芯片做成可交付器件，是 AI 算力密度的关键一环。",
        "upstream": ["ic_fab", "equipment"],
        "downstream": ["pc", "comms", "consumer", "auto", "iot"],
        "companies": [
            _co("ASX", "日月光", note="封测龙头"),
            _co("AMKR", "Amkor", note="先进封装"),
        ],
    },
    {
        "id": "pc",
        "label": "PC / 计算",
        "short": "PC",
        "tone": "app",
        "stage": "downstream",
        "group": "apps",
        "aliases": ["PC", "电脑", "服务器", "数据中心", "compute"],
        "blurb": "PC、服务器与云基础设施，是算力芯片的最大需求池之一。",
        "upstream": ["ic_design", "ic_fab", "osat"],
        "downstream": [],
        "companies": [
            _co("AAPL", "苹果", note="Mac / 自研芯片"),
            _co("MSFT", "微软", note="云与 PC 生态"),
            _co("AMZN", "亚马逊", note="AWS 算力"),
            _co("GOOGL", "谷歌", note="云与自研 TPU"),
            _co("SMCI", "超微电脑", note="AI 服务器"),
            _co("DELL", "戴尔", note="企业计算"),
        ],
    },
    {
        "id": "comms",
        "label": "通信",
        "short": "通信",
        "tone": "app",
        "stage": "downstream",
        "group": "apps",
        "aliases": ["通信", "5G", "射频", "基站", "comms"],
        "blurb": "手机、基站与网络设备拉动射频、基带与连接芯片需求。",
        "upstream": ["ic_design", "osat"],
        "downstream": [],
        "companies": [
            _co("AAPL", "苹果", note="智能手机"),
            _co("QCOM", "高通", note="基带 / 射频"),
            _co("AVGO", "博通", note="网络与无线"),
            _co("SWKS", "思佳讯", note="射频前端"),
            _co("ANET", "Arista", note="数据中心网络"),
        ],
    },
    {
        "id": "consumer",
        "label": "消费电子",
        "short": "消费",
        "tone": "app",
        "stage": "downstream",
        "group": "apps",
        "aliases": ["消费电子", "手机", "穿戴", "consumer"],
        "blurb": "手机、穿戴与家用电子决定中低端制程与模拟芯片出货节奏。",
        "upstream": ["ic_design", "osat", "discrete"],
        "downstream": [],
        "companies": [
            _co("AAPL", "苹果", note="消费电子旗舰"),
            _co("SONY", "索尼", note="影像传感 / 消费电子"),
            _co("QCOM", "高通", note="移动平台"),
        ],
    },
    {
        "id": "auto",
        "label": "汽车电子",
        "short": "汽车",
        "tone": "app",
        "stage": "downstream",
        "group": "apps",
        "aliases": ["汽车", "车规", "ADAS", "电动车", "auto"],
        "blurb": "电动化与智能化抬升车规 MCU、功率器件与传感含量。",
        "upstream": ["discrete", "ic_design", "osat"],
        "downstream": [],
        "companies": [
            _co("TSLA", "特斯拉", note="电动车 / 自研芯片", sector="consumer"),
            _co("NXPI", "恩智浦", note="车规 MCU"),
            _co("ON", "安森美", note="车用功率与传感"),
            _co("STM", "意法半导体", note="车用芯片"),
            _co("IFNNY", "英飞凌", note="车规功率"),
        ],
    },
    {
        "id": "industrial",
        "label": "工业 / 医疗",
        "short": "工业",
        "tone": "app",
        "stage": "downstream",
        "group": "apps",
        "aliases": ["工业", "医疗", "自动化", "industrial", "medical"],
        "blurb": "工业自动化与医疗设备需要高可靠模拟、功率与嵌入式方案。",
        "upstream": ["discrete", "ic_design"],
        "downstream": [],
        "companies": [
            _co("TXN", "德州仪器", note="工业模拟"),
            _co("ADI", "亚德诺", note="工业 / 医疗信号链"),
            _co("ON", "安森美", note="工业功率"),
        ],
    },
    {
        "id": "iot",
        "label": "物联网 / 安防",
        "short": "物联",
        "tone": "app",
        "stage": "downstream",
        "group": "apps",
        "aliases": ["物联网", "IoT", "安防", "信息安全", "iot"],
        "blurb": "连接、边缘计算与安防芯片承接海量终端渗透。",
        "upstream": ["ic_design", "osat"],
        "downstream": [],
        "companies": [
            _co("QCOM", "高通", note="连接平台"),
            _co("MRVL", "美满电子", note="边缘 / 连接"),
            _co("SWKS", "思佳讯", note="射频连接"),
        ],
    },
    {
        "id": "energy",
        "label": "新能源",
        "short": "新能源",
        "tone": "app",
        "stage": "downstream",
        "group": "apps",
        "aliases": ["新能源", "光伏", "储能", "充电", "energy"],
        "blurb": "光伏逆变、储能与充电基础设施拉动功率半导体需求。",
        "upstream": ["discrete", "ic_design"],
        "downstream": [],
        "companies": [
            _co("ON", "安森美", note="功率器件"),
            _co("STM", "意法半导体", note="功率 / SiC"),
            _co("IFNNY", "英飞凌", note="SiC / 功率"),
            _co("TSLA", "特斯拉", note="储能与电动车", sector="consumer"),
        ],
    },
]

SEMICONDUCTOR_FLOW: list[dict[str, Any]] = [
    {
        "id": "support",
        "label": "支撑产业",
        "tone": "support",
        "nodes": ["materials", "equipment"],
    },
    {
        "id": "core",
        "label": "半导体行业",
        "tone": "core",
        "nodes": ["discrete", "ic_design", "ic_fab", "osat"],
        "pipeline": ["ic_design", "ic_fab", "osat"],
    },
    {
        "id": "downstream",
        "label": "下游应用",
        "tone": "app",
        "nodes": ["pc", "comms", "consumer", "auto", "industrial", "iot", "energy"],
    },
]

CHAINS: list[dict[str, Any]] = [
    {
        "id": "semiconductor",
        "label": "半导体产业链",
        "blurb": "从材料设备到设计制造封测，再到 PC / 通信 / 汽车等下游应用的全景定位。",
        "default_node": "ic_design",
        "flow": SEMICONDUCTOR_FLOW,
        "nodes": SEMICONDUCTOR_NODES,
    }
]


def _node_map(chain: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {n["id"]: n for n in chain.get("nodes") or []}


def _match_text(hay: str, q: str) -> bool:
    return q in (hay or "").lower()


def search_chain(chain: dict[str, Any], query: str) -> list[dict[str, Any]]:
    q = (query or "").strip().lower()
    if not q:
        return []
    hits: list[dict[str, Any]] = []
    for node in chain.get("nodes") or []:
        node_blob = " ".join(
            [
                node.get("id", ""),
                node.get("label", ""),
                node.get("short", ""),
                node.get("blurb", ""),
                " ".join(node.get("aliases") or []),
            ]
        ).lower()
        if _match_text(node_blob, q):
            hits.append(
                {
                    "kind": "node",
                    "node_id": node["id"],
                    "label": node["label"],
                    "tone": node.get("tone"),
                    "blurb": node.get("blurb"),
                }
            )
        for co in node.get("companies") or []:
            co_blob = " ".join(
                [co.get("symbol", ""), co.get("name", ""), co.get("note", "")]
            ).lower()
            if _match_text(co_blob, q):
                hits.append(
                    {
                        "kind": "company",
                        "node_id": node["id"],
                        "node_label": node["label"],
                        "symbol": co["symbol"],
                        "name": co["name"],
                        "note": co.get("note") or "",
                        "sector": co.get("sector") or "technology",
                        "tone": node.get("tone"),
                    }
                )
    # De-dupe company hits preferring first node occurrence.
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for h in hits:
        key = (
            f"n:{h['node_id']}"
            if h["kind"] == "node"
            else f"c:{h['symbol']}:{h['node_id']}"
        )
        if key in seen:
            continue
        seen.add(key)
        out.append(h)
    return out[:40]


def build_chains_desk(
    *,
    chain_id: str | None = None,
    node_id: str | None = None,
    q: str | None = None,
) -> dict[str, Any]:
    chain = next((c for c in CHAINS if c["id"] == (chain_id or "semiconductor")), CHAINS[0])
    nodes = _node_map(chain)
    selected = (node_id or "").strip() or chain.get("default_node") or next(iter(nodes))
    if selected not in nodes:
        selected = chain.get("default_node") or next(iter(nodes))
    node = nodes[selected]
    upstream = [nodes[i] for i in (node.get("upstream") or []) if i in nodes]
    downstream = [nodes[i] for i in (node.get("downstream") or []) if i in nodes]
    query = (q or "").strip()
    hits = search_chain(chain, query) if query else []
    # If search hits a company/node, prefer focusing that node.
    if hits and not node_id:
        preferred = hits[0].get("node_id")
        if preferred in nodes:
            selected = preferred
            node = nodes[selected]
            upstream = [nodes[i] for i in (node.get("upstream") or []) if i in nodes]
            downstream = [nodes[i] for i in (node.get("downstream") or []) if i in nodes]
    return {
        "ok": True,
        "chains": [{"id": c["id"], "label": c["label"], "blurb": c["blurb"]} for c in CHAINS],
        "chain": {
            "id": chain["id"],
            "label": chain["label"],
            "blurb": chain["blurb"],
            "flow": chain["flow"],
            "nodes": [
                {
                    "id": n["id"],
                    "label": n["label"],
                    "short": n.get("short") or n["label"],
                    "tone": n.get("tone"),
                    "stage": n.get("stage"),
                    "group": n.get("group"),
                    "company_count": len(n.get("companies") or []),
                }
                for n in chain["nodes"]
            ],
        },
        "selected_node": selected,
        "node": {
            "id": node["id"],
            "label": node["label"],
            "short": node.get("short") or node["label"],
            "tone": node.get("tone"),
            "stage": node.get("stage"),
            "blurb": node.get("blurb"),
            "companies": node.get("companies") or [],
            "upstream": [
                {"id": u["id"], "label": u["label"], "tone": u.get("tone")}
                for u in upstream
            ],
            "downstream": [
                {"id": d["id"], "label": d["label"], "tone": d.get("tone")}
                for d in downstream
            ],
        },
        "q": query,
        "hits": hits,
    }
