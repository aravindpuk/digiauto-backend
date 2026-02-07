from django.shortcuts import render

# Create your views here.

# Django DRF API for Spare Management
# Includes: Spare, SpareStock, SparePurchaseData, JobCardSpare (partial)

from rest_framework import serializers, views, status
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Spare, SpareStock, SparePurchaseData

# ------------------------- SERIALIZERS ----------------------------
class SpareSerializer(serializers.ModelSerializer):
    class Meta:
        model = Spare
        fields = ['id', 'partnumber', 'partname']

class SpareStockSerializer(serializers.ModelSerializer):
    spare = SpareSerializer(read_only=True)
    spare_id = serializers.IntegerField(write_only=True)
    branch_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = SpareStock
        fields = ['id', 'spare', 'spare_id', 'branch_id', 'mrp', 'quantity', 'purchase_amount']

class SparePurchaseSerializer(serializers.ModelSerializer):
    spare = SpareSerializer(read_only=True)
    spare_id = serializers.IntegerField(write_only=True)
    branch_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = SparePurchaseData
        fields = ['id', 'spare', 'spare_id', 'branch_id', 'mrp', 'quantity', 'purchase_amount', 'created_at']

# ------------------------- API VIEWS ------------------------------

# 1. Create Spare (Master)
class CreateSpareAPI(views.APIView):
    def post(self, request):
        serializer = SpareSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Spare created', 'data': serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 2. List Spare (only showing items with stock > 0 per branch)
class SpareListAPI(views.APIView):
    def get(self, request, branch_id):
        stocks = SpareStock.objects.filter(branches_id=branch_id, quantity__gt=0).select_related('spare')
        serializer = SpareStockSerializer(stocks, many=True)
        return Response(serializer.data)

# 3. Add new stock (with purchase history)
class AddSpareStockAPI(views.APIView):
    def post(self, request):
        # save purchase history
        p_ser = SparePurchaseSerializer(data=request.data)
        p_ser.is_valid(raise_exception=True)
        p_ser.save()

        # update existing stock OR create new
        spare_id = p_ser.validated_data['spare_id']
        branch_id = p_ser.validated_data['branch_id']
        quantity = p_ser.validated_data['quantity']
        mrp = p_ser.validated_data['mrp']
        purchase_amount = p_ser.validated_data['purchase_amount']

        stock, created = SpareStock.objects.get_or_create(
            spare_id=spare_id,
            branches_id=branch_id,
            defaults={'quantity': quantity, 'mrp': mrp, 'purchase_amount': purchase_amount}
        )

        if not created:
            # Add new quantity to existing stock
            stock.quantity += quantity
            stock.mrp = mrp  # update price to latest
            stock.purchase_amount = purchase_amount
            stock.save()

        return Response({'message': 'Stock updated', 'stock_id': stock.id})

# 4. Update Spare (normal update – name, partnumber)
class UpdateSpareAPI(views.APIView):
    def put(self, request, spare_id):
        spare = get_object_or_404(Spare, id=spare_id)
        serializer = SpareSerializer(spare, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Spare updated', 'data': serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# 5. Update SpareStock (normal edit – price/quantity correction)
class UpdateSpareStockAPI(views.APIView):
    def put(self, request, stock_id):
        stock = get_object_or_404(SpareStock, id=stock_id)
        serializer = SpareStockSerializer(stock, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'message': 'Stock updated', 'data': serializer.data})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
