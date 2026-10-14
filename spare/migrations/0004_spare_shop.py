import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("spare", "0003_used_spare_request"),
        ("user", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SpareShop",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("name", models.CharField(max_length=255)),
                ("location", models.CharField(max_length=500)),
                ("latitude", models.FloatField()),
                ("longitude", models.FloatField()),
                ("owner", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="spare_shop", to="user.user")),
            ],
        ),
    ]
