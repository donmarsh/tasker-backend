# apps/projects/serializers.py
from rest_framework import serializers
from .models import Project, ProjectStatus

class ProjectStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProjectStatus
        fields = ['id', 'name']

class ProjectSerializer(serializers.ModelSerializer):
    created_by = serializers.ReadOnlyField(source='created_by.username')
    project_status = ProjectStatusSerializer(read_only=True)
    project_status_id = serializers.PrimaryKeyRelatedField(
        queryset=ProjectStatus.objects.all(),
        source='project_status',
        write_only=True,
        required=False,
        allow_null=True
    )

    class Meta:
        model = Project
        fields = [
            'id', 'name', 'project_start_date', 'project_end_date',
            'created_at', 'modified_at', 'deleted_at',
            'project_status', 'project_status_id', 'created_by'
        ]
        read_only_fields = ['created_at', 'modified_at', 'deleted_at', 'created_by']