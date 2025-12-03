# apps/accounts/urls.py
from django.urls import path
from .views import MyTokenObtainPairView, logout_view, RegisterView
from .views import csrf_view
from .views import UserList, UserDetail
from .views import RoleList, RoleDetail

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', MyTokenObtainPairView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
        path('csrf/', csrf_view, name='csrf'),
    path('users/', UserList.as_view(), name='user-list'),
    path('users/<int:pk>/', UserDetail.as_view(), name='user-detail'),
    # Singular route for compatibility: allow PATCH/PUT at /user/<id>/
    path('user/<int:pk>/', UserDetail.as_view(), name='user-update'),
    path('roles/', RoleList.as_view(), name='role-list'),
    path('roles/<int:pk>/', RoleDetail.as_view(), name='role-detail'),
]