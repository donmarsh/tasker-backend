# apps/tasks/serializers.py
from rest_framework import serializers
from .models import Task, TaskStatus
from django.contrib.auth import get_user_model
from apps.projects.models import Project

User = get_user_model()

class TaskStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStatus
        fields = ['id', 'name']

class TaskSerializer(serializers.ModelSerializer):
    assignee = serializers.SerializerMethodField()
    assignee_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.all(),
        source='assignee',
        write_only=True,
        required=False,
        allow_null=True
    )
    project = serializers.SerializerMethodField()
    project_id = serializers.PrimaryKeyRelatedField(
        queryset=Project.objects.all(),
        source='project',
        write_only=True
    )
    status = TaskStatusSerializer(read_only=True)
    status_id = serializers.PrimaryKeyRelatedField(
        queryset=TaskStatus.objects.all(),
        source='status',
        write_only=True
    )

    class Meta:
        model = Task
        fields = [
            'id', 'title', 'description', 'status', 'status_id',
            'assignee', 'assignee_id', 'deadline', 'created_at', 'modified_at',
            'deleted_at', 'project', 'project_id'
        ]
        read_only_fields = ['created_at', 'modified_at', 'deleted_at']

    def get_project(self, obj):
        if obj.project is None:
            return None
        return {
            'id': getattr(obj.project, 'id', None),
            'name': getattr(obj.project, 'name', None)
        }

    def get_assignee(self, obj):
        if obj.assignee is None:
            return None
        return {
            'id': getattr(obj.assignee, 'id', None),
            'username': getattr(obj.assignee, 'username', None)
        }