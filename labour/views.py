from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from labour.models import Labour, LabourPrice
from jobcard.models import JobCard, JobCardLabour, Complaint


# ─── Labour Master ────────────────────────────────────────────────────────────

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_labour(request):
    """
    GET /labour/search/?q=<text>
    Returns labour items whose name contains q (case-insensitive).
    If q is empty, returns all.
    """
    q = request.query_params.get("q", "").strip()
    qs = Labour.objects.filter(name__icontains=q).order_by("name")[:30] if q \
        else Labour.objects.all().order_by("name")[:50]
    data = [{"id": lb.id, "name": lb.name} for lb in qs]
    return Response({"labour": data}, status=status.HTTP_200_OK)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_labour(request):
    """
    POST /labour/create/
    Body: { "name": "Engine Flush" }
    Creates a new Labour master record if name doesn't exist.
    """
    name = request.data.get("name", "").strip()
    if not name:
        return Response({"message": "Labour name is required."},
                        status=status.HTTP_400_BAD_REQUEST)

    labour, created = Labour.objects.get_or_create(
        name__iexact=name,
        defaults={"name": name},
    )
    return Response(
        {"id": labour.id, "name": labour.name,
         "created": created},
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


# ─── JobCard Labour ───────────────────────────────────────────────────────────

class JobCardLabourView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, jobcard_id):
        """
        POST /labour/jobcard/<jobcard_id>/
        Body: {
            "labour_id": <int>,          // required — existing Labour
            "labour_name": "string",     // used if labour_id is absent → auto create
            "amount": "decimal",         // required
            "complaint_ids": [<int>]     // optional — link to complaints
        }
        """
        jobcard = JobCard.objects.filter(id=jobcard_id).first()
        if not jobcard:
            return Response({"message": "Job card not found."},
                            status=status.HTTP_404_NOT_FOUND)

        labour_id   = request.data.get("labour_id")
        labour_name = request.data.get("labour_name", "").strip()
        amount      = request.data.get("amount")

        if not amount:
            return Response({"message": "amount is required."},
                            status=status.HTTP_400_BAD_REQUEST)

        if labour_id:
            labour = Labour.objects.filter(id=labour_id).first()
            if not labour:
                return Response({"message": "Labour not found."},
                                status=status.HTTP_404_NOT_FOUND)
        elif labour_name:
            labour, _ = Labour.objects.get_or_create(
                name__iexact=labour_name,
                defaults={"name": labour_name},
            )
        else:
            return Response(
                {"message": "Either labour_id or labour_name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        jcl = JobCardLabour.objects.create(
            jobcard    = jobcard,
            labour     = labour,
            technician = request.user,
            amount     = amount,
        )

        complaint_ids = request.data.get("complaint_ids", [])
        if complaint_ids:
            complaints = Complaint.objects.filter(id__in=complaint_ids)
            jcl.complaints.set(complaints)

        return Response(
            {
                "message": "Labour added successfully.",
                "labour_service": {
                    "id":          jcl.id,
                    "labour_id":   labour.id,
                    "labour_name": labour.name,
                    "amount":      str(jcl.amount),
                    "technician":  request.user.name,
                },
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
        return Response({"message": "Labour removed."}, status=status.HTTP_200_OK)