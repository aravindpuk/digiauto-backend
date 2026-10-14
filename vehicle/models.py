from django.db import models


class VehicleMake(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "jobcard_vehiclemake"

    def __str__(self):
        return self.name


class VehicleModel(models.Model):
    name = models.CharField(max_length=100)
    fkMaker = models.ForeignKey(
        VehicleMake, on_delete=models.CASCADE, related_name="models"
    )

    class Meta:
        db_table = "jobcard_vehiclemodel"
        unique_together = ("name", "fkMaker")

    def __str__(self):
        return f"{self.fkMaker.name} {self.name}"


class Vehicle(models.Model):
    vehicle_number = models.CharField(max_length=20)
    vehicle_model = models.ForeignKey(
        VehicleModel, on_delete=models.SET_NULL, null=True, blank=True
    )
    user = models.ForeignKey("user.User", on_delete=models.CASCADE)
    year = models.CharField(max_length=4, blank=True, default="")
    chassis_number = models.CharField(max_length=50, blank=True, default="")
    engine_number = models.CharField(max_length=50, blank=True, default="")

    class Meta:
        db_table = "jobcard_vehicle"
        unique_together = ("vehicle_number", "user")

    def __str__(self):
        return self.vehicle_number
