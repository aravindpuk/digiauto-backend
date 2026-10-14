from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from django.db.models import Prefetch

from .models import VehicleMake, VehicleModel


class VehicleCatalog(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        makes = VehicleMake.objects.prefetch_related(
            Prefetch("models", queryset=VehicleModel.objects.order_by("name"))
        ).order_by("name")
        return Response(
            {
                "makes": [
                    {
                        "id": make.id,
                        "name": make.name,
                        "models": [
                            {"id": model.id, "name": model.name}
                            for model in make.models.all()
                        ],
                    }
                    for make in makes
                ]
            }
        )
