"""
Automated Data Analysis and KPI Calculation Module.
Dynamically computes business performance KPIs, 5-number statistical profiles,
variance metrics, and multi-dimensional aggregations.
"""
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from src.logger import log_event


def calculate_kpis(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Dynamically discover and calculate relevant business KPIs based on available columns.
    
    Returns:
        Dictionary of formatted KPI metrics and cards.
    """
    if df is None or df.empty:
        return {}

    kpis: Dict[str, Any] = {}
    total_records = len(df)
    kpis["total_records"] = {
        "label": "Total Records",
        "value": f"{total_records:,}",
        "raw": total_records,
        "description": "Total active rows in processed dataset"
    }

    # 1. Revenue / Sales Metrics
    rev_col = _find_col(df, ["calculated_revenue", "net_revenue", "revenue", "gross_revenue", "total_amount", "sales", "amount"])
    if rev_col and pd.api.types.is_numeric_dtype(df[rev_col]):
        total_rev = float(df[rev_col].sum())
        avg_rev = float(df[rev_col].mean())
        max_rev = float(df[rev_col].max())
        min_rev = float(df[rev_col].min())

        kpis["total_revenue"] = {
            "label": "Total Revenue / Sales",
            "value": f"${total_rev:,.2f}" if total_rev > 0 else f"{total_rev:,.2f}",
            "raw": total_rev,
            "description": f"Cumulative sum of '{rev_col}'"
        }
        kpis["average_order_value"] = {
            "label": "Average Order Value",
            "value": f"${avg_rev:,.2f}",
            "raw": avg_rev,
            "description": f"Average ticket size from '{rev_col}'"
        }
        kpis["max_transaction"] = {
            "label": "Max Transaction",
            "value": f"${max_rev:,.2f}",
            "raw": max_rev,
            "description": f"Highest recorded value in '{rev_col}'"
        }

    # 2. Volume / Quantity Metrics
    qty_col = _find_col(df, ["quantity", "qty", "units_sold", "volume"])
    if qty_col and pd.api.types.is_numeric_dtype(df[qty_col]):
        total_qty = float(df[qty_col].sum())
        avg_qty = float(df[qty_col].mean())
        kpis["total_quantity"] = {
            "label": "Total Units Sold",
            "value": f"{int(total_qty):,}",
            "raw": total_qty,
            "description": f"Total volume from '{qty_col}'"
        }

    # 3. Profit & Margin Metrics
    profit_col = _find_col(df, ["gross_profit", "net_profit", "profit"])
    if profit_col and pd.api.types.is_numeric_dtype(df[profit_col]):
        total_profit = float(df[profit_col].sum())
        kpis["total_profit"] = {
            "label": "Total Gross Profit",
            "value": f"${total_profit:,.2f}",
            "raw": total_profit,
            "description": f"Gross profit calculated from '{profit_col}'"
        }
        margin_col = _find_col(df, ["profit_margin_pct", "margin"])
        if margin_col and pd.api.types.is_numeric_dtype(df[margin_col]):
            avg_margin = float(df[margin_col].mean())
            kpis["average_margin"] = {
                "label": "Average Margin",
                "value": f"{avg_margin:.1f}%",
                "raw": avg_margin,
                "description": "Mean profit margin percentage"
            }

    # 4. Customer & People Metrics
    cust_col = _find_col(df, ["customer_id", "customer_name", "emp_id", "employee_name", "full_name", "client_id"])
    if cust_col:
        unique_custs = int(df[cust_col].nunique(dropna=True))
        kpis["unique_entities"] = {
            "label": "Unique Customers / Accounts",
            "value": f"{unique_custs:,}",
            "raw": unique_custs,
            "description": f"Distinct entities in '{cust_col}'"
        }

    # 5. Products / Categories
    item_col = _find_col(df, ["item", "product_name", "product", "sku", "job_title"])
    if item_col:
        unique_items = int(df[item_col].nunique(dropna=True))
        kpis["unique_products"] = {
            "label": "Unique Products / SKUs",
            "value": f"{unique_items:,}",
            "raw": unique_items,
            "description": f"Distinct offerings in '{item_col}'"
        }

    # 6. Top Category Performance
    cat_col = _find_col(df, ["product_category", "category", "department", "business_unit", "segment"])
    if cat_col:
        if rev_col and pd.api.types.is_numeric_dtype(df[rev_col]):
            top_cat_agg = df.groupby(cat_col)[rev_col].sum().sort_values(ascending=False)
            if not top_cat_agg.empty:
                top_cat_name = str(top_cat_agg.index[0])
                top_cat_val = float(top_cat_agg.iloc[0])
                share = (top_cat_val / total_rev * 100) if total_rev > 0 else 0
                kpis["top_category"] = {
                    "label": f"Top Category ({top_cat_name})",
                    "value": f"${top_cat_val:,.2f} ({share:.1f}%)",
                    "raw": top_cat_val,
                    "description": f"Leading contributor from '{cat_col}'"
                }
        else:
            top_cat_cnt = df[cat_col].value_counts()
            if not top_cat_cnt.empty:
                kpis["top_category"] = {
                    "label": f"Top Segment ({top_cat_cnt.index[0]})",
                    "value": f"{top_cat_cnt.iloc[0]:,} records",
                    "raw": int(top_cat_cnt.iloc[0]),
                    "description": f"Most frequent group in '{cat_col}'"
                }

    # 7. Period-over-Period Growth
    date_col = _find_col(df, ["month_year", "order_date", "signup_date", "fiscal_quarter", "hire_date"])
    if date_col and rev_col and pd.api.types.is_numeric_dtype(df[rev_col]):
        try:
            period_df = df.groupby(date_col)[rev_col].sum().reset_index()
            if len(period_df) >= 2:
                prev_p = period_df.iloc[-2][rev_col]
                curr_p = period_df.iloc[-1][rev_col]
                if prev_p > 0:
                    growth_rate = ((curr_p - prev_p) / prev_p) * 100
                    kpis["period_growth"] = {
                        "label": "Latest Period Growth",
                        "value": f"{growth_rate:+.1f}%",
                        "raw": round(growth_rate, 2),
                        "description": f"Growth between last two periods in '{date_col}'"
                    }
        except Exception:
            pass

    log_event("INFO", "ANALYZE", f"Calculated {len(kpis)} dynamic KPIs.")
    return kpis


def generate_statistical_summary(df: pd.DataFrame) -> pd.DataFrame:
    """
    Generate extended 5-number summary with mean, std dev, variance, skewness,
    and missing count for all numeric columns.
    """
    num_df = df.select_dtypes(include=[np.number])
    if num_df.empty:
        return pd.DataFrame()

    stats_list = []
    for col in num_df.columns:
        series = num_df[col].dropna()
        if series.empty:
            continue

        stats_list.append({
            "Column": col,
            "Count": int(series.count()),
            "Mean": round(float(series.mean()), 2),
            "Std Dev": round(float(series.std()), 2),
            "Min": round(float(series.min()), 2),
            "25% (Q1)": round(float(series.quantile(0.25)), 2),
            "Median (Q2)": round(float(series.median()), 2),
            "75% (Q3)": round(float(series.quantile(0.75)), 2),
            "Max": round(float(series.max()), 2),
            "IQR": round(float(series.quantile(0.75) - series.quantile(0.25)), 2),
            "Skewness": round(float(series.skew()), 2) if len(series) > 2 else 0.0,
            "Null Count": int(df[col].isna().sum())
        })

    return pd.DataFrame(stats_list)


def generate_aggregations(df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    """
    Generate grouped summaries across primary dimensions (Category, Region, Period, Status).
    """
    aggregations: Dict[str, pd.DataFrame] = {}
    if df is None or df.empty:
        return aggregations

    num_cols = list(df.select_dtypes(include=[np.number]).columns)
    val_col = _find_col(df, ["calculated_revenue", "net_revenue", "revenue", "gross_revenue", "total_amount", "salary", "annual_income", "quantity"])
    if not val_col and num_cols:
        val_col = num_cols[0]

    # 1. By Category / Department / Segment
    cat_col = _find_col(df, ["product_category", "category", "department", "business_unit", "customer_segment"])
    if cat_col:
        if val_col:
            agg_cat = df.groupby(cat_col).agg(
                Record_Count=(cat_col, "count"),
                Total_Value=(val_col, "sum"),
                Average_Value=(val_col, "mean")
            ).reset_index().sort_values(by="Total_Value", ascending=False)
            agg_cat["Share_Pct"] = ((agg_cat["Total_Value"] / agg_cat["Total_Value"].sum()) * 100).round(2)
            aggregations["by_category"] = agg_cat
        else:
            aggregations["by_category"] = df[cat_col].value_counts().reset_index(name="Record_Count")

    # 2. By Region / Location / City
    reg_col = _find_col(df, ["region", "location", "city", "country"])
    if reg_col:
        if val_col:
            agg_reg = df.groupby(reg_col).agg(
                Record_Count=(reg_col, "count"),
                Total_Value=(val_col, "sum"),
                Average_Value=(val_col, "mean")
            ).reset_index().sort_values(by="Total_Value", ascending=False)
            agg_reg["Share_Pct"] = ((agg_reg["Total_Value"] / agg_reg["Total_Value"].sum()) * 100).round(2)
            aggregations["by_region"] = agg_reg
        else:
            aggregations["by_region"] = df[reg_col].value_counts().reset_index(name="Record_Count")

    # 3. By Period / Time
    time_col = _find_col(df, ["order_month_year", "month_year", "order_year", "signup_month_year", "fiscal_quarter", "hire_year"])
    if time_col and val_col:
        agg_time = df.groupby(time_col).agg(
            Record_Count=(time_col, "count"),
            Total_Value=(val_col, "sum"),
            Average_Value=(val_col, "mean")
        ).reset_index().sort_values(by=time_col)
        aggregations["by_time"] = agg_time

    return aggregations


def _find_col(df: pd.DataFrame, keywords: List[str]) -> str:
    """Helper to locate exact or substring matching column in DataFrame."""
    for kw in keywords:
        for col in df.columns:
            if str(col).lower().strip() == kw:
                return col
    for kw in keywords:
        for col in df.columns:
            if kw in str(col).lower().strip():
                return col
    return ""
