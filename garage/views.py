from django.shortcuts import render

# Create your views here.

from multiprocessing import context
from rest_framework.views import APIView
from rest_framework.response import Response
from garage.serializer.garage_serializer import GarageSerializer
from rest_framework.permissions import IsAuthenticated


class RegisterGarage(APIView):
    permission_classes = [IsAuthenticated]
    
    def post(request):
        try:

            _serializer = GarageSerializer(data=request.data,context={'user':request.user})

            if _serializer.is_valid():
                _serializer.save()
            else:
                return Response({f"message:{_serializer.errors}"})
            return Response({"messgae":'garage saved...'})

        except Exception as e:
            print(e)

            return Response({"messgae":str(e)})   