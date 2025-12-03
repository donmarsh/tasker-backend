# apps/tasks/serializers.py
from rest_framework import serializers
from .models import Task, TaskStatus

class TaskStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaskStatus
        fields = ['id', 'name']

class TaskSerializer(serializers.ModelSerializer):
    assignee = serializers.ReadOnlyField(source='assignee.username' if hasattr(serializers.ReadOnlyField, 'source') else 'assignee.username')
    project = serializers.ReadOnlyField(source='project.name')
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
            'assignee', 'deadline', 'created_at', 'modified_at',
            'deleted_at', 'project'
        ]
        read_only_fields = ['created_at', 'modified_at', 'deleted_at']