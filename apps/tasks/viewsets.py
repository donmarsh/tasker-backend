# apps/tasks/viewsets.py
from rest_framework import viewsets, filters as drf_filters
from django_filters.rest_framework import DjangoFilterBackend
from django_filters import rest_framework as dj_filters
from rest_framework.permissions import IsAuthenticated
from .models import Task
from .serializers import TaskSerializer
from .permissions import IsProjectMemberOrReadOnly
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status as http_status
from apps.tasks.models import TaskStatus

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsProjectMemberOrReadOnly]

    def get_queryset(self):
        # Determine user identity and role. If the user is admin, return all
        # non-deleted tasks. If a normal user, only return tasks assigned to
        # them. Prefer `request.user` but fall back to JWT token payload.
        user = getattr(self.request, 'user', None)
        owner_id = None
        is_admin = False

        if user and getattr(user, 'is_authenticated', False):
            owner_id = getattr(user, 'id', None)
            try:
                is_admin = user.userrole_set.filter(deleted_at__isnull=True, role__name__iexact='admin').exists()
            except Exception:
                is_admin = False
        else:
            token = getattr(self.request, 'auth', None)
            if token is not None:
                # token may behave like a dict or have `.payload`
                payload = None
                if isinstance(token, dict):
                    payload = token
                else:
                    payload = getattr(token, 'payload', None) or {}

                owner_id = payload.get('user_id')
                roles = payload.get('roles') or []
                if isinstance(roles, (list, tuple)):
                    is_admin = any(str(r).lower() == 'admin' for r in roles)
                elif isinstance(roles, str):
                    is_admin = roles.lower() == 'admin'

        base_qs = Task.objects.filter(deleted_at__isnull=True).select_related('status', 'assignee', 'project')

        if is_admin:
            return base_qs

        if owner_id is not None:
            return base_qs.filter(assignee__id=owner_id)

        # No identity info -> return empty queryset to avoid leaking tasks.
        return Task.objects.none()

    def perform_create(self, serializer):
        # Legacy `tbl_tasks` has no `created_by` column, so just save the
        # task as provided. The frontend should set `assignee`/`project`.
        serializer.save()

    @action(detail=True, methods=['patch'], url_path='status')
    def status(self, request, pk=None):
        """Patch-only endpoint to update a task's status.

        Expects JSON body `{ "status_id": <int> }` and returns the
        updated Task representation. Permission checks are applied
        via the viewset's `permission_classes`.
        """
        task = self.get_object()
        status_id = request.data.get('status_id')
        if status_id is None:
            return Response({'detail': 'status_id is required'}, status=http_status.HTTP_400_BAD_REQUEST)

        try:
            status_obj = TaskStatus.objects.get(pk=status_id)
        except TaskStatus.DoesNotExist:
            return Response({'detail': 'Invalid status_id'}, status=http_status.HTTP_400_BAD_REQUEST)

        task.status = status_obj
        task.save(update_fields=['status', 'modified_at'])
        return Response(TaskSerializer(task, context={'request': request}).data, status=http_status.HTTP_200_OK)

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