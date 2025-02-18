from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings

# Custom User Model
class CustomUser(AbstractUser):
    email = models.EmailField(unique=True)  # Ensure email is unique

# User Profile Model
class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

# Settings Model
class Settings(models.Model):
    type = models.CharField(max_length=100)
    value = models.TextField()

# Metadata Model
class Metadata(models.Model):
    table_name = models.CharField(max_length=100)
    metadata_json = models.JSONField()
    created_at = models.DateTimeField(auto_now_add=True)

# Audit Log Model
class AuditLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
