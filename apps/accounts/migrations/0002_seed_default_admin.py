from django.contrib.auth.hashers import make_password
from django.utils import timezone
from django.db import migrations


def create_default_admin(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    User = apps.get_model('accounts', 'User')

    now = timezone.now()

    roles = (
        (1, 'Admin'),
        (2, 'Manager'),
        (3, 'User'),
    )

    role_map = {}
    for role_id, role_name in roles:
        role_obj, _ = Role.objects.update_or_create(
            id=role_id,
            defaults={
                'name': role_name,
                'created_at': now,
                'modified_at': now,
                'deleted_at': None,
            },
        )
        role_map[role_id] = role_obj

    role = role_map[1]

    user_defaults = {
        'email': 'admin@example.com',
        'full_name': 'System Admin',
        'telephone': '+254700100200',
        'password': make_password('secret123'),
        'role': role,
        'created_at': now,
        'modified_at': now,
        'deleted_at': None,
    }

    user, created = User.objects.get_or_create(
        username='admin',
        defaults=user_defaults,
    )

    if not created:
        update_fields = {}
        for field, value in user_defaults.items():
            current = getattr(user, field, None)
            if field == 'password':
                # Avoid clobbering an existing password if already set
                if not current:
                    update_fields[field] = value
            elif current != value:
                update_fields[field] = value

        if update_fields:
            for field, value in update_fields.items():
                setattr(user, field, value)
            user.save(update_fields=list(update_fields.keys()))


def reverse_code(apps, schema_editor):
    User = apps.get_model('accounts', 'User')
    Role = apps.get_model('accounts', 'Role')

    try:
        user = User.objects.get(username='admin')
        user.delete()
    except User.DoesNotExist:
        pass

    Role.objects.filter(id__in=[1, 2, 3]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_admin, reverse_code),
    ]
