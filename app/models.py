from datetime import datetime, timedelta

import pytz
from django.db import models
from django.urls import reverse
from django.utils import timezone

from . import api, enums, patterns, utils


class Asset(models.Model):
    name = models.CharField(max_length=32)
    confac = models.FloatField(null=True, blank=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} x {round(self.confac, 3) if self.confac else 0}"


class Pair(models.Model):
    name = models.CharField(max_length=16)
    altname = models.CharField(max_length=16, verbose_name="Display name")
    base: Asset = models.ForeignKey(
        "Asset",
        on_delete=models.CASCADE,
        related_name="base_pairs",
        null=True,
        blank=True,
    )  # type: ignore
    quote: Asset = models.ForeignKey(
        "Asset",
        on_delete=models.CASCADE,
        related_name="quote_pairs",
        null=True,
        blank=True,
    )  # type: ignore
    cost_decimals = models.PositiveSmallIntegerField(verbose_name="Price precision")
    lot_decimals = models.PositiveSmallIntegerField(verbose_name="Volume precision")
    ordermin = models.FloatField(verbose_name="Minimal order volume")
    max_leverage = models.PositiveSmallIntegerField(
        default=1,
        verbose_name="Maximum leverage",
    )

    class Meta:
        ordering = ["altname"]

    def __str__(self):
        return self.altname

    @property
    def pip(self) -> float:
        return pow(10, -1 * self.cost_decimals)

    @property
    def lot(self) -> float:
        return pow(10, -1 * self.lot_decimals)

    @classmethod
    def add_pairs(cls):
        pair_list = api.get_instruments()
        for pair in pair_list:
            base, created = Asset.objects.get_or_create(
                name=pair["displayName"].split("/")[0]
            )
            quote, created = Asset.objects.get_or_create(
                name=pair["displayName"].split("/")[1]
            )
            max_leverage = int(1 / float(pair["marginRate"]))
            try:
                p = Pair.objects.get(name=pair["name"])
                p.base = base
                p.quote = quote
                p.altname = pair["displayName"]
                p.cost_decimals = pair["pipLocation"] * -1
                p.lot_decimals = pair["tradeUnitsPrecision"]
                p.ordermin = pair["minimumTradeSize"]
                p.max_leverage = max_leverage
                p.save()
            except Pair.DoesNotExist:
                p = Pair(
                    name=pair["name"],
                    base=base,
                    quote=quote,
                    altname=pair["displayName"],
                    cost_decimals=pair["pipLocation"] * -1,
                    lot_decimals=pair["tradeUnitsPrecision"],
                    ordermin=pair["minimumTradeSize"],
                    max_leverage=max_leverage,
                )
                p.save()
            print(f"[+] Pair {p.name} created...")


