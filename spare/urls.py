
from django.urls import path
from . import views
from . import shop_views
urlpatterns = [
    path("shops/register/", views.RegisterSpareShop.as_view(), name="spare-shop-register"),
    path("used-requests/", views.UsedSpareRequestsAPI.as_view(), name="used-spare-requests"),
    path("used-requests/<int:request_id>/", views.UsedSpareRequestsAPI.as_view(), name="used-spare-request-detail"),
    path("shops/inventory/", shop_views.SpareShopInventoryAPI.as_view(), name="spare-shop-inventory"),
    path("shops/inventory/<int:item_id>/", shop_views.SpareShopInventoryDetailAPI.as_view(), name="spare-shop-inventory-detail"),
    path("shops/orders/", shop_views.SpareShopOrdersAPI.as_view(), name="spare-shop-orders"),
    path("shops/orders/<int:order_id>/", shop_views.SpareShopOrdersAPI.as_view(), name="spare-shop-order-action"),
    path("digi-staff/orders/", shop_views.DigiStaffSpareOrdersAPI.as_view(), name="digi-staff-spare-orders"),
    path("digi-staff/orders/<int:request_id>/forward/", shop_views.DigiStaffSpareOrdersAPI.as_view(), name="digi-staff-forward-spare-order"),
    path("spare-create", views.CreateSpareAPI.as_view(), name="spare-create"),
    path("search/", views.search_spare, name="spare-search"),
    path("list/<int:branch_id>/", views.SpareListAPI.as_view(), name="spare-list"),
    path("stock/add/", views.AddSpareStockAPI.as_view(), name="spare-stock-add"),
    path("update/<int:spare_id>/", views.UpdateSpareAPI.as_view(), name="spare-update"),
    path("stock/update/<int:stock_id>/", views.UpdateSpareStockAPI.as_view(), name="spare-stock-update"),
    path("jobcard/<int:jobcard_id>/", views.JobCardSpareView.as_view(), name="jobcard-spare"),
    ]
