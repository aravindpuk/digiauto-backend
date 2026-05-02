from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from jobcard.models import JobStatus
from user.models import UserRole

User = get_user_model()

#### this file and folder like management/commands/setup_data.py 
# is for initial setup of data like roles, job statuses, and superuser creation. 
# You can run this command using `python manage.py setup_data` 
# to populate the database with the necessary initial data. only for render setup testing case..
# no need for real production

class Command(BaseCommand):
    help = "Initial setup for roles, job statuses, and superuser"

    def handle(self, *args, **kwargs):

        # ✅ Create Roles
        roles = ["admin", "staff", "customer"]
        for role in roles:
            UserRole.objects.get_or_create(name=role)

        # ✅ Create Job Statuses
        statuses = [
            ("pending", 0),
            ("active", 1),
            ("completed", 2),
            ("delivered", 3),
        ]

        for name, order in statuses:
            JobStatus.objects.get_or_create(name=name, defaults={"order": order})

        # ✅ Create Superuser
        if not User.objects.filter(username="admin").exists():
            User.objects.create_superuser(
                username="admin",
                email="admin@example.com",
                password="admin123"
            )
            self.stdout.write("Superuser created")
        else:
            self.stdout.write("Superuser already exists")

        self.stdout.write("Initial setup completed")