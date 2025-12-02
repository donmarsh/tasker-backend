# apps/tasks/viewsets.py
from rest_framework import viewsets, filters
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.permissions import IsAuthenticated
from .models import Task
from .serializers import TaskSerializer
from .permissions import IsProjectMemberOrReadOnly

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsProjectMemberOrReadOnly]

    def get_queryset(self):
        return Task.objects.filter(
            deleted_at__isnull=True,
            project__created_by=self.request.user
        ).select_related('status', 'assignee', 'project')

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)

    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['status', 'assignee', 'project']
    search_fields = ['title', 'description']
    ordering_fields = ['deadline', 'created_at']
    ordering = ['-created_at']