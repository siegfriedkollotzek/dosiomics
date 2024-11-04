from django.urls import path

from mfi import views

urlpatterns = [
    path('', views.mfi, name='mfi'),
]