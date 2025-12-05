from django.db import migrations
from django.utils import timezone


def create_project_statuses(apps, schema_editor):
    ProjectStatus = apps.get_model('projects', 'ProjectStatus')
    now = timezone.now()
    statuses = ['todo', 'in progress', 'completed']

    for name in statuses:
        ProjectStatus.objects.update_or_create(
            name=name,
            defaults={
                'created_at': now,
                'modified_at': now,
                'deleted_at': None,
            },
        )


def reverse_code(apps, schema_editor):
    ProjectStatus = apps.get_model('projects', 'ProjectStatus')
    statuses = ['todo', 'in progress', 'completed']
    ProjectStatus.objects.filter(name__in=statuses).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('projects', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_project_statuses, reverse_code),
    ]
