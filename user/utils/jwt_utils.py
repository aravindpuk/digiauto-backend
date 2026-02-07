import jwt
from django.conf import settings
from jwt import ExpiredSignatureError, InvalidTokenError


'''this file is test for testing token manually...not the part of rest_framework request..
we can test token without request object..... set this some future task like any background runing jobs..
'''

def verify_jwt_token(token):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=["HS256"])
        return payload  # valid token
    except ExpiredSignatureError:
        return None  # token expired
    except InvalidTokenError:
        return None  # invalid token
