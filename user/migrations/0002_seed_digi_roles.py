from django.db import migrations


def create_digi_roles(apps, schema_editor):
    UserRole = apps.get_model("user", "UserRole")
    for name in ("digi-staff", "digiadmin"):
        UserRole.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [("user", "0001_initial")]

    operations = [migrations.RunPython(create_digi_roles, migrations.RunPython.noop)]
