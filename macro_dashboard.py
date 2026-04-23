"""
全球總經監控儀表板 v5 — Streamlit Edition
Global Macro Monitor · FRED API + Anthropic AI · 完全自動化版本
"""

import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from datetime import datetime, timedelta
import json
import time

# ══════════════════════════════════════════════════════════════════════════════
# CONFIG
# ══════════════════════════════════════════════════════════════════════════════
FRED_KEY = "a2ddfa1f7e106de7c01eb5d196b5ef27"
FRED_BASE = "https://api.stlouisfed.org/fred/series/observations"

YIELD_SERIES = [
    {"id": "DGS1MO", "label": "1M",  "months": 0.083},
    {"id": "DGS3MO", "label": "3M",  "months": 0.25},
    {"id": "DGS6MO", "label": "6M",  "months": 0.5},
    {"id": "DGS1",   "label": "1Y",  "months": 12},
    {"id": "DGS2",   "label": "2Y",  "months": 24},
    {"id": "DGS3",   "label": "3Y",  "months": 36},
    {"id": "DGS5",   "label": "5Y",  "months": 60},
    {"id": "DGS7",   "label": "7Y",  "months": 84},
    {"id": "DGS10",  "label": "10Y", "months": 120},
    {"id": "DGS20",  "label": "20Y", "months": 240},
    {"id": "DGS30",  "label": "30Y", "months": 360},
]

FX_SERIES = [
    {"id": "DEXUSEU", "pair": "EUR/USD", "invert": True,  "color": "#3B82F6",
     "note": "美元整體走弱，歐元相對受支撐。ECB 4/30 會議為近期觸媒，26% 升息機率需關注。"},
    {"id": "DEXJPUS", "pair": "USD/JPY", "invert": False, "color": "#EF4444",
     "note": "巨大利差（Fed 3.625% vs BOJ 0.75%）持續壓制日圓。BOJ 4/28 幾乎確定不動。"},
    {"id": "DEXTAUS", "pair": "USD/TWD", "invert": False, "color": "#10B981",
     "note": "台幣近一年走強，但中東緊張使短線承壓。長期受台灣貿易順差與科技出口支撐。"},
]

