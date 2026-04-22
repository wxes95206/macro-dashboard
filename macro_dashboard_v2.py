#!/usr/bin/env python3
"""
Macro Dashboard — Python CLI Version
=====================================
功能：
  1. 從 Yahoo Finance 抓取即時匯率（EUR/USD、USD/JPY、USD/TWD）
  2. 從 Yahoo Finance 抓取美國公債殖利率（2Y、5Y、10Y、30Y）
  3. 呼叫 Claude API（含 web_search 工具）整理：
       - 本週重要經濟數據
       - 下週重要事件預告
       - 近兩週央行官員重要談話

使用方式：
  pip install requests anthropic
  export ANTHROPIC_API_KEY="sk-ant-..."
  python macro_dashboard.py

  # 只抓市場數據（不呼叫 Claude）
  python macro_dashboard.py --market-only

  # 只抓 AI 週報（不抓 Yahoo Finance）
  python macro_dashboard.py --ai-only

  # 輸出 JSON 檔案
  python macro_dashboard.py --output report.json
"""

import os
import sys
import json
import argparse
import datetime
import requests
from typing import Optional

# ─────────────────────────────────────────────────────────────────────────────
# 央行靜態資料（每次央行開會後手動更新）
# ─────────────────────────────────────────────────────────────────────────────
LAST_MANUAL_UPDATE = "2026-04-22"

BANKS = [
    {
        "id": "fed", "flag": "🇺🇸", "name": "Fed", "fullName": "聯準會 Federal Reserve",
        "currentRate": "3.50–3.75%", "rateNum": 3.625,
        "trend": "hold", "prevAction": "▼ 降25bps（2025/12）→ 連續按兵不動",
        "nextMeeting": "2026/05/06–07",
        "shortView": "觀望，中東通膨壓力使降息推遲",
    },
    {
        "id": "ecb", "flag": "🇪🇺", "name": "ECB", "fullName": "歐洲央行 ECB",
        "currentRate": "2.15%", "rateNum": 2.15,
        "trend": "hold", "prevAction": "▼ 降息循環（2024–2025）已結束",
        "nextMeeting": "2026/04/29–30",
        "shortView": "按兵不動，中東能源衝擊使通膨反升至 2.6%",
    },
    {
        "id": "boe", "flag": "🇬🇧", "name": "BOE", "fullName": "英國央行 BOE",
        "currentRate": "3.75%", "rateNum": 3.75,
        "trend": "hold", "prevAction": "▼ 降25bps（2025/12），2026年均按兵不動",
        "nextMeeting": "2026/05/08",
        "shortView": "停滯困境：通膨頑固 × 成長停滯",
    },
    {
        "id": "boj", "flag": "🇯🇵", "name": "BOJ", "fullName": "日本央行 BOJ",
        "currentRate": "0.75%", "rateNum": 0.75,
        "trend": "hold", "prevAction": "▲ 升至 0.75%（2026/01），其後暫停",
        "nextMeeting": "2026/04/27–28",
        "shortView": "暫停升息，緊盯中東與薪資走勢",
    },
    {
        "id": "rba", "flag": "🇦🇺", "name": "RBA", "fullName": "澳洲央行 RBA",
        "currentRate": "4.10%", "rateNum": 4.10,
        "trend": "hike", "prevAction": "▲ 升25bps（2026/02）→ ▲ 升25bps（2026/03）",
        "nextMeeting": "2026/05/19–20",
        "shortView": "反向升息，供給側通膨壓力難消",
    },
]

FX_SYMBOLS = [
    {"pair": "EUR/USD", "symbol": "EURUSD=X"},
    {"pair": "USD/JPY", "symbol": "JPY=X"},
    {"pair": "USD/TWD", "symbol": "TWD=X"},
]

