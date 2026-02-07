from django.urls import path
from . import views
urlpatterns = [
    path('joblist/',views.jobcard_list, name='jobcard-list'),
]