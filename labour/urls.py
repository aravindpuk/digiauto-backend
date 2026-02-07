from django.urls import path
from . import views
urlpatterns = [
path('info/', views.labour_info, name='labour_info'),]   