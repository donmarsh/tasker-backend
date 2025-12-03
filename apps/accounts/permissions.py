from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    """Allow access only to users with an active 'admin' role.

    Checks the authenticated user's related `userrole_set` for an
    active role named 'admin'. If `request.user` is not populated
    (cookie->header middleware may not have run), it will also look
    in `request.auth` (JWT payload) for a `roles` claim.
    """

    def has_permission(self, request, view):
        user = getattr(request, 'user', None)

        if user and getattr(user, 'is_authenticated', False):
            try:
                return user.userrole_set.filter(deleted_at__isnull=True, role__name__iexact='admin').exists()
            except Exception:
                return False

        # Fallback: check token payload
        token = getattr(request, 'auth', None)
        if token is not None:
            payload = None
            if isinstance(token, dict):
                payload = token
            else:
                payload = getattr(token, 'payload', None) or {}

            roles = payload.get('roles') or []
            if isinstance(roles, (list, tuple)):
                return any(str(r).lower() == 'admin' for r in roles)
            elif isinstance(roles, str):
                return roles.lower() == 'admin'

        return False
