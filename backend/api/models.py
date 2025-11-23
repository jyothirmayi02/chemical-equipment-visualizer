from django.db import models
from django.contrib.postgres.fields import ArrayField  # if using Postgres; for SQLite we’ll just store JSON
from django.utils import timezone
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import JSONField

class Dataset(models.Model):
    name = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(default=timezone.now)
    original_file = models.FileField(upload_to='uploads/')
    summary = JSONField(encoder=DjangoJSONEncoder)  # store stats as JSON
    # optional: store few rows preview
    preview_rows = JSONField(encoder=DjangoJSONEncoder, null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        # Keep only last 5 datasets
        qs = Dataset.objects.order_by('-uploaded_at')
        if qs.count() > 5:
            for obj in qs[5:]:
                obj.delete()

    def __str__(self):
        return f"{self.name} ({self.uploaded_at})"
