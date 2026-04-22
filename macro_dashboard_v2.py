import streamlit as st
import pandas as pd
import altair as alt

# ─── PAGE CONFIG ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="全球總經監控儀表板",
    page_icon="🌐",
    layout="wide",
)

# ─── DATA ────────────────────────────────────────────────────────────────────
LAST_UPDATED = "2026-04-22"

BANKS = [
    {
        "id": "fed",
        "flag": "🇺🇸",
        "name": "Fed",
        "fullName": "聯準會 Federal Reserve",
        "currentRate": "3.50–3.75%",
        "rateNum": 3.625,
        "depositRate": None,
        "trend": "hold",
        "prevAction": "▼ 降25bps（2025/12）→ 連續按兵不動",
        "nextMeeting": "2026/05/06–07",
        "color": "#3B82F6",
        "shortView": "觀望，中東通膨壓力使降息推遲",
        "analysis": [
            {"title": "現況", "text": "聯邦基金利率維持 3.50–3.75%，為2022年緊縮週期後的最低水準。Fed 在12月完成第三次連續降息後開始暫停，因通膨黏性高於預期。"},
            {"title": "通膨 vs 就業", "text": "核心 PCE 仍頑固維持在目標以上，勞動市場呈現低招募、低裁員的「冷卻」格局，並未觸發緊急降息需求。Fed 陷入兩難——既不想太快放鬆引發通膨回頭，也不想拖累就業。"},
            {"title": "中東衝擊", "text": "美伊衝突帶來油價大幅跳升，直接拉升通膨預期，令市場原本預期的 2026 年降息窗口一再後推。Fed 現在被迫以「觀望」取代「行動」。"},
            {"title": "Fed 主席交接", "text": "現任主席 Powell 任期至 5 月 15 日。提名人 Kevin Warsh（4/21 出席參議院聽證）強調「Fed 專注物價穩定」、重申獨立性，但確認提案受制於 Powell 司法調查爭議，目前仍有變數。"},
            {"title": "前瞻", "text": "市場定價 2026 年至多一次降息（可能在 Q3–Q4）。若油價持續高位、通膨難降，甚至不排除年內按兵不動。新主席上任態度為最大未知數。"},
        ],
        "extraData": [
            {"label": "2Y 殖利率", "value": "3.81%"},
            {"label": "10Y 殖利率", "value": "4.27%"},
            {"label": "30Y 殖利率", "value": "4.88%"},
            {"label": "10Y−2Y 利差", "value": "+0.46%", "highlight": True},
        ],
    },
    {
        "id": "ecb",
        "flag": "🇪🇺",
        "name": "ECB",
        "fullName": "歐洲央行 European Central Bank",
        "currentRate": "2.15%",
        "rateNum": 2.15,
        "depositRate": "存款利率 2.00% / 邊際貸款利率 2.40%",
        "trend": "hold",
        "prevAction": "▼ 降息循環（2024–2025），現已暫停",
        "nextMeeting": "2026/04/29–30",
        "color": "#10B981",
        "shortView": "按兵不動，中東能源衝擊使通膨反升",
        "analysis": [
            {"title": "三率結構", "text": "主要再融資利率（Main Refinancing Rate）2.15%，存款便利利率（Deposit Facility）2.00%，邊際貸款利率 2.40%。ECB 以存款利率作為主要政策工具。"},
            {"title": "降息循環終結", "text": "ECB 在 2024–2025 年間完成一輪大規模降息，後期 Lagarde 多次宣稱「已達好地方（in a good place）」。但中東油價衝擊使此說法在 2026 Q1 被迫修正。"},
            {"title": "通膨與成長", "text": "3月歐元區通膨回升至 2.6%（主因能源），核心通膨 2.3%，尚算可控。ECB 預測 2026 年 GDP 成長僅 0.9%，能源衝擊同時壓低成長、推高通膨，形成類停滯膨脹。"},
            {"title": "Lagarde IMF 談話（4/17）", "text": "在 IMF 春季年會上，Lagarde 表示中東戰爭對全球成長形成拖累、對通膨帶來上行風險，強調 ECB「well positioned and well equipped」，已備妥工具因應衝擊，但未給出明確利率指引。"},
            {"title": "前瞻", "text": "4/29–30 會議市場定價 74% 機率維持不變，26% 有升息可能（摩根士丹利等銀行提出此風險）。若中東衝突延燒、能源通膨持續，ECB 可能被迫重啟升息。降息在 2026 年幾乎不可能。"},
        ],
        "extraData": [],
    },
    {
        "id": "boe",
        "flag": "🇬🇧",
        "name": "BOE",
        "fullName": "英國央行 Bank of England",
        "currentRate": "3.75%",
        "rateNum": 3.75,
        "depositRate": None,
        "trend": "hold",
        "prevAction": "▼ 降25bps（2025/12），2026年均按兵不動",
        "nextMeeting": "2026/05/08",
        "color": "#F59E0B",
        "shortView": "停滯困境：通膨頑固 × 成長停滯",
        "analysis": [
            {"title": "英國特殊困境", "text": "BOE 面臨「三明治困境」：通膨仍頑固高於 3%、勞動市場工資增長強勁，但經濟成長幾乎停滯（2025 Q3 幾乎零成長）。降息有引發通膨之虞，升息則恐壓垮脆弱經濟。"},
            {"title": "貨幣政策委員會分裂", "text": "上次投票呈四鴿四鷹、Bailey 居中的格局。鷹派擔憂 3.6% 通膨根深柢固，鴿派聚焦就業市場疲軟。中東油價衝擊使鷹派佔據上風，3 月決議全票維持。"},
            {"title": "中東能源衝擊", "text": "英國高度依賴進口能源，油氣價格飆升直接傳導至家庭能源帳單，形成二輪通膨壓力。BOE 聲明「對工資與價格設定中的二輪效應保持高度警覺」。"},
            {"title": "財政空間有限", "text": "英國財政部已大幅擴張支出，BOE 幾乎只能獨自對抗通膨而缺乏財政配合，形成政策夾縫。"},
            {"title": "前瞻", "text": "5 月會議預計維持 3.75%。除非通膨數據在 Q2 出現顯著下降，否則 2026 年降息機會微乎其微。需緊密追蹤英國 CPI 月度數據（本週 4/23 公布）。"},
        ],
        "extraData": [],
    },
    {
        "id": "boj",
        "flag": "🇯🇵",
        "name": "BOJ",
        "fullName": "日本央行 Bank of Japan",
        "currentRate": "0.75%",
        "rateNum": 0.75,
        "depositRate": None,
        "trend": "hold",
        "prevAction": "▲ 升至 0.75%（2026/01），其後暫停",
        "nextMeeting": "2026/04/27–28",
        "color": "#EF4444",
        "shortView": "暫停升息，緊盯中東與薪資走勢",
        "analysis": [
            {"title": "政策正常化之路", "text": "BOJ 在 2024 年終結負利率後，持續緩步升息，目前 0.75% 為 1995 年以來最高。但升息步伐遠慢於市場原先預期。"},
            {"title": "4 月會議（4/27–28）", "text": "市場定價 97% 機率按兵不動。行長植田和男 4 月 17 日演講刻意避開升息訊號，引用中東不確定性作為暫停理由。唯一例外：委員高田篤（Takata）於上次會議異議主張升息至 1%。"},
            {"title": "薪資與通膨", "text": "春季薪資談判（春鬪）結果持續強勁，支撐核心通膨持續於 2% 附近。這是 BOJ 主要升息依據，一旦中東不確定性消散，升息節奏有望恢復。"},
            {"title": "日圓承壓", "text": "USD/JPY 維持 158–160 高位，顯示市場認為 BOJ 升息步伐不足以縮小利差。若日圓繼續貶值，可能倒逼 BOJ 加速行動，以防輸入性通膨惡化。"},
            {"title": "前瞻", "text": "BOJ 最可能在中東情勢明朗後（Q2–Q3）恢復升息。路透引述 BOJ 消息源指，若基本情境如期展開，6 月具備升息條件。全年累積可能再升息 1–2 次至 1.0–1.25%。"},
        ],
        "extraData": [],
    },
    {
        "id": "rba",
        "flag": "🇦🇺",
        "name": "RBA",
        "fullName": "澳洲央行 Reserve Bank of Australia",
        "currentRate": "4.10%",
        "rateNum": 4.10,
        "depositRate": None,
        "trend": "hike",
        "prevAction": "▲ 升25bps（2026/02）→ ▲ 升25bps（2026/03）",
        "nextMeeting": "2026/05/19–20",
        "color": "#8B5CF6",
        "shortView": "反向升息，供給側通膨壓力難消",
        "analysis": [
            {"title": "2026 反向升息", "text": "RBA 在 2025 年曾降息三次至 3.60%，卻因通膨捲土重來，2026 年 2 月和 3 月連續兩次各升息 25bps，利率重返 4.10%。為全球主要央行中少數仍在升息的央行。"},
            {"title": "通膨為何回升", "text": "澳洲私人需求超預期強勁、產能壓力大於評估。加上中東能源衝擊，副行長 Hauser 直言面臨「停滯膨脹惡夢」——成長放緩同時通膨加速，供給端無法提振，政策兩難。"},
            {"title": "委員會分歧", "text": "上次投票：四人支持升息，四人主張按兵不動（非主張降息）。反對派也未倡議寬鬆，顯示市場對未來走勢偏緊縮共識。市場定價年底可達 4.56%。"},
            {"title": "關鍵數據", "text": "Q1 2026 CPI 數據預計 4 月底公布，將是 5 月會議關鍵輸入。若通膨仍高，進一步升息幾乎確定；若顯著下滑，則可能暫停。"},
            {"title": "前瞻", "text": "分析師預測 2026 年利率合理區間為 4.10% 或再升一次至 4.35%。在中東油價高燒、通膨風險未消之前，降息完全無望。澳幣走勢高度連動 RBA 政策預期。"},
        ],
        "extraData": [],
    },
]

