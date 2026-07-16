import pandas as pd

def calculate_vwap(data):

    data = data.copy()

    required = ["High", "Low", "Close", "Volume"]

    for col in required:
        if col not in data.columns:
            raise ValueError(f"Kolom '{col}' tidak ditemukan.")

    typical_price = (
        data["High"] +
        data["Low"] +
        data["Close"]
    ) / 3

    cumulative_tp_volume = (
        typical_price * data["Volume"]
    ).cumsum()

    cumulative_volume = (
        data["Volume"]
    ).cumsum()

    data["VWAP"] = (
        cumulative_tp_volume /
        cumulative_volume
    )

    return data

def calculate_ema(data):

    data = data.copy()

    if "Close" not in data.columns:
        raise ValueError("Kolom 'Close' tidak ditemukan.")

    data["EMA20"] = (
        data["Close"]
        .ewm(span=20, adjust=False)
        .mean()
    )

    data["EMA50"] = (
        data["Close"]
        .ewm(span=50, adjust=False)
        .mean()
    )

    data["EMA200"] = (
        data["Close"]
        .ewm(span=200, adjust=False)
        .mean()
    )

    return data


def calculate_ma(data):

    data = data.copy()

    if "Close" not in data.columns:
        raise ValueError("Kolom 'Close' tidak ditemukan.")

    data["Close"] = pd.to_numeric(
        data["Close"],
        errors="coerce"
    )

    data["MA20"] = (
        data["Close"]
        .rolling(window=20)
        .mean()
    )

    data["MA50"] = (
        data["Close"]
        .rolling(window=50)
        .mean()
    )

    return data


def calculate_rsi(data, period=14):

    data = data.copy()

    if "Close" not in data.columns:
        raise ValueError("Kolom 'Close' tidak ditemukan.")

    delta = data["Close"].diff()

    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    average_gain = gain.rolling(
        window=period
    ).mean()

    average_loss = loss.rolling(
        window=period
    ).mean()

    rs = average_gain / average_loss.replace(0, pd.NA)

    data["RSI14"] = 100 - (
        100 / (1 + rs)
    )

    return data


def calculate_macd(data):

    data = data.copy()

    if "Close" not in data.columns:
        raise ValueError("Kolom 'Close' tidak ditemukan.")

    data["Close"] = pd.to_numeric(
        data["Close"],
        errors="coerce"
    )

    ema12 = data["Close"].ewm(
        span=12,
        adjust=False
    ).mean()

    ema26 = data["Close"].ewm(
        span=26,
        adjust=False
    ).mean()

    data["MACD"] = ema12 - ema26

    data["Signal_Line"] = (
        data["MACD"]
        .ewm(
            span=9,
            adjust=False
        )
        .mean()
    )

    data["MACD_Histogram"] = (
        data["MACD"]
        - data["Signal_Line"]
    )

    return data