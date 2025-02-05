from io import StringIO

import pandas as pd
import plotly.graph_objects as go
import pytz
from dash import Input, Output, dcc, html
from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db.utils import OperationalError, ProgrammingError
from django.utils import timezone
from django_plotly_dash import DjangoDash

from app import enums

from .api import get_ohlc_data
from .enums import Interval, OrderDir
from .models import Bot, Order, Pair
from .utils import get_ohlc_analysis, prep_data

kc_app = DjangoDash("CandleChart")
kc_app.css.append_css({"external_url": "assets/chart.css"})

try:
    PAIRS = [x.name for x in Pair.objects.all()]
except (ProgrammingError, OperationalError):
    PAIRS = []
INTERVALS = list(map(lambda x: {"label": x.label, "value": x.label}, Interval))
ORDERTYPES = list(map(lambda x: {"label": x.label, "value": x.value}, OrderDir))
HEIGHT = [420, 480, 540, 600, 720, 864, 1024, 1152, 1280, 1440, 1920, 2560]
PLOT_BG_COLOR = "white"
MAVG_COLOR = "rgba(67,150,241,1)"

kc_app.layout = html.Div(  # type: ignore
    style={
        "display": "flex",
        "flex-direction": "column",
    },
    children=[
        dcc.Store(id="pair-value", storage_type="local"),
        dcc.Store(id="interval-value", storage_type="local"),
        dcc.Store(id="height-value", storage_type="local"),
        dcc.Store(id="chart-data"),
        html.Div(
            children=[
                dcc.Dropdown(
                    PAIRS,
                    id="pair-select",
                    clearable=False,
                    style={
                        "width": "10rem",
                    },
                ),
                dcc.RadioItems(
                    INTERVALS,
                    id="interval-radio",
                    inline=True,
                    style={
                        "display": "flex",
                        "align-items": "center",
                        "gap": "0.5rem",
                    },
                ),
                dcc.Dropdown(
                    HEIGHT,
                    id="height-select",
                    clearable=False,
                    style={
                        "width": "5rem",
                    },
                ),
                html.Button("Refresh", id="refresh-button", n_clicks=0),
            ],
            style={
                "margin-left": "1rem",
                "display": "flex",
                "flex-wrap": "wrap",
                "align-items": "center",
                "gap": "2rem",
            },
        ),
        dcc.Graph(
            id="graph",
            config={"responsive": True},
        ),
        html.Div(
            children=[
                dcc.RadioItems(
                    ORDERTYPES,
                    ORDERTYPES[0]["value"],
                    id="ordertype-radio",
                    style={
                        "display": "flex",
                        "flex-direction": "column",
                        "gap": "0.25rem",
                    },
                ),
                dcc.Input(
                    id="price-input",
                    type="number",
                    placeholder="Trigger Price",
                    debounce=True,
                    inputMode="numeric",
                    style={"width": "8rem", "border": "1px dashed gray"},
                ),
                dcc.Input(
                    id="stopprice-input",
                    type="number",
                    placeholder="Stop-Loss Price",
                    debounce=True,
                    inputMode="numeric",
                    style={"width": "8rem", "border": "1px dashed red"},
                ),
                dcc.Input(
                    id="vol-input",
                    type="number",
                    placeholder="Volume",
                    debounce=True,
                    inputMode="numeric",
                    style={"width": "6rem", "border": "1px dashed blue"},
                ),
                html.Button("Place order", id="order-button", n_clicks=0),
            ],
            style={
                "margin-left": "1rem",
                "margin-top": "1rem",
                "display": "flex",
                "flex-wrap": "wrap",
                "align-items": "center",
                "gap": "2rem",
            },
        ),
    ],
)


@kc_app.callback(
    Output("pair-value", "data"),
    Output("pair-select", "value"),
    Input("pair-select", "value"),
    state=[Input("pair-value", "data")],
)
def update_pair(select, store):
    if not select:
        if store:
            return store, store
        return PAIRS[0], PAIRS[0]
    return select, select


@kc_app.callback(
    Output("interval-value", "data"),
    Output("interval-radio", "value"),
    Input("interval-radio", "value"),
    state=[Input("interval-value", "data")],
)
def update_interval(radio, store):
    if not radio:
        if store:
            return store, store
        return INTERVALS[1]["value"], INTERVALS[1]["value"]
    return radio, radio


