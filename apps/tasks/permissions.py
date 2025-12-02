# apps/tasks/permissions.py
from rest_framework import permissions

class IsProjectMemberOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        # Must be in the project (as member or owner)
        return obj.project.created_by == request.user or request.user in obj.project.members.all()