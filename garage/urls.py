
from django.urls import path
from . import views
 
urlpatterns = [
    path("register/",views.RegisterGarage.as_view(),  name="garage-register"),
    path("<int:garage_id>/branches/",views.GarageBranches.as_view(),  name="garage-branches"),
]
