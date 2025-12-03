# apps/tasks/viewsets.py
from rest_framework import viewsets, filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as dj_filters
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

    filter_backends = [DjangoFilterBackend, drf_filters.SearchFilter, drf_filters.OrderingFilter]
    # support filtering by related project id via `?project_id=<id>`
    class TaskFilter(dj_filters.FilterSet):
        project_id = dj_filters.NumberFilter(field_name='project__id', lookup_expr='exact')

        class Meta:
            model = Task
            fields = ['status', 'assignee', 'project', 'project_id']

    filterset_class = TaskFilter
    search_fields = ['title', 'description']
    ordering_fields = ['deadline', 'created_at']
    ordering = ['-created_at']