class Order(models.Model):
    bot = models.ForeignKey("Bot", on_delete=models.CASCADE)
    order_dir = models.CharField(max_length=5, choices=enums.OrderDir)  # type: ignore
    price = models.FloatField(verbose_name="Position entry price")
    stopprice = models.FloatField(
        null=True, blank=True, verbose_name="Stop-loss trigger price"
    )
    vol = models.FloatField(null=True, blank=True, verbose_name="Volume")
    opentm = models.DateTimeField(default=timezone.now, verbose_name="Open time")
    closetm = models.DateTimeField(null=True, blank=True, verbose_name="Close time")
    closeprice = models.FloatField(null=True, blank=True, verbose_name="Close price")
    net = models.FloatField(default=0)
    status = models.CharField(max_length=9, choices=enums.OrderStatus, blank=True)  # type: ignore
    close_status = models.CharField(max_length=1, choices=enums.CloseStatus, blank=True)  # type: ignore
    rvr = models.FloatField(null=True, blank=True, verbose_name="Risk vs Reward")
    order_id = models.CharField(max_length=24, blank=True, verbose_name="Order ID")
    trade_id = models.CharField(max_length=24, blank=True, verbose_name="Trade ID")
    limitprice: float  # Price for limit order or market bound price

    class Meta:
        ordering = ["-pk"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        name = self.bot.pair.__str__()
        if self.closeprice:
            name += " " + str(self.net) + "USD"
        else:
            name += " x" + str(self.vol)
        return name

    def get_stop_buffer(self) -> float:
        return round_down(
            abs(self.price - self.stopprice) if self.stopprice else 0,
            self.bot.pair.cost_decimals,
        )

    def get_rvr(self) -> float:
        if self.closeprice:
            return round_down(
                abs(self.closeprice - self.price) / self.get_stop_buffer(), 1
            )
        return 0

    def get_close_status(self):
        if self.stopprice and self.closeprice:
            if self.price > self.stopprice:
                if self.closeprice > self.price:
                    return enums.CloseStatus.TOUCHED
                else:
                    return enums.CloseStatus.STOPPED
            else:
                if self.closeprice < self.price:
                    return enums.CloseStatus.TOUCHED
                else:
                    return enums.CloseStatus.STOPPED


class Bot(models.Model):
    pair: Pair = models.OneToOneField(
        Pair,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
    )  # type: ignore
    conseq_losses = models.PositiveSmallIntegerField(
        default=0, verbose_name="Consequetive losses"
    )
    on_status = models.BooleanField(default=True, verbose_name="On/Off")
    balance = models.FloatField(default=0, verbose_name="Relative balance (in R/R)")

    class Meta:
        ordering = ["pair__altname"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bg: BotGroup
        self.data = {}
        self.account_margin: float
        if self.pk:
            self.order: Order = self.open_order()

    def __str__(self):
        return self.pair.altname

    @classmethod
    def add_bots(cls):
        pairs = Pair.objects.all()
        for p in pairs:
            bot, created = cls.objects.get_or_create(pair=p)
            print(f"[+] Bot {bot.pair.name} created...")

    def get_log_url(self):
        return reverse("app:log", args=[str(self.pk)])

    def get_chart_url(self):
        return reverse("app:analytics") + f"?interval=5&pair={self.pair.pk}"

    @property
    def name(self) -> str:
        return self.pair.altname

    @property
    def health(self):
        if not self.on_status:
            return enums.BotHealth.STOPPED.value
        elif self.order:
            return enums.BotHealth.PENDING.value
        elif self.balance > 0:
            return enums.BotHealth.PROFITABLE.value
        elif self.balance < 0:
            return enums.BotHealth.UNPROFITABLE.value
        else:
            return enums.BotHealth.OTHER.value

    def open_order(self):
        return self.order_set.filter(closeprice=None).last()  # type: ignore

    def run(self, order: Order = None):  # type: ignore
        self.order = order

        if self.order:
            # If order is already placed (has TP price) check it's status
            if self.order.status:
                self._check_order()
            # Otherwise process the order (calculate SL, TP prices and volume) and place it
            elif self.bg.on_status and self.on_status and self._get_account():
                self._process_order()

        elif self.bg.on_status and self.on_status and self._get_account():
            self._analyze()

    def _get_account(self):
        if data := api.get_account():
            self.account_margin = float(data["account_margin"])
            return True
        return False

    def _get_pricing(self):
        if data := api.get_spread(self.pair.name):
            if not data["tradeable"]:
                print(f"[-] {self.pair.name} isn't tradeable at the moment...")
                return False

            self.bid_price = data["bid_price"]
            self.ask_price = data["ask_price"]
            self.pair.base.confac = data["baseconfac"]
            self.pair.quote.confac = data["quoteconfac"]
            return True

        return False

    def _get_data(
        self,
        i: enums.Interval,
        analyze=True,
        valid=True,
        simple=False,
        short=False,
    ):
        # Return cached data if it's not too old
        if valid and self._data_is_valid(i):
            return self.data[i]

        count = 100 if short else 500

        if api_data := api.get_ohlc_data(
            self.pair.name, enums.Interval(i).label, count=count
        ):
            prepped_data = utils.prep_data(api_data, smooth=self.bg.smooth)
            self.data[i]["last"] = datetime.now()
            if analyze:
                self.data[i] = self.data[i] | utils.get_ohlc_analysis(prepped_data)
            elif simple:
                self.data[i] = self.data[i] | utils.get_ohlc_analysis(
                    prepped_data, vz=False
                )
            else:
                self.data[i] = self.data[i] | prepped_data
            return self.data[i]

        return {}

    def _data_is_valid(self, i: enums.Interval):
        if i not in self.data or "last" not in self.data[i]:
            self.data[i] = {}
            return False

        if "last" not in self.data[i]:
            return False

        if (self.data[i]["last"] + timedelta(minutes=i / 60)) < datetime.now():
            return False

        return True

    def _analyze(self):
        if data := self._get_data(self.bg.interval_long, simple=True):
            if long_trend := patterns.get_long_trend(data["df"]):
                if data := self._get_data(self.bg.interval_short, simple=True):
                    df = data["df"]
                    if short_trend := patterns.get_short_trend(df):
                        if long_trend != short_trend and self._get_pricing():
                            price = (
                                self.ask_price
                                if short_trend == enums.OrderDir.LONG
                                else self.bid_price
                            )
                            self.order = Order(
                                bot=self,
                                order_dir=short_trend,
                                price=price,
                            )
                            self._process_order(df)

    def _process_order(self, df=None):
        if df is None:
            data = self._get_data(
                self.bg.interval_short, valid=False, simple=True, short=True
            )
            if not data:
                return
            df = data["df"]

        ATR = df.ATR.iloc[-2]
        k = 1 if self.order.order_dir == enums.OrderDir.LONG else -1

        if self.order.order_dir == enums.OrderDir.LONG:
            k = 1
            price = self.bid_price
        else:
            k = -1
            price = self.ask_price

        if not self.order.stopprice:
            self.order.stopprice = price - k * ATR * self.bg.buffer_multiplier

        self.order.limitprice = self.order.price + k * ATR * self.bg.limit_multiplier

        self._get_volume()

    def _get_volume(self):
        if self.bg.traiding_balance:
            available_margin = min(
                self.bg.traiding_balance,
                self.account_margin,
            )
        else:
            available_margin = self.account_margin
        if self.bg.min_order:
            self.order.vol = self.pair.ordermin
        elif not self.order.vol:
            self.order.vol = (
                self.bg.risk
                / 100
                * available_margin
                / abs(self.order.price - self.order.stopprice)
                / self.pair.quote.confac
            )

        leverage = self.pair.max_leverage if self.bg.margin else 1
        margin_value = self.order.vol * self.pair.base.confac / leverage
        if margin_value > available_margin:
            self.order.vol *= available_margin / margin_value

        self.order.vol = round_down(self.order.vol, self.pair.lot_decimals)

        if self.order.vol < self.pair.ordermin:
            self.log("Rejected order on min. volume")
            return

        self._place_order()

    def _place_order(self):
        self.order.price = round_down(self.order.price, self.pair.cost_decimals)
        self.order.limitprice = round_down(
            self.order.limitprice, self.pair.cost_decimals
        )
        self.order.stopprice = round_down(self.order.stopprice, self.pair.cost_decimals)
        if data := api.open_position(
            self.pair.name,
            self.order.vol,
            self.order.limitprice,
            self.order.order_dir,
        ):
            self.order.order_id = data["order_id"]
            self.order.trade_id = data["trade_id"]
            self.order.price = data["price"]
            self.order.opentm = data["time"]
            self.order.rvr = self.order.get_rvr()
            self.order.status = enums.OrderStatus.FILLED
            self.order.save()
            self.pair.base.save()
            self.pair.quote.save()
            self.bg.ready = False
            self.log(f"Opened {self.order.order_dir} position")
            self._open_stop_loss()
        else:
            self.log("Failed to place order")

    def _open_stop_loss(self):
        if api.open_stop_loss(
            self.order.trade_id,
            self.order.get_stop_buffer(),
        ):
            self.order.status = enums.OrderStatus.PENDING
            self.order.save(update_fields=["status"])
            self.log(f"Placed trailing stop")

    def _check_order(self):
        if self.order.status == enums.OrderStatus.FILLED:
            self._open_stop_loss()
        else:
            if data := api.get_trade(self.order.trade_id):
                if data["status"] == enums.OrderStatus.CLOSED:
                    self._close_order(data)

    def _close_order(self, data):
        self.order.closeprice = data["closeprice"]
        self.order.closetm = data["closetm"]
        self.order.close_status = self.order.get_close_status()
        self.order.net = data["net"]
        self.order.rvr = self.order.get_rvr()
        self.order.save()
        self.bg.ready = True
        self._add_balance()

    def _add_balance(self):
        self.bg.balance = round_down(self.bg.balance + self.order.net, 2)
        self.bg.save(update_fields=["balance"])
        self.log(f"Position closed. Order's net is {self.order.net} USD")

        if self.order.close_status == enums.CloseStatus.TOUCHED:
            self.balance = round_down(self.balance + self.order.rvr, 1)
            self.conseq_losses = 0
            self.bg.conseq_losses = 0
        else:
            self.balance = round_down(self.balance - self.order.rvr, 1)
            self.conseq_losses += 1
            self.bg.conseq_losses += 1

        self.save(update_fields=["balance", "conseq_losses"])
        self.bg.save(update_fields=["conseq_losses"])

        self._check_health()

    def _check_health(self):
        if self.bg.conseq_losses >= self.bg.max_conseq_all:
            self.bg.on_status = False
            self.bg.save(update_fields=["on_status"])
            self.log(f"Bot-group stopped")

    def reset(self, full=False):
        self.conseq_losses = 0
        self.balance = 0
        self.on_status = True
        self.save()
        self.log_set.all().delete()  # type: ignore
        if full:
            self.order_set.all().delete()  # type: ignore

    def log(self, text, origin=None, ltype="G"):
        print(f"[!] {self} {text}...")
        Log.objects.create(
            bot=self,
            text=text,
            origin=origin,
            ltype=ltype,
        )


class BotGroup(models.Model):
    name = models.CharField(max_length=16, default="Oanda")
    bots = models.ManyToManyField("Bot", blank=True, verbose_name="Instruments")
    interval_short = models.IntegerField(
        choices=enums.Interval,  # type: ignore
        default=enums.Interval.FIVE_MIN,
    )
    interval_long = models.IntegerField(
        choices=enums.Interval,  # type: ignore
        default=enums.Interval.FOUR_HOUR,
    )
    risk = models.PositiveSmallIntegerField(
        default=2,
        verbose_name="Max pecentage of account balance to risk on one order",
    )
    traiding_balance = models.FloatField(
        null=True,
        blank=True,
        verbose_name="Max. balance available for trading in home currency",
    )
    balance = models.FloatField(default=0, verbose_name="Profit/loss in quote currency")
    max_conseq = models.PositiveSmallIntegerField(
        default=3, verbose_name="Maximum losses in a row before pair is shutdown"
    )
    max_conseq_all = models.PositiveSmallIntegerField(
        default=10, verbose_name="Maximum losses in a row before bot is shutdown"
    )
    conseq_losses = models.PositiveSmallIntegerField(
        default=0, verbose_name="Consequetive losses"
    )
    buffer_multiplier = models.FloatField(
        default=1, verbose_name="ATR multiplier for stop/loss"
    )
    limit_multiplier = models.FloatField(
        default=0.1, verbose_name="ATR multiplier for limit"
    )
    on_status = models.BooleanField(default=True, verbose_name="On/Off")
    autorefresh = models.BooleanField(
        default=True, verbose_name="Auto refresh bot page"
    )
    smooth = models.BooleanField(default=False, verbose_name="Smooth last candle")
    margin = models.BooleanField(default=True, verbose_name="Trade with margin")
    min_order = models.BooleanField(
        default=False, verbose_name="Place minimal order possible"
    )
    single = models.BooleanField(
        default=True, verbose_name="One position at a time only"
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.ready = True
        self.closed = False
        if self.pk:
            self._init_bots()

    def _init_bots(self):
        self.bot_set = self.bots.all()
        for bot in self.bot_set:
            bot.bg = self
            if self.ready and bot.open_order():
                self.ready = False

    def __str__(self):
        return self.name

    def start(self):
        self.on_status = True
        self.save(update_fields=["on_status"])

    def stop(self):
        self.on_status = False
        self.save(update_fields=["on_status"])

    def reset(self, full=False):
        self.balance = 0
        self.conseq_losses = 0
        self.on_status = True
        self.save(update_fields=["balance", "conseq_losses", "on_status"])
        if not self.bot_set:
            self.bot_set = self.bots.all()
        for bot in self.bot_set:
            bot.reset(full)

    def run(self):
        self.refresh_from_db()
        if closed():
            if not self.closed:
                print("[!] Forex is closed...")
                self.closed = True
        else:
            if self.closed:
                print("[!] Forex opened...")
                self.closed = False
            for bot in self.bot_set:
                if order := bot.open_order():
                    bot.run(order)
                elif not self.single or self.ready:
                    bot.run()


class Log(models.Model):
    bot: Bot = models.ForeignKey(Bot, on_delete=models.CASCADE)  # type: ignore
    text = models.TextField()
    origin = models.CharField(max_length=64, null=True, blank=True)
    ltype = models.CharField(max_length=1, default="G")
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-pk"]

    def __str__(self):
        return f"{self.bot.name} {self.text}"


def get_time():
    return timezone.localtime(timezone.now()).strftime("%m/%d/%y %H:%M:%S")


def closed():
    tz_NY = pytz.timezone("America/New_York")
    now = datetime.now(tz_NY)
    if (
        (now.isoweekday() == 5 and now.hour >= 16 and now.minute >= 50)
        or (now.isoweekday() == 6)
        or (now.isoweekday() == 7)
        or (now.isoweekday() == 1 and now.hour < 8 and now.minute < 10)
    ):
        return True
    return False


def round_down(x: int | float, p: int):
    return int(x * pow(10, p)) / pow(10, p)
