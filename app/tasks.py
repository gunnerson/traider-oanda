from .celery import app
from .models import BotGroup

bg = BotGroup.objects.get(id=1)


@app.task
def run_bots():
    bg.run()
