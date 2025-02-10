import numpy as np
import pandas as pd

from .candles import *
from .indicators import *


def get_trend(df: pd.DataFrame):
    """
    Find important trend points.
    "H", "L": minor swings, highs and lows;
    "BP":  minor swing levels' values;
    "HH", "LL": higher highs and lower lows;
    "UpT", "DnT": trend break points
    """

    df.insert(5, "H", False, True)
    df.insert(5, "L", False, True)

    # Find price direction
    df["Bmax"] = df[["Open", "Close"]].max(axis=1)
    df["Bmin"] = df[["Open", "Close"]].min(axis=1)
    delta = df[["Bmax", "Bmin"]].diff()
    h = np.where([(delta.Bmax > 0)], 1, 0)[0]
    l = np.where([(delta.Bmin < 0)], 1, 0)[0]

    # If both are "1", zero the one that has has the closest "0" looking backwards.
    n = np.arange(h.size)
    idx = np.where(h * l == 1)[0]
    idx2 = _clossest_zero(h, idx, n) > _clossest_zero(l, idx, n)
    h[idx[idx2]] = 0
    l[idx[~idx2]] = 0

    # Find highest/lowest peaks/valleys in clusters
    h2 = np.where([h == 1], df.Bmax, 0)[0]
    l2 = np.where([l == 1], df.Bmin, 0)[0]
    df2 = pd.DataFrame({"H": h, "L": l, "High": h2, "Low": l2})
    df2 = df2.astype({"H": "bool", "L": "bool"})
    df2 = df2[df2.H | df2.L]
    g = df2.groupby(df2[["H", "L"]].ne(df2[["H", "L"]].shift()).any(axis=1).cumsum())  # type: ignore
    m1 = g["High"].transform("max").eq(df2["High"])
    m2 = g["Low"].transform("min").eq(df2["Low"])
    df2.loc[~(m1 & m2), ["H", "L"]] = False

    df.loc[df2.index, ["H", "L"]] = df2
    df.loc[df.H | df.L, "BP"] = df2.High + df2.Low

    # Find trend change points
    df.insert(7, "UpT", False, True)
    df.insert(7, "DnT", False, True)
    df.insert(7, "HH", False, True)
    df.insert(7, "LL", False, True)

    # Find higher highs and lower lows
    df2 = df[df.H | df.L]
    df3 = df2[df2.H & (df2.BP > df2.BP.shift(2))]
    df.loc[df3.index, ["HH", "UpT"]] = True  # type: ignore
    df3 = df2[df2.L & (df2.BP < df2.BP.shift(2))]
    df.loc[df3.index, ["LL", "DnT"]] = True  # type: ignore

    # Find trend change points
    df2 = df.loc[df.UpT | df.DnT, ["Date", "UpT", "DnT", "BP"]]
    g = df2.groupby(
        df2[["UpT", "DnT"]].ne(df2[["UpT", "DnT"]].shift()).any(axis=1).cumsum()
    )
    df.loc[~df["BP"].isin(g["BP"].max()), ["UpT"]] = False
    df.loc[~df["BP"].isin(g["BP"].min()), ["DnT"]] = False

    # Remove redundant trend points
    df2 = df.loc[df.UpT | df.DnT, ["Date", "UpT", "DnT"]]
    g = df2.groupby(
        df2[["UpT", "DnT"]].ne(df2[["UpT", "DnT"]].shift()).any(axis=1).cumsum()
    )
    df.loc[~df["Date"].isin(g["Date"].last()), ["UpT", "DnT"]] = False

    # Find major swing levels
    df2 = df[df.UpT | df.DnT]
    df3 = df2[
        (df2.UpT & (df2.BP > df2.BP.shift(2))) | (df2.DnT & (df2.BP < df2.BP.shift(2)))
    ].copy()
    df3.loc[:, "D"] = df3.BP.diff() > 0  # type: ignore
    g = df3.groupby(df3[["D"]].ne(df3[["D"]].shift()).any(axis=1).cumsum())  # type: ignore
    df.loc[~df["Date"].isin(g["Date"].last()), ["UpT", "DnT"]] = False
    try:
        df.loc[df3.index[0], "UpT"] = df.loc[df3.index[0], "HH"]  # type: ignore
        df.loc[df3.index[0], "DnT"] = df.loc[df3.index[0], "LL"]  # type: ignore
    except IndexError:
        pass

    # Find swings height "MSH"
    df2 = df[df.UpT | df.DnT].copy()
    df2["MSH"] = df2.BP.diff().abs()
    df3 = df2[
        (df2.MSH < df2.MSH.median())
        & (df2.BP != df2.BP.max())
        & (df2.BP != df2.BP.min())
    ]
    df.loc[df3.index, ["UpT", "DnT"]] = False  # type: ignore

    return df


def get_value_zones(df: pd.DataFrame):
    """Return DF with potential value zones."""

    atr = df.ATR.mean() * 0.75  # Bandwidth of the zone
    df2 = df[:-1]
    df3 = df2[df2.UpT | df2.DnT]

    # Add Fibonacci retracement levels
    # df2 = pd.concat([df2.BP[:-1], pd.DataFrame(get_fibonacci(df), columns=["BP"])])

    dfz = pd.DataFrame(
        {
            "Top": map(lambda x: x + atr / 2, df3.BP),  # type: ignore
            "Bottom": map(lambda x: x - atr / 2, df3.BP),  # type: ignore
        }
    ).sort_values(by=["Bottom", "Top"])

    # Merge overlapping zones
    dfz = _merge_overlaps(dfz, atr)

    return dfz


def _clossest_zero(arr: np.ndarray, arr_idx: np.ndarray, n: np.ndarray) -> np.ndarray:
    """Return an array where each value corresponds to the index of the closest 0 in the "arr" looking back relative to "peaks" in "arr_idx"."""
    return np.maximum.reduceat((1 - arr) * n, np.r_[0, arr_idx])[:-1]


def _merge_overlaps(dfz: pd.DataFrame, atr: float):
    """Merge overlapping value zones."""
    dfz = (
        dfz.assign(
            max_Top=lambda d: d["Top"].cummax(),
            group=lambda d: d["Bottom"].ge(d["max_Top"].shift(fill_value=0)).cumsum(),
        )
        .groupby("group", as_index=False)
        .agg(
            {
                "Top": "mean",
                "Bottom": "mean",
            }
        )
        .drop("group", axis=1)
    )  # type: ignore

    dfz.Top = dfz.Top - (dfz.Top - dfz.Bottom) / 2 + atr / 2
    dfz.Bottom = dfz.Top - atr

    return dfz
