from decimal import Decimal

import jwt
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from garage.models import Branch
from user.models import User
from .models import (Complaint, Invoice, JobCard, JobCardLabour, JobCardSpare,
                     JobStatus, Vehicle, VehicleMake, VehicleModel)
from .serializer.jobcard_serializer import (JobCardDetailSerializer,
                                            JobCardListSerializer)

# Status progression order
STATUS_ORDER = ["pending", "active", "completed", "delivered"]


class JobCardView(APIView):
    permission_classes = [IsAuthenticated]

    # ── LIST ──────────────────────────────────────────────────────────────────
    def get(self, request):
        """
        GET /jobcard/jobcards/
        Query params: branch_id, garage_id, status, exclude_delivered
        """
        qs = (JobCard.objects
              .select_related("branch__garage",
                              "vehicle__vehicle_model__fkMaker",
                              "status", "created_by")
              .prefetch_related("complaints", "mechanic", "spares",
                                "labour_services")
              .order_by("-created_at"))

        branch_id = request.query_params.get("branch_id")
        garage_id = request.query_params.get("garage_id")
        status_filter = request.query_params.get("status")

        if branch_id:
            qs = qs.filter(branch_id=branch_id)
        elif garage_id:
            qs = qs.filter(branch__garage_id=garage_id)
        else:
            user_branches = request.user.branches.all()
            if user_branches.exists():
                qs = qs.filter(branch__in=user_branches)

        if status_filter:
            qs = qs.filter(status__name__iexact=status_filter)

        serializer = JobCardListSerializer(qs, many=True)
        return Response({"jobcards": serializer.data}, status=status.HTTP_200_OK)

    # ── CREATE ────────────────────────────────────────────────────────────────
    @transaction.atomic
    def post(self, request):
        data = request.data
        branch_id      = data.get("branch_id")
        vehicle_number = data.get("vehicle_number", "").strip()
        kilometer      = data.get("kilometer")
        customer_name  = data.get("customer_name", "").strip()
        mobile         = data.get("mobile", "").strip()
        services       = data.get("services", [])

        errors = {}
        if not branch_id:      errors["branch_id"]      = "Required."
        if not vehicle_number: errors["vehicle_number"]  = "Required."
        if kilometer in (None, ""): errors["kilometer"]  = "Required."
        if not customer_name:  errors["customer_name"]   = "Required."
        if not mobile:         errors["mobile"]          = "Required."
        if not services:       errors["services"]        = "At least one service required."
        if errors:
            return Response({"message": "Validation failed.", "errors": errors},
                            status=status.HTTP_400_BAD_REQUEST)

        branch = Branch.objects.filter(id=branch_id).select_related("garage").first()
        if not branch:
            return Response({"message": "Branch not found."},
                            status=status.HTTP_404_NOT_FOUND)

        customer_role = _get_or_create_role("customer")
        customer, _ = User.objects.get_or_create(
            mobile=mobile,
            defaults={"name": customer_name,
                      "address": data.get("place", ""),
                      "role": customer_role},
        )
        _update_customer(customer, customer_name, data.get("place", ""))

        vehicle_model = _resolve_vehicle_model(
            data.get("vehicle_model", ""), data.get("vehicle_make", ""))

        vehicle, _ = Vehicle.objects.get_or_create(
            vehicle_number=vehicle_number.upper(),
            user=customer,
            defaults={"vehicle_model": vehicle_model,
                      "year": data.get("year", ""),
                      "chassis_number": data.get("chassis_number", ""),
                      "engine_number": data.get("engine_number", "")},
        )
        _update_vehicle(vehicle, vehicle_model, data)

        job_status, _ = JobStatus.objects.get_or_create(
            name="pending", defaults={"order": 0})

        jobcard = JobCard.objects.create(
            branch=branch, created_by=request.user,
            vehicle=vehicle, kilometer=int(kilometer), status=job_status)

        _set_complaints(jobcard, services)

        serializer = JobCardDetailSerializer(jobcard)
        return Response({"message": "Job card created successfully.",
                         "jobcard": serializer.data},
                        status=status.HTTP_201_CREATED)


class JobCardDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_jobcard(self, jobcard_id):
        return (JobCard.objects
                .select_related("branch__garage",
                                "vehicle__vehicle_model__fkMaker",
                                "status", "created_by")
                .prefetch_related("complaints", "mechanic",
                                  "spares__spare", "spares__complaints",
                                  "labour_services__labour",
                                  "labour_services__complaints")
                .filter(id=jobcard_id).first())

    # ── DETAIL ────────────────────────────────────────────────────────────────
    def get(self, request, jobcard_id):
        jobcard = self._get_jobcard(jobcard_id)
        if not jobcard:
            return Response({"message": "Job card not found."},
                            status=status.HTTP_404_NOT_FOUND)
        return Response(JobCardDetailSerializer(jobcard).data)

    # ── UPDATE STATUS ─────────────────────────────────────────────────────────
    def patch(self, request, jobcard_id):
        """
        PATCH /jobcard/jobcards/<id>/
        Body: { "action": "update_status" }
        Advances status by one level in STATUS_ORDER.
        """
        jobcard = self._get_jobcard(jobcard_id)
        if not jobcard:
            return Response({"message": "Job card not found."},
                            status=status.HTTP_404_NOT_FOUND)

        action = request.data.get("action")

        if action == "update_status":
            current = jobcard.status.name.lower()
            try:
                idx = STATUS_ORDER.index(current)
            except ValueError:
                idx = 0
            if idx >= len(STATUS_ORDER) - 1:
                return Response(
                    {"message": "Job card is already at the final status (delivered)."},
                    status=status.HTTP_400_BAD_REQUEST)

            next_name = STATUS_ORDER[idx + 1]
            next_status, _ = JobStatus.objects.get_or_create(
                name=next_name, defaults={"order": idx + 1})
            jobcard.status = next_status
            jobcard.save(update_fields=["status"])
            return Response(
                {"message": f"Status updated to {next_name}.",
                 "new_status": next_name},
                status=status.HTTP_200_OK)

        # ── EDIT JOBCARD (full update) ─────────────────────────────────────
        if action == "edit":
            return self._edit(request, jobcard)

        return Response({"message": "Unknown action."},
                        status=status.HTTP_400_BAD_REQUEST)

    # ── DELETE ────────────────────────────────────────────────────────────────
    def delete(self, request, jobcard_id):
        jobcard = JobCard.objects.filter(id=jobcard_id).first()
        if not jobcard:
            return Response({"message": "Job card not found."},
                            status=status.HTTP_404_NOT_FOUND)
        jobcard.delete()
        return Response({"message": "Job card deleted successfully."},
                        status=status.HTTP_200_OK)

    @transaction.atomic
    def _edit(self, request, jobcard):
        data = request.data
        vehicle = jobcard.vehicle

        if "kilometer" in data:
            jobcard.kilometer = int(data["kilometer"])

        if "services" in data and data["services"]:
            _set_complaints(jobcard, data["services"])

        vehicle_model = _resolve_vehicle_model(
            data.get("vehicle_model", ""), data.get("vehicle_make", ""))
        _update_vehicle(vehicle, vehicle_model, data)
        _update_customer(vehicle.user,
                         data.get("customer_name", vehicle.user.name),
                         data.get("place", vehicle.user.address),
                         data.get("mobile", vehicle.user.mobile))
        jobcard.save()
        return Response(
            {"message": "Job card updated.",
             "jobcard": JobCardDetailSerializer(jobcard).data},
            status=status.HTTP_200_OK)


