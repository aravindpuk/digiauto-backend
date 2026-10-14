from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from jobcard.models import JobStatus
from user.models import UserRole, User as AppUser

User = get_user_model()

#### this file and folder like management/commands/setup_data.py 
# is for initial setup of data like roles, job statuses, and superuser creation. 
# You can run this command using `python manage.py setup_data` 
# to populate the database with the necessary initial data. only for render setup testing case..
# no need for real production

class Command(BaseCommand):
    help = "Initial setup for roles, job statuses, and superuser"

    def handle(self, *args, **kwargs):

        # Rename legacy roles and preserve their user assignments.
        for old_name, new_name in (("admin", "garage-admin"), ("staff", "garage-staff")):
            old_role = UserRole.objects.filter(name=old_name).first()
            if old_role:
                new_role, _ = UserRole.objects.get_or_create(name=new_name)
                AppUser.objects.filter(role=old_role).update(role=new_role)
                old_role.delete()

        # ✅ Create Roles
        roles = [
            "customer",
            "garage-admin",
            "garage-staff",
            "digi-admin",
            "digi-staff",
            "scrap-team",
        ]
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
