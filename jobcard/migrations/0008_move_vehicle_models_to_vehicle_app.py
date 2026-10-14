import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("jobcard", "0007_jobcardspare_amount_price_mode"),
        # Labour must move its FK before the historical jobcard vehicle
        # catalog models are removed from migration state.
        ("labour", "0003_move_vehicle_model_to_vehicle_app"),
        ("vehicle", "0001_initial"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.AlterField(
                    model_name="vehicle",
                    name="vehicle_model",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="vehicle.vehiclemodel",
                    ),
                ),
                migrations.AlterField(
                    model_name="jobcard",
                    name="vehicle",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="vehicle.vehicle",
                    ),
                ),
            ],
            state_operations=[
                migrations.AlterField(
                    model_name="vehicle",
                    name="vehicle_model",
                    field=models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        to="vehicle.vehiclemodel",
                    ),
                ),
                migrations.AlterField(
                    model_name="jobcard",
                    name="vehicle",
                    field=models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        to="vehicle.vehicle",
                    ),
                ),
                migrations.DeleteModel(name="Vehicle"),
                migrations.DeleteModel(name="VehicleModel"),
                migrations.DeleteModel(name="VehicleMake"),
            ],
        ),
    ]
