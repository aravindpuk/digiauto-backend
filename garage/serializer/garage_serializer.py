
from rest_framework import serializers
from garage.models import Garage,Branch


# Serializers


class GarageSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = Garage
        fields = ['name', 'email', 'mobile', 'place', 'logo', 'seal']

    
    def create(self, validated_data):
        
        garage = Garage(**validated_data)
        garage.save()

        user = self.context.get('user')

        branch = Branch.objects.create(garage=garage, name='main',place=garage.place)
        
        user.branches.add(branch)
        user.save()

        return garage
        