YIELD_SYMBOLS = [
    {"label": "2Y",  "symbol": "^IRX",  "desc": "2年期（政策預期）", "maturity_sort": 2},
    {"label": "5Y",  "symbol": "^FVX",  "desc": "5年期",             "maturity_sort": 5},
    {"label": "10Y", "symbol": "^TNX",  "desc": "10年期（基準）",     "maturity_sort": 10},
    {"label": "30Y", "symbol": "^TYX",  "desc": "30年期（長端）",     "maturity_sort": 30},
]

# ─────────────────────────────────────────────────────────────────────────────
# Yahoo Finance 抓取
# ─────────────────────────────────────────────────────────────────────────────
def fetch_yahoo_price(symbol: str) -> dict:
    """
    透過 Yahoo Finance API 取得最新收盤價與漲跌幅。
    殖利率 symbols (^FVX, ^TNX, ^TYX) 回傳值需除以 10 換算成 %。
    ^IRX（2Y）直接為 % 值，需除以 100。
    """
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{requests.utils.quote(symbol)}?interval=1d&range=5d"
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("chart", {}).get("result", [{}])[0]
        closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        closes = [c for c in closes if c is not None]
        if not closes:
            return {"price": None, "change": 0.0, "ok": False, "error": "No close data"}
        curr = closes[-1]
        prev = closes[-2] if len(closes) >= 2 else curr
        change_pct = ((curr - prev) / prev * 100) if prev else 0.0
        return {"price": curr, "change": change_pct, "ok": True}
    except Exception as e:
        return {"price": None, "change": 0.0, "ok": False, "error": str(e)}


def fmt_price(price: Optional[float], symbol: str) -> str:
    if price is None:
        return "—"
    if symbol in ("JPY=X", "TWD=X"):
        return f"{price:.2f}"
    if symbol.startswith("^"):
        return f"{price:.4f}"  # raw value, will be converted separately
    return f"{price:.4f}"


def fetch_all_fx() -> list:
    """抓取所有匯率"""
    results = []
    for item in FX_SYMBOLS:
        r = fetch_yahoo_price(item["symbol"])
        price_str = fmt_price(r["price"], item["symbol"])
        change_str = f"{r['change']:+.3f}%" if r["ok"] else "—"
        results.append({
            "pair": item["pair"],
            "symbol": item["symbol"],
            "price": r["price"],
            "price_str": price_str,
            "change": r["change"],
            "change_str": change_str,
            "ok": r["ok"],
        })
    return results


def convert_yield_raw(raw: float, symbol: str) -> float:
    """Yahoo Finance 殖利率原始值換算成 %。
    ^IRX（13週）：原始值已是 %（e.g. 4.32 → 4.32%）
    ^FVX / ^TNX / ^TYX：原始值為 tenths（e.g. 43.2 → 4.32%）
    """
    if symbol == "^IRX":
        return raw  # 已是 %，不需換算
    return raw / 10.0


def fetch_yield_history_for_symbol(symbol: str) -> dict:
    """
    抓取單一殖利率 symbol 的兩年歷史，回傳以 date（YYYY-MM-DD）為 key 的收盤價 dict。
    """
    url = (
        f"https://query1.finance.yahoo.com/v8/finance/chart/"
        f"{requests.utils.quote(symbol)}?interval=1d&range=2y"
    )
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}
    try:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        result = data.get("chart", {}).get("result", [{}])[0]
        timestamps = result.get("timestamp", [])
        closes = result.get("indicators", {}).get("quote", [{}])[0].get("close", [])
        history = {}
        for ts, close in zip(timestamps, closes):
            if close is None:
                continue
            date_str = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%d")
            history[date_str] = convert_yield_raw(close, symbol)
        return history
    except Exception as e:
        return {}


def find_closest_date(history: dict, target_date: datetime.date, tolerance_days: int = 5) -> Optional[float]:
    """在 history dict 中找最接近 target_date 的值（往前找，允許 tolerance_days 天誤差）。"""
    for delta in range(tolerance_days + 1):
        d = (target_date - datetime.timedelta(days=delta)).strftime("%Y-%m-%d")
        if d in history:
            return history[d]
    return None


