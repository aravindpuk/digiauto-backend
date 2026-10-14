from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("spare", "0002_alter_spare_partnumber"),
        ("user", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="UsedSpareRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vehicle_make", models.CharField(max_length=100)),
                ("vehicle_model", models.CharField(max_length=100)),
                ("vehicle_year", models.CharField(max_length=4)),
                ("spare_name", models.CharField(blank=True, default="", max_length=200)),
                ("image", models.ImageField(blank=True, null=True, upload_to="used_spare_requests/")),
                ("status", models.CharField(choices=[("submitted", "Submitted"), ("reviewing", "Under review"), ("available", "Part found"), ("closed", "Closed")], default="submitted", max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("customer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="used_spare_requests", to="user.user")),
            ],
            options={"ordering": ["-created_at"]},
        ),
    ]
