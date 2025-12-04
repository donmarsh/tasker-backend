# apps/projects/viewsets.py
import logging
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from apps.accounts.permissions import IsAdminRole, IsAdminOrManagerRole
from .models import Project, ProjectStatus
from .serializers import ProjectSerializer
from .permissions import IsOwnerOrReadOnly

class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    # Admins and managers may access projects endpoints
    permission_classes = [IsAuthenticated, IsAdminOrManagerRole]
    logger = logging.getLogger(__name__)

    def get_queryset(self):
        # Return all non-deleted projects. Actual access control is handled
        # by the `IsAdminRole` permission class which allows only admins.
        try:
            qs = Project.objects.filter(deleted_at__isnull=True)
            self.logger.info("Project list requested by user id=%s: returning %s projects", getattr(self.request.user, 'id', None), qs.count())
            return qs
        except Exception:
            self.logger.exception("Failed to fetch projects for user id=%s", getattr(self.request, 'user', None))
            return Project.objects.none()

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    # Filtering, search, ordering
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['project_status']
    search_fields = ['name']
    ordering_fields = ['created_at', 'project_start_date', 'project_end_date']
    ordering = ['-created_at']