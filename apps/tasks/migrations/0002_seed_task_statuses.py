from django.db import migrations
from django.utils import timezone


def create_task_statuses(apps, schema_editor):
    TaskStatus = apps.get_model('tasks', 'TaskStatus')
    now = timezone.now()
    statuses = ['todo', 'in progress', 'completed']

    for name in statuses:
        TaskStatus.objects.update_or_create(
            name=name,
            defaults={
                'created_at': now,
                'modified_at': now,
                'deleted_at': None,
            },
        )


def reverse_code(apps, schema_editor):
    TaskStatus = apps.get_model('tasks', 'TaskStatus')
    statuses = ['todo', 'in progress', 'completed']
    TaskStatus.objects.filter(name__in=statuses).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('tasks', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_task_statuses, reverse_code),
    ]