YIELD_CURVE_DATA = [
    {"label": "Fed Rate", "value": 3.625, "color": "#64748B", "desc": "基準利率"},
    {"label": "1Y", "value": 4.05, "color": "#60A5FA", "desc": "1年期"},
    {"label": "2Y", "value": 3.81, "color": "#3B82F6", "desc": "2年期 / 政策預期"},
    {"label": "5Y", "value": 4.10, "color": "#F59E0B", "desc": "5年期"},
    {"label": "10Y", "value": 4.27, "color": "#F97316", "desc": "10年期 / 基準"},
    {"label": "30Y", "value": 4.88, "color": "#EF4444", "desc": "30年期 / 長端"},
]

FX_DATA = [
    {
        "pair": "EUR/USD",
        "value": "1.1726",
        "valueNum": 1.1726,
        "ytd": "+0.22%",
        "dir": "up",
        "range52w": "1.1417 – 1.2022",
        "color": "#3B82F6",
        "analysis": "美元整體走弱（Fed 按兵不動 + 新主席不確定性），歐元相對受支撐。中東危機使美元短線出現避險需求，但中長期美元弱勢結構未變。ECB 4/29–30 會議若偏鷹，歐元有望進一步走強。",
    },
    {
        "pair": "USD/JPY",
        "value": "158.95",
        "valueNum": 158.95,
        "ytd": "+11.6% (1年)",
        "dir": "up",
        "range52w": "150.84 – 160.27",
        "color": "#EF4444",
        "analysis": "巨大利差（Fed 3.625% vs BOJ 0.75%）持續壓制日圓。USD/JPY 在 158–160 區間整固。BOJ 4/28 維持不動預期強（97%），短期日圓難以大幅回升。若 BOJ 6 月重啟升息，有望看到日圓反彈至 155 附近。",
    },
    {
        "pair": "USD/TWD",
        "value": "31.42",
        "valueNum": 31.42,
        "ytd": "-3.35% (1年)",
        "dir": "down",
        "range52w": "28.74 – 32.60",
        "color": "#10B981",
        "analysis": "新台幣近一年走強（美元相對弱），央行與美財政部簽署不干預聲明後台幣曾大幅升值。中東緊張使短線承壓（超額遠期合約顯示市場預期進一步走弱），但長期仍受台灣貿易順差與科技出口支撐。",
    },
]

