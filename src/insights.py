"""
Automated Narrative Insights & Recommendations Engine.
Generates factual, calculation-backed data quality insights, business findings,
and strategic data governance recommendations.
"""
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from src.logger import log_event


def generate_insights(
    raw_validation: Dict[str, Any],
    clean_validation: Dict[str, Any],
    audit_log: Dict[str, Any],
    kpis: Dict[str, Any],
    aggregations: Dict[str, pd.DataFrame]
) -> Dict[str, List[str]]:
    """
    Produce structured narrative findings and recommendations.
    
    Returns:
        Dictionary with:
        - 'quality_insights': Bulleted data hygiene & cleaning observations
        - 'business_insights': Bulleted quantitative business findings
        - 'anomaly_insights': Outlier and distribution observations
        - 'recommendations': Actionable next steps
    """
    quality_insights: List[str] = []
    business_insights: List[str] = []
    anomaly_insights: List[str] = []
    recommendations: List[str] = []

    # -------------------------------------------------------------
    # 1. Data Quality & Cleaning Insights
    # -------------------------------------------------------------
    raw_score = raw_validation.get("quality_score", 0.0)
    clean_score = clean_validation.get("quality_score", 100.0)
    raw_grade = raw_validation.get("quality_grade", "N/A")
    clean_grade = clean_validation.get("quality_grade", "N/A")
    
    quality_insights.append(
        f"Overall Data Health Score improved from {raw_score}/100 [{raw_grade}] to {clean_score}/100 [{clean_grade}]."
    )

    raw_missing = raw_validation.get("missing_report", {}).get("total_missing", 0)
    clean_missing = clean_validation.get("missing_report", {}).get("total_missing", 0)
    if raw_missing > 0:
        imputed_count = raw_missing - clean_missing
        quality_insights.append(
            f"Resolved {imputed_count:,} missing values across {len(audit_log.get('missing_imputed', {}))} columns using statistical imputation strategies."
        )
    else:
        quality_insights.append("Dataset contained zero missing values initially.")

    dups_removed = audit_log.get("duplicates_removed", 0)
    if dups_removed > 0:
        quality_insights.append(
            f"Eliminated {dups_removed:,} exact duplicate rows, preventing skewed metrics and double-counting."
        )

    types_converted = audit_log.get("types_converted", {})
    if types_converted:
        quality_insights.append(
            f"Successfully standardized data types for {len(types_converted)} columns (including currency symbol stripping, date parsing, and boolean normalization)."
        )

    cols_standardized = len(audit_log.get("column_renaming", {}))
    if cols_standardized > 0:
        quality_insights.append(
            f"Standardized {cols_standardized} column headers into consistent snake_case format for SQL/pipeline compatibility."
        )

    # -------------------------------------------------------------
    # 2. Business KPI & Performance Insights
    # -------------------------------------------------------------
    if "total_revenue" in kpis:
        business_insights.append(
            f"Total cumulative revenue / sales volume stands at {kpis['total_revenue']['value']} across {kpis.get('total_records', {}).get('value', 'all')} transactions."
        )

    if "average_order_value" in kpis:
        business_insights.append(
            f"Average Order Value (AOV) was calculated at {kpis['average_order_value']['value']} per transaction."
        )

    # Category insights
    if "by_category" in aggregations and not aggregations["by_category"].empty:
        cat_df = aggregations["by_category"]
        top_row = cat_df.iloc[0]
        cat_name = top_row.iloc[0]
        if "Share_Pct" in cat_df.columns:
            share = top_row["Share_Pct"]
            val = top_row.get("Total_Value", 0)
            business_insights.append(
                f"Top contributing category is '{cat_name}' accounting for {share:.1f}% of total volume (${val:,.2f})."
            )
            if share > 50:
                business_insights.append(
                    f"Noticeable concentration risk: '{cat_name}' commands over half of the entire dataset revenue."
                )

    # Region insights
    if "by_region" in aggregations and not aggregations["by_region"].empty:
        reg_df = aggregations["by_region"]
        top_reg = reg_df.iloc[0]
        reg_name = top_reg.iloc[0]
        if "Share_Pct" in reg_df.columns:
            reg_share = top_reg["Share_Pct"]
            business_insights.append(
                f"Regional distribution is led by '{reg_name}' generating {reg_share:.1f}% of activity."
            )

    if "period_growth" in kpis:
        business_insights.append(
            f"Latest period performance demonstrated a growth rate of {kpis['period_growth']['value']}."
        )

    # -------------------------------------------------------------
    # 3. Outlier & Distribution Insights
    # -------------------------------------------------------------
    outlier_rep = audit_log.get("outlier_detection", {})
    if outlier_rep:
        for col, o_info in outlier_rep.items():
            cnt = o_info.get("outlier_count", 0)
            pct = o_info.get("outlier_pct", 0)
            upper = o_info.get("upper_bound", 0)
            anomaly_insights.append(
                f"Identified {cnt} statistical outlier values in '{col}' ({pct}% of rows) exceeding upper threshold of {upper:,.2f}."
            )
    else:
        anomaly_insights.append("No severe numerical outliers detected under IQR thresholding (1.5x IQR).")

    # -------------------------------------------------------------
    # 4. Strategic Recommendations
    # -------------------------------------------------------------
    if raw_missing > 0:
        recommendations.append(
            "Implement frontend form validation at data entry to mandate required fields and eliminate downstream missing values."
        )

    if dups_removed > 0:
        recommendations.append(
            "Enforce database UNIQUE constraints on transactional ID fields to prevent duplicate records at ingestion."
        )

    if types_converted:
        recommendations.append(
            "Enforce strict schema typing at the ingestion pipeline to avoid storing raw currency symbols and unformatted strings in numeric fields."
        )

    if "by_category" in aggregations and not aggregations["by_category"].empty:
        cat_df = aggregations["by_category"]
        if len(cat_df) > 1 and "Share_Pct" in cat_df.columns:
            bottom_row = cat_df.iloc[-1]
            recommendations.append(
                f"Evaluate marketing and promotional strategies for lower-performing category '{bottom_row.iloc[0]}' ({bottom_row['Share_Pct']:.1f}% share) to balance portfolio revenue."
            )

    recommendations.append(
        "Schedule automated daily/weekly runs of this cleaning pipeline to monitor data health drift over time."
    )

    log_event("SUCCESS", "INSIGHTS", f"Generated {len(quality_insights)} quality, {len(business_insights)} business, and {len(recommendations)} recommendation points.")

    return {
        "quality_insights": quality_insights,
        "business_insights": business_insights if business_insights else ["Metrics computed across active attributes."],
        "anomaly_insights": anomaly_insights,
        "recommendations": recommendations
    }
