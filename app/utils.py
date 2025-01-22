import numpy as np
import pandas as pd
from django.conf import settings

from .candles import *
from .indicators import *
from .patterns import *
from .ta import *


def prep_data(data: dict, smooth=False) -> dict:
    df = pd.DataFrame([{**x, **x.pop("mid")} for x in data["ohlc"]])
    df.drop(df.columns[[0, 1, 3]], axis=1, inplace=True)  # type: ignore
    df.rename(
        columns={
            "time": "Date",
            "o": "Open",
            "h": "High",
            "l": "Low",
            "c": "Close",
        },
        inplace=True,
    )

    df = df.astype(
        {
            "Date": "float",
            "Open": "float",
            "High": "float",
            "Low": "float",
            "Close": "float",
        }
    )
    df["Date"] = pd.to_datetime(df["Date"], unit="s", utc=True)
    df["Date"] = df["Date"].dt.tz_convert(settings.TIME_ZONE)

    # Smooth candles
    if smooth:
        df.Open = df.Close.shift()
        df.High = df[["Open", "Close", "High"]].max(axis=1)
        df.Low = df[["Open", "Close", "Low"]].min(axis=1)

    # Merge last two candles together
    df = _smooth_last(df)

    return {
        "df": df,
        "first": df.Date.iloc[0],
    }


def get_ohlc_analysis(data: dict, trend=True, vz=True):
    df: pd.DataFrame = data["df"]  # type: ignore

    # Get Indicators
    df = get_ema(df)
    df = get_atr(df)
    df = bollinger_bands(df)

    # Identify trend
    if trend:
        df = get_trend(df)

    # Get Support and Resistance
    if vz:
        dfz = get_value_zones(df)
    else:
        dfz = None

    return {"df": df, "dfz": dfz}


def _smooth_last(df: pd.DataFrame):
    """Smooth last candle merging it with the previous one."""
    df2 = df[-2:]
    df.iloc[-2, 4] = df.iloc[-1, 4]
    df.iloc[-2, 2] = max(df2[["Open", "High", "Low", "Close"]].max())
    df.iloc[-2, 3] = min(df2[["Open", "High", "Low", "Close"]].min())
    return df[:-1]


def get_avg_spread(data):
    arr = np.array(data)
    arr = np.delete(arr, np.s_[0], 1).astype(float)
    return np.diff(arr).mean() / 2
