from __future__ import annotations

from django.http import HttpResponse
from django.urls import path


def ping(_request):
    return HttpResponse("layouts v2 ok", content_type="text/plain")


app_name = "layout_v2"

urlpatterns = [
    path("ping", ping, name="ping"),
]

