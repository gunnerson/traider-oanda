from django.contrib.auth.decorators import login_required
from django.db.models import Avg
from django.http import HttpResponseBadRequest
from django.shortcuts import redirect, render

from . import chart
from .enums import CloseStatus
from .models import Bot, BotGroup, Log, Order


@login_required
def analytics(request):
    if request.method == "GET":
        context = {
            "page_title": "Analytics | ",
        }
        return render(request, "app/analytics.html", context)
    else:
        return HttpResponseBadRequest("Invalid request")


@login_required
def bot(request):
    if request.method == "GET":
        bg = BotGroup.objects.get(id=1)
        context = {
            "bg": bg,
            "page_title": "Bot | ",
            "logs": Log.objects.all(),
            "autorefresh": bg.autorefresh,
        }
        return render(request, "app/bot.html", context)
    else:
        return HttpResponseBadRequest("Invalid request")


@login_required
def log(request, pk):
    bot = Bot.objects.get(id=pk)
    if request.method == "GET":
        context = {
            "bot": bot,
            "logs": bot.log_set.all(),  # type: ignore
            "page_title": bot.__str__() + "LOG - ",
        }
        return render(request, "app/log.html", context)
    else:
        return HttpResponseBadRequest("Invalid request")


@login_required
def orders(request):
    if request.method == "GET":
        context = _get_orders_context()
        context["page_title"] = "ORDERS | "
        return render(request, "app/orders.html", context)
    else:
        return HttpResponseBadRequest("Invalid request")


@login_required
def bot_start(request, pk):
    if request.method == "GET":
        bg = BotGroup.objects.get(id=pk)
        bg.start()
        return redirect("app:bot")
    else:
        return HttpResponseBadRequest("Invalid request")


@login_required
def bot_stop(request, pk):
    if request.method == "GET":
        bg = BotGroup.objects.get(id=pk)
        bg.stop()
        return redirect("app:bot")
    else:
        return HttpResponseBadRequest("Invalid request")


@login_required
def bot_reset(request, pk):
    if request.method == "GET":
        bg = BotGroup.objects.get(id=pk)
        bg.reset(True)
        return redirect("app:bot")
    else:
        return HttpResponseBadRequest("Invalid request")


def _get_orders_context():
    orders = Order.objects.filter(closeprice__isnull=False)
    won = orders.filter(close_status=CloseStatus.TOUCHED)
    lost = orders.filter(close_status=CloseStatus.STOPPED)

    a = orders.count()
    w = won.count()
    l = lost.count()
    rwa = round(won.aggregate(Avg("rvr"))["rvr__avg"], 1) if w else 0
    rla = round(lost.aggregate(Avg("rvr"))["rvr__avg"], 1) if l else 0
    wp = round(w / a * 100) if a else 0

    context = {
        "orders": orders,
        "a": a,
        "w": w,
        "l": l,
        "ww": wp,
        "rwa": rwa,
        "rla": rla,
        "pr": True if (a and rwa * w / a > 0.5) else False,
    }

    return context
