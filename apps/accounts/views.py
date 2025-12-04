# apps/accounts/views.py
import logging
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import User
from .serializers import MyTokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.views.decorators.csrf import ensure_csrf_cookie
from django.http import JsonResponse
User = get_user_model()
logger = logging.getLogger(__name__)
from rest_framework import generics
from .serializers import UserSerializer
from .permissions import IsAdminRole, IsAdminOrManagerRole
from .serializers import RoleSerializer
from apps.accounts.models import Role
class RegisterView(generics.CreateAPIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get('username')
        email = request.data.get('email')
        full_name = request.data.get('full_name')
        telephone = request.data.get('telephone', '')
        password = request.data.get('password')

        if not all([username, email, full_name, password]):
            return Response({"error": "All fields are required"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(username=username).exists():
            return Response({"error": "Username already exists"}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({"error": "Email already exists"}, status=status.HTTP_400_BAD_REQUEST)
        
        role_id = request.data.get('role_id')
        if not role_id:
            role_id = 3
        # Create user with hashed password
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            telephone=telephone,
            password=make_password(password),  # ← Django hashes it
            created_at=timezone.now(),  # or use NOW() in DB trigger
            role_id=role_id
        )
        user.save()

        # Assign role on the user (single-role model)
        
        try:
            role_obj = Role.objects.get(pk=role_id)
            user.role = role_obj
            user.save(update_fields=['role'])
            logger.info("Assigned role id=%s to new user id=%s", role_obj.id, user.id)
        except Role.DoesNotExist:
            # ignore invalid role id and leave role null
            logger.warning("Role id=%s not found when creating user id=%s", role_id, getattr(user, 'id', None))

        return Response({
            "message": "User registered successfully",
            "user": {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "full_name": user.full_name
            }
        }, status=status.HTTP_201_CREATED)

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

    def post(self, request, *args, **kwargs):
        # Validate credentials with the token serializer so we can access
        # the authenticated user object directly (TokenObtainPairView's
        # super().post() doesn't populate request.user yet).
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tokens = serializer.validated_data
        user = getattr(serializer, 'user', None)

        role_obj = None
        if user is not None:
            try:
                r = getattr(user, 'role', None)
                if r is not None and getattr(r, 'deleted_at', None) is None:
                    role_obj = {"id": r.id, "role_name": r.name}
            except Exception:
                role_obj = None

        # Ensure `user` in response is always an object (not null) so clients
        # that access `user.username` won't throw `Cannot read properties of
        # undefined` if the field is missing.
        user_obj = {
            "id": user.id if user is not None else None,
            "username": user.username if user is not None else "",
            "email": user.email if user is not None else "",
            "full_name": user.full_name if user is not None else "",
            "role": role_obj
        }

        res = Response({
            "message": "Login successful",
            "tokens": {
                "access": tokens.get('access'),
                "refresh": tokens.get('refresh')
            },
            "user": user_obj
        }, status=status.HTTP_200_OK)

        if tokens.get('access'):
            res.set_cookie('access_token', tokens['access'], httponly=True, samesite='Lax', max_age=3600)
        if tokens.get('refresh'):
            res.set_cookie('refresh_token', tokens['refresh'], httponly=True, samesite='Lax', max_age=604800)
        return res


@api_view(['POST'])
def logout_view(request):
    """Logout endpoint.

    Accepts requests authenticated either via Authorization header or via
    `access_token` cookie. If a cookie is present we attempt to authenticate
    the request using it before clearing cookies.
    """
    user = getattr(request, 'user', None)

    # If not authenticated via headers, try cookie-based token
    if not (user and getattr(user, 'is_authenticated', False)):
        token = request.COOKIES.get('access_token')
        if token:
            # Temporarily set Authorization header so JWTAuthentication can read it
            request.META['HTTP_AUTHORIZATION'] = f'Bearer {token}'
            try:
                auth = JWTAuthentication()
                auth_result = auth.authenticate(request)
                if auth_result is not None:
                    user, validated_token = auth_result
                    request.user = user
                else:
                    return Response({"detail": "Not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)
            except Exception:
                return Response({"detail": "Invalid token"}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({"detail": "Not authenticated"}, status=status.HTTP_401_UNAUTHORIZED)

    # At this point the request is authenticated (or we allowed cookie auth)
    response = Response({"message": "Logged out"}, status=status.HTTP_200_OK)
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return response


@ensure_csrf_cookie
def csrf_view(request):
    # ensure_csrf_cookie will set the CSRF cookie; return the token in body
    from django.middleware.csrf import get_token
    return JsonResponse({"detail": "CSRF cookie set", "csrfToken": get_token(request)})


class UserList(generics.ListAPIView):
    """List users. Requires admin role."""
    # Allow admins and managers to list users
    permission_classes = [IsAuthenticated, IsAdminOrManagerRole]
    serializer_class = UserSerializer

    def get_queryset(self):
        # Only non-deleted users
        return User.objects.filter(deleted_at__isnull=True)


class UserDetail(generics.RetrieveUpdateAPIView):
    permission_classes = [IsAuthenticated, IsAdminRole]
    queryset = User.objects.filter(deleted_at__isnull=True)

    def get_serializer_class(self):
        # Use a write-capable serializer when updating, otherwise read-only
        if self.request.method in ('PUT', 'PATCH'):
            from .serializers import UserUpdateSerializer
            return UserUpdateSerializer
        return UserSerializer


class RoleList(generics.ListAPIView):
    permission_classes = [IsAuthenticated, IsAdminRole]
    serializer_class = RoleSerializer

    def get_queryset(self):
        return Role.objects.filter(deleted_at__isnull=True)


class RoleDetail(generics.RetrieveAPIView):
    permission_classes = [IsAuthenticated, IsAdminRole]
    serializer_class = RoleSerializer
    queryset = Role.objects.filter(deleted_at__isnull=True)