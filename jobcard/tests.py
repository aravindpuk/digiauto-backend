from decimal import Decimal

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIRequestFactory, force_authenticate

from garage.models import Branch, Garage
from labour.models import Labour
from spare.models import Spare
from user.models import User, UserRole
from .models import (
    JobCard,
    JobCardLabour,
    JobCardSpare,
    JobStatus,
    Vehicle,
    VehicleMake,
    VehicleModel,
)
from .views import JobCardDetailView, JobCardReportsView


class JobCardReportDeliveryDateTests(TestCase):
    def setUp(self):
        self.factory = APIRequestFactory()
        role = UserRole.objects.create(name="Owner")
        self.user = User.objects.create(
            name="Owner",
            mobile="9999999999",
            pin="1234",
            role=role,
        )
        garage = Garage.objects.create(name="Garage", mobile="8888888888")
        self.branch = Branch.objects.create(name="Main", garage=garage)
        self.user.branches.add(self.branch)

        make = VehicleMake.objects.create(name="Honda")
        model = VehicleModel.objects.create(name="City", fkMaker=make)
        customer = User.objects.create(
            name="Customer",
            mobile="7777777777",
            pin="1234",
            role=role,
        )
        vehicle = Vehicle.objects.create(
            vehicle_number="KL01AB1234",
            vehicle_model=model,
            user=customer,
            year="2020",
        )
        self.completed = JobStatus.objects.create(name="completed", order=2)
        JobStatus.objects.create(name="delivered", order=3)

        self.jobcard = JobCard.objects.create(
            branch=self.branch,
            created_by=self.user,
            vehicle=vehicle,
            kilometer=12000,
            status=self.completed,
        )
        old_created_at = timezone.now() - timezone.timedelta(days=45)
        JobCard.objects.filter(pk=self.jobcard.pk).update(created_at=old_created_at)

        spare = Spare.objects.create(partname="Oil Filter", partnumber="OF-1")
        JobCardSpare.objects.create(
            jobcard=self.jobcard,
            spare=spare,
            quantity=2,
            mrp=Decimal("100.00"),
        )
        labour = Labour.objects.create(name="Service")
        JobCardLabour.objects.create(
            jobcard=self.jobcard,
            labour=labour,
            amount=Decimal("300.00"),
        )

    def test_today_report_uses_delivery_date_for_old_jobcards(self):
        request = self.factory.patch(
            f"/jobcard/jobcards/{self.jobcard.id}/",
            {"action": "update_status"},
            format="json",
        )
        force_authenticate(request, user=self.user)
        response = JobCardDetailView.as_view()(request, self.jobcard.id)
        self.assertEqual(response.status_code, 200)

        self.jobcard.refresh_from_db()
        self.assertEqual(self.jobcard.status.name, "delivered")
        self.assertIsNotNone(self.jobcard.delivered_at)

        request = self.factory.get(
            "/jobcard/reports/",
            {"period": "today", "branch_id": str(self.branch.id)},
        )
        force_authenticate(request, user=self.user)
        response = JobCardReportsView.as_view()(request)
        self.assertEqual(response.status_code, 200)

        summary = response.data["summary"]
        self.assertEqual(summary["total_jobs"], 0)
        self.assertEqual(summary["delivered_jobs"], 1)
        self.assertEqual(summary["pending_jobs"], 0)
        self.assertEqual(summary["spare_income"], "200")
        self.assertEqual(summary["labour_income"], "300")
        self.assertEqual(summary["income"], "500")
