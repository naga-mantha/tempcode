import json
import logging
from typing import Any, Dict

from django.http import HttpRequest

logger = logging.getLogger(__name__)


def parse_json_body(request: HttpRequest) -> Dict[str, Any]:
    try:
        if request.body and request.content_type and "application/json" in request.content_type:
            return json.loads(request.body.decode("utf-8"))
        if request.body and not request.content_type:
            # Some fetches may omit content-type; try best-effort
            return json.loads(request.body.decode("utf-8"))
    except Exception as exc:
        body_len = len(request.body or b"")
        ctype = request.content_type or ""
        logger.warning("JSON parse failed: %s (len=%s, ctype=%s)", exc, body_len, ctype)
    return {}
