from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from rest_framework import serializers, status, views
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from vehicle.models import VehicleModel

from .models import (
    SpareShop,
    SpareShopInventory,
    SpareShopInventoryImage,
    SpareShopOrder,
    UsedSpareRequest,
)
from .notifications import send_topic_notification


def _is_role(user, role_name):
    role = getattr(user, "role", None)
    return bool(getattr(user, "is_active", False) and role and role.name == role_name)


def _owned_shop(user):
    if not _is_role(user, "scrap-team"):
        return None
    return SpareShop.objects.filter(owner=user).first()


def _inventory_data(item, request):
    return {
        "id": item.id,
        "vehicle_make": item.vehicle_model.fkMaker.name,
        "vehicle_model": item.vehicle_model.name,
        "vehicle_model_id": item.vehicle_model_id,
        "vehicle_year": item.vehicle_year,
        "spare_name": item.spare_name,
        "mrp": str(item.mrp),
        "images": [
            {"id": photo.id, "url": request.build_absolute_uri(photo.image.url)}
            for photo in item.photos.all()
        ],
        "created_at": item.created_at.isoformat(),
        "updated_at": item.updated_at.isoformat(),
    }


def _request_details(item, request):
    image_urls = [
        request.build_absolute_uri(photo.image.url) for photo in item.photos.all()
    ]
    if item.image:
        legacy_url = request.build_absolute_uri(item.image.url)
        if legacy_url not in image_urls:
            image_urls.insert(0, legacy_url)
    return {
        "request_id": item.id,
        "customer_name": item.customer.name,
        "customer_mobile": item.customer.mobile,
        "vehicle_make": item.vehicle_make,
        "vehicle_model": item.vehicle_model,
        "vehicle_year": item.vehicle_year,
        "spare_name": item.spare_name,
        "images": image_urls,
        "created_at": item.created_at.isoformat(),
    }


def _shop_order_data(order, request):
    return {
        "id": order.id,
        "status": order.status,
        "status_label": order.get_status_display(),
        "shop_note": order.shop_note,
        "updated_at": order.updated_at.isoformat(),
        **_request_details(order.request, request),
    }


def _notify_shop(order):
    item = order.request
    send_topic_notification(
        topic=f"digi-spare-shop-{order.shop_id}",
        title="New spare request for your shop",
        body=f"{item.vehicle_make} {item.vehicle_model}: {item.spare_name or 'Photo attached'}",
        data={"order_id": order.id, "request_id": item.id, "type": "shop_spare_order"},
    )


def _notify_staff(order):
    send_topic_notification(
        topic="digi-staff-spare-orders",
        title="Spare shop order update",
        body=f"{order.shop.name}: {order.get_status_display()} · request #{order.request_id}",
        data={"order_id": order.id, "request_id": order.request_id, "type": "shop_order_update"},
    )


def _validate_images(images):
    if len(images) > 6:
        return "Upload up to 6 photos."
    for image in images:
        if image.size > 5 * 1024 * 1024:
            return "Each photo must be 5 MB or smaller."
        try:
            serializers.ImageField().run_validation(image)
        except serializers.ValidationError:
            return "Upload valid image files."
    return None


def _remove_photo_files(photos):
    for photo in photos:
        if photo.image:
            photo.image.delete(save=False)


def _parse_mrp(value):
    try:
        amount = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not amount.is_finite():
        return None
    return amount if amount > 0 else None


class SpareShopInventoryAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shop = _owned_shop(request.user)
        if not shop:
            return Response({"message": "Registered spare shop account required."}, status=403)
        items = SpareShopInventory.objects.filter(shop=shop).select_related(
            "vehicle_model__fkMaker"
        ).prefetch_related("photos")
        query = request.query_params.get("q", "").strip()
        if query:
            items = items.filter(
                Q(spare_name__icontains=query)
                | Q(vehicle_model__name__icontains=query)
                | Q(vehicle_model__fkMaker__name__icontains=query)
            )
        return Response({"items": [_inventory_data(item, request) for item in items]})

    @transaction.atomic
    def post(self, request):
        shop = _owned_shop(request.user)
        if not shop:
            return Response({"message": "Registered spare shop account required."}, status=403)
        try:
            vehicle_model = VehicleModel.objects.select_related("fkMaker").get(
                pk=request.data.get("vehicle_model_id")
            )
        except (VehicleModel.DoesNotExist, TypeError, ValueError):
            return Response({"message": "Choose a valid vehicle make and model."}, status=400)
        spare_name = str(request.data.get("spare_name", "")).strip()
        year = str(request.data.get("vehicle_year", "")).strip()
        mrp = _parse_mrp(request.data.get("mrp"))
        images = request.FILES.getlist("images")
        image_error = _validate_images(images)
        if not spare_name:
            return Response({"message": "Spare name is required."}, status=400)
        if mrp is None:
            return Response({"message": "Enter an MRP greater than zero."}, status=400)
        if year and (len(year) != 4 or not year.isdigit()):
            return Response({"message": "Enter a valid 4-digit year or leave it empty."}, status=400)
        if image_error:
            return Response({"message": image_error}, status=400)
        if not images:
            return Response({"message": "Add at least one photo of the spare."}, status=400)

        item = SpareShopInventory.objects.create(
            shop=shop, vehicle_model=vehicle_model, vehicle_year=year,
            spare_name=spare_name, mrp=mrp,
        )
        for image in images:
            SpareShopInventoryImage.objects.create(inventory=item, image=image)
        item = SpareShopInventory.objects.select_related("vehicle_model__fkMaker").prefetch_related("photos").get(pk=item.pk)
        return Response({"message": "Spare added to your inventory.", "item": _inventory_data(item, request)}, status=201)


class SpareShopInventoryDetailAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def _get_item(self, request, item_id):
        shop = _owned_shop(request.user)
        if not shop:
            return None, Response({"message": "Registered spare shop account required."}, status=403)
        item = SpareShopInventory.objects.filter(pk=item_id, shop=shop).select_related(
            "vehicle_model__fkMaker"
        ).prefetch_related("photos").first()
        if not item:
            return None, Response({"message": "Spare not found."}, status=404)
        return item, None

    @transaction.atomic
    def put(self, request, item_id):
        item, error = self._get_item(request, item_id)
        if error:
            return error
        try:
            vehicle_model = VehicleModel.objects.select_related("fkMaker").get(
                pk=request.data.get("vehicle_model_id", item.vehicle_model_id)
            )
        except (VehicleModel.DoesNotExist, TypeError, ValueError):
            return Response({"message": "Choose a valid vehicle make and model."}, status=400)
        spare_name = str(request.data.get("spare_name", item.spare_name)).strip()
        year = str(request.data.get("vehicle_year", item.vehicle_year)).strip()
        mrp = _parse_mrp(request.data.get("mrp", item.mrp))
        images = request.FILES.getlist("images")
        image_error = _validate_images(images)
        remove_value = str(request.data.get("remove_image_ids", ""))
        remove_ids = [int(value) for value in remove_value.split(",") if value.strip().isdigit()]
        current_count = item.photos.count()
        removable_count = item.photos.filter(pk__in=remove_ids).count()
        if not spare_name:
            return Response({"message": "Spare name is required."}, status=400)
        if mrp is None:
            return Response({"message": "Enter an MRP greater than zero."}, status=400)
        if year and (len(year) != 4 or not year.isdigit()):
            return Response({"message": "Enter a valid 4-digit year or leave it empty."}, status=400)
        if image_error:
            return Response({"message": image_error}, status=400)
        if current_count - removable_count + len(images) > 6:
            return Response({"message": "An item can have up to 6 photos."}, status=400)
        if current_count - removable_count + len(images) < 1:
            return Response({"message": "Keep at least one spare photo."}, status=400)

        item.vehicle_model = vehicle_model
        item.vehicle_year = year
        item.spare_name = spare_name
        item.mrp = mrp
        item.save()
        removed_photos = list(item.photos.filter(pk__in=remove_ids))
        _remove_photo_files(removed_photos)
        item.photos.filter(pk__in=remove_ids).delete()
        for image in images:
            SpareShopInventoryImage.objects.create(inventory=item, image=image)
        item = SpareShopInventory.objects.select_related("vehicle_model__fkMaker").prefetch_related("photos").get(pk=item.pk)
        return Response({"message": "Spare updated.", "item": _inventory_data(item, request)})

    def delete(self, request, item_id):
        item, error = self._get_item(request, item_id)
        if error:
            return error
        _remove_photo_files(item.photos.all())
        item.delete()
        return Response({"message": "Spare removed from your inventory."})


class SpareShopOrdersAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        shop = _owned_shop(request.user)
        if not shop:
            return Response({"message": "Registered spare shop account required."}, status=403)
        orders = SpareShopOrder.objects.filter(shop=shop).select_related(
            "request__customer", "shop"
        ).prefetch_related("request__photos")
        return Response({"orders": [_shop_order_data(order, request) for order in orders]})

    @transaction.atomic
    def post(self, request, order_id):
        shop = _owned_shop(request.user)
        if not shop:
            return Response({"message": "Registered spare shop account required."}, status=403)
        order = SpareShopOrder.objects.select_for_update().filter(pk=order_id, shop=shop).select_related(
            "request__customer", "shop"
        ).prefetch_related("request__photos").first()
        if not order:
            return Response({"message": "Order not found."}, status=404)
        action = str(request.data.get("action", "")).strip().lower()
        if action in {"accept", "reject"}:
            if order.status != SpareShopOrder.STATUS_FORWARDED:
                return Response({"message": "This order has already been answered."}, status=400)
            order.status = SpareShopOrder.STATUS_ACCEPTED if action == "accept" else SpareShopOrder.STATUS_REJECTED
            order.shop_note = str(request.data.get("note", "")).strip()[:500]
        elif action == "delivered":
            if order.status != SpareShopOrder.STATUS_ACCEPTED:
                return Response({"message": "Accept the order before marking it delivered."}, status=400)
            order.status = SpareShopOrder.STATUS_DELIVERED
        else:
            return Response({"message": "Choose accept, reject, or delivered."}, status=400)

        order.save(update_fields=["status", "shop_note", "updated_at"])
        request_item = UsedSpareRequest.objects.select_for_update().get(pk=order.request_id)
        if order.status == SpareShopOrder.STATUS_ACCEPTED:
            request_item.status = UsedSpareRequest.STATUS_AVAILABLE
            request_item.save(update_fields=["status"])
        elif order.status == SpareShopOrder.STATUS_DELIVERED:
            request_item.status = UsedSpareRequest.STATUS_CLOSED
            request_item.save(update_fields=["status"])
        elif not request_item.shop_orders.filter(status=SpareShopOrder.STATUS_FORWARDED).exists():
            request_item.status = UsedSpareRequest.STATUS_SUBMITTED
            request_item.save(update_fields=["status"])
        _notify_staff(order)
        return Response({"message": f"Order {order.get_status_display().lower()}.", "order": _shop_order_data(order, request)})


class DigiStaffSpareOrdersAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if not _is_role(request.user, "digi-staff"):
            return Response({"message": "DigiAuto staff account required."}, status=403)
        requests = UsedSpareRequest.objects.select_related("customer").prefetch_related(
            "photos", "shop_orders__shop"
        )
        order_data = []
        for item in requests:
            assignments = [{
                "id": order.id,
                "shop_id": order.shop_id,
                "shop_name": order.shop.name,
                "status": order.status,
                "status_label": order.get_status_display(),
                "updated_at": order.updated_at.isoformat(),
            } for order in item.shop_orders.all()]
            order_data.append({
                **_request_details(item, request),
                "id": item.id,
                "customer_mobile": item.customer.mobile,
                "status": item.status,
                "assignments": assignments,
            })
        shops = SpareShop.objects.select_related("owner").order_by("name")
        shop_data = [{
            "id": shop.id,
            "name": shop.name,
            "mobile": shop.owner.mobile,
            "location": shop.location,
            "inventory_count": shop.inventory.count(),
        } for shop in shops]
        return Response({"orders": order_data, "shops": shop_data})

    def post(self, request, request_id):
        if not _is_role(request.user, "digi-staff"):
            return Response({"message": "DigiAuto staff account required."}, status=403)
        shop = get_object_or_404(SpareShop, pk=request.data.get("shop_id"))
        with transaction.atomic():
            item = get_object_or_404(UsedSpareRequest.objects.select_for_update(), pk=request_id)
            if item.status == UsedSpareRequest.STATUS_CLOSED:
                return Response({"message": "This request is already closed."}, status=400)
            if item.shop_orders.filter(status__in=[SpareShopOrder.STATUS_FORWARDED, SpareShopOrder.STATUS_ACCEPTED]).exists():
                return Response({"message": "This request is already with a shop."}, status=400)
            order = SpareShopOrder.objects.create(request=item, shop=shop, forwarded_by=request.user)
            item.status = UsedSpareRequest.STATUS_REVIEWING
            item.save(update_fields=["status"])
        _notify_shop(order)
        return Response({"message": f"Request forwarded to {shop.name}.", "order_id": order.id}, status=201)
