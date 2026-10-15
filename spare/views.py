from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.db.models import Q
from rest_framework import serializers, views, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import (
    Spare,
    SpareStock,
    SparePurchaseData,
    UsedSpareRequest,
    UsedSpareRequestImage,
    SpareShop,
    SpareShopInventory,
    SpareShopInventoryImage,
    SpareShopOrder,
)
from jobcard.models import Complaint, JobCard, JobCardSpare


class RegisterSpareShop(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        role = getattr(request.user, "role", None)
        if not role or role.name != "scrap-team":
            return Response(
                {"message": "Spare shop account required."},
                status=status.HTTP_403_FORBIDDEN,
            )
        name = str(request.data.get("name", "")).strip()
        location = str(request.data.get("location", "")).strip()
        try:
            latitude = float(request.data.get("latitude"))
            longitude = float(request.data.get("longitude"))
        except (TypeError, ValueError):
            return Response(
                {"message": "Choose a valid shop location."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if not name or not location:
            return Response(
                {"message": "Shop name and location are required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if SpareShop.objects.filter(owner=request.user).exists():
            return Response(
                {"message": "A spare shop is already registered for this account."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        shop = SpareShop.objects.create(
            owner=request.user,
            name=name,
            location=location,
            latitude=latitude,
            longitude=longitude,
        )
        return Response(
            {"message": "Spare shop registered successfully.", "shop_id": shop.id},
            status=status.HTTP_201_CREATED,
        )


class UsedSpareRequestsAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def _allowed_requester(self, request):
        role = getattr(request.user, "role", None)
        return bool(role and role.name in {"customer", "garage-admin"})

    def get(self, request):
        if not self._allowed_requester(request):
            return Response({"message": "Customer or garage account required."},
                            status=status.HTTP_403_FORBIDDEN)
        requests = UsedSpareRequest.objects.filter(customer=request.user).prefetch_related(
            "photos", "shop_orders__shop"
        )
        return Response({"orders": [self._data(item, request) for item in requests]},
                        status=status.HTTP_200_OK)

    def post(self, request):
        if not self._allowed_requester(request):
            return Response({"message": "Customer or garage account required."},
                            status=status.HTTP_403_FORBIDDEN)

        make = (request.data.get("vehicle_make") or "").strip()
        model = (request.data.get("vehicle_model") or "").strip()
        year = (request.data.get("vehicle_year") or "").strip()
        spare_name = (request.data.get("spare_name") or "").strip()
        images = request.FILES.getlist("images") or request.FILES.getlist("image")
        if len(images) > 6:
            return Response({"message": "Upload up to 6 photos per request."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not make or not model:
            return Response({"message": "Select the vehicle make and model."},
                            status=status.HTTP_400_BAD_REQUEST)
        if year and (len(year) != 4 or not year.isdigit()):
            return Response({"message": "Enter a valid 4-digit year or leave it empty."},
                            status=status.HTTP_400_BAD_REQUEST)
        if not spare_name and not images:
            return Response({"message": "Add a spare name or at least one photo."},
                            status=status.HTTP_400_BAD_REQUEST)
        for image in images:
            if image.size > 5 * 1024 * 1024:
                return Response({"message": "Each photo must be 5 MB or smaller."},
                                status=status.HTTP_400_BAD_REQUEST)
            try:
                serializers.ImageField().run_validation(image)
            except serializers.ValidationError:
                return Response({"message": "Upload valid image files."},
                                status=status.HTTP_400_BAD_REQUEST)

        item = UsedSpareRequest.objects.create(
            customer=request.user,
            vehicle_make=make,
            vehicle_model=model,
            vehicle_year=year,
            spare_name=spare_name,
        )
        for image in images:
            UsedSpareRequestImage.objects.create(request=item, image=image)
        _notify_digiauto_team(item)
        return Response({"message": "Your used spare request was submitted.",
                          "order": self._data(item, request)},
                         status=status.HTTP_201_CREATED)

    def patch(self, request, request_id):
        if not self._allowed_requester(request):
            return Response({"message": "Customer or garage account required."}, status=403)
        item = get_object_or_404(UsedSpareRequest, pk=request_id, customer=request.user)
        if item.status != UsedSpareRequest.STATUS_SUBMITTED:
            return Response({"message": "Only new requests can be edited."}, status=400)
        for field in ("vehicle_make", "vehicle_model", "vehicle_year", "spare_name"):
            if field in request.data:
                setattr(item, field, str(request.data[field]).strip())
        if not item.vehicle_make or not item.vehicle_model:
            return Response({"message": "Select the vehicle make and model."}, status=400)
        if item.vehicle_year and (len(item.vehicle_year) != 4 or not item.vehicle_year.isdigit()):
            return Response({"message": "Enter a valid 4-digit year or leave it empty."}, status=400)
        item.save()
        return Response({"message": "Request updated.", "order": self._data(item, request)})

    def delete(self, request, request_id):
        if not self._allowed_requester(request):
            return Response({"message": "Customer or garage account required."}, status=403)
        item = get_object_or_404(UsedSpareRequest, pk=request_id, customer=request.user)
        if item.status != UsedSpareRequest.STATUS_SUBMITTED:
            return Response({"message": "Only new requests can be cancelled."}, status=400)
        item.delete()
        return Response({"message": "Request cancelled."}, status=200)

    @staticmethod
    def _data(item, request):
        return {
            "id": item.id,
            "vehicle_make": item.vehicle_make,
            "vehicle_model": item.vehicle_model,
            "vehicle_year": item.vehicle_year,
            "spare_name": item.spare_name,
            "images": [request.build_absolute_uri(photo.image.url) for photo in item.photos.all()],
            "image_url": request.build_absolute_uri(item.image.url) if item.image else "",
            "has_image": bool(item.image or item.photos.exists()),
            "status": item.status,
            "created_at": item.created_at.isoformat(),
            "assignments": [{
                "shop_name": order.shop.name,
                "status": order.status,
                "status_label": order.get_status_display(),
                "shop_note": order.shop_note,
                "updated_at": order.updated_at.isoformat(),
            } for order in item.shop_orders.all()],
        }


def _notify_digiauto_team(item):
    """Send a topic notification when Firebase Admin credentials are configured."""
    from .notifications import send_topic_notification
    send_topic_notification(
        topic="digi-staff-spare-orders",
        title="New used spare request",
        body=f"{item.vehicle_make} {item.vehicle_model}: {item.spare_name or 'Photo attached'}",
        data={"request_id": item.id, "type": "used_spare_order"},
    )

# ------------------------- SERIALIZERS ----------------------------
class SpareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Spare
        fields = ['id', 'partnumber', 'partname']

class SpareStockSerializer(serializers.ModelSerializer):
    spare = SpareSerializer(read_only=True)
    spare_id = serializers.IntegerField(write_only=True)
    branch_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = SpareStock
        fields = ['id', 'spare', 'spare_id', 'branch_id', 'mrp', 'quantity', 'purchase_amount']

    def create(self, validated_data):
        spare_id = validated_data.pop('spare_id')
        branch_id = validated_data.pop('branch_id')
        return SpareStock.objects.create(
            spare_id=spare_id,
            branches_id=branch_id,
            **validated_data,
        )

class SparePurchaseSerializer(serializers.ModelSerializer):
    spare = SpareSerializer(read_only=True)
    spare_id = serializers.IntegerField(write_only=True)
    branch_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = SparePurchaseData
        fields = ['id', 'spare', 'spare_id', 'branch_id', 'mrp', 'quantity', 'purchase_amount', 'created_at']

    def create(self, validated_data):
        spare_id = validated_data.pop('spare_id')
        branch_id = validated_data.pop('branch_id')
        return SparePurchaseData.objects.create(
            spare_id=spare_id,
            branches_id=branch_id,
            **validated_data,
        )


def _jobcard_total(jobcard):
    if not jobcard:
        return Decimal("0.00")
    spare_total = sum(
        spare.amount or Decimal("0.00")
        for spare in jobcard.spares.all()
    )
    labour_total = sum(
        labour.amount or Decimal("0.00")
        for labour in jobcard.labour_services.all()
    )
    return spare_total + labour_total


def _parse_money(value, field_name):
    try:
        parsed = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise ValueError(f"{field_name} must be a valid number.")
    if parsed < 0:
        raise ValueError(f"{field_name} cannot be negative.")
    return parsed


def _parse_quantity(value):
    try:
        quantity = int(value)
    except (ValueError, TypeError):
        raise ValueError("quantity must be a valid number.")
    if quantity <= 0:
        raise ValueError("quantity must be greater than zero.")
    return quantity

# ------------------------- API VIEWS ------------------------------

# 1. Create Spare (Master)
class CreateSpareAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        partname = (request.data.get('partname') or request.data.get('name') or '').strip()
        partnumber = (request.data.get('partnumber') or '').strip()
        if not partname:
            return Response({'message': 'partname is required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        spare = Spare.objects.filter(partname__iexact=partname).first()
        created = False
        if spare:
            if partnumber and spare.partnumber != partnumber:
                spare.partnumber = partnumber
                spare.save(update_fields=['partnumber'])
        else:
            spare = Spare.objects.create(partname=partname, partnumber=partnumber)
            created = True

        return Response({
            'message': 'Spare created' if created else 'Spare already exists',
            'data': SpareSerializer(spare).data,
        }, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

# 2. List Spare (positive stock by default; edits can request zero quantity too)
class SpareListAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, branch_id):
        stocks = SpareStock.objects.filter(branches_id=branch_id).select_related('spare')
        if request.query_params.get('include_zero') not in ('1', 'true', 'True'):
            stocks = stocks.filter(quantity__gt=0)
        serializer = SpareStockSerializer(stocks, many=True)
        return Response(serializer.data)

# 3. Add new stock (with purchase history)
class AddSpareStockAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        # save purchase history
        p_ser = SparePurchaseSerializer(data=request.data)
        p_ser.is_valid(raise_exception=True)
        p_ser.save()

        # update existing stock OR create new
        spare_id = p_ser.validated_data['spare_id']
        branch_id = p_ser.validated_data['branch_id']
        quantity = p_ser.validated_data['quantity']
        mrp = p_ser.validated_data['mrp']
        purchase_amount = p_ser.validated_data['purchase_amount']

        stock, created = SpareStock.objects.get_or_create(
            spare_id=spare_id,
            branches_id=branch_id,
            defaults={'quantity': quantity, 'mrp': mrp, 'purchase_amount': purchase_amount}
        )

        if not created:
            # Add new quantity to existing stock
            stock.quantity += quantity
            stock.mrp = mrp  # update price to latest
            stock.purchase_amount = purchase_amount
            stock.save()

        return Response({'message': 'Stock updated', 'stock_id': stock.id})

# 4. Update Spare (normal update – name, partnumber)
class UpdateSpareAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def put(self, request, spare_id):
        spare = get_object_or_404(Spare, id=spare_id)
        partname = (request.data.get('partname') or request.data.get('name') or spare.partname).strip()
        partnumber = (request.data.get('partnumber') if 'partnumber' in request.data else spare.partnumber) or ''
        partnumber = partnumber.strip()

        if not partname:
            return Response({'message': 'partname is required.'},
                            status=status.HTTP_400_BAD_REQUEST)

        has_jobcard_usage = JobCardSpare.objects.filter(spare=spare).exists()
        details_changed = (
            spare.partname.strip() != partname
            or (spare.partnumber or '').strip() != partnumber
        )

        if has_jobcard_usage and details_changed:
            updated_spare = Spare.objects.create(partname=partname, partnumber=partnumber)
            SpareStock.objects.filter(spare=spare).update(spare=updated_spare)
            SparePurchaseData.objects.filter(spare=spare).update(spare=updated_spare)
        else:
            spare.partname = partname
            spare.partnumber = partnumber
            spare.save(update_fields=['partname', 'partnumber'])
            updated_spare = spare

        return Response({
            'message': 'Spare updated',
            'data': SpareSerializer(updated_spare).data,
        })

# 5. Update SpareStock (normal edit – price/quantity correction)
class UpdateSpareStockAPI(views.APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, stock_id):
        stock = get_object_or_404(SpareStock, id=stock_id)
        serializer = SpareStockSerializer(stock, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Stock updated', 'data': serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_spare(request):
    q = request.query_params.get("q", "").strip()
    qs = Spare.objects.all().order_by("partname")
    if q:
        qs = qs.filter(Q(partname__icontains=q) | Q(partnumber__icontains=q))
    data = [
        {
            "id": spare.id,
            "partname": spare.partname,
            "partnumber": spare.partnumber,
            "name": spare.partname,
        }
        for spare in qs[:30]
    ]
    return Response({"spares": data}, status=status.HTTP_200_OK)


class JobCardSpareView(views.APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request, jobcard_id):
        jobcard = JobCard.objects.filter(id=jobcard_id).first()
        if not jobcard:
            return Response({"message": "Job card not found."},
                            status=status.HTTP_404_NOT_FOUND)

        spare_id = request.data.get("spare_id")
        spare_name = (
            request.data.get("spare_name")
            or request.data.get("partname")
            or request.data.get("part_name")
            or ""
        ).strip()
        complaint_id = request.data.get("complaint_id")

        try:
            quantity = _parse_quantity(request.data.get("quantity"))
            price = _parse_money(request.data.get("mrp"), "price")
        except ValueError as exc:
            return Response({"message": str(exc)},
                            status=status.HTTP_400_BAD_REQUEST)

        price_mode = request.data.get("price_mode", JobCardSpare.PRICE_MODE_UNIT)
        if price_mode not in dict(JobCardSpare.PRICE_MODE_CHOICES):
            return Response({"message": "price_mode must be 'unit' or 'total'."},
                            status=status.HTTP_400_BAD_REQUEST)

        is_new = False
        if spare_id:
            spare = Spare.objects.filter(id=spare_id).first()
            if not spare:
                return Response({"message": "Spare not found."},
                                status=status.HTTP_404_NOT_FOUND)
        elif spare_name:
            spare = Spare.objects.filter(partname__iexact=spare_name).first()
            if not spare:
                spare = Spare.objects.create(partname=spare_name, partnumber="")
                is_new = True
        else:
            return Response(
                {"message": "Either spare_id or spare_name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        complaint = None
        if complaint_id:
            complaint = Complaint.objects.filter(id=complaint_id).first()

        # Preserve a unit rate for reports/invoices, but never use a rounded
        # derived rate to calculate a total-price line.
        total_amount = price * quantity if price_mode == JobCardSpare.PRICE_MODE_UNIT else price
        unit_mrp = price if price_mode == JobCardSpare.PRICE_MODE_UNIT else price / quantity
        job_spare = JobCardSpare.objects.create(
            jobcard=jobcard,
            spare=spare,
            quantity=quantity,
            mrp=unit_mrp,
            amount=total_amount,
            price_mode=price_mode,
        )
        if complaint:
            job_spare.complaints.add(complaint)

        return Response({
            "message": "Spare added successfully.",
            "jobcard_spare": {
                "id": job_spare.id,
                "spare_id": spare.id,
                "part_name": spare.partname,
                "partnumber": spare.partnumber,
                "quantity": job_spare.quantity,
                "mrp": str(job_spare.mrp),
                "amount": str(job_spare.amount),
                "price_mode": job_spare.price_mode,
                "services": (
                    [{"id": complaint.id, "text": complaint.text}]
                    if complaint else []
                ),
                "is_new": is_new,
            },
            "total": str(_jobcard_total(jobcard)),
        }, status=status.HTTP_201_CREATED)

    def delete(self, request, jobcard_id):
        jobcard_spare_id = request.data.get("jobcard_spare_id")
        job_spare = JobCardSpare.objects.filter(
            id=jobcard_spare_id,
            jobcard_id=jobcard_id,
        ).first()
        if not job_spare:
            return Response({"message": "Spare not found on this job card."},
                            status=status.HTTP_404_NOT_FOUND)
        job_spare.delete()
        jobcard = JobCard.objects.filter(id=jobcard_id).first()
        return Response({
            "message": "Spare removed successfully.",
            "total": str(_jobcard_total(jobcard)) if jobcard else "0.00",
        }, status=status.HTTP_200_OK)
