from collections import defaultdict
from django.shortcuts import render
from django.http import HttpRequest, HttpResponse
from apps.common.models import Roadmap


def roadmap_list(request: HttpRequest) -> HttpResponse:
    sort = request.GET.get("sort", "timeframe")
    status = request.GET.get("status", "all")

    qs = Roadmap.objects.all()
    if status in {Roadmap.Status.PLANNED, Roadmap.Status.IN_PROGRESS, Roadmap.Status.COMPLETED}:
        qs = qs.filter(status=status)

    groups = []
    title = "Roadmap by Timeframe" if sort == "timeframe" else "Roadmap by App"

    if sort == "app":
        grouped = defaultdict(list)
        for item in qs.order_by("app", "timeframe", "title"):
            grouped[item.app].append(item)
        for key in sorted(grouped.keys()):
            groups.append({"name": key, "items": grouped[key]})
    else:
        # default by timeframe Q1..Q4 in order
        order = [Roadmap.Timeframe.Q1, Roadmap.Timeframe.Q2, Roadmap.Timeframe.Q3, Roadmap.Timeframe.Q4]
        grouped = {k: [] for k in order}
        for item in qs.order_by("timeframe", "app", "title"):
            grouped[item.timeframe].append(item)
        for key in order:
            groups.append({"name": key, "items": grouped[key]})

    context = {
        "title": title,
        "groups": groups,
        "sort": sort,
        "status": status,
        "status_choices": [
            ("all", "All"),
            (Roadmap.Status.PLANNED, "Planned"),
            (Roadmap.Status.IN_PROGRESS, "In Progress"),
            (Roadmap.Status.COMPLETED, "Completed"),
        ],
    }
    return render(request, "roadmap/list.html", context)

