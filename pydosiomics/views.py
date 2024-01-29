from django.shortcuts import render
from datetime import datetime, time

def home(request):
    return render(request, 'home.html')

def index(request):
    return render(request, 'index.html')

def video(request):
    return render(request, 'Sam_Video.html')