class JobCardDocumentView(APIView):
    authentication_classes = []
    permission_classes = []

    def get(self, request, jobcard_id):
        token_user = _authenticate_document_request(request)
        if not token_user:
            return Response({"message": "Authentication required."},
                            status=status.HTTP_401_UNAUTHORIZED)

        jobcard = _document_jobcard_queryset().filter(id=jobcard_id).first()
        if not jobcard:
            return Response({"message": "Job card not found."},
                            status=status.HTTP_404_NOT_FOUND)

        if not _user_can_access_jobcard(token_user, jobcard):
            return Response({"message": "You do not have access to this job card."},
                            status=status.HTTP_403_FORBIDDEN)

        document_type = _resolve_document_type(jobcard)
        if document_type == "closed":
            return Response(
                {"message": "Invoice or quotation is not available after delivery."},
                status=status.HTTP_400_BAD_REQUEST)

        has_billable_items = jobcard.labour_services.exists() or jobcard.spares.exists()
        if document_type == "quotation" and not has_billable_items:
            return Response(
                {"message": "Quotation is available only after adding at least one labour or spare item."},
                status=status.HTTP_400_BAD_REQUEST)
        if document_type == "invoice" and jobcard.status.name.lower() != "completed":
            return Response(
                {"message": "Invoice is available only after the job is completed."},
                status=status.HTTP_400_BAD_REQUEST)

        context = _document_context(jobcard, document_type)
        html = render_to_string("jobcard/invoice_quotation_pdf.html", context)

        try:
            from xhtml2pdf import pisa
        except ImportError:
            return Response(
                {"message": "PDF renderer is not installed. Run pip install -r requirements.txt."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response = HttpResponse(content_type="application/pdf")
        filename = f"{context['document_number']}.pdf"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        result = pisa.CreatePDF(html, dest=response, encoding="UTF-8")
        if result.err:
            return Response({"message": "Unable to generate PDF."},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return response


# ─── Manage Jobs list (for assistant) ─────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def manage_jobs_list(request):
    """
    GET /jobcard/manage/
    Returns id, job_id_display, vehicle_number, status for all non-delivered jobs.
    Used by the assistant's Manage Jobs panel.
    """
    branch_id = request.query_params.get("branch_id")
    garage_id = request.query_params.get("garage_id")

    qs = (JobCard.objects
          .select_related("vehicle", "status")
          .exclude(status__name__iexact="delivered")
          .order_by("-created_at"))

    if branch_id:
        qs = qs.filter(branch_id=branch_id)
    elif garage_id:
        qs = qs.filter(branch__garage_id=garage_id)
    else:
        user_branches = request.user.branches.all()
        if user_branches.exists():
            qs = qs.filter(branch__in=user_branches)

    data = [
        {
            "id":             jc.id,
            "job_id":         jc.job_id_display(),
            "vehicle_number": jc.vehicle.vehicle_number if jc.vehicle else "-",
            "status":         jc.status.name,
        }
        for jc in qs
    ]
    return Response({"jobs": data}, status=status.HTTP_200_OK)


# ─── helpers ──────────────────────────────────────────────────────────────────

def _get_or_create_role(name):
    from user.models import UserRole
    role, _ = UserRole.objects.get_or_create(name=name)
    return role


def _resolve_vehicle_model(model_name, make_name):
    if not model_name or not make_name:
        return None
    make, _ = VehicleMake.objects.get_or_create(
        name__iexact=make_name, defaults={"name": make_name})
    vm, _ = VehicleModel.objects.get_or_create(
        name__iexact=model_name, fkMaker=make,
        defaults={"name": model_name})
    return vm


def _update_vehicle(vehicle, vehicle_model, data):
    changed = False
    vehicle_number = data.get("vehicle_number", "").strip().upper()
    if vehicle_number and vehicle.vehicle_number != vehicle_number:
        vehicle.vehicle_number = vehicle_number
        changed = True
    if vehicle_model and vehicle.vehicle_model_id != vehicle_model.id:
        vehicle.vehicle_model = vehicle_model
        changed = True
    for field in ("year", "chassis_number", "engine_number"):
        val = data.get(field, "").strip()
        if val and getattr(vehicle, field) != val:
            setattr(vehicle, field, val)
            changed = True
    if changed:
        vehicle.save()


def _update_customer(customer, name, address, mobile=None):
    changed = False
    if name and customer.name != name:
        customer.name = name
        changed = True
    if address and customer.address != address:
        customer.address = address
        changed = True
    if mobile and customer.mobile != mobile:
        customer.mobile = mobile
        changed = True
    if changed:
        customer.save(update_fields=["name", "address", "mobile"])


def _set_complaints(jobcard, services):
    objs = []
    for svc in services:
        if isinstance(svc, str) and svc.strip():
            obj, _ = Complaint.objects.get_or_create(text=svc.strip())
            objs.append(obj)
    if objs:
        jobcard.complaints.set(objs)


def _authenticate_document_request(request):
    auth_header = request.headers.get("Authorization", "")
    token = request.query_params.get("token")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    if not token:
        return None

    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return User.objects.filter(id=payload["user_id"]).first()
    except (KeyError, jwt.ExpiredSignatureError, jwt.DecodeError):
        return None


def _document_jobcard_queryset():
    return (JobCard.objects
            .select_related("branch__garage",
                            "vehicle__vehicle_model__fkMaker",
                            "vehicle__user", "status", "created_by")
            .prefetch_related("spares__spare", "labour_services__labour",
                              "complaints"))


def _user_can_access_jobcard(user, jobcard):
    user_branches = user.branches.all()
    return not user_branches.exists() or user_branches.filter(id=jobcard.branch_id).exists()


def _resolve_document_type(jobcard):
    requested = ""
    status_name = jobcard.status.name.lower()
    if status_name == "delivered":
        requested = "closed"
    elif status_name == "completed":
        requested = "invoice"
    return requested or "quotation"


def _document_context(jobcard, document_type):
    labour_services = list(jobcard.labour_services.select_related("labour").all())
    jobcard_spares = list(jobcard.spares.select_related("spare").all())
    labour_total = sum((item.amount or Decimal("0.00")) for item in labour_services)
    spare_total = sum((item.mrp or Decimal("0.00")) * item.quantity
                      for item in jobcard_spares)
    grand_total = labour_total + spare_total
    today = timezone.localdate()

    invoice = None
    if document_type == "invoice":
        invoice_number = f"INV-{today.year}-{jobcard.id:05d}"
        invoice, _ = Invoice.objects.get_or_create(
            jobcard=jobcard,
            defaults={
                "invoice_number": invoice_number,
                "total_amount": grand_total,
            },
        )
        if invoice.total_amount != grand_total:
            invoice.total_amount = grand_total
            invoice.save(update_fields=["total_amount"])

    vehicle = jobcard.vehicle
    customer = vehicle.user if vehicle else None
    vehicle_model = vehicle.vehicle_model if vehicle else None
    garage = jobcard.branch.garage
    return {
        "document_title": "Invoice" if document_type == "invoice" else "Quotation",
        "document_number": invoice.invoice_number if invoice else f"QT-{today.year}-{jobcard.id:05d}",
        "document_date": invoice.date if invoice else today,
        "jobcard": jobcard,
        "garage": garage,
        "branch": jobcard.branch,
        "customer": customer,
        "vehicle": vehicle,
        "vehicle_model_name": vehicle_model.name if vehicle_model else "",
        "vehicle_make_name": vehicle_model.fkMaker.name if vehicle_model else "",
        "labour_items": labour_services,
        "spare_items": [
            {
                "partname": item.spare.partname,
                "quantity": item.quantity,
                "mrp": item.mrp or Decimal("0.00"),
                "amount": (item.mrp or Decimal("0.00")) * item.quantity,
            }
            for item in jobcard_spares
        ],
        "labour_total": labour_total,
        "spare_total": spare_total,
        "grand_total": grand_total,
    }