def fetch_all_yields_with_history() -> dict:
    """
    抓取所有殖利率的兩年歷史，回傳：
      today / 1m_ago / 6m_ago / 1y_ago 四條殖利率曲線，
      每條為 list of {label, maturity, value}，依天期由小到大排列。
    """
    today = datetime.date.today()
    targets = {
        "today":  today,
        "1m_ago": today - datetime.timedelta(days=30),
        "6m_ago": today - datetime.timedelta(days=182),
        "1y_ago": today - datetime.timedelta(days=365),
    }

    # 先把每個 symbol 的歷史全部抓回來
    all_history = {}
    for item in YIELD_SYMBOLS:
        print(f"   抓取 {item['label']} ({item['symbol']}) 歷史...")
        all_history[item["symbol"]] = fetch_yield_history_for_symbol(item["symbol"])

    # 組裝四條曲線（按 maturity 排序）
    curves = {key: [] for key in targets}
    for item in sorted(YIELD_SYMBOLS, key=lambda x: x.get("maturity_sort", 0)):
        sym = item["symbol"]
        history = all_history[sym]
        for curve_key, target_date in targets.items():
            value = find_closest_date(history, target_date)
            curves[curve_key].append({
                "label": item["label"],
                "desc": item["desc"],
                "value": round(value, 3) if value is not None else None,
                "ok": value is not None,
            })

    return {"curves": curves, "as_of": today.isoformat()}


def fetch_all_yields() -> list:
    """抓取所有殖利率（僅今日，向下相容）"""
    result = fetch_all_yields_with_history()
    return result["curves"]["today"]


# ─────────────────────────────────────────────────────────────────────────────
# Claude API — AI 週報
# ─────────────────────────────────────────────────────────────────────────────
def fetch_weekly_data_from_ai(api_key: str) -> dict:
    """
    呼叫 Claude API（含 web_search 工具）取得：
      - thisWeek: 本週重要經濟數據
      - nextWeek: 下週重要事件
      - speeches: 近兩週央行官員談話
    回傳解析後的 dict。
    """
    today = datetime.date.today()
    # 週一為起點
    week_start = today - datetime.timedelta(days=today.weekday())
    week_end = week_start + datetime.timedelta(days=6)

    prompt = f"""Today is {today.isoformat()}. Current week: {week_start.isoformat()} to {week_end.isoformat()}.

You are a macro research assistant. Please provide:

1. THIS_WEEK_DATA: Important global economic data releases this week (already released or scheduled). Include: date, region emoji, event name, result (actual if released, "待公布" if pending), previous value, impact (high/medium/low), brief note in Traditional Chinese.

2. NEXT_WEEK_DATA: Important data releases and central bank meetings next week. Include: date, region emoji, event name, impact, brief note in Traditional Chinese.

3. SPEECHES: Recent important central bank official speeches from the past 2 weeks (Fed, ECB, BOJ, BOE, RBA). Include: date (MM/DD), who (name + title), org (Fed/ECB/BOJ/BOE/RBA), title of speech/event, key points in Traditional Chinese, flag emoji.

Respond ONLY with valid JSON, no markdown, no preamble:
{{
  "thisWeek": [{{"date":"","region":"","event":"","result":"","prev":"","impact":"","note":""}}],
  "nextWeek": [{{"date":"","region":"","event":"","impact":"","note":""}}],
  "speeches": [{{"date":"","who":"","org":"","title":"","key":"","flag":""}}]
}}

Focus on: US (CPI, NFP, GDP, retail sales, PCE, FOMC), Eurozone (CPI, PMI, ECB meeting), UK (CPI, BOE), Japan (CPI, BOJ meeting), Australia (CPI, RBA). Only include high-impact events."""

    payload = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 2000,
        "tools": [{"type": "web_search_20250305", "name": "web_search"}],
        "messages": [{"role": "user", "content": prompt}],
    }
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01",
    }

    resp = requests.post(
        "https://api.anthropic.com/v1/messages",
        json=payload,
        headers=headers,
        timeout=60,
    )
    resp.raise_for_status()
    data = resp.json()

    # 找最後一個 text block
    text_block = None
    for block in reversed(data.get("content", [])):
        if block.get("type") == "text":
            text_block = block["text"]
            break

    if not text_block:
        raise ValueError("Claude 回應中找不到 text block")

    # 清理並解析 JSON
    raw = text_block.replace("```json", "").replace("```", "").strip()
    start = raw.find("{")
    end = raw.rfind("}") + 1
    if start == -1 or end == 0:
        raise ValueError(f"找不到 JSON 內容。原始回應：{raw[:200]}")
    return json.loads(raw[start:end])


