from decimal import Decimal

from rest_framework import serializers
from jobcard.models import JobCard, JobCardLabour, JobCardSpare


class JobCardListSerializer(serializers.ModelSerializer):
    """Lightweight serializer used for the home screen list."""

    garage_id    = serializers.SerializerMethodField()
    garage_name  = serializers.SerializerMethodField()
    branch_id    = serializers.IntegerField(source="branch.id",   read_only=True)
    branch_name  = serializers.CharField(source="branch.name",   read_only=True)
    vehicle_number   = serializers.SerializerMethodField()
    vehicle_model    = serializers.SerializerMethodField()
    vehicle_make     = serializers.SerializerMethodField()
    customer_name    = serializers.SerializerMethodField()
    mobile           = serializers.SerializerMethodField()
    place            = serializers.SerializerMethodField()
    status           = serializers.CharField(source="status.name", read_only=True)
    created_by_name  = serializers.CharField(source="created_by.name", read_only=True)
    services         = serializers.SerializerMethodField()
    total            = serializers.SerializerMethodField()

    class Meta:
        model  = JobCard
        fields = [
            "id", "garage_id", "garage_name", "branch_id", "branch_name",
            "vehicle_number", "vehicle_model", "vehicle_make",
            "customer_name", "mobile", "place",
            "kilometer", "status", "created_at",
            "created_by_name", "services", "total",
        ]

    def get_garage_id(self, obj):
        return obj.branch.garage.id

    def get_garage_name(self, obj):
        return obj.branch.garage.name

    def get_vehicle_number(self, obj):
        return obj.vehicle.vehicle_number if obj.vehicle else ""

    def get_vehicle_model(self, obj):
        if obj.vehicle and obj.vehicle.vehicle_model:
            return obj.vehicle.vehicle_model.name
        return ""

    def get_vehicle_make(self, obj):
        if obj.vehicle and obj.vehicle.vehicle_model:
            return obj.vehicle.vehicle_model.fkMaker.name
        return ""

    def get_customer_name(self, obj):
        return obj.vehicle.user.name if obj.vehicle else ""

    def get_mobile(self, obj):
        return obj.vehicle.user.mobile if obj.vehicle else ""

    def get_place(self, obj):
        return obj.vehicle.user.address if obj.vehicle else ""

    def get_services(self, obj):
        return [{"id": c.id, "text": c.text} for c in obj.complaints.all()]

    def get_total(self, obj):
        return str(_jobcard_total(obj))


class JobCardDetailSerializer(serializers.ModelSerializer):
    """Full serializer used after create and for detail view."""

    garage_id    = serializers.SerializerMethodField()
    garage_name  = serializers.SerializerMethodField()
    branch_id    = serializers.IntegerField(source="branch.id",  read_only=True)
    branch_name  = serializers.CharField(source="branch.name",  read_only=True)
    vehicle_number  = serializers.SerializerMethodField()
    vehicle_model_id = serializers.SerializerMethodField()
    vehicle_model   = serializers.SerializerMethodField()
    vehicle_make    = serializers.SerializerMethodField()
    year            = serializers.SerializerMethodField()
    chassis_number  = serializers.SerializerMethodField()
    engine_number   = serializers.SerializerMethodField()
    customer_name   = serializers.SerializerMethodField()
    mobile          = serializers.SerializerMethodField()
    place           = serializers.SerializerMethodField()
    status          = serializers.CharField(source="status.name", read_only=True)
    created_by_name = serializers.CharField(source="created_by.name", read_only=True)
    services        = serializers.SerializerMethodField()
    spares          = serializers.SerializerMethodField()
    labour_services = serializers.SerializerMethodField()
    total           = serializers.SerializerMethodField()

    class Meta:
        model  = JobCard
        fields = [
            "id", "garage_id", "garage_name", "branch_id", "branch_name",
            "vehicle_number", "vehicle_model_id", "vehicle_model", "vehicle_make", "year",
            "chassis_number", "engine_number",
            "customer_name", "mobile", "place",
            "kilometer", "status", "created_at", "created_by_name",
            "services", "spares", "labour_services", "total",
        ]

    def get_garage_id(self, obj):
        return obj.branch.garage.id

    def get_garage_name(self, obj):
        return obj.branch.garage.name

    def get_vehicle_number(self, obj):
        return obj.vehicle.vehicle_number if obj.vehicle else ""

    def get_vehicle_model(self, obj):
        if obj.vehicle and obj.vehicle.vehicle_model:
            return obj.vehicle.vehicle_model.name
        return ""

    def get_vehicle_model_id(self, obj):
        if obj.vehicle and obj.vehicle.vehicle_model:
            return obj.vehicle.vehicle_model_id
        return None

    def get_vehicle_make(self, obj):
        if obj.vehicle and obj.vehicle.vehicle_model:
            return obj.vehicle.vehicle_model.fkMaker.name
        return ""

    # These are stored on the Vehicle model — extend Vehicle if needed
    def get_year(self, obj):
        return getattr(obj.vehicle, "year", "") or ""

    def get_chassis_number(self, obj):
        return getattr(obj.vehicle, "chassis_number", "") or ""

    def get_engine_number(self, obj):
        return getattr(obj.vehicle, "engine_number", "") or ""

    def get_customer_name(self, obj):
        return obj.vehicle.user.name if obj.vehicle else ""

    def get_mobile(self, obj):
        return obj.vehicle.user.mobile if obj.vehicle else ""

    def get_place(self, obj):
        return obj.vehicle.user.address if obj.vehicle else ""

    def get_services(self, obj):
        return [
            {
                "id": c.id,
                "text": c.text,
            }
            for c in obj.complaints.all()
        ]

    def get_spares(self, obj):
        return [
            {
                "id":        s.id,
                "part_name": s.spare.partname,
                "quantity":  s.quantity,
                "mrp":       str(s.mrp),
                "amount":    str(s.mrp * s.quantity),
                "services":  [{"id": c.id, "text": c.text} for c in s.complaints.all()],
            }
            for s in obj.spares.select_related("spare").all()
        ]

    def get_labour_services(self, obj):
        return [
            {
                "id":          lb.id,
                "labour_id":   lb.labour_id,
                "labour_name": lb.labour.name,
                "amount":      str(lb.amount),
                "technician":  lb.technician.name if lb.technician else None,
                "services":    [{"id": c.id, "text": c.text} for c in lb.complaints.all()],
            }
            for lb in obj.labour_services.select_related("labour", "technician").all()
        ]

    def get_total(self, obj):
        return str(_jobcard_total(obj))


def _jobcard_total(obj):
    spare_total = sum(
        (spare.mrp or Decimal("0.00")) * spare.quantity
        for spare in obj.spares.all()
    )
    labour_total = sum(
        labour.amount or Decimal("0.00")
        for labour in obj.labour_services.all()
    )
    return spare_total + labour_total
