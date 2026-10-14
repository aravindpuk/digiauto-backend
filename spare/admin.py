from django.contrib import admin
from .models import (
    SpareShop,
    SpareShopInventory,
    SpareShopInventoryImage,
    SpareShopOrder,
    UsedSpareRequest,
    UsedSpareRequestImage,
)

admin.site.register(SpareShop)
admin.site.register(UsedSpareRequestImage)
admin.site.register(SpareShopInventory)
admin.site.register(SpareShopInventoryImage)


@admin.register(SpareShopOrder)
class SpareShopOrderAdmin(admin.ModelAdmin):
    list_display = ("id", "request", "shop", "status", "updated_at")
    list_filter = ("status", "created_at")
    search_fields = ("shop__name", "request__spare_name", "request__customer__mobile")


@admin.register(UsedSpareRequest)
class UsedSpareRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "customer", "spare_name", "vehicle_make", "vehicle_model", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("customer__name", "customer__mobile", "spare_name", "vehicle_make", "vehicle_model")
    list_editable = ("status",)

# Register your models here.
