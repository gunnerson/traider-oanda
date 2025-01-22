import numpy as np
import pandas as pd


def get_atr(df: pd.DataFrame, period=14):
    """Add Average True Range index as "ATR" column."""
    df2 = df[["High", "Low", "Close"]].copy()
    df2["tr1"] = abs(df2.High - df2.Low)
    df2["tr2"] = abs(df2.High - df2.Close.shift())
    df2["tr3"] = abs(df2.Low - df2.Close.shift())
    tr = df2[["tr1", "tr2", "tr3"]].max(axis=1)
    df["ATR"] = tr.ewm(alpha=1 / period, adjust=False).mean()
    return df


def get_sma(df: pd.DataFrame, period=50):
    """Add Simple Moving Average index as "MA" column."""
    df["MA"] = df["Close"].rolling(period).mean()
    return df


def get_ema(df: pd.DataFrame, period=50):
    """Add Exponensial Moving Average index as "MA" column."""
    df["MA"] = df["Close"].ewm(span=period, adjust=False).mean()
    return df


def bollinger_bands(df: pd.DataFrame, length=20, sigma=2):
    """Add Bollinder Bands index as "BBL", "BBH" and "BBD" columns."""
    close = df.Close.rolling(length)
    close_mean = close.mean()
    std_dev = close.std(ddof=0)
    df["BBL"] = close_mean - (std_dev * sigma)
    df["BBH"] = close_mean + (std_dev * sigma)
    df["BBD"] = std_dev
    return df


def get_rsi(df: pd.DataFrame, period=14):
    """Add Relative Strength Index as "RSI" column."""

    delta = df["Close"].diff().dropna()
    u = delta * 0
    d = u.copy()
    u[delta > 0] = delta[delta > 0]  # type: ignore
    d[delta < 0] = -delta[delta < 0]  # type: ignore
    u[u.index[period - 1]] = np.mean(u[:period])
    u = u.drop(u.index[: (period - 1)])
    d[d.index[period - 1]] = np.mean(d[:period])
    d = d.drop(d.index[: (period - 1)])
    rs = (
        pd.DataFrame.ewm(u, com=period - 1, adjust=False).mean()  # type: ignore
        / pd.DataFrame.ewm(d, com=period - 1, adjust=False).mean()  # type: ignore
    )
    df["RSI"] = 100 - 100 / (1 + rs)
    return df


def get_stochastic_oscillator(df: pd.DataFrame, period=14):
    """
    Add column "SO" indicating trade direction recommendation accordint to Stochastic Oscillator.
    "1": Long entry
    "-1": Short entry
    "0": No entry
    """

    df2 = df.copy()
    df2["L14"] = df2["Low"].rolling(period).min()
    df2["H14"] = df2["High"].rolling(period).max()
    df2["%K"] = 100 * ((df2["Close"] - df2["L14"]) / (df2["H14"] - df2["L14"]))
    df2["%D"] = df2["%K"].rolling(3).mean()

    df2["Sell Entry"] = (
        (df2["%K"] < df2["%D"]) & (df2["%K"].shift(1) > df2["%D"].shift(1))
    ) & (df2["%D"] > 80)
    df2["Sell Exit"] = (df2["%K"] > df2["%D"]) & (
        df2["%K"].shift(1) < df2["%D"].shift(1)
    )
    df2["Short"] = np.nan
    df2.loc[df2["Sell Entry"], "Short"] = -1
    df2.loc[df2["Sell Exit"], "Short"] = 0
    df2.loc[0, "Short"] = 0
    df2["Short"] = df2["Short"].ffill()

    df2["Buy Entry"] = (
        (df2["%K"] > df2["%D"]) & (df2["%K"].shift(1) < df2["%D"].shift(1))
    ) & (df2["%D"] < 20)
    df2["Buy Exit"] = (df2["%K"] < df2["%D"]) & (
        df2["%K"].shift(1) > df2["%D"].shift(1)
    )
    df2["Long"] = np.nan
    df2.loc[df2["Buy Entry"], "Long"] = 1
    df2.loc[df2["Buy Exit"], "Long"] = 0
    df2.loc[0, "Long"] = 0
    df2["Long"] = df2["Long"].ffill()

    df["SO"] = df2["Long"] + df2["Short"]
    return df


def get_fibonacci(df: pd.DataFrame) -> list[float]:
    """Return a list of Fibonacci retracement levels."""
    l = df.loc[df.LL, "Close"].min()
    h = df.loc[df.HH, "Close"].max()
    m = [0.236, 0.382, 0.5, 0.618]
    return [l + ((h - l) * x) for x in m]


