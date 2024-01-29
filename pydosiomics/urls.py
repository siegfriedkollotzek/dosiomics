from django.urls import path
from . import views
from django.contrib.auth.views import LoginView


urlpatterns = [
    path('home/', views.home, name='home'),
    path('', views.index, name='index'),
    path('index/', views.index, name='index2'),
    path('video/', views.video, name='video'),

]