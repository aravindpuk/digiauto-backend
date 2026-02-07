
from django.urls import path
from . import views
urlpatterns = [
    path("spare-create", views.CreateSpareAPI.as_view(), name="spare-create"),
    ]