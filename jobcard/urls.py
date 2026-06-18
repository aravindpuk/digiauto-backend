from django.urls import path
from . import views

urlpatterns = [
    path("customer/latest/", views.customer_latest_jobcard, name="customer-latest-jobcard"),
    path("jobcards/", views.JobCardView.as_view(), name="jobcards"),
    path("jobcards/<int:jobcard_id>/", views.JobCardDetailView.as_view(), name="jobcard-detail"),
    path("jobcards/<int:jobcard_id>/document/", views.JobCardDocumentView.as_view(), name="jobcard-document"),
    path("jobcards/<int:jobcard_id>/view/", views.JobCardViewDocument.as_view(), name="jobcard-view"),
    path("jobcards/<int:jobcard_id>/share-whatsapp/", views.ShareWhatsAppView.as_view(), name="jobcard-share-whatsapp"),
    path("view/q/<str:token>/", views.PublicQuotationView.as_view(), name="jobcard-public-quotation"),
    path("manage/", views.manage_jobs_list, name="manage-jobs"),
    path("invoice-pdf/<str:token>/", views.InvoicePdfView.as_view(), name="jobcard-invoice-pdf"),
    path("reports/", views.JobCardReportsView.as_view(), name="jobcard-reports"),
]