@kc_app.callback(
    Output("height-value", "data"),
    Output("height-select", "value"),
    Input("height-select", "value"),
    state=[Input("height-value", "data")],
)
def update_height(select, store):
    if not select:
        if store:
            return store, store
        return HEIGHT[0], HEIGHT[0]
    return select, select


@kc_app.callback(
    Output("chart-data", "data"),
    Input("pair-value", "data"),
    Input("interval-value", "data"),
    Input("refresh-button", "n_clicks"),
    state=[Input("chart-data", "data")],
)
def update_data(pair, interval, refresh, data):
    """Return data from 'dcc.Store' unless 'refresh' button is pressed."""
    i = str(interval)
    if (
        data
        and pair in data
        and i in data[pair]
        and (data[pair][i]["refresh"] == refresh or refresh == 0)
    ):
        return data

    if not data:
        data = {}

    if not pair in data:
        data[pair] = {}

    if not i in data[pair]:
        data[pair][i] = {}

    ohlc_data = get_ohlc_data(pair, interval, 500)
    prepped_data = prep_data(ohlc_data)
    ready_data = get_ohlc_analysis(prepped_data)
    df = ready_data["df"]
    dfz = ready_data["dfz"]

    data[pair][i]["df"] = df.to_json()
    data[pair][i]["dfz"] = dfz.to_json()
    data[pair][i]["atr"] = df.ATR.iloc[-2]
    data[pair][i]["orders"] = _get_orders(pair, since=prepped_data["first"])
    for pair in data.keys():
        for i in data[pair].keys():
            data[pair][i]["refresh"] = refresh

    return data


@kc_app.callback(
    Output("graph", "figure"),
    Input("chart-data", "data"),
    Input("height-value", "data"),
    state=[
        Input("pair-value", "data"),
        Input("interval-value", "data"),
    ],
)
def update_figure(data, height, pair, interval):
    interval = str(interval)
    df = pd.read_json(StringIO(data[pair][interval]["df"]))
    df["Date"] = pd.to_datetime(df["Date"], unit="s", utc=True)
    df["Date"] = df["Date"].dt.tz_convert(settings.TIME_ZONE)
    dfz = pd.read_json(StringIO(data[pair][interval]["dfz"]))
    orders = data[pair][interval]["orders"]

    fig = go.Figure(
        data=[
            go.Candlestick(
                name="Candle",
                x=df["Date"],
                open=df["Open"],
                high=df["High"],
                low=df["Low"],
                close=df["Close"],
                opacity=1,
            ),
        ],
    )

    fig.update_layout(
        title="",
        plot_bgcolor=PLOT_BG_COLOR,
        yaxis_title="",
        hovermode="x unified",
        height=height,
        margin=dict(
            l=0,
            r=0,
            b=0,
            t=40,
            pad=0,
        ),
    )

    fig.update_yaxes(
        fixedrange=False,
        title_standoff=20,
        automargin="height+width+left",
    )

    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["MA"],
            name="MA",
            line=dict(color=MAVG_COLOR),
        )
    )

    # fig.add_trace(
    #     go.Scatter(
    #         x=df["Date"],
    #         y=df["BBH"],
    #         name="BBH",
    #         line=dict(color=MAVG_COLOR),
    #         opacity=0.5,
    #     )
    # )
    #
    # fig.add_trace(
    #     go.Scatter(
    #         x=df["Date"],
    #         y=df["BBL"],
    #         name="BBL",
    #         line=dict(color=MAVG_COLOR),
    #         opacity=0.5,
    #     )
    # )

    fig.add_trace(
        go.Scatter(
            x=df["Date"],
            y=df["BP"],
            name="Price",
            line=dict(color=MAVG_COLOR),
            connectgaps=True,
            opacity=0.5,
        )
    )

    tbps = df[df.UpT | df.DnT]
    fig.add_trace(
        go.Scatter(
            x=tbps["Date"],
            y=tbps["BP"],
            name="Trend break-points",
            mode="markers",
            showlegend=False,
            marker=dict(
                color="LightSkyBlue",
                size=20,
                line=dict(color="MediumPurple", width=2),
                opacity=0.5,
            ),
        )
    )

    for idx in range(len(dfz.index)):
        fig.add_hrect(
            y0=dfz.Top.iloc[idx],
            y1=dfz.Bottom.iloc[idx],
            fillcolor="rgba(128,0,128,0.1)",
            line_width=0,
        )

    for idx in range(0, len(orders["target"]), 2):
        COLOR = "rgba(0,255,0,0.2)"
        fig.add_trace(
            go.Scatter(
                x=orders["target"][idx],
                y=orders["target"][idx + 1],
                line=dict(color=COLOR),
                fill="tozeroy",
                fillcolor=COLOR,
            )
        )

    for idx in range(0, len(orders["stop"]), 2):
        COLOR = "rgba(255,0,0,0.2)"
        fig.add_trace(
            go.Scatter(
                x=orders["stop"][idx],
                y=orders["stop"][idx + 1],
                line=dict(color=COLOR),
                fill="tozeroy",
                fillcolor=COLOR,
            )
        )

    return fig


