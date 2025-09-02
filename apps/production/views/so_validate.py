from django.shortcuts import render

from apps.common.models import SalesOrderLine, CustomerPurchaseOrder
import environ
import pandas as pd

env = environ.Env()
environ.Env.read_env()
host = env('HOST')

def so_validate(request):
    mai_orders = SalesOrderLine.df_objects.filter(sales_order__customer__name__icontains="Goodrich").values("item__code", "d2_date", "back_order")
    collins_orders = CustomerPurchaseOrder.df_objects.filter(customer="Collins").values("item__code", "d2_date", "back_order")

    fieldnames = ["item__code", "d2_date", "back_order"]
    collins_orders_df = collins_orders.to_dataframe(fieldnames=fieldnames)
    collins_orders_df["Company"] = "Collins"

    fieldnames = ["item__code", "d2_date", "back_order"]
    mai_orders_df = mai_orders.to_dataframe(fieldnames=fieldnames)
    mai_orders_df["Company"] = "MAI"

    combined_df = pd.concat([mai_orders_df, collins_orders_df], ignore_index=True)

    # Normalize column names
    combined_df = combined_df.rename(columns={"item__code": "Item", "d2_date": "d2_date", "back_order": "back_order"})

    # Ensure d2_date is a datetime and create month labels in MMYY while preserving chronological order
    combined_df["d2_date"] = pd.to_datetime(combined_df["d2_date"], errors="coerce")
    # Drop rows where date couldn't be parsed
    combined_df = combined_df.dropna(subset=["d2_date"]).copy()

    # Create a monthly period for sorting, and a display label MMYY
    combined_df["d2_period"] = combined_df["d2_date"].dt.to_period("M")
    combined_df["MMYY"] = combined_df["d2_period"].dt.strftime("%m%y")

    # Aggregate sums per Company, Item, MMYY
    grouped = (
        combined_df
        .groupby(["Company", "Item", "d2_period", "MMYY"], as_index=False)["back_order"].sum()
    )

    # Determine chronological column order by the period
    periods_sorted = (
        grouped[["d2_period", "MMYY"]]
        .drop_duplicates()
        .sort_values("d2_period")
    )
    columns_order = periods_sorted["MMYY"].tolist()

    # Pivot to get sums per Item and Company, columns by MMYY
    pivot_sum = grouped.pivot_table(
        index=["Item", "Company"],
        columns="MMYY",
        values="back_order",
        aggfunc="sum",
        fill_value=0,
    )

    # Reindex columns to chronological MMYY order
    pivot_sum = pivot_sum.reindex(columns=columns_order)

    # For each Item, produce rows for Collins, MAI, and Delta = Collins - MAI
    row_frames = []
    for item, df_item in pivot_sum.groupby(level=0):
        df_item_companies = df_item.droplevel(0)
        # Ensure both companies exist; fill missing with zeros
        df_item_companies = df_item_companies.reindex(["Collins", "MAI"]).fillna(0)

        # Collins and MAI rows
        for company in ["Collins", "MAI"]:
            row = df_item_companies.loc[company].to_frame().T
            row.insert(0, "Company", company)
            row.insert(0, "Item", item)
            row_frames.append(row)

        # Delta row (Collins - MAI) per month
        delta_row = (df_item_companies.loc["Collins"] - df_item_companies.loc["MAI"]).to_frame().T
        delta_row.insert(0, "Company", "Delta")
        delta_row.insert(0, "Item", item)
        row_frames.append(delta_row)

    display_df = pd.concat(row_frames, ignore_index=True) if row_frames else pd.DataFrame(columns=["Item", "Company"] + columns_order)

    table_html = display_df.to_html(index=False, classes="table table-striped table-sm", border=0)

    context = {
        "table_html": table_html,
        "host": host,
    }

    return render(request, "so_validate.html", context)
