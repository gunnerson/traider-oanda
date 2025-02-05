from datetime import datetime

from django.conf import settings
from django.utils import timezone

from . import enums
from .oanda import Endpoint

API_ACCOUNT = settings.OANDA_API
API_TOKEN = settings.OANDA_SECRET
BASE_URL = settings.OANDA_BASE_URL

api = Endpoint(API_ACCOUNT, API_TOKEN, BASE_URL)


def get_account() -> dict:
    if data := api.summary():
        return {
            "account_margin": float(data["account"]["marginAvailable"]),
        }
    return {}


def get_instruments() -> list:
    if data := api.instruments():
        return data["instruments"]
    return []


def get_ohlc_data(
    pair: str,
    interval: str,
    count: int,
) -> dict:
    if data := api.candles(pair, interval, count):
        return {"ohlc": data["candles"], "last_ohlc": data["candles"][-1]}
    return {}


def get_spread(pair: str) -> dict:
    if data := api.pricing(pair):
        return {
            "tradeable": True if data["prices"][0]["status"] == "tradeable" else False,
            "bid_price": float(data["prices"][0]["bids"][0]["price"]),
            "ask_price": float(data["prices"][0]["asks"][0]["price"]),
            "baseconfac": float(data["homeConversions"][0]["accountLoss"]),
            "quoteconfac": float(data["homeConversions"][1]["accountLoss"]),
        }
    return {}


def open_position(
    pair: str,
    vol: int | float,
    price: float,
    stopprice: float,
    order_dir: enums.OrderDir,
) -> dict:
    vol = vol if order_dir == enums.OrderDir.LONG else -1 * vol
    if data := api.place_order(
        pair=pair,
        vol=vol,
        price=price,
        stopprice=stopprice,
    ):
        try:
            return {
                "sl_id": data["relatedTransactionIDs"][-1],
                "trade_id": data["orderFillTransaction"]["tradeOpened"]["tradeID"],
                "price": float(data["orderFillTransaction"]["price"]),
                "time": datetime.fromtimestamp(
                    float(data["orderFillTransaction"]["time"]),
                    tz=timezone.get_current_timezone(),
                ),
            }
        except KeyError:
            pass
    return {}


def adjust_stop_loss(
    distance: float,
    sl_id: str,
    trade_id: str,
) -> str:
    if data := api.change_order(
        distance,
        sl_id,
        trade_id,
    ):
        return data["orderCreateTransaction"]["id"]
    return ""


def get_trade(trade_id: str) -> dict:
    if data := api.get_trade(trade_id):
        status = enums.OrderStatus(data["trade"]["state"])
        if status == enums.OrderStatus.CLOSED:
            return {
                "status": status,
                "closetm": datetime.fromtimestamp(
                    float(data["trade"].get("closeTime")),
                    tz=timezone.get_current_timezone(),
                ),
                "net": round(float(data["trade"].get("realizedPL")), 2),
                "closeprice": float(data["trade"].get("averageClosePrice")),
            }
        else:
            return {"status": status}
    return {}
