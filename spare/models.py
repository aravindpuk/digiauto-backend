from django.db import models

# Create your models here.

class Spare(models.Model):
    partnumber = models.CharField(max_length=50)
    partname   = models.CharField(max_length=255)
    

class SparePurchaseData(models.Model):
    mrp             = models.DecimalField(max_digits=10, decimal_places=2)
    quantity        = models.IntegerField(default=1)
    purchase_amount = models.DecimalField(max_digits=10,decimal_places=2)
    
    spare           = models.ForeignKey(Spare, on_delete=models.CASCADE)
    branches        = models.ForeignKey('garage.Branch',on_delete=models.CASCADE)

    created_at      = models.DateTimeField(auto_now_add=True)


class SpareStock(models.Model):
    mrp             = models.DecimalField(max_digits=10, decimal_places=2)
    quantity        = models.IntegerField(default=1)
    purchase_amount = models.DecimalField(max_digits=10,decimal_places=2)
    
    spare           = models.ForeignKey(Spare, on_delete=models.CASCADE)
    branches        = models.ForeignKey('garage.Branch',on_delete=models.CASCADE)