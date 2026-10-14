import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("labour", "0002_alter_labour_name"),
        ("vehicle", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="labourprice",
            name="vehicle_model",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="labour_prices",
                to="vehicle.vehiclemodel",
            ),
        ),
    ]
