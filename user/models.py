from django.db import models
from django.conf import settings
from datetime import datetime, timedelta, timezone

from django.contrib.auth.hashers import make_password,check_password


import jwt

# Create your models here.

class UserRole(models.Model):
    name = models.CharField(max_length=50, unique=True)

    def __str__(self):
        return self.name

class User(models.Model):
   
    name      = models.CharField(max_length=100)
    mobile    = models.CharField(max_length=15, unique=True)
    address   = models.TextField(max_length=255, blank=True)
    pin       = models.CharField(max_length=128)   # optional, we can store hashed only
   
    role      = models.ForeignKey(UserRole, on_delete=models.SET_NULL, null=True)

    branches  = models.ManyToManyField("garage.Branch", blank=True)

    is_active = models.BooleanField(default=True)
    
    def set_pin(self, raw_pin):
        self.pin = make_password(raw_pin)

    def check_pin(self, raw_pin):
        return check_password(raw_pin, self.pin)

    def __str__(self):
        return f"{self.name} ({self.mobile})"


class LoginInfo(models.Model):
    user          = models.ForeignKey(User, on_delete=models.CASCADE)
    login_time    = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    logout_time   = models.DateTimeField(null=True, blank=True)
    token         = models.CharField(max_length=512,blank=True,null=True)
    
    login_status  = models.BooleanField(default=False)
    is_active     = models.BooleanField(default=True)
   

    def generate_auth_token(self,expire_hours = 24):
        payload = {
            "user_id": self.user.id,
            "mobile": self.user.mobile,
            "exp": datetime.now(timezone.utc) + timedelta (hours=expire_hours),
            'iat': datetime.now(timezone.utc) # issued at
        }
        token = jwt.encode(payload, settings.SECRET_KEY, algorithm="HS256")
        self.token = token
        self.login_status = True
        self.save()
        return token