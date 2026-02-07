from math import e
from rest_framework.views import APIView
from rest_framework.response import Response
from .models import VehicleMake,VehicleModel,Vehicle,Complaint,JobCard,JobStatus

# Create your views here.



class JobCardView(APIView):

    def create_jobcard(self, request):
        try:
            data           = request.data
            customer       = data.get('customer')
            vehicle_number = data.get('vehicle_number')
            vehicle_model  = data.get('vehicle_model')
            vehicle_make   = data.get('vehicle_make')
            complaints     = data.get('complaints', [])
            kilometer      = data.get('kilometer')
            mechanic_ids   = data.get('mechanic_ids', [])
            status_id      = data.get('status_id')

            # Create or get VehicleMake
            make, created = VehicleMake.objects.get_or_create(name=vehicle_make)    
        
        except Exception as e:
            return Response({"error": str(e)}, status=400)
    # Logic to handle job card operations   