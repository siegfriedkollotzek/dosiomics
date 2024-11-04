from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import TemplateView

urlpatterns = [
    path('admin/', admin.site.urls),

    path('accounts/',
         include('django.contrib.auth.urls')),

    path('dicom/', include('dicom.urls')),
    path('mfi/', include('mfi.urls')),

    path('', TemplateView.as_view(template_name='home.html'), name='home'),

    path('video/', TemplateView.as_view(template_name='Sam_Video.html'), name='video'),
]

if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
