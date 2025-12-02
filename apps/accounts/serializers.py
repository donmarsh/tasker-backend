# apps/accounts/serializers.py
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from .models import User

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add your roles to the token
        roles = [ur.role.name for ur in user.userrole_set.filter(deleted_at__isnull=True)]
        token['roles'] = roles
        token['username'] = user.username
        token['user_id'] = user.id
        token['full_name'] = user.full_name
        return token