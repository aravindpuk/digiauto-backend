import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("spare", "0006_alter_used_spare_request_vehicle_year"),
        ("user", "0001_initial"),
        ("vehicle", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SpareShopInventory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("vehicle_year", models.CharField(blank=True, default="", max_length=4)),
                ("spare_name", models.CharField(max_length=200)),
                ("mrp", models.DecimalField(decimal_places=2, max_digits=10)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="inventory", to="spare.spareshop")),
                ("vehicle_model", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="shop_spares", to="vehicle.vehiclemodel")),
            ],
            options={"ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="SpareShopInventoryImage",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("image", models.ImageField(upload_to="spare_shop_inventory/")),
                ("inventory", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="photos", to="spare.spareshopinventory")),
            ],
        ),
        migrations.CreateModel(
            name="SpareShopOrder",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("status", models.CharField(choices=[("forwarded", "Forwarded to shop"), ("accepted", "Accepted"), ("rejected", "Rejected"), ("delivered", "Delivered")], default="forwarded", max_length=20)),
                ("shop_note", models.CharField(blank=True, default="", max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("forwarded_by", models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="forwarded_spare_orders", to="user.user")),
                ("request", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="shop_orders", to="spare.usedsparerequest")),
                ("shop", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="orders", to="spare.spareshop")),
            ],
            options={"ordering": ["-updated_at", "-created_at"]},
        ),
    ]
