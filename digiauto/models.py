# from django.db import models
# from django.conf import settings
# from datetime import datetime, timedelta, timezone

# import jwt


# # Create your models here.


# from django.contrib.auth.hashers import make_password,check_password



# class Garage(models.Model):
#     name    =  models.CharField(max_length=255)
#     email   = models.EmailField()
#     mobile  = models.CharField(max_length=15)
#     place   = models.CharField(max_length=255)
#     logo    = models.FileField(upload_to='garage_logos/',blank=True,null=True)
#     seal    = models.FileField(upload_to='garage_seals/',blank=True,null=True)

#     def __str__(self):
#         return self.name

# class Branch(models.Model):
#     garage   = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='branches')
#     name     = models.CharField(max_length=255)
#     place    = models.CharField(max_length=255)

#     def __str__(self):
#         return f"{self.name} - {self.garage.name}"




# class UserRole(models.Model):
#     name = models.CharField(max_length=50, unique=True)

#     def __str__(self):
#         return self.name

# class User(models.Model):
   
#     name      = models.CharField(max_length=100)
#     mobile    = models.CharField(max_length=15, unique=True)
#     pin       = models.CharField(max_length=128)   # optional, we can store hashed only
   
#     role      = models.ForeignKey(UserRole, on_delete=models.SET_NULL, null=True)

#     branches  = models.ManyToManyField(Branch, blank=True)

#     is_active = models.BooleanField(default=True)
    
#     def set_pin(self, raw_pin):
#         self.pin = make_password(raw_pin)

#     def check_pin(self, raw_pin):
#         return check_password(raw_pin, self.pin)

#     def __str__(self):
#         return f"{self.name} ({self.mobile})"


# class LoginInfo(models.Model):
#     user          = models.ForeignKey(User, on_delete=models.CASCADE)
#     login_time    = models.DateTimeField(auto_now_add=True)
#     last_activity = models.DateTimeField(auto_now=True)
#     logout_time   = models.DateTimeField(null=True, blank=True)
#     token         = models.CharField(max_length=512,blank=True,null=True)
    
#     login_status  = models.BooleanField(default=False)
#     is_active     = models.BooleanField(default=True)
   

#     def generate_auth_token(self,expire_hours = 24):
#         payload = {
#             "user_id": self.user.id,
#             "mobile": self.user.mobile,
#             "exp": datetime.now(timezone.utc) + timedelta (hours=expire_hours),
#             'iat': datetime.now(timezone.utc) # issued at
#         }
#         token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
#         self.token = token
#         self.login_status = True
#         self.save()
#         return token



# class VehicleMake(models.Model):
#     name = models.CharField(max_length=100, unique=True)

#     def __str__(self):
#         return self.name
    


# class VehicleModel(models.Model):
#     name    = models.CharField(max_length=100)
#     fkMaker = models.ForeignKey(VehicleMake,on_delete=models.CASCADE,related_name='models')

#     class Meta:
#         unique_together = ('name', 'fkMaker')  # ensures no duplicate model for same maker

#     def __str__(self):
#         return self.name

# class Complaint(models.Model):
#     text = models.CharField(max_length=255, unique=True)

#     def __str__(self):
#         return self.text

# class JobStatus(models.Model):
#     name = models.CharField(max_length=50, unique=True)

#     def __str__(self):
#         return self.name


# class JobCard(models.Model):
#     branch         = models.ForeignKey(Branch, on_delete=models.CASCADE)
#     created_by     = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True,related_name='Job_creator')
#     complaints     = models.ManyToManyField(Complaint, related_name='jobcards')
#     vehicle_number = models.CharField(max_length=20)
#     kilometer      = models.IntegerField()
#     vehicle_model  = models.ForeignKey(VehicleModel, on_delete=models.SET_NULL, null=True, blank=True)
#     created_at     = models.DateTimeField(auto_now_add=True)
#     mechanic       = models.ManyToManyField(User,related_name='job_mechanic')
#     status         = models.ForeignKey(JobStatus, on_delete=models.CASCADE)

#     def __str__(self):
#         return f"JobCard {self.id} - {self.vehicle_number}"


# class Spare(models.Model):
#     partnumber = models.CharField(max_length=50)
#     partname   = models.CharField(max_length=255)
    

# class SparePurchaseData(models.Model):
#     mrp             = models.DecimalField(max_digits=10, decimal_places=2)
#     quantity        = models.IntegerField(default=1)
#     purchase_amount = models.DecimalField(max_digits=10,decimal_places=2)
    
#     spare           = models.ForeignKey(Spare, on_delete=models.CASCADE)
#     branches        = models.ForeignKey('Branch',on_delete=models.CASCADE)

#     created_at      = models.DateTimeField(auto_now_add=True)


# class SpareStock(models.Model):
#     mrp             = models.DecimalField(max_digits=10, decimal_places=2)
#     quantity        = models.IntegerField(default=1)
#     purchase_amount = models.DecimalField(max_digits=10,decimal_places=2)
    
#     spare           = models.ForeignKey(Spare, on_delete=models.CASCADE)
#     branches        = models.ForeignKey('Branch',on_delete=models.CASCADE)


    

# class Labour(models.Model):
   
#     name = models.CharField(max_length=255)
#     def __str__(self):
#         return self.name

# class LabourPrice(models.Model):
#     labour        = models.ForeignKey(Labour, on_delete=models.CASCADE, related_name='prices')
#     garage        = models.ForeignKey(Garage, on_delete=models.CASCADE, related_name='labour_prices')
#     vehicle_model = models.ForeignKey(VehicleModel, null=True, blank=True, on_delete=models.CASCADE, related_name='labour_prices')

#     price         = models.DecimalField(max_digits=10, decimal_places=2)

#     class Meta:
#         unique_together = ('labour', 'garage', 'vehicle_model')

#     def __str__(self):
        
#         vehicle = self.vehicle_model.name if self.vehicle_model else "Default"
#         return f"{self.labour.name} - {vehicle} → {self.price}"

# class JobCardSpare(models.Model):
#     jobcard    = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='spares')
#     spare      = models.ForeignKey(Spare, on_delete=models.CASCADE)
#     quantity   = models.IntegerField()
#     mrp        = models.DecimalField(max_digits=10, decimal_places=2)
#     complaints = models.ManyToManyField(Complaint, related_name='spares', blank=True)

#     def __str__(self):
#         return f"{self.spare.partname} - Qty: {self.quantity}"

# class JobCardLabour(models.Model):
#     jobcard    = models.ForeignKey(JobCard, on_delete=models.CASCADE, related_name='labour_services')
#     labour     = models.ForeignKey(Labour, on_delete=models.CASCADE)
#     technician = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)

#     complaints = models.ManyToManyField(Complaint, related_name='labours', blank=True)

#     def __str__(self):
#         return f"{self.labour.name}"

# class Invoice(models.Model):
#     jobcard        = models.OneToOneField(JobCard, on_delete=models.CASCADE, related_name='invoice')
#     invoice_number = models.CharField(max_length=50, unique=True)
#     date           = models.DateField(auto_now_add=True)
#     total_amount   = models.DecimalField(max_digits=12, decimal_places=2)
#     paid           = models.BooleanField(default=False)

#     def __str__(self):
#         return f"Invoice {self.invoice_number}"
