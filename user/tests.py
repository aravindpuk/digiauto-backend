from django.test import TestCase, Client
from django.urls import reverse

from user.models import User, UserRole


class DigiAdminDashboardTests(TestCase):
    def setUp(self):
        role, _ = UserRole.objects.get_or_create(name="digi-admin")
        self.admin = User(name="DigiAuto Admin", mobile="9000000001", role=role)
        self.admin.set_password("DigiAdmin!2026")
        self.admin.save()
        self.client = Client()

    def test_login_dashboard_and_create_digi_staff(self):
        dashboard_url = reverse("digiadmin-dashboard")
        login_url = reverse("digiadmin-login")

        self.assertRedirects(self.client.get(dashboard_url), login_url)
        failed = self.client.post(login_url, {
            "mobile": self.admin.mobile,
            "password": "wrong-password",
        })
        self.assertContains(failed, "credentials don’t match", status_code=200)

        response = self.client.post(login_url, {
            "mobile": self.admin.mobile,
            "password": "DigiAdmin!2026",
        })
        self.assertRedirects(response, dashboard_url)
        self.assertContains(self.client.get(dashboard_url), "Operations dashboard")

        response = self.client.post(dashboard_url, {
            "name": "Digi Staff One",
            "mobile": "9000000002",
            "pin": "4826",
        })
        self.assertRedirects(response, dashboard_url)
        staff = User.objects.get(mobile="9000000002")
        self.assertEqual(staff.role.name, "digi-staff")
        self.assertTrue(staff.check_pin("4826"))
        self.assertNotEqual(staff.pin, "4826")

    def test_wrong_role_cannot_sign_in_as_digiadmin(self):
        customer_role, _ = UserRole.objects.get_or_create(name="customer")
        customer = User(name="Customer", mobile="9000000003", role=customer_role)
        customer.set_password("DigiAdmin!2026")
        customer.save()

        response = self.client.post(reverse("digiadmin-login"), {
            "mobile": customer.mobile,
            "password": "DigiAdmin!2026",
        })
        self.assertContains(response, "credentials don’t match", status_code=200)
