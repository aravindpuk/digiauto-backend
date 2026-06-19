from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from garage.models import Branch, Garage
from garage.serializer.garage_serializer import GarageSerializer, BranchSerializer
from user.models import User


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


# ─── Current Garage Profile ──────────────────────────────────────────────────

class GarageProfile(APIView):
    """
    GET /garages/profile/
    PUT /garages/profile/

    Returns and updates the logged-in admin profile with the first garage
    assigned through the user's branch.
    """
    permission_classes = [IsAuthenticated]

    def _profile_data(self, user, branch):
        garage = branch.garage if branch else None
        return {
            "admin_name": user.name,
            "mobile": user.mobile,
            "garage_id": garage.id if garage else None,
            "garage_name": garage.name if garage else "",
            "garage_mobile": garage.mobile if garage else "",
            "email": garage.email if garage else "",
            "branch_id": branch.id if branch else None,
            "branch_name": branch.name if branch else "",
        }

    def get(self, request):
        branch = request.user.branches.select_related("garage").first()
        if not branch:
            return Response(
                {"message": "Garage profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(self._profile_data(request.user, branch), status=status.HTTP_200_OK)

    def put(self, request):
        user = request.user
        branch = user.branches.select_related("garage").first()
        if not branch:
            return Response(
                {"message": "Garage profile not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        garage = branch.garage
        admin_name = request.data.get("admin_name")
        mobile = request.data.get("mobile")
        pin = request.data.get("pin")
        garage_name = request.data.get("garage_name")
        garage_mobile = request.data.get("garage_mobile")
        email = request.data.get("email")

        if admin_name is not None:
            admin_name = admin_name.strip()
            if not admin_name:
                return Response(
                    {"message": "Admin name is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.name = admin_name

        if mobile is not None:
            mobile = mobile.strip()
            if not mobile:
                return Response(
                    {"message": "Mobile number is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            if User.objects.filter(mobile=mobile).exclude(id=user.id).exists():
                return Response(
                    {"message": "Mobile number is already registered."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.mobile = mobile

        if pin is not None and str(pin).strip():
            pin = str(pin).strip()
            if len(pin) != 4 or not pin.isdigit():
                return Response(
                    {"message": "PIN must be exactly 4 digits."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            user.set_pin(pin)

        if garage_name is not None:
            garage_name = garage_name.strip()
            if not garage_name:
                return Response(
                    {"message": "Garage name is required."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            duplicate = Garage.objects.filter(name__iexact=garage_name).exclude(id=garage.id)
            if duplicate.exists():
                return Response(
                    {"message": f'A garage named "{garage_name}" already exists.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            garage.name = garage_name

        if garage_mobile is not None:
            garage.mobile = garage_mobile.strip()

        if email is not None:
            garage.email = email.strip()

        user.save()
        garage.save()

        return Response(
            {
                "message": "Profile updated successfully.",
                "profile": self._profile_data(user, branch),
            },
            status=status.HTTP_200_OK,
        )
