from django.urls import path

from mfi import views

urlpatterns = [
    path('', views.mfi_form, name='mfi'),
    path('<uuid:uuid>/', views.mfi_status, name='mfi-status'),
    path('download/<uuid:uuid>/', views.mfi_download, name='mfi-download'),
]
