# apps/projects/models.py
from django.db import models
from django.contrib.auth import get_user_model

User = get_user_model()

class ProjectStatus(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=50)
    created_at = models.DateTimeField(null=True, blank=True)
    modified_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tbl_project_status'
        managed = True

    def __str__(self):
        return self.name


class Project(models.Model):
    id = models.AutoField(primary_key=True)  # DB uses autoincrement
    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500)
    project_start_date = models.DateTimeField()
    project_end_date = models.DateTimeField()
    created_at = models.DateTimeField(null=True, blank=True)
    modified_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    project_status = models.ForeignKey(
        ProjectStatus,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        db_column='project_status_id'
    )
    
    created_by = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='projects',
        db_column='created_by'
    )
    

    class Meta:
        db_table = 'tbl_projects'
        ordering = ['-created_at']
        managed = True

    def __str__(self):
        return self.name

    # Soft delete
    def delete(self, *args, **kwargs):
        self.deleted_at = models.functions.Now()
        self.save(update_fields=['deleted_at'])

    def restore(self):
        self.deleted_at = None
        self.save(update_fields=['deleted_at'])