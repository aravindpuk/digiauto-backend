
from rest_framework import serializers

from user.models import User,UserRole


class UserRoleSerializer(serializers.ModelSerializer):
    model = UserRole
    fields = ['id','name']



class UserSerializer(serializers.ModelSerializer):
   

    class Meta:
        model = User
        fields = ['name','mobile','pin','role']
    
    def validate_mobile(self,value):

        if User.objects.filter(mobile=value).exists():
            raise serializers.ValidationError("mobile Already Exist...")
        return value
    
    def create(self, validated_data):
        pin = validated_data.pop('pin')
        role = validated_data.pop('role')
        
        _role = UserRole.objects.get(id=role.id)
        
        user = User(role=_role,**validated_data)

        user.set_pin(pin)
        user.save()

        return user