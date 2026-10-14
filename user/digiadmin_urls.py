from django.urls import path

from user import digiadmin_views


urlpatterns = [
    path("login/", digiadmin_views.login_view, name="digiadmin-login"),
    path("", digiadmin_views.dashboard_view, name="digiadmin-dashboard"),
    path("logout/", digiadmin_views.logout_view, name="digiadmin-logout"),
]
