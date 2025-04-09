from django.contrib import admin

from mfi.models import Mfi


@admin.register(Mfi)
class MfiAdmin(admin.ModelAdmin):
    list_display = ['uuid', 'created', 'status']
    ordering = ['-created']
