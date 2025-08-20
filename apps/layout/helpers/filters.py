from typing import Mapping, Any

from django.http import QueryDict, HttpRequest


def build_namespaced_get(request: HttpRequest, ns: str, values: Mapping[str, Any]) -> QueryDict:
    """Return a QueryDict copy of request.GET with `values` injected under a namespace.

    Example: ns="Table__42__filters." and values={"status": [1,2], "active": True}
    yields GET keys like "Table__42__filters.status" with appropriate stringified values.
    """
    qd = request.GET.copy()
    prefix = ns or ""
    for k, v in (values or {}).items():
        name = f"{prefix}{k}"
        if isinstance(v, (list, tuple)):
            qd.setlist(name, [str(x) for x in v])
        elif isinstance(v, bool):
            qd[name] = "1" if v else "0"
        elif v is not None:
            qd[name] = str(v)
    return qd

