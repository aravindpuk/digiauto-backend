from django.urls import path
from . import views
urlpatterns = [
    path("search/",views.search_labour,name="labour-search"),
    path("jobcard/<int:jobcard_id>/",views.JobCardLabourView.as_view(),name="jobcard-labour"),
]