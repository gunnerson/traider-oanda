from django.core.management.base import BaseCommand

from app.models import Bot, BotGroup, Pair


class Command(BaseCommand):
    help = "Import Instruments"

    def handle(self, *args, **options):
        Pair.add_pairs()
        Bot.add_bots()
        bg, created = BotGroup.objects.get_or_create(id=1)
        bg.bots.set(Bot.objects.all())
        print(f"[+] BotGroup {bg.name} created...")
        self.stdout.write(self.style.SUCCESS("Successfully imported instruments"))
