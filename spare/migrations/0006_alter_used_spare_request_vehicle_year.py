from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("spare", "0005_used_spare_request_image")]

    operations = [
        migrations.AlterField(
            model_name="usedsparerequest",
            name="vehicle_year",
            field=models.CharField(blank=True, default="", max_length=4),
        ),
    ]
