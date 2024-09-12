from django.contrib.auth.decorators import login_required
from django.urls import path
from django.views.generic import TemplateView

from .views import FileUploadView, plot_control_point

urlpatterns = [
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('image/plotControlPoint/<uuid:file_uuid>/<int:beam>/<int:control_point>/',
         plot_control_point,
         name='plot-control-point'),
    path('app/', login_required(TemplateView.as_view(template_name='dicom/index.html')),
         name='dicom-app'),
]
