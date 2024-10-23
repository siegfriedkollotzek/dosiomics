from django.db import models


class MfiLog(models.Model):
    datetime = models.DateTimeField()
    filename = models.CharField(max_length=255)
    log = models.TextField()
