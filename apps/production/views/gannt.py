from django.shortcuts import render
from apps.common.models import ProductionOrderSchedule, ProductionOrderOperation
from apps.production.views.scheduling import try_schedule_operation, BACKWARD_PLANNING_ENGINE_FAIL
import plotly.express as px
import pandas as pd
from django.shortcuts import redirect



# This is to run and schedule the operations and it redirects to the gannt page
# Later add the same to the management commands, so that it can run automatically everyday
def run_scheduler(request):
    ProductionOrderSchedule.objects.all().delete()

    unscheduled_ops = ProductionOrderOperation.objects.filter(
        schedule__isnull=True
    ).order_by("priority", "required_end")   #Schedules operations with priority 1,2,3 etc..

    for op in unscheduled_ops:
        x = try_schedule_operation(op, direction="forward")

        if x == BACKWARD_PLANNING_ENGINE_FAIL:
            print(BACKWARD_PLANNING_ENGINE_FAIL)

    return redirect("gantt_view")

def gannt_page(request):
    schedule = ProductionOrderSchedule.df_objects.all()

    df = schedule.to_dataframe(fieldnames=['operation', 'machine', 'operation__operation', 'operation__labor','start_datetime', 'end_datetime'])

    fig = px.timeline(df, x_start="start_datetime", x_end="end_datetime", y="machine", color="operation__labor", text="operation__operation")
    fig.update_yaxes(autorange="reversed")

    fig = fig.to_html()
    return render(request, "gannt.html", context={"fig": fig})
