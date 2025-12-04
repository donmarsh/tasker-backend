# apps/tasks/permissions.py
from rest_framework import permissions

class IsProjectMemberOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Primary rule for non-safe methods:
        # - If caller has role 'admin' or 'manager' (from token), allow.
        # - Otherwise, require that the token user's id matches the task assignee id.

        token = getattr(request, 'auth', None)
        payload = None
        if token is not None:
            if isinstance(token, dict):
                payload = token
            else:
                payload = getattr(token, 'payload', None) or {}

        # Check role from token (prefer single `role` object)
        if payload is not None:
            role_obj = payload.get('role')
            if isinstance(role_obj, dict):
                name = role_obj.get('role_name') or role_obj.get('name')
                if name and str(name).lower() in ('admin', 'manager'):
                    return True
            if isinstance(role_obj, str) and role_obj.lower() in ('admin', 'manager'):
                return True

            # Backwards compatibility: check `roles` array
            roles = payload.get('roles') or []
            if isinstance(roles, (list, tuple)):
                if any(str(r).lower() in ('admin', 'manager') for r in roles):
                    return True
            elif isinstance(roles, str) and roles.lower() in ('admin', 'manager'):
                return True

        # Not admin/manager: ensure token user id matches assignee id
        token_user_id = None
        if payload is not None:
            token_user_id = payload.get('user_id')

        # If token didn't provide user_id, fall back to request.user if available
        if token_user_id is None:
            user = getattr(request, 'user', None)
            if user and getattr(user, 'is_authenticated', False):
                token_user_id = getattr(user, 'id', None)

        assignee = getattr(obj, 'assignee', None)
        assignee_id = getattr(assignee, 'id', None) if assignee is not None else None

        try:
            if token_user_id is not None and assignee_id is not None:
                return int(token_user_id) == int(assignee_id)
        except Exception:
            return False

        return False