# apps/accounts/models.py
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone

# Custom User Manager
class UserManager(BaseUserManager):
    def create_user(self, username, email, password=None, **extra_fields):
        if not username:
            raise ValueError('Username is required')
        if not email:
            raise ValueError('Email is required')
        
        email = self.normalize_email(email)
        user = self.model(username=username, email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(username, email, password, **extra_fields)


# Your real tbl_users table
class User(AbstractBaseUser, PermissionsMixin):
    id = models.AutoField(primary_key=True)
    telephone = models.CharField(max_length=20)
    email = models.CharField(max_length=100, unique=True)
    full_name = models.CharField(max_length=100)
    username = models.CharField(max_length=100, unique=True)
    # Single-role now stored on the users table as `role_id` FK
    role = models.ForeignKey('Role', on_delete=models.SET_NULL, null=True, blank=True, db_column='role_id')
    reset_token = models.CharField(max_length=20, null=True, blank=True)
    reset_expiry = models.DateTimeField(null=True, blank=True)
    password = models.CharField(max_length=256)
    created_at = models.DateTimeField()
    deleted_at = models.DateTimeField(null=True, blank=True)
    modified_at = models.DateTimeField(null=True, blank=True)

    # Expose auth attributes as properties so Django's authentication
    # treats legacy rows correctly (without changing DB schema).
    def _last_login(self):
        return None

    def _is_active(self):
        return self.deleted_at is None

    def _is_staff(self):
        return False

    def _is_superuser(self):
        return False

    last_login = property(_last_login)
    is_active = property(_is_active)
    is_staff = property(_is_staff)
    is_superuser = property(_is_superuser)

    objects = UserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email', 'full_name',]

    class Meta:
        db_table = 'tbl_users'
        managed = True
        app_label = 'accounts'

    def __str__(self):
        return self.username


# Your real roles & permissions
class Role(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(null=True, blank=True)
    modified_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tbl_roles'
        managed = True
        app_label = 'accounts'

    def __str__(self):
        return self.name

class UserRole(models.Model):
    id = models.IntegerField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, db_column='user_id')
    role = models.ForeignKey(Role, on_delete=models.CASCADE, db_column='role_id')
    created_at = models.DateTimeField(null=True, blank=True)
    modified_at = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'tbl_user_roles'
        managed = True
        app_label = 'accounts'
        unique_together = ('user', 'role')