THIS_WEEK = [
    {"date": "4/21 (二)", "region": "🇺🇸", "event": "美國零售銷售 (3月)", "result": "+1.7% MoM", "prev": "+0.6%", "impact": "high", "note": "超預期強勁，消費韌性支撐美元"},
    {"date": "4/21 (二)", "region": "🇺🇸", "event": "Warsh 參議院聽證", "result": "「Fed 保持獨立」", "prev": "—", "impact": "high", "note": "強調物價穩定優先，確認提案仍有政治變數"},
    {"date": "4/23 (四)", "region": "🌐", "event": "全球 Flash PMI（4月）", "result": "待公布", "prev": "見各國", "impact": "high", "note": "早期景氣指標，低於50顯示收縮"},
    {"date": "4/24 (五)", "region": "🇺🇸", "event": "耐久財訂單 (3月)", "result": "待公布", "prev": "+0.9%", "impact": "medium", "note": "資本支出前瞻指標"},
    {"date": "4/24 (五)", "region": "🇺🇸", "event": "密大消費者信心 (最終)", "result": "待公布", "prev": "—", "impact": "medium", "note": "消費預期風向標"},
    {"date": "4/23 (四)", "region": "🇬🇧", "event": "英國 CPI (3月)", "result": "待公布", "prev": "~3%", "impact": "high", "note": "影響 BOE 5月決策關鍵數據"},
]

