import re
from functools import wraps

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from garage.models import Garage
from user.models import User, UserRole


SESSION_KEY = "digiadmin_user_id"


def _current_admin(request):
    user_id = request.session.get(SESSION_KEY)
    if not user_id:
        return None
    return User.objects.filter(
        pk=user_id, is_active=True, role__name="digiadmin"
    ).first()


def admin_required(view):
    @wraps(view)
    def wrapped(request, *args, **kwargs):
        admin_user = _current_admin(request)
        if not admin_user:
            request.session.pop(SESSION_KEY, None)
            return redirect("digiadmin-login")
        request.digiadmin_user = admin_user
        return view(request, *args, **kwargs)

    return wrapped


@require_http_methods(["GET", "POST"])
def login_view(request):
    if _current_admin(request):
        return redirect("digiadmin-dashboard")

    error = ""
    if request.method == "POST":
        mobile = request.POST.get("mobile", "").strip()
        password = request.POST.get("password", "")
        admin_user = User.objects.filter(
            mobile=mobile, is_active=True, role__name="digiadmin"
        ).first()
        if admin_user and admin_user.check_password(password):
            request.session.cycle_key()
            request.session[SESSION_KEY] = admin_user.pk
            return redirect("digiadmin-dashboard")
        error = "Those credentials don’t match an active Digiadmin account."
    return render(request, "user/digiadmin/login.html", {"error": error})


@require_http_methods(["GET", "POST"])
@admin_required
def dashboard_view(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        mobile = request.POST.get("mobile", "").strip()
        pin = request.POST.get("pin", "").strip()
        if not name or not mobile:
            messages.error(request, "Enter the staff member’s name and mobile number.")
        elif not re.fullmatch(r"\d{10,15}", mobile):
            messages.error(request, "Enter a valid mobile number using 10 to 15 digits.")
        elif not re.fullmatch(r"\d{4}", pin):
            messages.error(request, "The staff PIN must contain exactly 4 digits.")
        elif User.objects.filter(mobile=mobile).exists():
            messages.error(request, "An account already uses that mobile number.")
        else:
            role, _ = UserRole.objects.get_or_create(name="digi-staff")
            staff = User(name=name, mobile=mobile, role=role)
            staff.set_pin(pin)
            staff.save()
            messages.success(request, f"{name} has been added to DigiAuto staff.")
            return redirect("digiadmin-dashboard")

    garages = Garage.objects.prefetch_related("branches").order_by("name")
    staff = User.objects.filter(role__name="digi-staff").order_by("name")
    context = {
        "admin_user": request.digiadmin_user,
        "garages": garages,
        "staff_members": staff,
        "garage_count": garages.count(),
        "branch_count": sum(garage.branches.count() for garage in garages),
        "staff_count": staff.count(),
    }
    return render(request, "user/digiadmin/dashboard.html", context)


@require_http_methods(["POST"])
def logout_view(request):
    request.session.pop(SESSION_KEY, None)
    return redirect("digiadmin-login")
