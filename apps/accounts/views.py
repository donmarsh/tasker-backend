# apps/accounts/views.py
from rest_framework import generics, status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from .models import User, UserRole
from .serializers import MyTokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.utils import timezone
User = get_user_model()
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

        # Create user with hashed password
        user = User(
            username=username,
            email=email,
            full_name=full_name,
            telephone=telephone,
            password=make_password(password),  # ← Django hashes it
            created_at=timezone.now()  # or use NOW() in DB trigger
        )
        user.save()

        # Add user role
        role_id = request.data.get('role_id')
        if not role_id:
            role_id = 3
        
        UserRole.objects.create(
            user=user,
            role_id=role_id,
            created_at=timezone.now()
        )

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

        roles = []
        if user is not None:
            roles = [ur.role.name for ur in user.userrole_set.filter(deleted_at__isnull=True)]

        res = Response({
            "message": "Login successful",
            "tokens": {
                "access": tokens.get('access'),
                "refresh": tokens.get('refresh')
            },
            "user": {
                "id": user.id if user else None,
                "username": user.username if user else None,
                "email": user.email if user else None,
                "full_name": user.full_name if user else None,
                "roles": roles
            }
        }, status=status.HTTP_200_OK)

        if tokens.get('access'):
            res.set_cookie('access_token', tokens['access'], httponly=True, samesite='Lax', max_age=3600)
        if tokens.get('refresh'):
            res.set_cookie('refresh_token', tokens['refresh'], httponly=True, samesite='Lax', max_age=604800)
        return res


def logout_view(request):
    response = Response({"message": "Logged out"})
    response.delete_cookie('access_token')
    response.delete_cookie('refresh_token')
    return response