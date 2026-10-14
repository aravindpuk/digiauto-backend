import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("spare", "0004_spare_shop")]

    operations = [
        migrations.CreateModel(
            name="UsedSpareRequestImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="used_spare_requests/")),
                ("request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="photos", to="spare.usedsparerequest")),
            ],
        ),
    ]
