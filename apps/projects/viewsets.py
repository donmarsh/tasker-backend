# apps/projects/viewsets.py
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from .models import Project, ProjectStatus
from .serializers import ProjectSerializer
from .permissions import IsOwnerOrReadOnly

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsOwnerOrReadOnly]

    def get_queryset(self):
        return Project.objects.filter(deleted_at__isnull=True, created_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    # Filtering, search, ordering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project_status']
    search_fields = ['name']
    ordering_fields = ['created_at', 'project_start_date', 'project_end_date']
    ordering = ['-created_at']