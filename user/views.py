from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.exceptions import ValidationError

from user.models import LoginInfo, User, UserRole
from user.serializer.user_serializer import UserSerializer


# ─── Register ────────────────────────────────────────────────────────────────

class RegisterUser(APIView):
    """
    POST /user/register/
    Body: { name, mobile, pin, role }
    role must be an existing UserRole name e.g. "admin" / "staff"
    """
    def post(self, request):
        try:
            serializer = UserSerializer(data=request.data)
            if serializer.is_valid(raise_exception=True):
                serializer.save()
                return Response(
                    {"message": "Registration successful. Please log in."},
                    status=status.HTTP_201_CREATED,
                )
        except ValidationError:
            errors = serializer.errors
            field, messages = next(iter(errors.items()))
            return Response(
                {"message": f"{field}: {messages[0]}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except Exception as e:
            return Response(
                {"message": str(e)},
                status=status.HTTP_400_BAD_REQUEST,
            )


# ─── Login ────────────────────────────────────────────────────────────────────

@api_view(["POST"])
def login(request):
    """
    POST /user/login/
    Body: { mobile, pin }

    Response:
    {
        "message": "Login successful",
        "token": "<jwt>",
        "garage_id": <int> | null,
        "branch_id": <int> | null
    }
    garage_id is null when the user has not registered a garage yet.
    The Flutter app uses this to decide whether to redirect to GarageScreen.
    """
    mobile = request.data.get("mobile", "").strip()
    pin    = request.data.get("pin", "").strip()

    if not mobile or not pin:
        return Response(
            {"message": "Mobile and PIN are required."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    try:
        user = User.objects.get(mobile=mobile)
    except User.DoesNotExist:
        return Response(
            {"message": "No account found with this mobile number."},
            status=status.HTTP_404_NOT_FOUND,
        )

    if not user.is_active:
        return Response(
            {"message": "Your account has been deactivated."},
            status=status.HTTP_403_FORBIDDEN,
        )

    if not user.check_pin(pin):
        return Response(
            {"message": "Invalid PIN. Please try again."},
            status=status.HTTP_401_UNAUTHORIZED,
        )

    # Create login record & generate token
    login_info = LoginInfo.objects.create(user=user)
    token = login_info.generate_auth_token()

    # Resolve garage and branch for this user
    branch  = user.branches.select_related("garage").first()
    garage_id = branch.garage.id if branch else None
    branch_id = branch.id       if branch else None

    return Response(
        {
            "message": "Login successful",
            "token":     token,
            "garage_id": garage_id,
            "branch_id": branch_id,
        },
        status=status.HTTP_200_OK,
    )


# ─── Logout ───────────────────────────────────────────────────────────────────

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    LoginInfo.objects.filter(user=request.user, login_status=True).update(
        login_status=False,
        logout_time=timezone.now(),
    )
    return Response(
        {"message": "Logged out successfully."},
        status=status.HTTP_200_OK,
    )