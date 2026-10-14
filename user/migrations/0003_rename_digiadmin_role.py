from django.db import migrations


def rename_and_seed_roles(apps, schema_editor):
    UserRole = apps.get_model("user", "UserRole")
    AppUser = apps.get_model("user", "User")

    old_role = UserRole.objects.filter(name="digiadmin").first()
    admin_role, _ = UserRole.objects.get_or_create(name="digi-admin")
    if old_role:
        AppUser.objects.filter(role_id=old_role.pk).update(role_id=admin_role.pk)
        old_role.delete()

    for name in (
        "customer",
        "garage-admin",
        "garage-staff",
        "digi-admin",
        "digi-staff",
        "scrap-team",
    ):
        UserRole.objects.get_or_create(name=name)


class Migration(migrations.Migration):
    dependencies = [("user", "0002_seed_digi_roles")]

    operations = [
        migrations.RunPython(rename_and_seed_roles, migrations.RunPython.noop),
    ]
