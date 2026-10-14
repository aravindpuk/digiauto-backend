from django.test import TestCase

# Create your tests here.
from io import BytesIO
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from PIL import Image
from rest_framework.test import APIClient

from spare.models import SpareShop, UsedSpareRequest
from user.models import LoginInfo, User, UserRole
from vehicle.models import VehicleMake, VehicleModel


def _test_image(name="part.png"):
    image = Image.new("RGB", (2, 2), color="blue")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


class SpareShopWorkflowTests(TestCase):
    def _user(self, role_name, mobile):
        role, _ = UserRole.objects.get_or_create(name=role_name)
        user = User(name=role_name, mobile=mobile, role=role)
        user.set_pin("1234")
        user.save()
        login_info = LoginInfo.objects.create(user=user)
        return user, login_info.generate_auth_token()

    def test_inventory_crud_and_forward_accept_deliver_flow(self):
        owner, owner_token = self._user("scrap-team", "9000000010")
        staff, staff_token = self._user("digi-staff", "9000000011")
        customer, _ = self._user("customer", "9000000012")
        shop = SpareShop.objects.create(
            owner=owner,
            name="City Spares",
            location="Chennai",
            latitude=13.08,
            longitude=80.27,
        )
        make = VehicleMake.objects.create(name="Hyundai")
        model = VehicleModel.objects.create(name="Venue", fkMaker=make)

        shop_client = APIClient()
        shop_client.credentials(HTTP_AUTHORIZATION=f"Bearer {owner_token}")
        inventory_response = shop_client.post(
            "/spare/shops/inventory/",
            {
                "vehicle_model_id": model.id,
                "vehicle_year": "2021",
                "spare_name": "Gear box",
                "mrp": "18500.00",
                "images": _test_image(),
            },
            format="multipart",
        )
        self.assertEqual(inventory_response.status_code, 201, inventory_response.data)
        inventory_id = inventory_response.data["item"]["id"]
        self.assertEqual(inventory_response.data["item"]["vehicle_make"], "Hyundai")
        self.assertEqual(inventory_response.data["item"]["vehicle_model"], "Venue")

        search = shop_client.get("/spare/shops/inventory/?q=gear")
        self.assertEqual(search.status_code, 200)
        self.assertEqual(len(search.data["items"]), 1)
        self.assertEqual(search.data["items"][0]["spare_name"], "Gear box")

        update = shop_client.put(
            f"/spare/shops/inventory/{inventory_id}/",
            {
                "vehicle_model_id": model.id,
                "vehicle_year": "2022",
                "spare_name": "Automatic gear box",
                "mrp": "19200",
            },
            format="multipart",
        )
        self.assertEqual(update.status_code, 200, update.data)
        self.assertEqual(update.data["item"]["vehicle_year"], "2022")
        self.assertEqual(update.data["item"]["spare_name"], "Automatic gear box")

        request = UsedSpareRequest.objects.create(
            customer=customer,
            vehicle_make="Hyundai",
            vehicle_model="Venue",
            vehicle_year="2021",
            spare_name="Gear box",
        )
        staff_client = APIClient()
        staff_client.credentials(HTTP_AUTHORIZATION=f"Bearer {staff_token}")

        with patch("spare.shop_views._notify_shop"), patch("spare.shop_views._notify_staff"):
            forward = staff_client.post(
                f"/spare/digi-staff/orders/{request.id}/forward/",
                {"shop_id": shop.id},
                format="json",
            )
            self.assertEqual(forward.status_code, 201, forward.data)
            order_id = forward.data["order_id"]

            incoming = shop_client.get("/spare/shops/orders/")
            self.assertEqual(incoming.status_code, 200)
            self.assertEqual(incoming.data["orders"][0]["status"], "forwarded")

            accepted = shop_client.post(
                f"/spare/shops/orders/{order_id}/",
                {"action": "accept"},
                format="json",
            )
            self.assertEqual(accepted.status_code, 200, accepted.data)
            staff_view = staff_client.get("/spare/digi-staff/orders/")
            self.assertEqual(staff_view.data["orders"][0]["status"], "available")
            self.assertEqual(staff_view.data["orders"][0]["assignments"][0]["status"], "accepted")

            delivered = shop_client.post(
                f"/spare/shops/orders/{order_id}/",
                {"action": "delivered"},
                format="json",
            )
            self.assertEqual(delivered.status_code, 200, delivered.data)
            staff_view = staff_client.get("/spare/digi-staff/orders/")
            self.assertEqual(staff_view.data["orders"][0]["status"], "closed")
            self.assertEqual(staff_view.data["orders"][0]["assignments"][0]["status"], "delivered")

        removed = shop_client.delete(f"/spare/shops/inventory/{inventory_id}/")
        self.assertEqual(removed.status_code, 200)
        self.assertEqual(shop_client.get("/spare/shops/inventory/").data["items"], [])
