# apps/tasks/models.py
from django.db import models
from django.contrib.auth import get_user_model
from apps.projects.models import Project

User = get_user_model()


class TaskStatus(models.Model):
    id = models.IntegerField(primary_key=True)
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField()
    modified_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tbl_task_status'
        app_label = 'tasks'
        managed = False   # ← THIS IS KEY: tells Django "don't touch this table"

    def __str__(self):
        return self.name


class Task(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100)
    description = models.CharField(max_length=500)
    deadline = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    modified_at = models.DateTimeField(auto_now=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    status = models.ForeignKey(
        TaskStatus,
        on_delete=models.CASCADE,
        db_column='status_id'
    )
    assignee = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_tasks',
        db_column='assignee_id'
    )
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='tasks',
        db_column='project_id'
    )
    # Note: legacy `tbl_tasks` does not include a `created_by` column.
    # We do not model it here to match the existing schema.


    class Meta:
        db_table = 'tbl_tasks'
        app_label = 'tasks'
        managed = False   # ← Django won't try to create or modify this table
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def delete(self, *args, **kwargs):
        self.deleted_at = models.functions.Now()
        self.save(update_fields=['deleted_at'])