import streamlit as st
import pandas as pd
from main import (
    load_data,
    classify_market,
    generate_signals,
    backtest,
    calculate_metrics
)




st.set_page_config(
    page_title="Strategy Research Dashboard",
    layout="wide"
)

st.title("📊 Strategy Research & Validation Engine")

st.write("""
This dashboard presents research insights and validation metrics
for algorithmic trading strategies.
""")

# =========================
# PARAMETERS
# =========================
ma_period = 50

# =========================
# LOAD & PROCESS DATA (CALLING FUNCTIONS)
# =========================
df = load_data()
df = classify_market(df)
df = generate_signals(df)

trades = backtest(df)
metrics = calculate_metrics(trades)



# =========================
# DISPLAY DATA
# =========================
st.subheader("📄 Market Data Preview")

# st.dataframe(
#     df[["Datetime", "Close", "MA", "EMA_20", "EMA_50", "EMA_200", 'pnl','equity']],
#     use_container_width=True
# )

st.dataframe(df, use_container_width=True)

# Trades dataframe
df_trades = pd.DataFrame(trades)

st.subheader("📊 Trade Log")

st.dataframe(
    df_trades,
    use_container_width=True
)



# # =========================
# # SHOW SLIDING WINDOW (OPTION 3 - CORRECT WAY)
# # =========================
# st.subheader("🔍 MA Sliding Window (Latest Candle)")
#
# last_window = df["Close"].tail(ma_period).tolist()
#
# st.write(
#     "Last MA window (used for latest MA calculation):",
#     last_window
# )