def _calc_wave_length(p1: pd.Series, p2: pd.Series, atr: float) -> float:
    a = (p2["index"] - p1["index"]) * atr
    b = abs(p1.BP - p2.BP)
    return a * a + b * b


def get_wave_length(df: pd.DataFrame):
    """Add relative length of trend wave as "WL" column."""
    df2 = df[df.UpT | df.DnT]
    df2 = df2.reset_index()
    df2 = df2.assign(WL=abs(df2.BP - df2.BP.shift()))
    df2 = df2.set_index("index")
    df["WL"] = df2.WL
    return df


def get_elliott(df: pd.DataFrame):
    """Add "Wave" column representing the number of the wave according to Elliot Wave Theory."""

    df.insert(9, "Wave", 0, True)

    # Get waves "1"
    df2 = df[df.HH | df.LL]
    df.loc[df2[df2.WL > df2.ATR].index, "Wave"] = 1  # type: ignore

    # Get waves "2"
    df2 = df[df.HH | df.LL]
    df3 = df2[
        (df2.Wave.shift() == 1)
        & (
            (df2.LL & (df2.BP > df2.BP.shift(2)))
            | (df2.HH & (df2.BP < df2.BP.shift(2)))
        )
    ]
    df.loc[df3.index, "Wave"] = 2  # type: ignore

    # Get waves "3"
    df2 = df[df.HH | df.LL]
    try:
        df3 = df2[
            (df2.Wave.shift() == 2)
            & ((df2.WL > df2.WL.shift(2)) | (df2.WL > df2.WL.shift(-2)))
        ]
        df.loc[df3.index, "Wave"] = 3  # type: ignore
    except IndexError:
        df3 = df2[(df2.Wave.shift() == 2) & (df2.WL > df2.WL.shift(2))]
        df.loc[df3.index, "Wave"] = 3  # type: ignore

    # Get waves "4"
    df2 = df[df.HH | df.LL]
    df3 = df2[
        (df2.Wave.shift() == 3)
        & (
            (df2.LL & (df2.BP > df2.BP.shift(3)))
            | (df2.HH & (df2.BP < df2.BP.shift(3)))
        )
    ]
    df.loc[df3.index, "Wave"] = 4  # type: ignore

    # Get waves "5"
    df2 = df[df.HH | df.LL]
    df3 = df2[
        (df2.Wave.shift() == 4)
        & (
            (df2.HH & (df2.BP > df2.BP.shift(2)))
            | (df2.LL & (df2.BP < df2.BP.shift(2)))
        )
    ]
    df.loc[df3.index, "Wave"] = 5  # type: ignore

    n = 5
    while not df3.empty:  # type: ignore
        df2 = df[df.HH | df.LL]
        df3 = df2[
            (df2.Wave.shift() == n)
            & (
                (df2.LL & (df2.BP > df2.BP.shift(2)))
                | (df2.HH & (df2.BP < df2.BP.shift(2)))
            )
        ]
        df.loc[df3.index, "Wave"] = n + 1  # type: ignore

        df2 = df[df.HH | df.LL]
        df3 = df2[(df2.Wave.shift() == n + 1)]
        df.loc[df3.index, "Wave"] = n + 2  # type: ignore

        n += 2

    return df


def get_rsi_divergence(df: pd.DataFrame, tol=2):
    """Check for RSI divergence indicators."""

    df = get_rsi(df)

    df2 = df[df.HHi | df.LLi]
    try:
        last = df2.iloc[-1]
        prev = df2.iloc[-3]
    except IndexError:
        return False
    prev_rsi = df.loc[prev.name - tol : prev.name + tol, "RSI"]  # type: ignore
    last_rsi = df.loc[last.name - tol : last.name + tol, "RSI"]  # type: ignore

    if last.HHi == True and last_rsi.max() < prev_rsi.max():
        return True
    elif last.LLi == True and last_rsi.min() > prev_rsi.min():
        return True
    else:
        return False


def get_so_line(df: pd.DataFrame):
    """Helper function to draw Stochastic Oscillator over candlestick chart."""
    top = df.High.max()
    bottom = df.Low.min()
    mid = df.Close.mean()
    df.loc[df.SO == 1, "SOL"] = top
    df.loc[df.SO == 0, "SOL"] = mid
    df.loc[df.SO == -1, "SOL"] = bottom
    return df
