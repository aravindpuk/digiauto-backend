from decimal import Decimal, InvalidOperation

from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from labour.models import Labour, LabourPrice
from jobcard.models import JobCard, JobCardLabour, Complaint


# ─── Labour Search ────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_labour(request):
    """
    GET /labour/search/?q=<text>&garage_id=<int>&vehicle_model_id=<int>

    Returns matching labour items with suggested price from LabourPrice table.
    Priority:
      1. Price for this garage + this vehicle model
      2. Price for this garage + no vehicle model (default)
      3. No price (null) — user must enter

    Response:
    {
        "labour": [
            { "id": 1, "name": "Engine Flush", "suggested_price": "450.00" },
            ...
        ]
    }
    """
    q              = request.query_params.get("q", "").strip()
    garage_id      = request.query_params.get("garage_id")
    vehicle_model_id = request.query_params.get("vehicle_model_id")

    qs = Labour.objects.filter(name__icontains=q).order_by("name")[:30] if q \
        else Labour.objects.all().order_by("name")[:50]

    result = []
    for labour in qs:
        suggested_price = _get_suggested_price(labour, garage_id, vehicle_model_id)
        result.append({
            "id":              labour.id,
            "name":            labour.name,
            "suggested_price": str(suggested_price) if suggested_price else None,
        })

    return Response({"labour": result}, status=status.HTTP_200_OK)


def _get_suggested_price(labour, garage_id, vehicle_model_id):
    if not garage_id:
        return None
    # Try specific model price first
    if vehicle_model_id:
        price = LabourPrice.objects.filter(
            labour=labour,
            garage_id=garage_id,
            vehicle_model_id=vehicle_model_id,
        ).first()
        if price:
            return price.price

    # Fall back to garage default (no vehicle model)
    price = LabourPrice.objects.filter(
        labour=labour,
        garage_id=garage_id,
        vehicle_model__isnull=True,
    ).first()
    return price.price if price else None


# ─── JobCard Labour ───────────────────────────────────────────────────────────

class JobCardLabourView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, jobcard_id):
        """
        POST /labour/jobcard/<jobcard_id>/

        Case 1 — Existing labour:
          Body: { "labour_id": <int>, "amount": "450.00", "complaint_id": <int> }

        Case 2 — New labour (not in DB):
          Body: { "labour_name": "New Labour", "amount": "350.00", "complaint_id": <int> }

        In Case 2:
          - Creates a new Labour entry
          - Optionally saves a LabourPrice for this garage so it's suggested next time

        Always creates a JobCardLabour entry.
        """
        jobcard = (JobCard.objects
                   .select_related("branch__garage", "vehicle__vehicle_model")
                   .filter(id=jobcard_id).first())
        if not jobcard:
            return Response({"message": "Job card not found."},
                            status=status.HTTP_404_NOT_FOUND)

        labour_id    = request.data.get("labour_id")
        labour_name  = (request.data.get("labour_name") or "").strip()
        amount       = request.data.get("amount")
        complaint_id = request.data.get("complaint_id")

        if not amount:
            return Response({"message": "amount is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        try:
            amount_decimal = Decimal(str(amount)).quantize(Decimal("0.01"))
        except (InvalidOperation, ValueError, TypeError):
            return Response({"message": "amount must be a valid number."},
                            status=status.HTTP_400_BAD_REQUEST)
        if amount_decimal < 0:
            return Response({"message": "amount cannot be negative."},
                            status=status.HTTP_400_BAD_REQUEST)

        # ── Resolve labour ────────────────────────────────────────────────────
        is_new_labour = False

        if labour_id:
            labour = Labour.objects.filter(id=labour_id).first()
            if not labour:
                return Response({"message": "Labour not found."},
                                status=status.HTTP_404_NOT_FOUND)
        elif labour_name:
            labour, is_new_labour = Labour.objects.get_or_create(
                name__iexact=labour_name,
                defaults={"name": labour_name},
            )
        else:
            return Response(
                {"message": "Either labour_id or labour_name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # ── Save latest garage/model price for future suggestions ────────────
        if jobcard.branch and jobcard.branch.garage:
            price = LabourPrice.objects.filter(
                labour=labour,
                garage=jobcard.branch.garage,
                vehicle_model=jobcard.vehicle.vehicle_model
                    if jobcard.vehicle else None,
            ).first()
            if price:
                price.price = amount_decimal
                price.save(update_fields=["price"])
            else:
                LabourPrice.objects.create(
                    labour=labour,
                    garage=jobcard.branch.garage,
                    vehicle_model=jobcard.vehicle.vehicle_model
                        if jobcard.vehicle else None,
                    price=amount_decimal,
                )

        # ── Resolve complaint ─────────────────────────────────────────────────
        complaint = None
        if complaint_id:
            complaint = Complaint.objects.filter(id=complaint_id).first()

        # ── Create JobCardLabour ──────────────────────────────────────────────
        jcl = JobCardLabour.objects.create(
            jobcard    = jobcard,
            labour     = labour,
            technician = request.user,
            amount     = amount_decimal,
        )
        if complaint:
            jcl.complaints.add(complaint)

        return Response(
            {
                "message": "Labour added successfully.",
                "labour_service": {
                    "id":          jcl.id,
                    "labour_id":   labour.id,
                    "labour_name": labour.name,
                    "amount":      str(jcl.amount),
                    "technician":  request.user.name,
                    "services":    (
                        [{"id": complaint.id, "text": complaint.text}]
                        if complaint else []
                    ),
                    "is_new":      is_new_labour,
                },
                "total": str(_jobcard_total(jobcard)),
            },
            status=status.HTTP_201_CREATED,
        )

    def delete(self, request, jobcard_id):
        """
        DELETE /labour/jobcard/<jobcard_id>/
        Body: { "labour_service_id": <int> }
        """
        labour_service_id = request.data.get("labour_service_id")
        jcl = JobCardLabour.objects.filter(
            id=labour_service_id, jobcard_id=jobcard_id
        ).first()
        if not jcl:
            return Response({"message": "Labour service not found."},
                            status=status.HTTP_404_NOT_FOUND)
        jcl.delete()
        jobcard = JobCard.objects.filter(id=jobcard_id).first()
        return Response({"message": "Labour removed successfully.",
                         "total": str(_jobcard_total(jobcard)) if jobcard else "0.00"},
                        status=status.HTTP_200_OK)


def _jobcard_total(jobcard):
    if not jobcard:
        return Decimal("0.00")
    spare_total = sum(
        (spare.mrp or Decimal("0.00")) * spare.quantity
        for spare in jobcard.spares.all()
    )
    labour_total = sum(
        labour.amount or Decimal("0.00")
        for labour in jobcard.labour_services.all()
    )
    return spare_total + labour_total
