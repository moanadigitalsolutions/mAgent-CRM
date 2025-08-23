from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission

GROUPS = [
    ("Admin", None),
    ("Employee", None),
    ("Sales", None),
    ("ReadOnly", None),
]

class Command(BaseCommand):
    help = "Initialize default user groups for RBAC"

    def handle(self, *args, **options):
        for name, perms in GROUPS:
            group, created = Group.objects.get_or_create(name=name)
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created group {name}"))
            if perms:
                for codename in perms:
                    try:
                        perm = Permission.objects.get(codename=codename)
                        group.permissions.add(perm)
                    except Permission.DoesNotExist:
                        self.stdout.write(self.style.WARNING(f"Permission {codename} not found for group {name}"))
        self.stdout.write(self.style.SUCCESS("Group initialization complete."))