NEXT_WEEK = [
    {"date": "4/28 (一)", "region": "🇯🇵", "event": "日本 BOJ 政策會議", "impact": "high", "note": "97% 維持 0.75%，聚焦後續指引語氣"},
    {"date": "4/29–30", "region": "🇪🇺", "event": "ECB 政策會議", "impact": "high", "note": "74% 維持，26% 升息機率，中東能源通膨為關鍵"},
    {"date": "4/30 (三)", "region": "🇺🇸", "event": "美國 GDP 初值 (Q1)", "impact": "high", "note": "衰退/成長確認指標，市場高度關注"},
    {"date": "4/30 (三)", "region": "🇺🇸", "event": "個人消費支出 PCE (3月)", "impact": "high", "note": "Fed 最重視通膨指標，影響 5 月決策"},
    {"date": "5/2 (五)", "region": "🇺🇸", "event": "非農就業（4月）NFP", "impact": "high", "note": "就業市場健康度，影響 Fed 降息時機"},
]

SPEECHES = [
    {
        "date": "4/21",
        "who": "Kevin Warsh（Fed 主席提名人）",
        "org": "Fed",
        "color": "#3B82F6",
        "title": "參議院聽證 — 貨幣政策獨立性",
        "key": "「我不認為貨幣政策獨立性在民選官員表達利率看法時受到特別威脅」；承諾「Fed 應守本分（stay in its lane）」；強調物價穩定優先於就業目標；暗示可能減少 FOMC 新聞發布會頻率。",
        "flag": "🇺🇸",
    },
    {
        "date": "4/17",
        "who": "Christine Lagarde（ECB 行長）",
        "org": "ECB",
        "color": "#10B981",
        "title": "IMF 春季年會 — IMFC 聲明",
        "key": "「全球經濟正在航行動盪水域」；中東戰爭對全球成長構成拖累、對通膨帶來上行風險；ECB「定位良好，備妥工具」但未預承諾任何利率路徑；歐元區 3 月通膨升至 2.6%，核心 2.3%，GDP 預測僅 0.9%。",
        "flag": "🇪🇺",
    },
    {
        "date": "4/17",
        "who": "植田和男（BOJ 行長）",
        "org": "BOJ",
        "color": "#EF4444",
        "title": "公開講話 — 避免升息訊號",
        "key": "4/17 演講刻意迴避升息訊號；強調中東地緣不確定性為主要制約因素；但路透社引述內部消息指，若基本情境如期，BOJ 最早 6 月可望重啟升息，實際利率仍顯著負值佐證仍有正常化空間。",
        "flag": "🇯🇵",
    },
    {
        "date": "4/16",
        "who": "Andrew Hauser（RBA 副行長）",
        "org": "RBA",
        "color": "#8B5CF6",
        "title": "IIF 全球展望論壇",
        "key": "直言面臨「惡夢般停滯膨脹情境」：成長放緩同時通膨加速；中東能源衝擊為重大收入衝擊，正侵蝕家庭購買力；強調 RBA 首要任務是防止通膨預期脫錨，即使這意味著短期犧牲成長。",
        "flag": "🇦🇺",
    },
]

