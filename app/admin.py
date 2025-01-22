from django.contrib import admin

from .models import *

admin.site.register(Asset)
admin.site.register(Pair)
admin.site.register(Order)
admin.site.register(Bot)
admin.site.register(BotGroup)
admin.site.register(Log)