# 央行利率：currentRate 仍手動，但 rateNum 可以在下方加 FRED 自動抓取
BANKS = [
    {
        "id": "fed", "flag": "🇺🇸", "name": "Fed", "fullName": "聯準會 Federal Reserve",
        "currentRate": "3.50–3.75%", "rateNum": 3.625, "depositRate": None,
        "trend": "hold", "prevAction": "▼ 降25bps（2025/12）→ 連續按兵不動",
        "nextMeeting": "2026/05/06–07", "color": "#3B82F6",
        "shortView": "觀望，中東通膨壓力使降息推遲",
        # FRED series for policy rate (optional auto-fetch)
        "fred_rate_id": "FEDFUNDS",
        "analysis": [
            {"title": "現況", "text": "聯邦基金利率維持 3.50–3.75%，Fed 在 12 月完成第三次連續降息後開始暫停，因通膨黏性高於預期。"},
            {"title": "通膨 vs 就業", "text": "核心 PCE 仍頑固維持在目標以上，勞動市場呈現低招募、低裁員的「冷卻」格局，並未觸發緊急降息需求。"},
            {"title": "中東衝擊", "text": "美伊衝突帶來油價跳升，直接拉升通膨預期，令 2026 年降息窗口一再後推，Fed 被迫以「觀望」取代「行動」。"},
            {"title": "Fed 主席交接", "text": "Powell 任期至 5/15。提名人 Warsh（4/21 聽證）強調「Fed 專注物價穩定」，確認受制於 Powell 司法調查爭議。"},
            {"title": "前瞻", "text": "市場定價 2026 年至多一次降息（可能 Q3–Q4）。若油價持續高位，不排除年內按兵不動。新主席態度為最大未知數。"},
        ],
    },
    {
        "id": "ecb", "flag": "🇪🇺", "name": "ECB", "fullName": "歐洲央行 ECB",
        "currentRate": "2.15%", "rateNum": 2.15, "depositRate": "存款 2.00% / 邊際貸款 2.40%",
        "trend": "hold", "prevAction": "▼ 降息循環（2024–2025）已結束",
        "nextMeeting": "2026/04/29–30", "color": "#10B981",
        "shortView": "按兵不動，中東能源衝擊使通膨反升至 2.6%",
        "fred_rate_id": None,
        "analysis": [
            {"title": "三率結構", "text": "主要再融資利率 2.15%，存款便利利率 2.00%，邊際貸款利率 2.40%。ECB 以存款利率作為主要政策工具。"},
            {"title": "通膨與成長", "text": "3 月歐元區通膨回升至 2.6%（主因能源），核心 2.3%。ECB 預測 2026 GDP 僅 0.9%，類停滯膨脹風險升高。"},
            {"title": "Lagarde（4/17）", "text": "IMF 春季年會表示「定位良好、備妥工具」，中東戰爭帶來上行通膨與下行成長雙重風險，未給明確利率指引。"},
            {"title": "4/29–30 前瞻", "text": "市場定價 74% 維持不變，26% 升息機率（摩根士丹利等提出此風險）。若中東持續，不排除重啟升息。"},
            {"title": "前瞻", "text": "降息在 2026 年幾乎不可能。主要風險為升息而非降息。"},
        ],
    },
    {
        "id": "boe", "flag": "🇬🇧", "name": "BOE", "fullName": "英國央行 BOE",
        "currentRate": "3.75%", "rateNum": 3.75, "depositRate": None,
        "trend": "hold", "prevAction": "▼ 降25bps（2025/12），2026 年均按兵不動",
        "nextMeeting": "2026/05/08", "color": "#F59E0B",
        "shortView": "停滯困境：通膨頑固 × 成長停滯",
        "fred_rate_id": None,
        "analysis": [
            {"title": "英國特殊困境", "text": "BOE 面臨「三明治困境」：通膨仍高於 3%、工資強勁，但經濟成長幾乎停滯（2025 Q3 幾乎零成長）。"},
            {"title": "委員會分裂", "text": "上次投票呈四鴿四鷹格局。中東油價衝擊使鷹派佔上風，3 月決議全票維持不動。"},
            {"title": "中東能源衝擊", "text": "英國高度依賴進口能源，油氣飆升直接傳導至家庭能源帳單。BOE 高度警覺二輪通膨效應。"},
            {"title": "財政空間有限", "text": "英國財政部已大幅擴張支出，BOE 幾乎只能獨自對抗通膨而缺乏財政配合，形成政策夾縫。"},
            {"title": "前瞻", "text": "5 月維持 3.75%。除非通膨在 Q2 顯著下降，2026 年降息機會微乎其微。"},
        ],
    },
    {
        "id": "boj", "flag": "🇯🇵", "name": "BOJ", "fullName": "日本央行 BOJ",
        "currentRate": "0.75%", "rateNum": 0.75, "depositRate": None,
        "trend": "hold", "prevAction": "▲ 升至 0.75%（2026/01），其後暫停",
        "nextMeeting": "2026/04/27–28", "color": "#EF4444",
        "shortView": "暫停升息，緊盯中東與薪資走勢",
        "fred_rate_id": None,
        "analysis": [
            {"title": "政策正常化", "text": "BOJ 終結負利率後緩步升息，0.75% 為 1995 年以來最高，但升息步伐遠慢於市場預期。"},
            {"title": "4/27–28 會議", "text": "市場定價 97% 機率按兵不動。植田和男 4/17 演講刻意避開升息訊號，引用中東不確定性。"},
            {"title": "薪資與通膨", "text": "春季薪資談判（春鬪）強勁，支撐核心通膨於 2% 附近。一旦中東不確定性消散，升息節奏有望恢復。"},
            {"title": "日圓承壓", "text": "USD/JPY 維持 158–160 高位，顯示市場認為 BOJ 升息不足以縮小利差。"},
            {"title": "前瞻", "text": "BOJ 最可能在中東明朗後（Q2–Q3）恢復升息。路透引述消息指 6 月具備條件。全年可能再升 1–2 次至 1.0–1.25%。"},
        ],
    },
    {
        "id": "rba", "flag": "🇦🇺", "name": "RBA", "fullName": "澳洲央行 RBA",
        "currentRate": "4.10%", "rateNum": 4.10, "depositRate": None,
        "trend": "hike", "prevAction": "▲ 升25bps（2026/02）→ ▲ 升25bps（2026/03）",
        "nextMeeting": "2026/05/19–20", "color": "#8B5CF6",
        "shortView": "反向升息，供給側通膨壓力難消",
        "fred_rate_id": None,
        "analysis": [
            {"title": "2026 反向升息", "text": "RBA 在 2025 年曾降息三次後，2026 年連升兩次回到 4.10%。為全球主要央行中少數仍在升息者。"},
            {"title": "通膨回升", "text": "澳洲私人需求超預期 + 中東能源衝擊。副行長 Hauser 直言面臨「停滯膨脹惡夢」。"},
            {"title": "委員會分歧", "text": "上次四比四平票，反對派也未倡議降息，顯示整體偏緊縮共識。市場定價年底可達 4.56%。"},
            {"title": "Q1 CPI（4 月底）", "text": "季度 CPI 為 5 月會議關鍵輸入，若通膨仍高，再次升息幾乎確定。"},
            {"title": "前瞻", "text": "合理區間 4.10% 或再升至 4.35%。中東油價高燒前降息完全無望。"},
        ],
    },
]

