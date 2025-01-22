from __future__ import absolute_import, unicode_literals

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "traider.settings")

app = Celery("app")

app.config_from_object("django.conf:settings", namespace="CELERY")

app.autodiscover_tasks()

app.conf.beat_schedule = {
    "run_bots": {
        "task": "app.tasks.run_bots",
        "schedule": 5.0,
        "options": {
            "expires": 6.0,
        },
    },
}
