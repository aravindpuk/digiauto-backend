import re
from decimal import Decimal

import jwt
import requests
from django.conf import settings
from django.core import signing
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.db import transaction
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.urls import reverse
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
from .utils.whatsapp import send_invoice_whatsapp, send_quotation_whatsapp

# Status progression order
STATUS_ORDER = ["pending", "active", "completed", "delivered"]

# Salt used to sign the public, customer-facing quotation link.
QUOTATION_SHARE_SALT = "jobcard-quotation-view"
INVOICE_SHARE_SALT = "jobcard-invoice-pdf"
INVOICE_LINK_MAX_AGE = 60 * 60 * 24 # 24 hours — plenty of time for MSG91 to fetch it


@api_view(["GET"])
@permission_classes([])
def customer_latest_jobcard(request):
    vehicle_number = re.sub(
        r"[^A-Z0-9]", "", request.query_params.get("vehicle_number", "").upper()
    )
    if len(vehicle_number) < 5:
        return Response(
            {"message": "A valid vehicle number is required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    vehicle_pattern = r"[^A-Z0-9]*".join(re.escape(char) for char in vehicle_number)
    jobcard = (
        JobCard.objects
        .select_related(
            "branch__garage",
            "vehicle__vehicle_model__fkMaker",
            "status",
            "created_by",
        )
        .prefetch_related("complaints")
        .filter(vehicle__vehicle_number__iregex=f"^{vehicle_pattern}$")
        .order_by("-created_at")
        .first()
    )
    if not jobcard:
        return Response(
            {"message": "No job card found for this vehicle number."},
            status=status.HTTP_404_NOT_FOUND,
        )

    serialized = JobCardListSerializer(jobcard).data
    customer_fields = (
        "id",
        "vehicle_number",
        "vehicle_model",
        "vehicle_make",
        "customer_name",
        "place",
        "kilometer",
        "status",
        "created_at",
        "services",
    )
    customer_data = {key: serialized[key] for key in customer_fields}
    return Response({"jobcard": customer_data}, status=status.HTTP_200_OK)


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


class JobCardViewDocument(APIView):
    """
    GET /jobcard/jobcards/<id>/view/?token=<jwt>

    Renders the quotation/invoice as a normal HTML page so garage staff
    can view it straight in the browser (opened from the Flutter app's
    "View Quotation/Invoice" button). Includes a "Share to WhatsApp"
    button that is not part of the bill and never appears in the PDF.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request, jobcard_id):
        token = _extract_request_token(request)
        token_user = _authenticate_document_request(request)
        if not token_user:
            return HttpResponse(_simple_message_page("Authentication required."),
                                status=401)

        jobcard = _document_jobcard_queryset().filter(id=jobcard_id).first()
        if not jobcard:
            return HttpResponse(_simple_message_page("Job card not found."), status=404)

        if not _user_can_access_jobcard(token_user, jobcard):
            return HttpResponse(
                _simple_message_page("You do not have access to this job card."),
                status=403)

        document_type = _resolve_document_type(jobcard)
        if document_type == "closed":
            return HttpResponse(
                _simple_message_page(
                    "This job has already been delivered. Invoice and "
                    "quotation are no longer available."),
                status=400)

        has_billable_items = jobcard.labour_services.exists() or jobcard.spares.exists()
        if document_type == "quotation" and not has_billable_items:
            return HttpResponse(
                _simple_message_page(
                    "Add at least one labour or spare item to generate a quotation."),
                status=400)

        context = _document_context(jobcard, document_type)
        context["show_whatsapp_button"] = True
        share_url = request.build_absolute_uri(
            reverse("jobcard-share-whatsapp", args=[jobcard.id]))
        if token:
            share_url += f"?token={token}"
        context["share_endpoint"] = share_url

        html = render_to_string("jobcard/invoice_quotation_pdf.html", context)
        return HttpResponse(html)


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

        pdf_content = _render_document_pdf(html, request)
        if pdf_content is None:
            return Response(
                {"message": "PDF renderer is not installed. Run pip install -r requirements.txt."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        response = HttpResponse(content_type="application/pdf")
        filename = _document_filename(context)
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        response.write(pdf_content)
        return response


class PublicQuotationView(APIView):
    """
    GET /jobcard/view/q/<token>/

    Public, unauthenticated page used for the link shared with the
    customer over WhatsApp. The link is unique per job card and stops
    resolving the moment the job moves past the quotation stage
    (i.e. once it becomes an invoice or is delivered).
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request, token):
        try:
            jobcard_id = int(signing.Signer(salt=QUOTATION_SHARE_SALT).unsign(token))
        except Exception:
            return HttpResponse(_simple_message_page("This link is invalid."), status=404)

        jobcard = _document_jobcard_queryset().filter(id=jobcard_id).first()
        if not jobcard:
            return HttpResponse(_simple_message_page("Quotation not found."), status=404)

        document_type = _resolve_document_type(jobcard)
        if document_type != "quotation":
            return HttpResponse(
                _simple_message_page(
                    "This quotation link is no longer available. Please "
                    "contact the garage for your invoice."),
                status=410)

        context = _document_context(jobcard, document_type)
        html = render_to_string("jobcard/invoice_quotation_pdf.html", context)
        return HttpResponse(html)


class ShareWhatsAppView(APIView):
    """
    POST /jobcard/jobcards/<id>/share-whatsapp/?token=<jwt>

    Triggered from the "Share to WhatsApp" button on the view page.
    Sends the quotation link or the invoice PDF to the customer's
    WhatsApp number via MSG91.
    """
    authentication_classes = []
    permission_classes = []

    def post(self, request, jobcard_id):
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

        vehicle = jobcard.vehicle
        customer = vehicle.user if vehicle else None
        if not customer or not customer.mobile:
            return Response({"message": "Customer mobile number not found."},
                            status=status.HTTP_400_BAD_REQUEST)

        garage = jobcard.branch.garage
        document_type = _resolve_document_type(jobcard)

        try:
            if document_type == "quotation":
                if not (jobcard.labour_services.exists() or jobcard.spares.exists()):
                    return Response(
                        {"message": "Add at least one labour or spare item first."},
                        status=status.HTTP_400_BAD_REQUEST)

                token = signing.Signer(salt=QUOTATION_SHARE_SALT).sign(str(jobcard.id))
                quotation_url = request.build_absolute_uri(
                    reverse("jobcard-public-quotation", args=[token]))

                whatsapp_response = send_quotation_whatsapp(
                    mobile=customer.mobile,
                    customer_name=customer.name,
                    quotation_url=quotation_url,
                    garage_name=garage.name,
                )

            elif document_type == "invoice":
                context = _document_context(jobcard, document_type)
                
                filename = _document_filename(context)

                token = signing.TimestampSigner(salt=INVOICE_SHARE_SALT).sign(
                    str(jobcard.id))
                pdf_url = request.build_absolute_uri(
                    reverse("jobcard-invoice-pdf", args=[token]))
              

                whatsapp_response = send_invoice_whatsapp(
                    mobile=customer.mobile,
                    customer_name=customer.name,
                    garage_name=garage.name,
                    pdf_url=pdf_url,
                    filename=filename,
                )

            else:
                return Response({"message": "Document not available for sharing."},
                                status=status.HTTP_400_BAD_REQUEST)
        except requests.RequestException as exc:
            return Response({"message": f"Could not reach WhatsApp service: {exc}"},
                            status=status.HTTP_502_BAD_GATEWAY)

        if whatsapp_response.status_code >= 300:
            return Response(
                {"message": f"WhatsApp API error ({whatsapp_response.status_code}): {whatsapp_response.text}"},
                status=status.HTTP_502_BAD_GATEWAY)

        return Response({"message": "Shared to customer's WhatsApp successfully."},
                        status=status.HTTP_200_OK)


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


def _extract_request_token(request):
    auth_header = request.headers.get("Authorization", "")
    token = request.query_params.get("token")
    if auth_header.startswith("Bearer "):
        token = auth_header.split(" ", 1)[1]
    return token


def _authenticate_document_request(request):
    token = _extract_request_token(request)
    if not token:
        return None
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return User.objects.filter(id=payload["user_id"]).first()
    except (KeyError, jwt.ExpiredSignatureError, jwt.DecodeError):
        return None


def _simple_message_page(message):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>DigiAuto</title>
<style>
body {{
    margin: 0;
    font-family: Arial, Helvetica, sans-serif;
    background-color: #f4f7f9;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100vh;
}}
.message-box {{
    background-color: #ffffff;
    padding: 32px 28px;
    border-radius: 12px;
    max-width: 420px;
    text-align: center;
    color: #333333;
    box-shadow: 0 4px 14px rgba(0, 0, 0, 0.08);
}}
</style>
</head>
<body>
<div class="message-box"><p>{message}</p></div>
</body>
</html>"""


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
    now = timezone.localtime(timezone.now())
    today = now.date()
    document_number = _make_document_number(
        "INV" if document_type == "invoice" else "QT",
        today,
        jobcard.id,
    )

    invoice = None
    if document_type == "invoice":
        invoice, _ = Invoice.objects.get_or_create(
            jobcard=jobcard,
            defaults={
                "invoice_number": document_number,
                "total_amount": grand_total,
            },
        )
        if invoice.invoice_number != document_number:
            invoice.invoice_number = document_number
        if invoice.total_amount != grand_total:
            invoice.total_amount = grand_total
        invoice.save(update_fields=["invoice_number", "total_amount"])

    vehicle = jobcard.vehicle
    customer = vehicle.user if vehicle else None
    vehicle_model = vehicle.vehicle_model if vehicle else None
    garage = jobcard.branch.garage
    return {
        "document_title": "Invoice" if document_type == "invoice" else "Quotation",
        "document_number": invoice.invoice_number if invoice else document_number,
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


def _render_document_pdf(html, request):
    try:
        from weasyprint import HTML
    except ImportError:
        return None
    else:
        return HTML(
            string=html,
            base_url=request.build_absolute_uri("/"),
        ).write_pdf()


def _make_document_number(prefix, date_value, jobcard_id):
    return f"{prefix}-{date_value:%d%m%Y}{jobcard_id}"


def _document_filename(context):
    customer = context["customer"]
    customer_name = getattr(customer, "name", "") if customer else ""
    clean_name = re.sub(r"[^A-Za-z0-9]+", "_", customer_name).strip("_")
    if not clean_name:
        clean_name = "customer"
    return f"{clean_name}_{context['document_number']}.pdf"


class InvoicePdfView(APIView):
    """
    GET /jobcard/invoice-pdf/<token>/

    Generates the invoice PDF on the fly and streams it directly in the
    response — nothing is ever written to disk. The signed token expires
    after INVOICE_LINK_MAX_AGE seconds, which is enough time for MSG91 to
    fetch and deliver the document over WhatsApp.
    """
    authentication_classes = []
    permission_classes = []

    def get(self, request, token):
        try:
            jobcard_id = int(
                signing.TimestampSigner(salt=INVOICE_SHARE_SALT)
                .unsign(token, max_age=INVOICE_LINK_MAX_AGE)
            )
        except signing.SignatureExpired:
            return HttpResponse(_simple_message_page("This link has expired."), status=410)
        except Exception:
            return HttpResponse(_simple_message_page("This link is invalid."), status=404)

        jobcard = _document_jobcard_queryset().filter(id=jobcard_id).first()
        if not jobcard:
            return HttpResponse(_simple_message_page("Invoice not found."), status=404)

        if _resolve_document_type(jobcard) != "invoice":
            return HttpResponse(
                _simple_message_page("Invoice is not available for this job."),
                status=400)

        context = _document_context(jobcard, "invoice")
        html = render_to_string("jobcard/invoice_quotation_pdf.html", context)
        pdf_bytes = _render_document_pdf(html, request)
        if pdf_bytes is None:
            return HttpResponse(
                _simple_message_page("PDF renderer is not installed."),
                status=500)

        filename = _document_filename(context)
        response = HttpResponse(pdf_bytes, content_type="application/pdf")
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response