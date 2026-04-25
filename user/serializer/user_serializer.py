
from os import name

from django.forms import SlugField
from rest_framework import serializers

from user.models import User,UserRole


class UserRoleSerializer(serializers.ModelSerializer):
    model = UserRole
    fields = ['id','name']


class UserSerializer(serializers.ModelSerializer):
    
    role = serializers.SlugRelatedField(queryset=UserRole.objects.all(),slug_field='name')

    class Meta:
        model = User
        fields = ['name','mobile','pin','role']
    
   
    def create(self, validated_data):
        pin = validated_data.pop('pin')
        
        user = User(**validated_data)

        user.set_pin(pin)
        user.save()

        return user