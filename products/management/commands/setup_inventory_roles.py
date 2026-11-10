from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Create the 'inventory' and 'owner' groups (assign users to them in /admin/ > Users > Groups)."

    def handle(self, *args, **opts):
        for name in ('inventory', 'owner'):
            _, created = Group.objects.get_or_create(name=name)
            self.stdout.write(f"{'created' if created else 'exists '} group: {name}")