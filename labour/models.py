from django.db import models

# Create your models here.

class Labour(models.Model):
   
    name = models.CharField(max_length=255)
    def __str__(self):
        return self.name

class LabourPrice(models.Model):
    labour        = models.ForeignKey(Labour, on_delete=models.CASCADE, related_name='prices')
    garage        = models.ForeignKey("garage.Garage", on_delete=models.CASCADE, related_name='labour_prices')
    vehicle_model = models.ForeignKey("jobcard.VehicleModel", null=True, blank=True, on_delete=models.CASCADE, related_name='labour_prices')

    price         = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ('labour', 'garage', 'vehicle_model')

    def __str__(self):
        
        vehicle = self.vehicle_model.name if self.vehicle_model else "Default"
        return f"{self.labour.name} - {vehicle} → {self.price}"
