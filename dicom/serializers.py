from rest_framework import serializers
from dicom import models


class FileUploadSerializer(serializers.ModelSerializer):
    class Meta:
        model = models.DicomFile
        fields = ['file']
