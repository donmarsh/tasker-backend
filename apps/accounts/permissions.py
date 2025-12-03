from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Allow access only to users with an active 'admin' role.

    Checks the authenticated user's `role` FK for an
    active role named 'admin'. If `request.user` is not populated
    (cookie->header middleware may not have run), it will also look
    in `request.auth` (JWT payload) for a `roles` claim.
    """

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)

        if user and getattr(user, 'is_authenticated', False):
            try:
                role = getattr(user, 'role', None)
                if role is not None and getattr(role, 'deleted_at', None) is None:
                    return str(role.name).lower() == 'admin'
                return False
            except Exception:
                return False

        # Fallback: check token payload for single `role` object or legacy `roles`
        token = getattr(request, 'auth', None)
        if token is not None:
            payload = None
            if isinstance(token, dict):
                payload = token
            else:
                payload = getattr(token, 'payload', None) or {}

            # Prefer single-role object
            role_obj = payload.get('role')
            if isinstance(role_obj, dict):
                name = role_obj.get('role_name') or role_obj.get('name')
                return str(name or '').lower() == 'admin'
            if isinstance(role_obj, str):
                return role_obj.lower() == 'admin'

            # Backwards-compat: look for `roles` array
            roles = payload.get('roles') or []
            if isinstance(roles, (list, tuple)):
                return any(str(r).lower() == 'admin' for r in roles)
            elif isinstance(roles, str):
                return roles.lower() == 'admin'

        return False
