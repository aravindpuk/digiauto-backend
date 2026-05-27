
from django.urls import path
from . import views
 
urlpatterns = [
    path("jobcards/", views.JobCardView.as_view(), name="jobcards"),
    path("jobcards/<int:jobcard_id>/", views.JobCardDetailView.as_view(), name="jobcard-detail"),
    path("jobcards/<int:jobcard_id>/document/", views.JobCardDocumentView.as_view(), name="jobcard-document"),
    path("manage/",views.manage_jobs_list,name="manage-jobs"),
]
