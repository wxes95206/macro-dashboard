import streamlit as st
from macro_dashboard_v2 import (
    fetch_all_fx,
    fetch_all_yields_with_history,
    BANKS
)

st.set_page_config(page_title="Macro Dashboard", layout="wide")

# ───────────────────────
# Title
# ───────────────────────
st.title("🌍 Macro Dashboard")

# ───────────────────────
# FX（卡片）
# ───────────────────────
st.subheader("💱 FX")

fx = fetch_all_fx()
cols = st.columns(len(fx))

for i, item in enumerate(fx):
    with cols[i]:
        st.metric(
            label=item["pair"],
            value=item["price_str"],
            delta=item["change_str"]
        )

# ───────────────────────
# 央行（卡片化）
# ───────────────────────
st.subheader("🏦 Central Banks")

bank_cols = st.columns(3)

for i, b in enumerate(BANKS):
    with bank_cols[i % 3]:
        st.markdown(f"""
        ### {b['flag']} {b['name']}
        **利率：** {b['currentRate']}  
        **下次會議：** {b['nextMeeting']}  
        {b['shortView']}
        """)

# ───────────────────────
# Yield Curve（多條線）
# ───────────────────────
st.subheader("📈 Yield Curve")

y = fetch_all_yields_with_history()
curves = y["curves"]

x = ["2Y", "5Y", "10Y", "30Y"]

chart_data = {
    "今日": [p["value"] for p in curves["today"]],
    "1M": [p["value"] for p in curves["1m_ago"]],
    "6M": [p["value"] for p in curves["6m_ago"]],
    "1Y": [p["value"] for p in curves["1y_ago"]],
}

st.line_chart(chart_data)

# ───────────────────────
# Spread（加一個專業點）
# ───────────────────────
today_curve = curves["today"]

y2 = today_curve[0]["value"]
y10 = today_curve[2]["value"]

if y2 and y10:
    spread = y10 - y2
    st.metric("10Y - 2Y Spread", f"{spread:.2f}%")

# ───────────────────────
# Footer
# ───────────────────────
st.caption("Data: Yahoo Finance | Manual: Central Banks")
