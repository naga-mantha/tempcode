"""Views for the Blocks Demo app."""

from django.http import HttpRequest, HttpResponse


def healthcheck(_request: HttpRequest) -> HttpResponse:
    """Simple healthcheck endpoint for the demo app."""

    return HttpResponse("ok")
