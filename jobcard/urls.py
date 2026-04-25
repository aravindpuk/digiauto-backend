from django.urls import path
from . import views
urlpatterns = [
    path('create-jobcard',views.JobCardView.as_view()),
    path('joblist/',views.fetch_jobcards, name='jobcard-list'),
]