TAIL_RISKS = [
    {"icon": "🛢️", "risk": "中東衝突持續", "detail": "油價維持高位 → 通膨再起 → 央行被迫升息 → 風險資產承壓"},
    {"icon": "🇺🇸", "risk": "Fed 主席交接", "detail": "Warsh 確認受阻，Powell 任期空窗恐引發市場波動"},
    {"icon": "🇯🇵", "risk": "日圓繼續貶值", "detail": "BOJ 升息節奏若落後，日圓恐突破 160 引發干預"},
    {"icon": "🇦🇺", "risk": "澳洲滯脹螺旋", "detail": "RBA 升息壓制需求，但油價通膨供給側無法藉利率解決"},
    {"icon": "📊", "risk": "美國 Q1 GDP",  "detail": "4/30 公布，若為負值衰退恐慌重燃"},
]

LAST_MANUAL_UPDATE = "2026-04-22"

# ══════════════════════════════════════════════════════════════════════════════
# FRED FETCH HELPERS
# ══════════════════════════════════════════════════════════════════════════════

@st.cache_data(ttl=3600)
def fetch_fred_series(series_id: str, limit: int = 400) -> pd.DataFrame:
    """Fetch a FRED series. Returns DataFrame with columns: date, value."""
    params = {
        "series_id": series_id,
        "api_key": FRED_KEY,
        "file_type": "json",
        "sort_order": "desc",
        "limit": limit,
    }
    try:
        r = requests.get(FRED_BASE, params=params, timeout=15)
        r.raise_for_status()
        obs = r.json().get("observations", [])
        df = pd.DataFrame(obs)[["date", "value"]]
        df["value"] = pd.to_numeric(df["value"], errors="coerce")
        df["date"] = pd.to_datetime(df["date"])
        df = df.dropna(subset=["value"]).sort_values("date", ascending=False)
        return df
    except Exception as e:
        st.warning(f"⚠ FRED {series_id} 抓取失敗：{e}")
        return pd.DataFrame(columns=["date", "value"])


def closest_value(df: pd.DataFrame, target_date: datetime) -> float | None:
    """Return the closest non-null FRED value on or before target_date."""
    filtered = df[df["date"] <= pd.Timestamp(target_date)]
    if filtered.empty:
        return None
    return float(filtered.iloc[0]["value"])


@st.cache_data(ttl=3600)
def fetch_all_yields() -> dict:
    """Fetch all yield series. Returns dict of {series_id: DataFrame}."""
    return {s["id"]: fetch_fred_series(s["id"]) for s in YIELD_SERIES}


def build_yield_curve(all_obs: dict, target_date: datetime) -> list[dict]:
    """Build yield curve snapshot for a given date."""
    pts = []
    for s in YIELD_SERIES:
        df = all_obs.get(s["id"], pd.DataFrame())
        val = closest_value(df, target_date)
        if val is not None:
            pts.append({"label": s["label"], "months": s["months"], "value": val})
    return pts


@st.cache_data(ttl=3600)
def fetch_all_fx() -> dict:
    """Fetch FX series from FRED. Returns dict of {pair: {price, change, date, range52w}}."""
    result = {}
    for fx in FX_SERIES:
        df = fetch_fred_series(fx["id"], limit=300)
        if df.empty:
            result[fx["pair"]] = None
            continue
        invert = fx["invert"]
        curr_val = df.iloc[0]["value"]
        prev_val = df.iloc[1]["value"] if len(df) > 1 else curr_val
        if invert:
            curr_val = 1 / curr_val
            prev_val = 1 / prev_val
        change_pct = ((curr_val - prev_val) / prev_val) * 100
        yr_vals = df.head(252)["value"].apply(lambda v: 1/v if invert else v)
        result[fx["pair"]] = {
            "price": curr_val,
            "change": change_pct,
            "date": df.iloc[0]["date"].strftime("%Y-%m-%d"),
            "lo": float(yr_vals.min()),
            "hi": float(yr_vals.max()),
        }
    return result


@st.cache_data(ttl=86400)
def fetch_fed_rate_from_fred() -> float | None:
    """Auto-fetch effective Federal Funds Rate from FRED."""
    df = fetch_fred_series("FEDFUNDS", limit=5)
    if df.empty:
        return None
    return float(df.iloc[0]["value"])


# ══════════════════════════════════════════════════════════════════════════════
# AI WEEKLY (Anthropic API)
# ══════════════════════════════════════════════════════════════════════════════

