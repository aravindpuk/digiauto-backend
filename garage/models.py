from django.db import models

# Create your models here.

class Garage(models.Model):
    name    =  models.CharField(max_length=255)
    email   = models.EmailField()
    mobile  = models.CharField(max_length=15)
    place   = models.CharField(max_length=255)
    logo    = models.FileField(upload_to='garage_logos/',blank=True,null=True)
    seal    = models.FileField(upload_to='garage_seals/',blank=True,null=True)

    def __str__(self):
        return self.name

class Branch(models.Model):
    garage   = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='branches')
    name     = models.CharField(max_length=255)
    place    = models.CharField(max_length=255)

    def __str__(self):
        return f"{self.name} - {self.garage.name}"