TAIL_RISKS = [
    {"icon": "🛢️", "risk": "中東衝突持續", "detail": "油價維持高位 → 通膨再起 → 全球央行被迫升息 → 風險資產承壓"},
    {"icon": "🇺🇸", "risk": "Fed 主席交接不確定性", "detail": "Warsh 確認受阻，若 Powell 任期空窗，政策方向未明引發市場波動"},
    {"icon": "🇯🇵", "risk": "日圓繼續貶值", "detail": "BOJ 升息節奏若再落後，日圓恐突破 160 引發干預，或被迫跳升"},
    {"icon": "🇦🇺", "risk": "澳洲滯脹螺旋", "detail": "RBA 升息壓制需求，但供給側油價通膨無法藉利率解決，兩難加深"},
    {"icon": "📊", "risk": "美國 Q1 GDP 意外收縮", "detail": "4/30 公布，若為負值，衰退恐慌重燃，加速 Fed 降息預期"},
]

SOURCES = [
    ["利率決策", "federalreserve.gov / ecb.europa.eu / boj.or.jp / rba.gov.au"],
    ["殖利率", "fred.stlouisfed.org (DGS2, DGS10) / home.treasury.gov"],
    ["匯率", "wise.com/history 或 investing.com/currencies"],
    ["經濟行事曆", "forexfactory.com / investing.com/economic-calendar"],
    ["官員談話", "federalreserve.gov/speeches / bis.org/cbspeeches"],
    ["PMI 數據", "spglobal.com/marketintelligence/pmi"],
]

# ─── HELPERS ─────────────────────────────────────────────────────────────────
def trend_label(trend: str) -> str:
    return {
        "cut": "降息 ▼",
        "hold": "按兵 →",
        "hike": "升息 ▲",
    }.get(trend, trend)


def impact_label(impact: str) -> str:
    return {
        "high": "高",
        "medium": "中",
        "low": "低",
    }.get(impact, impact)


def render_header():
    st.title("全球總經監控儀表板")
    st.caption(f"Global Macro Monitor v2 · 利率 / 匯率 / 行事曆 / 官員談話 · 更新：{LAST_UPDATED}")
    st.divider()