def fetch_weekly_from_ai(anthropic_key: str) -> dict | None:
    """Call Anthropic API with web search to get this week's macro calendar."""
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday())
    week_end = week_start + timedelta(days=6)

    prompt = f"""Today is {today.strftime('%Y-%m-%d')}. Current week: {week_start.strftime('%Y-%m-%d')} to {week_end.strftime('%Y-%m-%d')}.

You are a macro research assistant. Search the web for current data and provide in Traditional Chinese:

1. THIS_WEEK: Important global economic data releases this week (released or scheduled). For each: date (M/D 週X), region emoji flag, event name, result ("待公布" if not yet released, otherwise actual value with unit), previous value, impact (high/medium/low), brief note.

2. NEXT_WEEK: Next week's important events. For each: date, region emoji, event name, impact, note.

3. SPEECHES: Central bank official speeches/statements from past 14 days (Fed, ECB, BOJ, BOE, RBA). For each: date (M/DD), speaker name + title in Chinese, org (Fed/ECB/BOJ/BOE/RBA), color hex (#3B82F6 for Fed, #10B981 ECB, #EF4444 BOJ, #F59E0B BOE, #8B5CF6 RBA), event/title, key points in Chinese (2-3 sentences), flag emoji.

Focus on: US CPI/NFP/GDP/PCE/retail sales/FOMC, ECB/BOE/BOJ/RBA meetings, PMI, employment. Only high-impact events.

Respond ONLY with valid JSON (no markdown, no preamble):
{{"thisWeek":[{{"date":"","region":"","event":"","result":"","prev":"","impact":"","note":""}}],"nextWeek":[{{"date":"","region":"","event":"","impact":"","note":""}}],"speeches":[{{"date":"","who":"","org":"","color":"","title":"","key":"","flag":""}}]}}"""

    headers = {"Content-Type": "application/json"}
    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [{"role": "user", "content": prompt}],
    }
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=60,
        )
        r.raise_for_status()
        data = r.json()
        text_block = next((b for b in reversed(data["content"]) if b["type"] == "text"), None)
        if not text_block:
            return None
        raw = text_block["text"].replace("```json", "").replace("```", "").strip()
        s, e = raw.index("{"), raw.rindex("}")
        return json.loads(raw[s:e+1])
    except Exception as ex:
        st.error(f"AI 數據抓取失敗：{ex}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# CHART BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def build_yield_curve_chart(curves: dict) -> go.Figure:
    """Build multi-curve US yield curve chart using Plotly."""
    configs = [
        {"key": "now", "label": "現在",    "color": "#60A5FA", "width": 3,   "dash": "solid"},
        {"key": "1m",  "label": "1個月前", "color": "#F59E0B", "width": 1.5, "dash": "dash"},
        {"key": "6m",  "label": "6個月前", "color": "#A78BFA", "width": 1.5, "dash": "dash"},
        {"key": "1y",  "label": "1年前",   "color": "#6B7280", "width": 1,   "dash": "dot"},
    ]

    fig = go.Figure()
    for cfg in reversed(configs):  # draw oldest first
        pts = curves.get(cfg["key"], [])
        if not pts:
            continue
        x = [p["label"] for p in pts]
        y = [p["value"] for p in pts]
        fig.add_trace(go.Scatter(
            x=x, y=y, mode="lines+markers" if cfg["key"] == "now" else "lines",
            name=cfg["label"],
            line=dict(color=cfg["color"], width=cfg["width"], dash=cfg["dash"]),
            marker=dict(size=6 if cfg["key"] == "now" else 0),
        ))

    # Spread annotation
    now = curves.get("now", [])
    now_2y  = next((p["value"] for p in now if p["label"] == "2Y"), None)
    now_10y = next((p["value"] for p in now if p["label"] == "10Y"), None)
    if now_2y and now_10y:
        spread = now_10y - now_2y
        color = "#22C55E" if spread >= 0 else "#EF4444"
        sign  = "+" if spread >= 0 else ""
        signal = "正斜率 → 衰退信號解除" if spread >= 0 else "倒掛 → 衰退警示"
        fig.add_annotation(
            x=0.99, y=0.05, xref="paper", yref="paper",
            text=f"10Y−2Y: <b>{sign}{spread:.2f}%</b><br><span style='font-size:10px'>{signal}</span>",
            showarrow=False, align="right",
            font=dict(color=color, size=12),
            bgcolor="#0A1628", bordercolor=color, borderwidth=1, borderpad=6,
        )

    fig.update_layout(
        paper_bgcolor="#020B18",
        plot_bgcolor="#080F1A",
        font=dict(color="#94A3B8", family="DM Mono, monospace"),
        legend=dict(bgcolor="#0A1628", bordercolor="#1E293B", borderwidth=1),
        margin=dict(l=40, r=20, t=20, b=40),
        height=300,
        xaxis=dict(gridcolor="#1E293B", title=None),
        yaxis=dict(gridcolor="#1E293B", title="殖利率 (%)", ticksuffix="%"),
        hovermode="x unified",
    )
    return fig


def build_fx_chart(pair: str, df: pd.DataFrame, color: str) -> go.Figure:
    """Build 90-day FX price chart."""
    df90 = df.head(90).sort_values("date")
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df90["date"], y=df90["value"],
        mode="lines", line=dict(color=color, width=2),
        fill="tozeroy", fillcolor=color.replace(")", ",0.07)").replace("rgb", "rgba"),
        name=pair,
    ))
    fig.update_layout(
        paper_bgcolor="#020B18", plot_bgcolor="#080F1A",
        font=dict(color="#94A3B8"), showlegend=False,
        margin=dict(l=40, r=10, t=10, b=30), height=140,
        xaxis=dict(gridcolor="#1E293B", showticklabels=True),
        yaxis=dict(gridcolor="#1E293B"),
    )
    return fig


