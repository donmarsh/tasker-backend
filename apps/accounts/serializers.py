# apps/accounts/serializers.py
import logging
from rest_framework import serializers
from rest_framework.exceptions import ValidationError
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from apps.accounts.models import Role

User = get_user_model()
logger = logging.getLogger(__name__)


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
            email_value = attrs['email']
            try:
                user = User.objects.get(email__iexact=email_value)
                attrs[username_field] = getattr(user, username_field)
            except User.DoesNotExist:
                # fall back to using the email as username input so parent
                # serializer still sees credentials and returns invalid login
                attrs[username_field] = email_value

        # If username field contains an email, resolve it to actual username
        if username_field in attrs and attrs.get(username_field) and '@' in str(attrs.get(username_field)):
            try:
                user = User.objects.get(email__iexact=attrs[username_field])
                attrs[username_field] = getattr(user, username_field)
            except User.DoesNotExist:
                # Leave as-is so parent serializer produces invalid creds
                attrs[username_field] = attrs[username_field]

        if not attrs.get(username_field):
            raise ValidationError({'detail': 'Provide either username or email.'})

        data = super().validate(attrs)

        # enrich token payload via get_token when needed
        user = getattr(self, 'user', None) or getattr(self, 'validated_data', {}).get('user')
        if user is None:
            # TokenObtainPairSerializer may set `user` on itself during validation
            user = getattr(self, 'user', None)

        if user:
            token = self.get_token(user)
            # ensure extra claim is present on token (single role object)
            try:
                r = getattr(user, 'role', None)
                if r is not None and getattr(r, 'deleted_at', None) is None:
                    role_obj = {'id': r.id, 'role_name': r.name}
                else:
                    role_obj = None
            except Exception:
                role_obj = None
            token['role'] = role_obj
            token['username'] = user.username
            token['user_id'] = user.id
            token['full_name'] = user.full_name

        return data

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add roles and identifying claims so they appear in both
        # refresh and access tokens created by the parent serializer.
        try:
            r = getattr(user, 'role', None)
            if r is not None and getattr(r, 'deleted_at', None) is None:
                role_obj = {'id': r.id, 'role_name': r.name}
            else:
                role_obj = None
        except Exception:
            role_obj = None
        token['role'] = role_obj
        token['username'] = user.username
        token['user_id'] = user.id
        token['full_name'] = user.full_name
        return token


class UserSerializer(serializers.ModelSerializer):
    role = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'telephone', 'created_at', 'role']

    def get_role(self, obj):
        try:
            r = getattr(obj, 'role', None)
            if r is not None and getattr(r, 'deleted_at', None) is None:
                return {'id': r.id, 'role_name': r.name}
            return None
        except Exception:
            return None


class RoleSerializer(serializers.ModelSerializer):
    role_name = serializers.CharField(source='name')

    class Meta:
        model = Role
        fields = ['id', 'role_name']


class UserUpdateSerializer(serializers.ModelSerializer):
    # Allow updating the user's role via `role_id` in requests.
    role_id = serializers.PrimaryKeyRelatedField(
        source='role',
        queryset=Role.objects.filter(deleted_at__isnull=True),
        required=False,
        allow_null=True,
        write_only=True
    )

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'telephone', 'role_id']
        read_only_fields = ['id']

    def update(self, instance, validated_data):
        # `role` is provided via `role_id` (source='role') and will appear
        # in validated_data as the Role instance. Apply it explicitly.
        role_val = validated_data.pop('role', None)

        # Update simple fields
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        # Apply role if provided (may be None to unset)
        try:
            old_role = getattr(instance, 'role', None)
            old_role_id = getattr(old_role, 'id', None)
            old_role_name = getattr(old_role, 'name', None)

            if role_val is not None:
                new_role_id = getattr(role_val, 'id', None)
                new_role_name = getattr(role_val, 'name', None)
            else:
                new_role_id = None
                new_role_name = None

            logger.info(
                "Updating user id=%s: old_role=(%s,%s) -> new_role=(%s,%s)",
                getattr(instance, 'id', None),
                old_role_id,
                old_role_name,
                new_role_id,
                new_role_name,
            )

            if role_val is not None:
                instance.role = role_val

            # Persist changes. Because this is a legacy unmanaged model, do a
            # full save. We save all fields that changed.
            instance.save()
            logger.debug("User id=%s updated successfully", getattr(instance, 'id', None))
        except Exception:
            logger.exception("Failed updating user id=%s", getattr(instance, 'id', None))
            raise

        return instance