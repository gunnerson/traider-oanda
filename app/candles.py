def candle_is_bullish(df):

    o1, h1, l1, c1 = df.iloc[-2, 1:5].to_numpy()
    o2, h2, l2, c2 = df.iloc[-1, 1:5].to_numpy()

    mid = l2 + ((h2 - l2) * 0.75)
    if o2 < mid and c2 < mid:
        return False

    # if c2 != h2:
    #     return False

    if c2 > o2:

        if c2 > h1:
            return True

        if (c2 - o2) > abs(o1 - c1):
            return True

        # if o2 > mid and (h2 - l2) >= (h1 - l1):
        #     return True

    return False


def candle_is_bearish(df):

    o1, h1, l1, c1 = df.iloc[-2, 1:5].to_numpy()
    o2, h2, l2, c2 = df.iloc[-1, 1:5].to_numpy()

    mid = h2 - ((h2 - l2) * 0.75)
    if o2 > mid and c2 > mid:
        return False

    # if c2 != l2:
    #     return False

    if c2 < o2:

        if c2 < l1:
            return True

        if (o2 - c2) > abs(o1 - c1):
            return True

        # if o2 < mid and (h2 - l2) >= (h1 - l1):
        #     return True

    return False


def get_candle_analysis(df):
    o1, h1, l1, c1 = df.iloc[-2, 1:5].to_numpy()
    o2, h2, l2, c2 = df.iloc[-1, 1:5].to_numpy()
    if c2 > o2:
        t2 = "u"
    elif c2 < o2:
        t2 = "d"
    else:
        t2 = "s"
    if t2 == "u":
        if (c2 - o2) > abs(o1 - c1):
            df.at[df.index[-1], "Engulf"] = 2
        else:
            df.at[df.index[-1], "Engulf"] = 0
        if c2 > h1:
            df.at[df.index[-1], "Closed"] = 2
        else:
            df.at[df.index[-1], "Closed"] = 0
    elif t2 == "d":
        if (o2 - c2) > abs(o1 - c1):
            df.at[df.index[-1], "Engulf"] = 1
        else:
            df.at[df.index[-1], "Engulf"] = 0
        if c2 < l1:
            df.at[df.index[-1], "Closed"] = 1
        else:
            df.at[df.index[-1], "Closed"] = 0
    else:
        df.at[df.index[-1], "Engulf"] = 0
        df.at[df.index[-1], "Closed"] = 0

    fri382 = h2 - ((h2 - l2) * 0.382)
    if o2 > fri382 and c2 > fri382:
        df.at[df.index[-1], "Hammer"] = 2
    else:
        fri382 = l2 + ((h2 - l2) * 0.382)
        if o2 < fri382 and c2 < fri382:
            df.at[df.index[-1], "Hammer"] = 1
        else:
            df.at[df.index[-1], "Hammer"] = 0

    return df