@kc_app.callback(
    # Output("price-input", "value"),
    # Output("stopprice-input", "value"),
    # Output("vol-input", "value"),
    Output("price-input", "min"),
    Output("stopprice-input", "min"),
    Output("price-input", "step"),
    Output("stopprice-input", "step"),
    Output("vol-input", "step"),
    Output("vol-input", "min"),
    Input("pair-value", "data"),
)
def init_order_form(pair_name):
    pair = Pair.objects.get(name=pair_name)
    price_min = 10 ** (-1 * pair.cost_decimals)
    return [price_min for _ in range(4)] + [pair.ordermin for _ in range(2)]


@kc_app.callback(
    Output("price-input", "value"),
    Output("stopprice-input", "value"),
    Output("vol-input", "value"),
    Output("graph", "clickData"),
    Output("order-button", "n_clicks"),
    Input("graph", "clickData"),
    Input("order-button", "n_clicks"),
    state=[
        Input("pair-value", "data"),
        Input("price-input", "value"),
        Input("stopprice-input", "value"),
        Input("vol-input", "value"),
        Input("ordertype-radio", "value"),
        Input("interval-value", "data"),
        Input("chart-data", "data"),
    ],
)
def set_order_values(
    clickData,
    submit,
    pair_name,
    price,
    stopprice,
    vol,
    order_dir,
    interval,
    data,
):
    pair = Pair.objects.get(name=pair_name)
    if submit:
        order = Order(
            bot=pair.bot,  # type: ignore
            order_dir=order_dir,
        )
        if price:
            order.price = round(price, pair.cost_decimals)
            if stopprice:
                order.stopprice = round(stopprice, pair.cost_decimals)
        if vol:
            order.vol = round(vol, pair.lot_decimals)
        order.save()
        return None, None, None, None, 0

    if not clickData:
        return price, stopprice, vol, None, 0

    value = round(clickData["points"][-1]["close"], pair.cost_decimals)
    atr = data[pair_name][str(interval)]["atr"]

    if not price:
        return value, stopprice, vol, None, 0

    if not stopprice:
        stop = (value - atr) if order_dir == OrderDir.LONG.value else (value + atr)
        return price, round(stop, pair.cost_decimals), vol, None, 0

    return None, None, None, None, 0


def _get_orders(pair, since):
    order_target = []
    order_stop = []
    try:
        pair = Pair.objects.get(name=pair)
        bot = Bot.objects.get(pair=pair)
        orders = bot.order_set.filter(opentm__gte=since)  # type: ignore
        for order in orders:
            close = (
                order.closetm.astimezone(pytz.timezone(settings.TIME_ZONE))
                if order.closetm
                else timezone.localtime(timezone.now())
            )
            opentm = order.opentm.astimezone(pytz.timezone(settings.TIME_ZONE))
            order_target.append([opentm, opentm, close, close, opentm])
            order_target.append(
                [
                    order.tpprice,
                    order.price,
                    order.price,
                    order.tpprice,
                    order.tpprice,
                ]
            )
            order_stop.append([opentm, opentm, close, close, opentm])
            order_stop.append(
                [
                    order.stopprice,
                    order.price,
                    order.price,
                    order.stopprice,
                    order.stopprice,
                ]
            )
    except ObjectDoesNotExist:
        return {"target": [], "stop": []}
    return {"target": order_target, "stop": order_stop}
