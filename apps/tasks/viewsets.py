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
from rest_framework.exceptions import PermissionDenied

class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, IsProjectMemberOrReadOnly]

    def get_queryset(self):
        # Determine user identity and role. If the user is admin, return all
        # non-deleted tasks. If a normal user, only return tasks assigned to
        # them. Prefer `request.user` but fall back to JWT token payload.
        user = getattr(self.request, 'user', None)
        owner_id = None
        is_privileged = False  # admin or manager

        if user and getattr(user, 'is_authenticated', False):
            owner_id = getattr(user, 'id', None)
            try:
                role = getattr(user, 'role', None)
                if role is not None and getattr(role, 'deleted_at', None) is None:
                    name = str(getattr(role, 'name', '')).lower()
                    is_privileged = name in ('admin', 'manager')
                else:
                    is_privileged = False
            except Exception:
                is_privileged = False
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
                # Prefer single `role` object in token payload
                role_obj = payload.get('role')
                if isinstance(role_obj, dict):
                    name = role_obj.get('role_name') or role_obj.get('name')
                    is_privileged = str(name or '').lower() in ('admin', 'manager')
                elif isinstance(role_obj, str):
                    is_privileged = role_obj.lower() in ('admin', 'manager')
                else:
                    # Backwards-compat: look for `roles` array
                    roles = payload.get('roles') or []
                    if isinstance(roles, (list, tuple)):
                        is_privileged = any(str(r).lower() in ('admin', 'manager') for r in roles)
                    elif isinstance(roles, str):
                        is_privileged = roles.lower() in ('admin', 'manager')

        base_qs = Task.objects.filter(deleted_at__isnull=True).select_related('status', 'assignee', 'project')

        # Support optional filtering by ?user_id=<id>
        user_id_param = self.request.query_params.get('user_id')
        if user_id_param is not None:
            try:
                uid = int(user_id_param)
            except (TypeError, ValueError):
                return Task.objects.none()

                # If caller is admin or manager allow fetching tasks for that user
                if is_privileged:
                    # When filtering by a specific assignee id, exclude tasks
                    # that have no assignee (assignee is NULL) so they aren't
                    # returned for an explicit `user_id`/`assignee_id` query.
                    return base_qs.filter(assignee__id=uid, assignee__isnull=False)

            # If we have a resolved role variable from request.user above,
            # check for manager role as well. If not populated, try payload.
            is_manager = False
            try:
                if user and getattr(user, 'is_authenticated', False):
                    role = getattr(user, 'role', None)
                    if role is not None and getattr(role, 'deleted_at', None) is None:
                        is_manager = str(getattr(role, 'name', '')).lower() == 'manager'
                else:
                    payload = None
                    token = getattr(self.request, 'auth', None)
                    if token is not None:
                        if isinstance(token, dict):
                            payload = token
                        else:
                            payload = getattr(token, 'payload', None) or {}

                    role_obj = (payload or {}).get('role') if payload is not None else None
                    if isinstance(role_obj, dict):
                        name = role_obj.get('role_name') or role_obj.get('name')
                        is_manager = str(name or '').lower() == 'manager'
                    elif isinstance(role_obj, str):
                        is_manager = role_obj.lower() == 'manager'
            except Exception:
                is_manager = False

            if is_manager:
                return base_qs.filter(assignee__id=uid, assignee__isnull=False)

            # If caller is a normal user, only allow if uid matches owner's id
            if owner_id is not None and owner_id == uid:
                return base_qs.filter(assignee__id=owner_id)

            # Unauthorized to view other user's tasks
            return Task.objects.none()

        # No user_id param: preserve previous behavior
        if is_privileged:
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
        user_id = dj_filters.NumberFilter(field_name='assignee__id', lookup_expr='exact')
        assignee_id = dj_filters.NumberFilter(field_name='assignee__id', lookup_expr='exact')

        class Meta:
            model = Task
            fields = ['status', 'assignee', 'project', 'project_id', 'user_id', 'assignee_id']

    filterset_class = TaskFilter
    search_fields = ['title', 'description']
    ordering_fields = ['deadline', 'created_at']
    ordering = ['-created_at']

    def retrieve(self, request, pk=None):
        """Return a single Task if the caller is admin/manager or the assignee.

        Admins/managers may view any task. Regular users may view only tasks
        where their token `user_id` equals the task's assignee id.
        """
        task = self.get_object()

        # Inspect token payload first
        token = getattr(request, 'auth', None)
        payload = None
        if token is not None:
            if isinstance(token, dict):
                payload = token
            else:
                payload = getattr(token, 'payload', None) or {}

        # Check role from token (prefer single `role` object)
        is_privileged = False
        if payload is not None:
            role_obj = payload.get('role')
            if isinstance(role_obj, dict):
                name = role_obj.get('role_name') or role_obj.get('name')
                if name and str(name).lower() in ('admin', 'manager'):
                    is_privileged = True
            elif isinstance(role_obj, str) and role_obj.lower() in ('admin', 'manager'):
                is_privileged = True

            # Backwards-compat: check `roles` array
            roles = payload.get('roles') or []
            if isinstance(roles, (list, tuple)) and any(str(r).lower() in ('admin', 'manager') for r in roles):
                is_privileged = True
            elif isinstance(roles, str) and roles.lower() in ('admin', 'manager'):
                is_privileged = True

        if is_privileged:
            return Response(TaskSerializer(task, context={'request': request}).data)

        # Not privileged: verify user identity matches assignee
        token_user_id = None
        if payload is not None:
            token_user_id = payload.get('user_id')

        if token_user_id is None:
            user = getattr(request, 'user', None)
            if user and getattr(user, 'is_authenticated', False):
                token_user_id = getattr(user, 'id', None)

        assignee = getattr(task, 'assignee', None)
        assignee_id = getattr(assignee, 'id', None) if assignee is not None else None

        try:
            if token_user_id is not None and assignee_id is not None and int(token_user_id) == int(assignee_id):
                return Response(TaskSerializer(task, context={'request': request}).data)
        except Exception:
            pass

        raise PermissionDenied(detail='Not authorized to view this task')