# ─────────────────────────────────────────────────────────────────────────────
# 顯示函數（CLI）
# ─────────────────────────────────────────────────────────────────────────────
TREND_LABELS = {"cut": "降息 ▼", "hold": "按兵 →", "hike": "升息 ▲"}
SEPARATOR = "─" * 70


def print_header(title: str):
    print(f"\n{'═' * 70}")
    print(f"  {title}")
    print(f"{'═' * 70}")


def print_section(title: str):
    print(f"\n{'─' * 70}")
    print(f"  {title}")
    print(f"{'─' * 70}")


def display_banks():
    print_header("🏦 央行政策利率總覽")
    print(f"  最後手動更新：{LAST_MANUAL_UPDATE}\n")
    for b in BANKS:
        trend = TREND_LABELS.get(b["trend"], b["trend"])
        print(f"  {b['flag']} {b['name']:6s}  {b['currentRate']:12s}  [{trend}]")
        print(f"         下次會議：{b['nextMeeting']}")
        print(f"         {b['shortView']}")
        print()


def display_fx(fx_data: list):
    print_header("💱 即時匯率（Yahoo Finance）")
    print(f"  {'幣對':<12} {'價格':>12} {'漲跌':>10}  狀態")
    print(f"  {SEPARATOR}")
    for item in fx_data:
        status = "✅" if item["ok"] else "⚠️"
        chg = item["change_str"]
        direction = "▲" if item["change"] > 0 else ("▼" if item["change"] < 0 else "→")
        print(f"  {item['pair']:<12} {item['price_str']:>12} {direction}{chg:>9}  {status}")


def display_yields_with_history(yield_result: dict):
    """顯示殖利率四條曲線表格，並用 matplotlib 畫圖。"""
    curves = yield_result["curves"]
    as_of = yield_result.get("as_of", "")

    print_header(f"📈 美國公債殖利率曲線（Yahoo Finance）  as of {as_of}")

    curve_meta = [
        ("today",  "今日",      "━"),
        ("1m_ago", "1個月前",   "╌"),
        ("6m_ago", "6個月前",   "╌"),
        ("1y_ago", "1年前",     "╌"),
    ]

    # 表格
    labels = [item["label"] for item in curves["today"]]
    header = f"  {'曲線':<12}" + "".join(f" {lb:>8}" for lb in labels)
    print(header)
    print(f"  {SEPARATOR}")

    for key, name, _ in curve_meta:
        row = curves.get(key, [])
        vals = "".join(
            (" {:>8}".format(f"{pt['value']:.3f}%") if pt["value"] is not None else " {:>8}".format("—"))
            for pt in row
        )
        print(f"  {name:<12}{vals}")

    # 10Y−2Y 利差（今日）
    today_curve = curves["today"]
    y2  = next((p for p in today_curve if p["label"] == "2Y"),  None)
    y10 = next((p for p in today_curve if p["label"] == "10Y"), None)
    if y2 and y10 and y2["value"] and y10["value"]:
        spread = y10["value"] - y2["value"]
        direction = "正斜率 ✅" if spread >= 0 else "倒掛 ⚠️"
        print(f"\n  10Y−2Y 利差（今日）：{spread:+.3f}%  {direction}")

    # matplotlib 圖表
    _plot_yield_curves(curves, as_of)


