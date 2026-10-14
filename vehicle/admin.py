from django.contrib import admin

from .models import Vehicle, VehicleMake, VehicleModel


admin.site.register((Vehicle, VehicleMake, VehicleModel))
