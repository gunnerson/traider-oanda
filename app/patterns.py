from pandas import DataFrame

from .enums import OrderDir


def get_long_trend(df: DataFrame):
    last = df.iloc[-1]
    if last.UpT:
        return OrderDir.LONG
    elif last.DnT:
        return OrderDir.SHORT


def get_short_trend(df: DataFrame):
    df2 = df[df.H | df.L]
    last = df2.iloc[-1]
    prev = df2.iloc[-2]
    ref = df2.iloc[-4]
    if prev.HH and (last.BP < ref.BP):
        return OrderDir.SHORT
    elif prev.LL and (last.BP > ref.BP):
        return OrderDir.LONG
