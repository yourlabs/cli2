from django.db import models


class Object(models.Model):
    name = models.CharField(max_length=100, unique=True)
    data = models.JSONField(default=dict, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