def render_yield_curve():
    df = pd.DataFrame(YIELD_CURVE_DATA)
    chart = (
        alt.Chart(df)
        .mark_line(point=True, strokeWidth=3)
        .encode(
            x=alt.X("label:N", title="期限"),
            y=alt.Y("value:Q", title="殖利率 (%)", scale=alt.Scale(domain=[3.4, 5.2])),
            tooltip=["label", alt.Tooltip("value:Q", format=".2f"), "desc"],
        )
        .properties(height=280)
    )
    st.altair_chart(chart, use_container_width=True)

    col1, col2, col3 = st.columns(3)
    col1.metric("10Y−2Y 利差", "+0.46%", "正斜率")
    col2.metric("30Y−10Y", "+0.61%", "長端保費擴大")
    col3.metric("倒掛結束日", "2024/09/05", "此後持續正值")


def render_rates():
    bank_map = {f"{b['flag']} {b['name']}": b for b in BANKS}
    selected = st.selectbox("選擇央行", list(bank_map.keys()))
    bank = bank_map[selected]

    left, right = st.columns([1.05, 1], gap="large")

    with left:
        st.subheader(bank["fullName"])
        st.metric("當前利率", bank["currentRate"], trend_label(bank["trend"]))
        if bank["depositRate"]:
            st.write(f"**補充：** {bank['depositRate']}")
        st.write(f"**前次動作：** {bank['prevAction']}")
        st.write(f"**下次會議：** {bank['nextMeeting']}")
        st.info(bank["shortView"])

        if bank["extraData"]:
            st.markdown("#### 美國殖利率曲線（現況）")
            render_yield_curve()
            extra_cols = st.columns(2)
            for idx, item in enumerate(bank["extraData"]):
                with extra_cols[idx % 2]:
                    st.metric(item["label"], item["value"])

    with right:
        st.markdown("#### 深度分析")
        for item in bank["analysis"]:
            with st.container(border=True):
                st.markdown(f"**{item['title']}**")
                st.write(item["text"])

    st.markdown("#### 各央行利率比較")
    rate_df = pd.DataFrame(BANKS)
    rate_chart = (
        alt.Chart(rate_df)
        .mark_bar(cornerRadiusTopRight=3, cornerRadiusBottomRight=3)
        .encode(
            x=alt.X("rateNum:Q", title="政策利率 (%)"),
            y=alt.Y("name:N", sort="-x", title="央行"),
            color=alt.Color("name:N", legend=None),
            tooltip=["fullName", "currentRate", "prevAction", "nextMeeting"],
        )
        .properties(height=260)
    )
    st.altair_chart(rate_chart, use_container_width=True)


def render_fx():
    st.subheader("主要匯率")
    cols = st.columns(len(FX_DATA))
    for col, fx in zip(cols, FX_DATA):
        with col:
            with st.container(border=True):
                st.markdown(f"### {fx['pair']}")
                st.metric("現值", fx["value"], fx["ytd"])
                st.write(f"**52 週區間：** {fx['range52w']}")
                st.write(fx["analysis"])

    fx_df = pd.DataFrame(FX_DATA)
    chart = (
        alt.Chart(fx_df)
        .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4)
        .encode(
            x=alt.X("pair:N", title="貨幣對"),
            y=alt.Y("valueNum:Q", title="現值"),
            color=alt.Color("pair:N", legend=None),
            tooltip=["pair", alt.Tooltip("valueNum:Q", format=".4f"), "range52w", "ytd"],
        )
        .properties(height=320)
    )
    st.altair_chart(chart, use_container_width=True)


def render_macro():
    st.subheader("全球大局觀")
    st.markdown("#### 各央行一句話前瞻")
    cols = st.columns(len(BANKS))
    for col, bank in zip(cols, BANKS):
        with col:
            with st.container(border=True):
                st.markdown(f"**{bank['flag']} {bank['name']}**")
                st.write(bank["analysis"][-1]["text"])
                st.caption(f"下次會議：{bank['nextMeeting']}")

    st.markdown("#### 關鍵尾部風險")
    for risk in TAIL_RISKS:
        with st.container(border=True):
            st.markdown(f"**{risk['icon']} {risk['risk']}**")
            st.write(risk["detail"])


