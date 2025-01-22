from django.urls import path

app_name = "app"
from . import views

urlpatterns = [
    path("analytics/", views.analytics, name="analytics"),
    path("bot/", views.bot, name="bot"),
    path("bot/<int:pk>/log", views.log, name="log"),
    path("orders/", views.orders, name="orders"),
    path("bot/group/<int:pk>/start", views.bot_start, name="bot_start"),
    path("bot/group/<int:pk>/stop", views.bot_stop, name="bot_stop"),
    path("bot/group/<int:pk>/reset", views.bot_reset, name="bot_reset"),
]
