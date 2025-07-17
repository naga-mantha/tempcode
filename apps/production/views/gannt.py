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
    ).order_by("priority", "required_start")   #Schedules operations with priority 1,2,3 etc..

    for op in unscheduled_ops:
        try:
            try_schedule_operation(op, direction="forward")
        except:
            continue


    return redirect("gantt_view")

def gannt_page(request):
    schedule = ProductionOrderSchedule.df_objects.all()

    df = schedule.to_dataframe(fieldnames=['operation', 'machine', 'operation__operation', 'labor','start_datetime', 'end_datetime', 'operation__remaining_time'])
    df['op_and_remain'] = (df['operation'].astype(str) + ' (' + df['operation__remaining_time'].astype(str)) + ' hrs)'

    fig = px.timeline(df, x_start="start_datetime", x_end="end_datetime", y="machine", color="labor", text="op_and_remain",
                      color_discrete_sequence=px.colors.qualitative.Set2, custom_data=df[["operation", "labor"]])
    # 3) force the text to appear inside each bar
    fig.update_traces(
        texttemplate="%{text}",
        textposition="inside",
        textangle = 0,
        textfont = dict(
            size=16,
            family="Arial, sans-serif"
        ),
        marker_line_width=1,
        marker_line_color="black",
        opacity=1,
        width=0.8,
        hovertemplate=
        "<b>%{y}</b><br>" +
        "Order: %{customdata[0]}<br>" +
        "Labor: %{customdata[1]}<br>" +
        "Start: %{x}<br>"
    )

    start = df['start_datetime'].min()
    end = start + pd.Timedelta(days=1)
    fig.update_xaxes(
        autorange=False,
        range=[start, end],
    )


    fig.update_yaxes(autorange="reversed")

    fig.update_layout(template="ggplot2",  # or "plotly_white", "plotly_dark", "ggplot2", etc.
                      # width=1500,
                      height=900,
                      margin=dict(l=50, r=50, t=50, b=50),
                      title="Master Production Schedule",
                      dragmode="pan"
                      )

    fig = fig.to_html(config={"responsive": True,
                              "modeBarButtonsToRemove": ["zoom2d", "zoomIn2d", "zoomOut2d", "autoScale2d"],
                              "scrollZoom": True})
    return render(request, "gannt.html", context={"fig": fig})
