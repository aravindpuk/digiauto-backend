from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("jobcard", "0007_jobcardspare_amount_price_mode"),
        ("user", "0001_initial"),
    ]

    # These tables were created by jobcard's historical migrations. Adopt them
    # into this app's migration state without dropping or recreating their data.
    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.CreateModel(
                    name="VehicleMake",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=100, unique=True)),
                    ],
                    options={"db_table": "jobcard_vehiclemake"},
                ),
                migrations.CreateModel(
                    name="VehicleModel",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("name", models.CharField(max_length=100)),
                        ("fkMaker", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="models", to="vehicle.vehiclemake")),
                    ],
                    options={
                        "db_table": "jobcard_vehiclemodel",
                        "unique_together": {("name", "fkMaker")},
                    },
                ),
                migrations.CreateModel(
                    name="Vehicle",
                    fields=[
                        ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                        ("vehicle_number", models.CharField(max_length=20)),
                        ("year", models.CharField(blank=True, default="", max_length=4)),
                        ("chassis_number", models.CharField(blank=True, default="", max_length=50)),
                        ("engine_number", models.CharField(blank=True, default="", max_length=50)),
                        ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="user.user")),
                        ("vehicle_model", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to="vehicle.vehiclemodel")),
                    ],
                    options={
                        "db_table": "jobcard_vehicle",
                        "unique_together": {("vehicle_number", "user")},
                    },
                ),
            ],
        ),
    ]