def _plot_yield_curves(curves: dict, as_of: str):
    """用 matplotlib 畫四條殖利率曲線並儲存圖檔。"""
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.ticker as ticker
    except ImportError:
        print("\n  ℹ️  安裝 matplotlib 可產生殖利率曲線圖：pip install matplotlib")
        return

    today = datetime.date.today()
    curve_styles = [
        ("today",  f"今日 ({as_of})",              "#3B82F6", 2.5, "solid"),
        ("1m_ago", f"1個月前 ({(today - datetime.timedelta(days=30)).strftime('%Y-%m-%d')})",  "#10B981", 1.8, "dashed"),
        ("6m_ago", f"6個月前 ({(today - datetime.timedelta(days=182)).strftime('%Y-%m-%d')})", "#F59E0B", 1.8, "dashed"),
        ("1y_ago", f"1年前 ({(today - datetime.timedelta(days=365)).strftime('%Y-%m-%d')})",   "#EF4444", 1.8, "dashed"),
    ]

    fig, ax = plt.subplots(figsize=(9, 5))
    fig.patch.set_facecolor("#0D1829")
    ax.set_facecolor("#0D1829")

    maturities = [2, 5, 10, 30]
    labels = ["2Y", "5Y", "10Y", "30Y"]

    for key, label, color, lw, ls in curve_styles:
        pts = curves.get(key, [])
        ys = [pt["value"] for pt in pts]
        if all(v is None for v in ys):
            continue
        # 只畫有值的點
        x_plot = [maturities[i] for i, v in enumerate(ys) if v is not None]
        y_plot = [v for v in ys if v is not None]
        ax.plot(x_plot, y_plot, color=color, linewidth=lw, linestyle=ls,
                marker="o", markersize=5 if key == "today" else 4,
                markerfacecolor=color, markeredgecolor="#0D1829", markeredgewidth=1,
                label=label, zorder=3 if key == "today" else 2)
        # 標注今日數值
        if key == "today":
            for xi, yi in zip(x_plot, y_plot):
                ax.annotate(f"{yi:.2f}%", (xi, yi),
                            textcoords="offset points", xytext=(0, 9),
                            ha="center", fontsize=8, color=color, fontweight="bold")

    # 格線
    ax.grid(True, color="#1E293B", linewidth=0.7, alpha=0.8)
    ax.set_xticks(maturities)
    ax.set_xticklabels(labels, color="#94A3B8", fontsize=10)
    ax.tick_params(axis="y", colors="#94A3B8", labelsize=9)
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter("%.2f%%"))
    ax.spines[:].set_color("#1E293B")

    ax.set_title("🇺🇸 美國公債殖利率曲線", color="#E2E8F0", fontsize=13,
                 fontweight="bold", pad=14)
    ax.set_xlabel("天期", color="#64748B", fontsize=10)
    ax.set_ylabel("殖利率 (%)", color="#64748B", fontsize=10)

    legend = ax.legend(loc="best", framealpha=0.15, facecolor="#1E293B",
                       edgecolor="#334155", labelcolor="#E2E8F0", fontsize=9)

    plt.tight_layout()
    out_path = "yield_curve.png"
    plt.savefig(out_path, dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close()
    print(f"\n  📊 殖利率曲線圖已儲存：{out_path}")


def display_weekly(weekly: dict):
    # 本週數據
    print_section("📅 本週重要經濟數據")
    this_week = weekly.get("thisWeek", [])
    if this_week:
        print(f"  {'日期':<8} {'地區':<4} {'影響':<6} {'事件':<30} {'結果':<12} {'前值'}")
        print(f"  {SEPARATOR}")
        for row in this_week:
            impact_icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(row.get("impact", ""), "  ")
            result = row.get("result", "—")
            result_display = result if result != "待公布" else "⏳ 待公布"
            print(f"  {row.get('date',''):<8} {row.get('region',''):<4} {impact_icon:<4}  "
                  f"{row.get('event',''):<30} {result_display:<14} {row.get('prev','')}")
            if row.get("note"):
                print(f"           💬 {row['note']}")
    else:
        print("  （無資料）")

    # 下週事件
    print_section("📋 下週重要事件")
    next_week = weekly.get("nextWeek", [])
    if next_week:
        print(f"  {'日期':<8} {'地區':<4} {'影響':<6} {'事件'}")
        print(f"  {SEPARATOR}")
        for row in next_week:
            impact_icon = {"high": "🔴", "medium": "🟡", "low": "⚪"}.get(row.get("impact", ""), "  ")
            print(f"  {row.get('date',''):<8} {row.get('region',''):<4} {impact_icon:<4}  {row.get('event','')}")
            if row.get("note"):
                print(f"           💬 {row['note']}")
    else:
        print("  （無資料）")

    # 官員談話
    print_section("🎤 近兩週央行官員重要談話")
    speeches = weekly.get("speeches", [])
    if speeches:
        for s in speeches:
            print(f"\n  {s.get('flag','')} [{s.get('date','')}] {s.get('who','')} ({s.get('org','')})")
            print(f"  📝 {s.get('title','')}")
            print(f"  重點：{s.get('key','')}")
    else:
        print("  （無資料）")


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(description="Macro Dashboard — Python CLI")
    parser.add_argument("--market-only", action="store_true", help="只抓市場數據（不呼叫 Claude API）")
    parser.add_argument("--ai-only",     action="store_true", help="只抓 AI 週報（不抓 Yahoo Finance）")
    parser.add_argument("--output",      type=str,            help="輸出 JSON 至指定檔案（例：report.json）")
    parser.add_argument("--api-key",     type=str,            help="Anthropic API Key（也可透過 ANTHROPIC_API_KEY 環境變數設定）")
    args = parser.parse_args()

    api_key = args.api_key or os.environ.get("ANTHROPIC_API_KEY", "")
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n{'█' * 70}")
    print(f"  🌍  MACRO DASHBOARD  —  Python v1.0")
    print(f"  📅  {now}")
    print(f"{'█' * 70}")

    report = {"generated_at": now, "banks": BANKS}

    # ── 市場數據 ──────────────────────────────────────────────────────────────
    if not args.ai_only:
        print("\n⏳ 正在抓取 Yahoo Finance 市場數據...")

        fx_data = fetch_all_fx()
        print("   匯率抓取完成。正在抓取殖利率歷史（2年）...")
        yield_result = fetch_all_yields_with_history()

        display_banks()
        display_fx(fx_data)
        display_yields_with_history(yield_result)

        report["fx"] = fx_data
        report["yields"] = yield_result
    else:
        display_banks()

    # ── AI 週報 ───────────────────────────────────────────────────────────────
    if not args.market_only:
        if not api_key:
            print("\n⚠️  未設定 Anthropic API Key。")
            print("   請執行：export ANTHROPIC_API_KEY='sk-ant-...'")
            print("   或使用參數：--api-key sk-ant-...")
        else:
            print("\n⏳ 正在呼叫 Claude API 整理本週經濟行事曆...")
            try:
                weekly = fetch_weekly_data_from_ai(api_key)
                display_weekly(weekly)
                report["weekly"] = weekly
            except Exception as e:
                print(f"\n❌ Claude API 呼叫失敗：{e}")

    # ── 輸出 JSON ─────────────────────────────────────────────────────────────
    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 報告已儲存至：{args.output}")

    print(f"\n{'─' * 70}")
    print("  數據來源：Yahoo Finance · Claude AI · 各央行官網")
    print("  ⚠️  僅供參考，非投資建議")
    print(f"{'─' * 70}\n")


if __name__ == "__main__":
    main()
