# apps/projects/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .viewsets import ProjectViewSet

router = DefaultRouter()
router.register(r'', ProjectViewSet, basename='project')

urlpatterns = [
    path('', include(router.urls)),
]