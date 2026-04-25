from rest_framework import serializers
from jobcard.models import JobCard, JobCardSpare, JobCardLabour, Complaint, Vehicle
from garage.models import Branch
from user.models import User


class JobCardCreateSerializer(serializers.Serializer):
    """Serializer for creating jobcards with garage_id"""
    garage_id = serializers.IntegerField()
    vehicle_number = serializers.CharField(max_length=20)
    vehicle_model_id = serializers.IntegerField()
    complaints = serializers.ListField(child=serializers.IntegerField())
    kilometer = serializers.IntegerField()
    mechanic_ids = serializers.ListField(child=serializers.IntegerField(), required=False)
    status_id = serializers.IntegerField()

    def create(self, validated_data):
        garage_id = validated_data.pop('garage_id')
        complaints_ids = validated_data.pop('complaints')
        mechanic_ids = validated_data.pop('mechanic_ids', [])
        
        # Get the main branch for the garage
        branch = Branch.objects.filter(garage_id=garage_id).first()
        if not branch:
            raise serializers.ValidationError({"garage_id": "No branch found for this garage"})

        # Create JobCard
        jobcard = JobCard.objects.create(
            branch=branch,
            created_by=self.context.get('user'),
            vehicle_id=validated_data.get('vehicle_id'),
            kilometer=validated_data['kilometer'],
            status_id=validated_data['status_id']
        )

        # Add complaints
        if complaints_ids:
            complaints = Complaint.objects.filter(id__in=complaints_ids)
            jobcard.complaints.set(complaints)

        # Add mechanics
        if mechanic_ids:
            mechanics = User.objects.filter(id__in=mechanic_ids)
            jobcard.mechanic.set(mechanics)

        jobcard.save()
        return jobcard


class JobCardListSerializer(serializers.ModelSerializer):
    """Serializer for listing jobcards"""
    garage_id = serializers.SerializerMethodField()
    garage_name = serializers.SerializerMethodField()
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    vehicle_number = serializers.SerializerMethodField()
    status_name = serializers.CharField(source='status.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    complaints_list = serializers.SerializerMethodField()
    mechanics_list = serializers.SerializerMethodField()

    class Meta:
        model = JobCard
        fields = [
            'id', 'garage_id', 'garage_name', 'branch_name',
            'vehicle_number', 'kilometer', 'status_name', 'created_at',
            'created_by_name', 'complaints_list', 'mechanics_list'
        ]

    def get_garage_id(self, obj):
        return obj.branch.garage.id

    def get_garage_name(self, obj):
        return obj.branch.garage.name

    def get_vehicle_number(self, obj):
        return obj.vehicle.vehicle_number if obj.vehicle else ''

    def get_complaints_list(self, obj):
        return [{'id': c.id, 'text': c.text} for c in obj.complaints.all()]

    def get_mechanics_list(self, obj):
        return [{'id': m.id, 'name': m.name} for m in obj.mechanic.all()]


class JobCardDetailSerializer(serializers.ModelSerializer):
    """Serializer for jobcard details"""
    garage_id = serializers.SerializerMethodField()
    garage_name = serializers.SerializerMethodField()
    branch_name = serializers.CharField(source='branch.name', read_only=True)
    vehicle_number = serializers.SerializerMethodField()
    vehicle_model = serializers.CharField(source='vehicle.vehicle_model.name', read_only=True)
    vehicle_make = serializers.SerializerMethodField()
    status_name = serializers.CharField(source='status.name', read_only=True)
    created_by_name = serializers.CharField(source='created_by.name', read_only=True)
    complaints_list = serializers.SerializerMethodField()
    mechanics_list = serializers.SerializerMethodField()
    spares_list = serializers.SerializerMethodField()
    labour_services = serializers.SerializerMethodField()

    class Meta:
        model = JobCard
        fields = [
            'id', 'garage_id', 'garage_name', 'branch_name',
            'vehicle_number', 'vehicle_model', 'vehicle_make',
            'kilometer', 'status_name', 'created_at', 'created_by_name',
            'complaints_list', 'mechanics_list', 'spares_list', 'labour_services'
        ]

    def get_garage_id(self, obj):
        return obj.branch.garage.id

    def get_garage_name(self, obj):
        return obj.branch.garage.name

    def get_vehicle_number(self, obj):
        return obj.vehicle.vehicle_number if obj.vehicle else ''

    def get_vehicle_make(self, obj):
        if obj.vehicle and obj.vehicle.vehicle_model:
            return obj.vehicle.vehicle_model.fkMaker.name
        return ''

    def get_complaints_list(self, obj):
        return [{'id': c.id, 'text': c.text} for c in obj.complaints.all()]

    def get_mechanics_list(self, obj):
        return [{'id': m.id, 'name': m.name} for m in obj.mechanic.all()]

    def get_spares_list(self, obj):
        return [
            {
                'id': spare.id,
                'spare_name': spare.spare.partname,
                'quantity': spare.quantity,
                'mrp': str(spare.mrp)
            }
            for spare in obj.spares.all()
        ]

    def get_labour_services(self, obj):
        return [
            {
                'id': labour.id,
                'labour_name': labour.labour.name,
                'technician': labour.technician.name if labour.technician else None
            }
            for labour in obj.labour_services.all()
        ]
