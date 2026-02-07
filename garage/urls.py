from django.urls import path
from . import views
urlpatterns = [
    path('garage-info/', views.RegisterGarage.as_view(), name='garage-info'),
]