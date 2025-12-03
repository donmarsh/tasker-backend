# apps/accounts/urls.py
from django.urls import path
from .views import MyTokenObtainPairView, logout_view, RegisterView
from .views import csrf_view

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', MyTokenObtainPairView.as_view(), name='login'),
    path('logout/', logout_view, name='logout'),
        path('csrf/', csrf_view, name='csrf'),
]