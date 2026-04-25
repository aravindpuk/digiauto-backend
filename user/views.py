from django.http import HttpResponse
from django.shortcuts import render

# Create your views here.


from rest_framework.views import APIView
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.exceptions import ValidationError

from user.serializer.user_serializer import UserRoleSerializer, UserSerializer,UserRole
from . models import LoginInfo,User, UserRole

from django.utils import timezone


def get_userRoles(request):
    roles = UserRole.objects.filter(name__in=['admin','customer'])
    serializer = UserRoleSerializer(roles,many=True)
    return Response({'user_roles':serializer.data})

class RegisterUser(APIView):

    def post(self,request):
        try:
           
            _serializer = UserSerializer(data=request.data)
            if _serializer.is_valid(raise_exception=True):
                _serializer.save()
                return Response({'message':'user saved...'},status=201)
        except ValidationError:
                errors = _serializer.errors
                field, message = next(iter(errors.items()))
                
                return Response({'message':f"user Reg failed .. {message[0]}"},status=400)
        except Exception as e:
            print(e)
            return Response({'message':str(e)},status=400)


    
        


@api_view(['POST'])
def login(request):
    try:
        mobile = request.data.get('mobile')
        pin = request.data.get('pin')

        if not mobile or not pin:
            return Response({'message': 'Mobile and PIN are required'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            
            user = User.objects.get(mobile=mobile)
        except User.DoesNotExist as u:
            print(u)
            return Response({'message': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        if not user.check_pin(pin):
            return Response({'message': 'Invalid PIN'}, status=status.HTTP_401_UNAUTHORIZED)

        # Create a login info record
        login = LoginInfo.objects.create(user=user, login_status=True)
        token = login.generate_auth_token()

        branch = user.branches.select_related('garage').first()
        return Response({
                'message': 'Login successful',
                'token': token,
                'garage':branch.garage.id if branch else None #currently 
                # 'user': user.id,            
                
        }, status=status.HTTP_200_OK)
    
        # return HttpResponse('login view')

    except Exception as e:
        print(e)
        return  Response({'message': str(e)}, status=status.HTTP_404_NOT_FOUND)



@api_view(['POST'])
def logout(request):
    user = request.user
    LoginInfo.objects.filter(user=user, Login_status=True).update(
        login_status=False, logout_time=timezone.now()
        )
    return Response({'message': 'Logged out successfully'},status=status.HTTP_200_OK)
