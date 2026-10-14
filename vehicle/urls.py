from django.urls import path

from .views import VehicleCatalog


urlpatterns = [path("catalog/", VehicleCatalog.as_view(), name="vehicle-catalog")]
