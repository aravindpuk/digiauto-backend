
from django.db import models
from django.forms import modelformset_factory

# Create your models here.

class Garage(models.Model):
    name       =  models.CharField(max_length=255)
    email      = models.EmailField(blank=True)
    mobile     = models.CharField(max_length=15)
    latitude   = models.FloatField(null=True,blank=True)
    longitude  = models.FloatField(null=True,blank=True)
    logo       = models.FileField(upload_to='garage_logos/',blank=True,null=True)
    

    def __str__(self):
        return self.name

class Branch(models.Model):
    garage     = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='branches')
    name       = models.CharField(max_length=255)
    latitude   = models.FloatField(null=True,blank=True)
    longitude  = models.FloatField(null=True,blank=True)

    def __str__(self):
        return f"{self.name} - {self.garage.name}"