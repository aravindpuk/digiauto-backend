from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from garage.models import Branch, Garage
from garage.serializer.garage_serializer import GarageSerializer, BranchSerializer


# ─── Register Garage ─────────────────────────────────────────────────────────

class RegisterGarage(APIView):
    """
    POST /garages/register/
    Headers: Authorization: Bearer <token>
    Body: { name, mobile, email?, latitude, longitude }

    Rules:
    - Garage name must be unique (case-insensitive).
    - A default "Main Branch" is created automatically.
    - The requesting user is assigned to that branch.
    - Returns garage_id and branch_id so Flutter can save them.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Unique name check (case-insensitive)
        name = request.data.get("name", "").strip()
        if not name:
            return Response(
                {"message": "Garage name is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if Garage.objects.filter(name__iexact=name).exists():
            return Response(
                {"message": f'A garage named "{name}" already exists. Please choose a different name.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        serializer = GarageSerializer(
            data=request.data,
            context={"user": request.user},
        )
        if serializer.is_valid():
            garage, branch = serializer.save()
            return Response(
                {
                    "message":   "Garage registered successfully.",
                    "garage_id": garage.id,
                    "branch_id": branch.id,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(
            {"message": str(serializer.errors)},
            status=status.HTTP_400_BAD_REQUEST,
        )


# ─── List Branches for a Garage ───────────────────────────────────────────────

class GarageBranches(APIView):
    """
    GET /garages/<garage_id>/branches/
    Returns all branches belonging to the garage.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, garage_id):
        branches = Branch.objects.filter(garage_id=garage_id)
        serializer = BranchSerializer(branches, many=True)
        return Response({"branches": serializer.data}, status=status.HTTP_200_OK)