# ══════════════════════════════════════════════════════════════════════════════
# STREAMLIT UI
# ══════════════════════════════════════════════════════════════════════════════

def main():
    st.set_page_config(
        page_title="全球總經監控儀表板",
        page_icon="📊",
        layout="wide",
        initial_sidebar_state="collapsed",
    )

    # Global CSS
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&display=swap');
    html, body, .stApp { background: #020B18; color: #E2E8F0; font-family: 'DM Mono', monospace; }
    .stTabs [data-baseweb="tab-list"] { background: #0A1628; border-radius: 8px; gap: 4px; padding: 4px; }
    .stTabs [data-baseweb="tab"] { color: #64748B; background: transparent; border-radius: 6px; font-size: 12px; font-weight: 600; }
    .stTabs [aria-selected="true"] { background: #1E293B !important; color: #F1F5F9 !important; }
    .metric-card { background: #080F1A; border: 1px solid #1E293B; border-radius: 12px; padding: 18px; }
    .stButton > button { background: #1E293B; color: #64748B; border: none; border-radius: 6px; font-family: 'DM Mono', monospace; }
    .stButton > button:hover { color: #E2E8F0; }
    h1,h2,h3 { color: #F8FAFC !important; font-family: 'DM Mono', monospace !important; }
    .stDataFrame { background: #080F1A; }
    div[data-testid="stMetric"] { background: #080F1A; border: 1px solid #1E293B; border-radius: 10px; padding: 14px; }
    div[data-testid="stMetricValue"] { color: #F1F5F9; }
    </style>
    """, unsafe_allow_html=True)

    today_str = datetime.now().strftime("%Y-%m-%d")

    # ── Header ─────────────────────────────────────────────────────────────
    col_h1, col_h2 = st.columns([3, 1])
    with col_h1:
        st.markdown(f"""
        <div style='margin-bottom:4px'>
            <span style='display:inline-block;width:8px;height:8px;border-radius:50%;background:#22C55E;box-shadow:0 0 8px #22C55E;margin-right:6px;'></span>
            <span style='color:#475569;font-size:11px;letter-spacing:0.1em'>{today_str} · FRED API · 殖利率&匯率每小時更新</span>
        </div>
        <h1 style='margin:0;font-size:22px;font-weight:800;letter-spacing:-0.02em'>全球總經監控儀表板</h1>
        <div style='color:#475569;font-size:11px;margin-top:3px'>Global Macro Monitor v5 · Streamlit + FRED API Live Edition</div>
        """, unsafe_allow_html=True)
    with col_h2:
        if st.button("↻ 重新整理所有數據", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

    st.markdown("---")

    # ── Tabs ───────────────────────────────────────────────────────────────
    tab_rates, tab_fx, tab_macro, tab_cal, tab_speeches = st.tabs([
        "🏦 央行利率", "💱 即時匯率", "🌐 大局觀", "📅 數據行事曆", "🎙 官員談話"
    ])

    # ══════════════════════════════════════════════════════════════════════
    # TAB 1: RATES
    # ══════════════════════════════════════════════════════════════════════
    with tab_rates:
        # Auto-fetch Fed rate from FRED
        fed_rate_live = fetch_fed_rate_from_fred()

        bank_names = [f"{b['flag']} {b['name']}" for b in BANKS]
        sel = st.radio("選擇央行", bank_names, horizontal=True, label_visibility="collapsed")
        bank = next(b for b in BANKS if f"{b['flag']} {b['name']}" == sel)

        # Override Fed rate with FRED live data if available
        display_rate = bank["currentRate"]
        if bank["id"] == "fed" and fed_rate_live:
            display_rate = f"{fed_rate_live:.2f}% (FRED即時)"

        col_left, col_right = st.columns([1, 1])

        with col_left:
            trend_map = {"cut": "🟢 降息 ▼", "hold": "🔵 按兵 →", "hike": "🔴 升息 ▲"}
            st.markdown(f"""
            <div class='metric-card' style='border-color:{bank["color"]}44'>
                <div style='color:#94A3B8;font-size:11px;margin-bottom:4px'>{bank["fullName"]}</div>
                <div style='color:{bank["color"]};font-size:30px;font-weight:800;letter-spacing:-0.02em'>{display_rate}</div>
                <div style='margin:8px 0'><span style='background:{bank["color"]}22;color:{bank["color"]};border:1px solid {bank["color"]}55;border-radius:4px;padding:2px 10px;font-size:12px;font-weight:700'>{trend_map.get(bank["trend"],"→")}</span></div>
                <div style='color:#64748B;font-size:11px;margin-bottom:4px'>{bank["prevAction"]}</div>
                {"<div style='color:#64748B;font-size:11px;margin-bottom:4px'>" + bank["depositRate"] + "</div>" if bank.get("depositRate") else ""}
                <div style='color:#475569;font-size:11px'>📅 下次：<span style='color:#94A3B8'>{bank["nextMeeting"]}</span></div>
                <div style='margin-top:10px;background:#0A1628;border-radius:6px;padding:8px 10px;color:#7DD3FC;font-size:11px'>💡 {bank["shortView"]}</div>
                {"<div style='color:#22C55E;font-size:9px;margin-top:6px'>✓ Fed Funds Rate 由 FRED 自動更新</div>" if bank["id"] == "fed" and fed_rate_live else ""}
            </div>
            """, unsafe_allow_html=True)

            # Yield curve for Fed
            if bank["id"] == "fed":
                st.markdown("<div style='color:#94A3B8;font-size:11px;letter-spacing:0.08em;margin-top:18px;margin-bottom:8px'>📈 美國殖利率曲線（FRED 自動更新）</div>", unsafe_allow_html=True)
                with st.spinner("載入殖利率數據…"):
                    all_obs = fetch_all_yields()
                today_dt = datetime.now()
                curves = {
                    "now": build_yield_curve(all_obs, today_dt),
                    "1m":  build_yield_curve(all_obs, today_dt - timedelta(days=31)),
                    "6m":  build_yield_curve(all_obs, today_dt - timedelta(days=183)),
                    "1y":  build_yield_curve(all_obs, today_dt - timedelta(days=365)),
                }
                if curves["now"]:
                    fig = build_yield_curve_chart(curves)
                    st.plotly_chart(fig, use_container_width=True)
                    # Spread metrics
                    now_pts = curves["now"]
                    v2y  = next((p["value"] for p in now_pts if p["label"] == "2Y"), None)
                    v10y = next((p["value"] for p in now_pts if p["label"] == "10Y"), None)
                    if v2y and v10y:
                        spread = v10y - v2y
                        c1, c2, c3 = st.columns(3)
                        sign = "+" if spread >= 0 else ""
                        c1.metric("10Y−2Y 利差", f"{sign}{spread:.2f}%",
                                  "正斜率" if spread >= 0 else "⚠ 倒掛")
                        c2.metric("2Y 殖利率", f"{v2y:.2f}%")
                        c3.metric("10Y 殖利率", f"{v10y:.2f}%")
                else:
                    st.warning("殖利率數據載入中，請稍後重整…")

        with col_right:
            st.markdown(f"<div style='color:#94A3B8;font-size:11px;letter-spacing:0.1em;margin-bottom:14px'>深度分析（手動更新：{LAST_MANUAL_UPDATE}）</div>", unsafe_allow_html=True)
            for a in bank["analysis"]:
                st.markdown(f"""
                <div style='margin-bottom:14px;padding-bottom:14px;border-bottom:1px solid #0F172A'>
                    <div style='color:{bank["color"]};font-size:11px;font-weight:700;margin-bottom:5px'>{a["title"]}</div>
                    <div style='color:#94A3B8;font-size:12px;line-height:1.7'>{a["text"]}</div>
                </div>
                """, unsafe_allow_html=True)

        # Rate bar comparison
        st.markdown("---")
        st.markdown("<div style='color:#94A3B8;font-size:11px;letter-spacing:0.1em;margin-bottom:12px'>各央行利率一覽</div>", unsafe_allow_html=True)
        for b in BANKS:
            cols = st.columns([1, 4, 1, 1])
            with cols[0]:
                st.markdown(f"<div style='color:#94A3B8;font-size:11px'>{b['flag']} {b['name']}</div>", unsafe_allow_html=True)
            with cols[1]:
                pct = min((b["rateNum"] / 5) * 100, 100)
                st.markdown(f"""
                <div style='height:5px;background:#1E293B;border-radius:3px;margin-top:8px'>
                    <div style='height:100%;width:{pct}%;background:{b["color"]};border-radius:3px'></div>
                </div>""", unsafe_allow_html=True)
            with cols[2]:
                st.markdown(f"<div style='color:{b['color']};font-size:12px;font-weight:700'>{b['currentRate']}</div>", unsafe_allow_html=True)
            with cols[3]:
                badge_map = {"cut": "🟢 降息", "hold": "🔵 按兵", "hike": "🔴 升息"}
                st.markdown(f"<div style='font-size:11px'>{badge_map.get(b['trend'],'')}</div>", unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # TAB 2: FX
    # ══════════════════════════════════════════════════════════════════════
    with tab_fx:
        st.markdown("<div style='color:#94A3B8;font-size:11px;margin-bottom:12px'>📡 FRED API · 每日更新 · 每小時自動刷新</div>", unsafe_allow_html=True)

        with st.spinner("載入匯率數據（FRED API）…"):
            fx_data = fetch_all_fx()

        cols = st.columns(3)
        for i, fx in enumerate(FX_SERIES):
            d = fx_data.get(fx["pair"])
            with cols[i]:
                if d:
                    chg = d["change"]
                    is_pos = chg >= 0
                    chg_color = "#F87171" if is_pos else "#34D399"
                    chg_bg    = "#450A0A" if is_pos else "#064E3B"
                    chg_sym   = "▲" if is_pos else "▼"
                    # Format price
                    pair = fx["pair"]
                    if pair == "USD/JPY":
                        price_str = f"{d['price']:.2f}"
                    elif pair == "USD/TWD":
                        price_str = f"{d['price']:.3f}"
                    else:
                        price_str = f"{d['price']:.4f}"

                    st.markdown(f"""
                    <div class='metric-card'>
                        <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:4px'>
                            <div style='color:{fx["color"]};font-size:13px;font-weight:700'>{pair}</div>
                            <span style='font-size:11px;color:{chg_color};background:{chg_bg};padding:2px 7px;border-radius:4px'>{chg_sym} {abs(chg):.2f}%</span>
                        </div>
                        <div style='color:#F1F5F9;font-size:28px;font-weight:800;letter-spacing:-0.02em'>{price_str}</div>
                        <div style='color:#475569;font-size:10px;margin-bottom:6px'>52W: {d["lo"]:.4f} – {d["hi"]:.4f} · FRED {d["date"]}</div>
                        <hr style='border-color:#1E293B;margin:8px 0'>
                        <div style='color:#94A3B8;font-size:11px;line-height:1.6'>{fx["note"]}</div>
                    </div>
                    """, unsafe_allow_html=True)
                else:
                    st.error(f"{fx['pair']} 數據抓取失敗")

        # Yield curve in FX tab too
        st.markdown("---")
        st.markdown("<div style='color:#94A3B8;font-size:11px;letter-spacing:0.1em;margin-bottom:8px'>美國殖利率曲線對比（FRED）</div>", unsafe_allow_html=True)
        with st.spinner("載入殖利率…"):
            all_obs2 = fetch_all_yields()
        today_dt = datetime.now()
        curves2 = {
            "now": build_yield_curve(all_obs2, today_dt),
            "1m":  build_yield_curve(all_obs2, today_dt - timedelta(days=31)),
            "6m":  build_yield_curve(all_obs2, today_dt - timedelta(days=183)),
            "1y":  build_yield_curve(all_obs2, today_dt - timedelta(days=365)),
        }
        if curves2["now"]:
            st.plotly_chart(build_yield_curve_chart(curves2), use_container_width=True)
        else:
            st.warning("殖利率載入中…")

    # ══════════════════════════════════════════════════════════════════════
    # TAB 3: MACRO
    # ══════════════════════════════════════════════════════════════════════
    with tab_macro:
        st.markdown(f"""
        <div style='background:#080F1A;border:1px solid #3B82F644;border-radius:12px;padding:18px;margin-bottom:14px'>
            <div style='color:#F1F5F9;font-size:14px;font-weight:700;margin-bottom:10px'>2026 Q2 主題：利率高原期 × 中東地緣衝擊</div>
            <div style='color:#94A3B8;font-size:12px;line-height:1.8'>
                全球並非在「降息循環」中，而是進入曖昧的「利率高原期」。Fed/ECB/BOE 均按兵不動，BOJ 緩步升息正常化，RBA 反向升息。
                中東戰爭（美以對伊朗）是最大變數：油價衝擊同時推高通膨、壓低成長，各央行陷入類停滯膨脹困境，降息窗口後推、升息風險反升。
            </div>
            <div style='color:#475569;font-size:10px;margin-top:8px'>⚠ 大局觀為手動更新（{LAST_MANUAL_UPDATE}），不自動刷新</div>
        </div>
        """, unsafe_allow_html=True)

        cols = st.columns(2)
        for i, b in enumerate(BANKS):
            with cols[i % 2]:
                trend_map2 = {"cut": "🟢 降息 ▼", "hold": "🔵 按兵 →", "hike": "🔴 升息 ▲"}
                st.markdown(f"""
                <div style='background:#080F1A;border:1px solid {b["color"]}33;border-radius:12px;padding:16px;margin-bottom:12px'>
                    <div style='display:flex;justify-content:space-between;align-items:center;margin-bottom:8px'>
                        <div style='color:{b["color"]};font-size:13px;font-weight:700'>{b["flag"]} {b["name"]}</div>
                        <span style='font-size:11px'>{trend_map2.get(b["trend"],"")}</span>
                    </div>
                    <div style='color:#E2E8F0;font-size:17px;font-weight:800;margin-bottom:4px'>{b["currentRate"]}</div>
                    <div style='color:#94A3B8;font-size:11px;line-height:1.6;margin-bottom:8px'>{b["analysis"][-1]["text"]}</div>
                    <div style='background:{b["color"]}11;border-radius:6px;padding:5px 10px;color:{b["color"]};font-size:11px'>📅 下次：{b["nextMeeting"]}</div>
                </div>
                """, unsafe_allow_html=True)

        st.markdown("<div style='color:#EF4444;font-size:11px;letter-spacing:0.1em;margin-bottom:12px'>⚠️ 關鍵尾部風險</div>", unsafe_allow_html=True)
        for r in TAIL_RISKS:
            st.markdown(f"""
            <div style='display:flex;gap:10px;margin-bottom:10px;padding-bottom:10px;border-bottom:1px solid #0F172A'>
                <div style='font-size:18px;flex-shrink:0'>{r["icon"]}</div>
                <div>
                    <div style='color:#E2E8F0;font-size:12px;font-weight:700;margin-bottom:2px'>{r["risk"]}</div>
                    <div style='color:#64748B;font-size:11px;line-height:1.5'>{r["detail"]}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ══════════════════════════════════════════════════════════════════════
    # TAB 4 & 5: CALENDAR + SPEECHES (AI powered)
    # ══════════════════════════════════════════════════════════════════════
    def render_ai_section(section: str):
        # Sidebar for API key
        anthropic_key = st.sidebar.text_input(
            "Anthropic API Key（選填，用於 AI 行事曆）",
            type="password",
            key="anthropic_key",
            help="填入後可啟用 AI 自動抓取本週數據與官員談話"
        )

        week_key = f"macro_weekly_{datetime.now().strftime('%Y-W%V')}"
        cached = st.session_state.get(week_key)

        col_a, col_b = st.columns([3, 1])
        with col_b:
            force = st.button("↻ 強制重整", key=f"refresh_{section}")

        if cached and not force:
            weekly = cached
            st.markdown("<div style='color:#22C55E;font-size:11px;margin-bottom:12px'>✓ AI 已更新（本週快取）</div>", unsafe_allow_html=True)
        elif anthropic_key:
            with st.spinner("Claude AI 正在搜尋本週經濟數據… 約需 15–30 秒"):
                weekly = fetch_weekly_from_ai(anthropic_key)
            if weekly:
                st.session_state[week_key] = weekly
                st.markdown("<div style='color:#22C55E;font-size:11px;margin-bottom:12px'>✓ AI 已更新</div>", unsafe_allow_html=True)
            else:
                st.error("AI 抓取失敗，請重試。")
                return
        else:
            st.info("請在左側 Sidebar 輸入 Anthropic API Key 以啟用 AI 行事曆功能。\n\n或您可以手動查閱 [Investing.com](https://www.investing.com/economic-calendar/) 取得本週數據。")
            return

        if section == "calendar" and weekly:
            # This week
            st.markdown("<div style='color:#F59E0B;font-size:11px;letter-spacing:0.1em;margin-bottom:10px'>📅 本週重要數據</div>", unsafe_allow_html=True)
            this_week = weekly.get("thisWeek", [])
            if this_week:
                df_tw = pd.DataFrame(this_week)
                df_tw.columns = ["日期", "地區", "事件", "結果", "前值", "重要性", "說明"] if len(df_tw.columns) == 7 else df_tw.columns
                st.dataframe(df_tw, use_container_width=True, hide_index=True)

            # Next week
            st.markdown("<div style='color:#3B82F6;font-size:11px;letter-spacing:0.1em;margin:16px 0 10px'>📋 下週重要事件</div>", unsafe_allow_html=True)
            next_week = weekly.get("nextWeek", [])
            if next_week:
                df_nw = pd.DataFrame(next_week)
                st.dataframe(df_nw, use_container_width=True, hide_index=True)

        elif section == "speeches" and weekly:
            speeches = weekly.get("speeches", [])
            if not speeches:
                st.info("本期無官員談話記錄")
                return
            org_colors = {"Fed": "#3B82F6", "ECB": "#10B981", "BOJ": "#EF4444", "BOE": "#F59E0B", "RBA": "#8B5CF6"}
            for s in speeches:
                c = org_colors.get(s.get("org", ""), s.get("color", "#64748B"))
                st.markdown(f"""
                <div style='background:#080F1A;border:1px solid {c}33;border-radius:12px;padding:18px;margin-bottom:12px'>
                    <div style='display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:10px'>
                        <div>
                            <div style='color:{c};font-size:12px;font-weight:700;margin-bottom:2px'>{s.get("flag","")} {s.get("who","")}</div>
                            <div style='color:#94A3B8;font-size:13px;font-weight:700'>{s.get("title","")}</div>
                        </div>
                        <div style='color:#475569;font-size:11px;flex-shrink:0'>📅 {s.get("date","")}</div>
                    </div>
                    <hr style='border-color:#1E293B;margin:10px 0'>
                    <div style='color:#94A3B8;font-size:12px;line-height:1.7'>
                        <span style='color:{c};font-weight:700'>重點：</span>{s.get("key","")}
                    </div>
                </div>
                """, unsafe_allow_html=True)

    with tab_cal:
        render_ai_section("calendar")

    with tab_speeches:
        render_ai_section("speeches")

    # Footer
    st.markdown("""
    <div style='margin-top:24px;padding-top:12px;border-top:1px solid #0F172A;color:#1E293B;font-size:10px'>
        數據來源：FRED (St. Louis Fed) · Claude AI 網路搜尋 · 各央行官網 · 僅供參考，非投資建議 · v5.0 Streamlit Edition
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
