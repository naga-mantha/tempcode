"""
URL configuration for mag360 project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.urls import include
from django.urls import re_path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('django.contrib.auth.urls')),
    path(r'comments/', include('django_comments_xtd.urls')),
    path('', include('apps.common.urls')),
    path('', include('apps.production.urls')),
    path('workflow/', include('apps.workflow.urls')),
    # Versioned mount for current Blocks implementation
    path('blocks/v1/', include('apps.blocks.urls')),
    # V2 mount (rewrite). Safe to add alongside v1.
    path('blocks/v2/', include('apps_v2.blocks.urls')),
    # Temporary compatibility redirect: /blocks/* -> /blocks/v1/*
    # Remove this once v2 is mounted at /blocks/
    re_path(r'^blocks/(?P<rest>.*)$', RedirectView.as_view(url='/blocks/v1/%(rest)s', permanent=False)),
    # Versioned mount for current Layouts implementation
    path('layouts/v1/', include('apps.layout.urls')),
    # V2 mount (rewrite). Safe to add alongside v1.
    path('layouts/v2/', include('apps_v2.layout.urls')),
    # Temporary compatibility redirect: /layouts/* -> /layouts/v1/*
    # Remove this once v2 is mounted at /layouts/
    re_path(r'^layouts/(?P<rest>.*)$', RedirectView.as_view(url='/layouts/v1/%(rest)s', permanent=False)),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
