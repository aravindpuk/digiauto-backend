from django.db import transaction
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response

from rest_framework.decorators import api_view,permission_classes
from rest_framework.permissions import IsAuthenticated
from django.views.decorators.csrf import csrf_exempt

from garage.models import Branch
from user.models import User

from .models import VehicleMake,VehicleModel,Vehicle,Complaint,JobCard,JobStatus
from .serializer.jobcard_serializer import JobCardDetailSerializer, JobCardListSerializer

# Create your views here.



class JobCardView(APIView):
    permission_classes = [IsAuthenticated]

    @transaction.atomic
    def post(self, request):
        try:
            data = request.data
            customer_id = data.get('customer')
            garage_id = data.get('garage_id')
            branch_id = data.get('branch_id')
            vehicle_number = data.get('vehicle_number')
            vehicle_model_id = data.get('vehicle_model_id')
            vehicle_model_name = data.get('vehicle_model')
            vehicle_make_name = data.get('vehicle_make')
            complaints = data.get('complaints', [])
            kilometer = data.get('kilometer')
           

            if not customer_id:
                return Response({"message": "customer is required"}, status=status.HTTP_400_BAD_REQUEST)
            if not vehicle_number:
                return Response({"message": "vehicle_number is required"}, status=status.HTTP_400_BAD_REQUEST)
            if kilometer in [None, ""]:
                return Response({"message": "kilometer is required"}, status=status.HTTP_400_BAD_REQUEST)
            
        
            customer = User.objects.filter(id=customer_id).first()
            if not customer:
                return Response({"message": "Customer not found"}, status=status.HTTP_404_NOT_FOUND)

            branch = None
            if branch_id:
                branch = Branch.objects.filter(id=branch_id).select_related('garage').first()
            
            elif garage_id:
                branch = Branch.objects.filter(garage_id=garage_id).select_related('garage').first()
            else:
                branch = request.user.branches.select_related('garage').first()

            if not branch:
                return Response({"message": "No branch found for this jobcard"}, status=status.HTTP_400_BAD_REQUEST)

            vehicle_model = None
            if vehicle_model_id:
                vehicle_model = VehicleModel.objects.filter(id=vehicle_model_id).first()
                
                if not vehicle_model:
                    return Response({"message": "Vehicle model not found"}, status=status.HTTP_404_NOT_FOUND)
            
            elif vehicle_model_name and vehicle_make_name:
                make, _ = VehicleMake.objects.get_or_create(name=vehicle_make_name.strip())
                vehicle_model, _ = VehicleModel.objects.get_or_create(
                    name=vehicle_model_name.strip(),
                    fkMaker=make,
                )

            vehicle, _ = Vehicle.objects.get_or_create(
                vehicle_number=vehicle_number,
                user=customer,
                defaults={"vehicle_model": vehicle_model},
            )

            if vehicle_model and vehicle.vehicle_model_id != vehicle_model.id:
                vehicle.vehicle_model = vehicle_model
                vehicle.save(update_fields=['vehicle_model'])

            jobcard = JobCard.objects.create(
                branch=branch,
                created_by=request.user,
                vehicle=vehicle,
                kilometer=kilometer,
                status_id=status_id,
            )

            complaint_instances = []
            for complaint in complaints:
                if isinstance(complaint, int) or (isinstance(complaint, str) and complaint.isdigit()):
                    complaint_obj = Complaint.objects.filter(id=complaint).first()
                    if complaint_obj:
                        complaint_instances.append(complaint_obj)
                elif isinstance(complaint, str) and complaint.strip():
                    complaint_obj, _ = Complaint.objects.get_or_create(text=complaint.strip())
                    complaint_instances.append(complaint_obj)

            if complaint_instances:
                jobcard.complaints.set(complaint_instances)

            if mechanic_ids:
                mechanics = User.objects.filter(id__in=mechanic_ids)
                jobcard.mechanic.set(mechanics)

            serializer = JobCardDetailSerializer(jobcard)
            return Response(
                {
                    "message": "Jobcard created successfully",
                    "jobcard": serializer.data,
                },
                status=status.HTTP_201_CREATED,
            )
        except Exception as e:
            return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fetch_jobcards(request):
    try:
        jobs = (
            JobCard.objects.exclude(status__name__iexact='delivered')
            .select_related('branch__garage', 'vehicle__vehicle_model__fkMaker', 'status', 'created_by')
            .prefetch_related('complaints', 'mechanic')
            .order_by('-created_at')
        )

        user_branches = request.user.branches.all()
        if user_branches.exists():
            jobs = jobs.filter(branch__in=user_branches)

        serializer = JobCardListSerializer(jobs, many=True)
        return Response({"jobcards": serializer.data}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({"message": str(e)}, status=status.HTTP_400_BAD_REQUEST)
