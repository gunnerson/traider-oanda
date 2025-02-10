from django.db import models
from django.utils.translation import gettext_lazy as _


class Interval(models.IntegerChoices):
    ONE_MIN = 1, _("M1")
    FIVE_MIN = 5, _("M5")
    FIFTEEN_MIN = 15, _("M15")
    THIRTY_MIN = 30, _("M30")
    SIXTY_MIN = 60, _("H1")
    FOUR_HOUR = 240, _("H4")
    ONE_DAY = 1440, _("D")
    ONE_WEEK = 10080, _("W")


class OrderDir(models.TextChoices):
    LONG = "LONG"
    SHORT = "SHORT"


class OrderType(models.TextChoices):
    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TRAILING_STOP_LOSS = "TRAILING_STOP_LOSS"


class CloseStatus(models.TextChoices):
    PROFIT = "P"
    LOSS = "L"


class OrderStatus(models.TextChoices):
    PENDING = "PENDING"
    FILLED = "FILLED"
    TRIGGERED = "TRIGGERED"
    CANCELLED = "CANCELLED"
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    TRAILING = "TRAILING"


class BotHealth(models.TextChoices):
    STOPPED = "bg-black"
    PENDING = "bg-blue-700"
    PROFITABLE = "bg-green-700"
    UNPROFITABLE = "bg-red-700"
    OTHER = "bg-gray-700"


class Method(models.TextChoices):
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
