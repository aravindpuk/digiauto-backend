from django.db import models


class SpareShop(models.Model):
    owner = models.OneToOneField(
        "user.User", on_delete=models.CASCADE, related_name="spare_shop"
    )
    name = models.CharField(max_length=255)
    location = models.CharField(max_length=500)
    latitude = models.FloatField()
    longitude = models.FloatField()

    def __str__(self):
        return self.name


class SpareShopInventory(models.Model):
    shop = models.ForeignKey(
        SpareShop, on_delete=models.CASCADE, related_name="inventory"
    )
    vehicle_model = models.ForeignKey(
        "vehicle.VehicleModel", on_delete=models.PROTECT, related_name="shop_spares"
    )
    vehicle_year = models.CharField(max_length=4, blank=True, default="")
    spare_name = models.CharField(max_length=200)
    mrp = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.spare_name} - {self.vehicle_model}"


class SpareShopInventoryImage(models.Model):
    inventory = models.ForeignKey(
        SpareShopInventory, on_delete=models.CASCADE, related_name="photos"
    )
    image = models.ImageField(upload_to="spare_shop_inventory/")


class SpareShopOrder(models.Model):
    STATUS_FORWARDED = "forwarded"
    STATUS_ACCEPTED = "accepted"
    STATUS_REJECTED = "rejected"
    STATUS_DELIVERED = "delivered"
    STATUS_CHOICES = [
        (STATUS_FORWARDED, "Forwarded to shop"),
        (STATUS_ACCEPTED, "Accepted"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_DELIVERED, "Delivered"),
    ]

    request = models.ForeignKey(
        "UsedSpareRequest", on_delete=models.CASCADE, related_name="shop_orders"
    )
    shop = models.ForeignKey(
        SpareShop, on_delete=models.CASCADE, related_name="orders"
    )
    forwarded_by = models.ForeignKey(
        "user.User", on_delete=models.SET_NULL, null=True, related_name="forwarded_spare_orders"
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_FORWARDED
    )
    shop_note = models.CharField(max_length=500, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at", "-created_at"]

    def __str__(self):
        return f"Request #{self.request_id} → {self.shop.name} ({self.status})"


class UsedSpareRequest(models.Model):
    STATUS_SUBMITTED = "submitted"
    STATUS_REVIEWING = "reviewing"
    STATUS_AVAILABLE = "available"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_SUBMITTED, "Submitted"),
        (STATUS_REVIEWING, "Under review"),
        (STATUS_AVAILABLE, "Part found"),
        (STATUS_CLOSED, "Closed"),
    ]

    customer = models.ForeignKey("user.User", on_delete=models.CASCADE,
                                  related_name="used_spare_requests")
    vehicle_make = models.CharField(max_length=100)
    vehicle_model = models.CharField(max_length=100)
    vehicle_year = models.CharField(max_length=4, blank=True, default="")
    spare_name = models.CharField(max_length=200, blank=True, default="")
    image = models.ImageField(upload_to="used_spare_requests/", null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES,
                              default=STATUS_SUBMITTED)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"Used spare request #{self.pk} by {self.customer}"


class UsedSpareRequestImage(models.Model):
    request = models.ForeignKey(
        UsedSpareRequest, on_delete=models.CASCADE, related_name="photos"
    )
    image = models.ImageField(upload_to="used_spare_requests/")

# Create your models here.

class Spare(models.Model):
    partnumber = models.CharField(max_length=50, blank=True, default="")
    partname   = models.CharField(max_length=255)

    def __str__(self):
        return self.partname

class SparePurchaseData(models.Model):
    mrp             = models.DecimalField(max_digits=10, decimal_places=2)
    quantity        = models.IntegerField(default=1)
    purchase_amount = models.DecimalField(max_digits=10,decimal_places=2)
    
    spare           = models.ForeignKey(Spare, on_delete=models.CASCADE)
    branches        = models.ForeignKey('garage.Branch',on_delete=models.CASCADE)

    created_at      = models.DateTimeField(auto_now_add=True)


class SpareStock(models.Model):
    mrp             = models.DecimalField(max_digits=10, decimal_places=2)
    quantity        = models.IntegerField(default=1)
    purchase_amount = models.DecimalField(max_digits=10,decimal_places=2)
    
    spare           = models.ForeignKey(Spare, on_delete=models.CASCADE)
    branches        = models.ForeignKey('garage.Branch',on_delete=models.CASCADE)