def render_calendar():
    st.subheader("數據行事曆")
    st.markdown("#### 本週數據（4/21–4/25）")
    this_df = pd.DataFrame(THIS_WEEK)
    this_df["重要性"] = this_df["impact"].map(impact_label)
    st.dataframe(
        this_df[["date", "region", "event", "result", "prev", "重要性", "note"]]
        .rename(columns={
            "date": "日期",
            "region": "地區",
            "event": "事件",
            "result": "結果",
            "prev": "前值",
            "note": "說明",
        }),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### 下週重要數據與央行會議（4/28–5/2）")
    next_df = pd.DataFrame(NEXT_WEEK)
    next_df["重要性"] = next_df["impact"].map(impact_label)
    st.dataframe(
        next_df[["date", "region", "event", "重要性", "note"]].rename(columns={
            "date": "日期",
            "region": "地區",
            "event": "事件",
            "note": "說明",
        }),
        use_container_width=True,
        hide_index=True,
    )


def render_speeches():
    st.subheader("近期重要央行官員發言摘要（2026/04）")
    for speech in SPEECHES:
        with st.container(border=True):
            left, right = st.columns([5, 1])
            with left:
                st.markdown(f"**{speech['flag']} {speech['who']}**")
                st.write(speech["title"])
            with right:
                st.caption(f"📅 {speech['date']}")
            st.write(f"**重點：** {speech['key']}")


def render_howto():
    st.subheader("如何更新這份看板")

    sections = [
        {
            "freq": "每次央行會議後（即時）",
            "items": [
                "更新 BANKS 中對應央行的 currentRate、rateNum、trend",
                "更新 prevAction（描述最新動作）",
                "更新 analysis 陣列，尤其是「現況」與「前瞻」",
                "更新 shortView（一句話摘要）",
            ],
        },
        {
            "freq": "每週（週一更新）",
            "items": [
                "更新 FX_DATA 的 value 與 range52w",
                "清空 THIS_WEEK 並填入本週數據",
                "發布後補上 result 實際值",
                "更新 NEXT_WEEK 為下週重要事件",
            ],
        },
        {
            "freq": "官員談話（隨時）",
            "items": [
                "在 SPEECHES 最前面新增條目",
                "來源可用各央行 speeches 頁面或 BIS",
                "保留最近 4–6 則即可",
            ],
        },
        {
            "freq": "殖利率曲線（每週）",
            "items": [
                "更新 YIELD_CURVE_DATA 各期限 value",
                "來源：FRED 或 Treasury.gov",
                "重新計算利差並更新說明文字",
            ],
        },
    ]

    for sec in sections:
        with st.container(border=True):
            st.markdown(f"**{sec['freq']}**")
            for item in sec["items"]:
                st.write(f"- {item}")

    st.markdown("#### 推薦數據來源")
    src_df = pd.DataFrame(SOURCES, columns=["類別", "來源"])
    st.dataframe(src_df, use_container_width=True, hide_index=True)


# ─── APP ─────────────────────────────────────────────────────────────────────
render_header()

tab_rates, tab_fx, tab_macro, tab_calendar, tab_speeches, tab_howto = st.tabs([
    "🏦 央行利率",
    "💱 匯率",
    "🌐 大局觀",
    "📅 數據行事曆",
    "🎙 官員談話",
    "📖 更新指南",
])

with tab_rates:
    render_rates()
with tab_fx:
    render_fx()
with tab_macro:
    render_macro()
with tab_calendar:
    render_calendar()
with tab_speeches:
    render_speeches()
with tab_howto:
    render_howto()

st.divider()
st.caption("資料來源：Fed.gov · ECB.europa.eu · BOJ.or.jp · RBA.gov.au · TradingEconomics · Advisor Perspectives · Wise · BIS.org · Census.gov · 僅供參考，非投資建議")
