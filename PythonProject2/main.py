import pandas as pd
import numpy as np
import requests

# =========================
# 1. LOAD DATA (BINANCE)
# =========================
def load_data():
    url = "https://api.binance.com/api/v3/klines"

    params = {
        "symbol": "BTCUSD",
        "interval": "1h",
        "startTime": int(pd.Timestamp("2026-01-01").timestamp() * 1000),
        "endTime": int(pd.Timestamp("2026-01-24").timestamp() * 1000),
        "limit": 1000
    }

    response = requests.get(url, params=params, timeout=10)
    response.raise_for_status()
    data = response.json()

    df = pd.DataFrame(data, columns=[
        "Open_time", "Open", "High", "Low", "Close",
        "Volume", "Close_time", "Quote_volume",
        "Trades", "Taker_buy_base", "Taker_buy_quote", "Ignore"
    ])

    df["Datetime"] = pd.to_datetime(df["Open_time"], unit="ms", utc=True)
    df[["Open", "High", "Low", "Close"]] = df[["Open", "High", "Low", "Close"]].astype(float)

    df = df[["Datetime", "Open", "High", "Low", "Close"]]
    df.dropna(inplace=True)
    df.reset_index(drop=True, inplace=True)

    return df


# =========================
# 2. MARKET CLASSIFICATION
# =========================
def classify_market(df, ma_period=50):

    # Moving Average
    df["MA"] = df["Close"].rolling(ma_period).mean()

    # MA slope
    df["MA_slope"] = df["MA"].diff()

    # Market classification
    df["market_type"] = np.where(
        (abs(df["MA_slope"]) > abs(df["MA_slope"].rolling(20).mean())) & (df["Close"] > df["MA"]),
        "UPTREND",
        np.where(
            (abs(df["MA_slope"]) > abs(df["MA_slope"].rolling(20).mean())) & (df["Close"] < df["MA"]),
            "DOWNTREND",
            "RANGING"
        )
    )



# ATR calculation
    high_low = df['High'] - df['Low'] #intracandle volatility
    high_close = abs(df['High'] - df['Close'].shift()) #gap-up volatility
    low_close = abs(df['Low'] - df['Close'].shift())#gap-down volatility

    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(14).mean()

    # Volatility regime
    df['volatility_type'] = np.where(
        df['ATR'] > df['ATR'].rolling(50).mean(),
        'HIGH_VOL',
        'LOW_VOL'
    )

    return df



# =========================
# 3. EMA STRATEGY LOGIC
# =========================
def generate_signals(df):
    df = df.copy()

    # Calculate EMAs
    df["EMA_20"] = df["Close"].ewm(span=20, adjust=False).mean()
    df["EMA_50"] = df["Close"].ewm(span=50, adjust=False).mean()
    df["EMA_200"] = df["Close"].ewm(span=200, adjust=False).mean()

    df["signal"] = 0

    # State variables
    sell_crossover = False
    buy_crossover = False

    for i in range(1, len(df)):

        # -------- Detect SELL crossover --------
        if (
            df.loc[i-1, "EMA_20"] > df.loc[i-1, "EMA_50"] and
            df.loc[i, "EMA_20"] < df.loc[i, "EMA_50"]
        ):
            sell_crossover = True

        # -------- Execute SELL when price confirms --------
        if sell_crossover and df.loc[i, "Close"] < df.loc[i, "EMA_200"]:
            df.loc[i, "signal"] = -1
            sell_crossover = False  # reset after execution

        # -------- Detect BUY crossover --------
        if (
            df.loc[i-1, "EMA_20"] < df.loc[i-1, "EMA_50"] and
            df.loc[i, "EMA_20"] > df.loc[i, "EMA_50"]
        ):
            buy_crossover = True

        # -------- Execute BUY when price confirms --------
        if buy_crossover and df.loc[i, "Close"] > df.loc[i, "EMA_200"]:
            df.loc[i, "signal"] = 1
            buy_crossover = False  # reset after execution

    return df



# =========================
# BACKTEST ENGINE
# =========================
def backtest(df, initial_capital=10000):
    position = 0
    entry_price = 0
    Acc_balance = initial_capital

    trades = []

    for i in range(len(df)):
        signal = df.loc[i, 'signal']
        price = df.loc[i, 'Close']

        if signal == 1 and position == 0:
            position = 1
            entry_price = price
            entry_market = df.loc[i, 'market_type']
            entry_vol = df.loc[i, 'volatility_type']

        elif signal == -1 and position == 1:
            pnl = price - entry_price
            Acc_balance += pnl

            trades.append({
                'entry_price': entry_price,
                'exit_price': price,
                'pnl': pnl,
                'Acc_balance': Acc_balance,
                'market_type': entry_market,
                'volatility_type': entry_vol,
                'exit_time': df.loc[i, 'Datetime']
            })

            position = 0

    return trades

# =========================
# METRICS
# =========================
def calculate_metrics(trades):
    if len(trades) == 0:
        return {}

    df_trades = pd.DataFrame(trades)

    win_rate = (df_trades['pnl'] > 0).mean() * 100 # %profitable trades
    total_pnl = df_trades['pnl'].sum() #Net profit/loss of strategy

    df_trades['peak'] = df_trades['equity'].cummax()
    df_trades['drawdown'] = df_trades['equity'] - df_trades['peak']
    max_drawdown = df_trades['drawdown'].min()

    return {
        'Total Trades': len(df_trades),
        'Win Rate (%)': round(win_rate, 2),
        'Total PnL': round(total_pnl, 2),
        'Max Drawdown': round(max_drawdown, 2)
    }


def research_analysis(trades_df):
    print("\n--- PERFORMANCE BY MARKET TYPE ---")
    print(trades_df.groupby('market_type')['pnl'].agg(['count', 'mean', 'sum']))

    print("\n--- PERFORMANCE BY VOLATILITY ---")
    print(trades_df.groupby('volatility_type')['pnl'].agg(['count', 'mean', 'sum']))

    print("\n--- FALSE SIGNAL DISTRIBUTION ---")
    print(trades_df.groupby(['market_type', 'volatility_type'])['false_signal'].mean())


def drawdown_analysis(trades_df):
    trades_df['peak'] = trades_df['equity'].cummax()
    trades_df['drawdown'] = trades_df['equity'] - trades_df['peak']

    max_dd = trades_df['drawdown'].min()

    print("\nMax Drawdown:", round(max_dd, 2))

    dd_periods = trades_df[trades_df['drawdown'] < -0.02 * trades_df['peak']]
    print("Extended Drawdown Trades:", len(dd_periods))



