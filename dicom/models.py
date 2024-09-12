from uuid import uuid4

from django.contrib.auth.models import User
from django.db import models


class DicomFile(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid4, editable=False)
    uploaded_by = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    file = models.FileField(upload_to='dicom/')
