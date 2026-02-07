
import jwt
from django.conf import settings
from rest_framework import authentication, exceptions
from user.models import User  # your custom User model

class JWTAuthentication(authentication.BaseAuthentication):
    def authenticate(self, request):
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            return None

        try:
            token = auth_header.split(' ')[1]  # "Bearer <token>"
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=['HS256'])
        except (IndexError, jwt.ExpiredSignatureError, jwt.DecodeError):
            raise exceptions.AuthenticationFailed('Invalid or expired token')

        try:
            user = User.objects.get(id=payload['user_id'])
        except User.DoesNotExist:
            raise exceptions.AuthenticationFailed('User not found')

        return (user, token)
