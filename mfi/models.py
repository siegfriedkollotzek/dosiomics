from uuid import uuid4

from django.db import models


class Mfi(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    created = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='mfi')
    file_output = models.FileField(upload_to='mfi')
    log = models.TextField()
    status = models.CharField(
        max_length=255, default='started',
        choices=[('started', 'started'), ('finished', 'finished'), ('error', 'error')])

    def __str__(self):
        return f"{self.uuid}"

    class Meta:
        ordering = ('-created',)
