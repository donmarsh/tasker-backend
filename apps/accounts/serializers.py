# apps/accounts/serializers.py
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model

User = get_user_model()


class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Allow login with either username or email.

    Accepts `{'username': ..., 'password': ...}` or
    `{'email': ..., 'password': ...}`. If an email is provided we
    look up the corresponding username and pass it to the parent
    serializer for authentication.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # provide optional `email` field so clients can post email-only
        if 'email' not in self.fields:
            self.fields['email'] = serializers.CharField(write_only=True, required=False)
        # make username optional; we'll resolve it from email if needed
        username_field = self.username_field
        if username_field in self.fields:
            self.fields[username_field].required = False

    def validate(self, attrs):
        username_field = self.username_field

        # If email provided and username missing, resolve username
        if 'email' in attrs and not attrs.get(username_field):
            try:
                user = User.objects.get(email=attrs['email'])
                attrs[username_field] = getattr(user, username_field)
            except User.DoesNotExist:
                # leave attrs alone; parent will raise invalid credentials
                pass

        # If username field contains an email, resolve it to actual username
        if username_field in attrs and attrs.get(username_field) and '@' in str(attrs.get(username_field)):
            try:
                user = User.objects.get(email=attrs[username_field])
                attrs[username_field] = getattr(user, username_field)
            except User.DoesNotExist:
                pass

        data = super().validate(attrs)

        # enrich token payload via get_token when needed
        user = getattr(self, 'user', None) or getattr(self, 'validated_data', {}).get('user')
        if user is None:
            # TokenObtainPairSerializer may set `user` on itself during validation
            user = getattr(self, 'user', None)

        if user:
            token = self.get_token(user)
            # ensure extra claims are present on token (roles etc.)
            roles = [ur.role.name for ur in user.userrole_set.filter(deleted_at__isnull=True)]
            token['roles'] = roles
            token['username'] = user.username
            token['user_id'] = user.id
            token['full_name'] = user.full_name

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        return token