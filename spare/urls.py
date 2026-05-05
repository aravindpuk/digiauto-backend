
from django.urls import path
from . import views
urlpatterns = [
    path("spare-create", views.CreateSpareAPI.as_view(), name="spare-create"),
    path("search/", views.search_spare, name="spare-search"),
    path("list/<int:branch_id>/", views.SpareListAPI.as_view(), name="spare-list"),
    path("stock/add/", views.AddSpareStockAPI.as_view(), name="spare-stock-add"),
    path("update/<int:spare_id>/", views.UpdateSpareAPI.as_view(), name="spare-update"),
    path("stock/update/<int:stock_id>/", views.UpdateSpareStockAPI.as_view(), name="spare-stock-update"),
    path("jobcard/<int:jobcard_id>/", views.JobCardSpareView.as_view(), name="jobcard-spare"),
    ]
