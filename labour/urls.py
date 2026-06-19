from django.urls import path
from . import views
urlpatterns = [
    path("search/",views.search_labour,name="labour-search"),
    path("create/",views.LabourMasterView.as_view(),name="labour-create"),
    path("update/<int:labour_id>/",views.LabourMasterView.as_view(),name="labour-update"),
    path("jobcard/<int:jobcard_id>/",views.JobCardLabourView.as_view(),name="jobcard-labour"),
]
