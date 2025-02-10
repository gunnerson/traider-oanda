from pandas import DataFrame

from app.candles import candle_is_bearish, candle_is_bullish

from .enums import OrderDir


def get_long_trend(data: dict):
    df = data["df"]
    dfz = data["dfz"]
    df2 = df[df.H | df.L]
    last = df.iloc[-1]
    prev = df2.iloc[-3]
    z = dfz[(dfz.Top >= last.BP) & (dfz.Bottom <= last.BP)]
    if not z.empty:
        z = z.iloc[-1]
        if last.DnT and (prev.BP > z.Top):
            return OrderDir.LONG
        elif last.UpT and (prev.BP < z.Bottom):
            return OrderDir.SHORT


def get_short_trend(df: DataFrame):
    df2 = df[df.H | df.L]
    last = df2.iloc[-2]
    if last.DnT and candle_is_bullish(df):
        return {
            "order_dir": OrderDir.LONG,
        }
    if last.UpT and candle_is_bearish(df):
        return {
            "order_dir": OrderDir.SHORT,
        }
