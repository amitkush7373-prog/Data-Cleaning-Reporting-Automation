"""
Data Transformation & Feature Engineering Module.
Performs context-aware transformations, date extraction, calculated business metrics,
and categorical binning based on available columns.
"""
from typing import Dict, Any, Tuple
import pandas as pd
import numpy as np
from src.logger import log_event


def transform_data(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Apply intelligent feature engineering and domain transformations.
    
    Returns:
        Tuple of (Transformed DataFrame, Dictionary of transformations created)
    """
    transformed_df = df.copy()
    transformations_applied: Dict[str, str] = {}

    # -------------------------------------------------------------
    # 1. Date & Time Feature Extraction
    # -------------------------------------------------------------
    date_cols = transformed_df.select_dtypes(include=["datetime", "datetimetz"]).columns
    for col in date_cols:
        col_prefix = str(col).replace("_date", "").replace("date", "").strip("_")
        prefix = f"{col_prefix}_" if col_prefix else ""

        year_col = f"{prefix}year"
        month_col = f"{prefix}month"
        quarter_col = f"{prefix}quarter"
        month_year_col = f"{prefix}month_year"
        day_name_col = f"{prefix}day_name"
        weekend_col = f"{prefix}is_weekend"

        if year_col not in transformed_df.columns:
            transformed_df[year_col] = transformed_df[col].dt.year
            transformations_applied[year_col] = f"Extracted calendar year from '{col}'"

        if month_col not in transformed_df.columns:
            transformed_df[month_col] = transformed_df[col].dt.month
            transformations_applied[month_col] = f"Extracted month number (1-12) from '{col}'"

        if quarter_col not in transformed_df.columns:
            transformed_df[quarter_col] = transformed_df[col].dt.to_period("Q").astype(str)
            transformations_applied[quarter_col] = f"Extracted fiscal quarter from '{col}'"

        if month_year_col not in transformed_df.columns:
            transformed_df[month_year_col] = transformed_df[col].dt.strftime("%Y-%m")
            transformations_applied[month_year_col] = f"Extracted YYYY-MM period from '{col}'"

        if day_name_col not in transformed_df.columns:
            transformed_df[day_name_col] = transformed_df[col].dt.day_name()
            transformations_applied[day_name_col] = f"Extracted day of week name from '{col}'"

        if weekend_col not in transformed_df.columns:
            transformed_df[weekend_col] = transformed_df[col].dt.dayofweek.isin([5, 6])
            transformations_applied[weekend_col] = f"Extracted weekend boolean flag from '{col}'"

    # -------------------------------------------------------------
    # 2. Sales & Commerce Calculated Metrics
    # -------------------------------------------------------------
    # Revenue = Quantity * Unit Price
    qty_col = _find_matching_col(transformed_df, ["quantity", "qty", "units_sold", "volume"])
    price_col = _find_matching_col(transformed_df, ["unit_price", "price", "item_price", "rate"])
    
    if qty_col and price_col and pd.api.types.is_numeric_dtype(transformed_df[qty_col]) and pd.api.types.is_numeric_dtype(transformed_df[price_col]):
        rev_col = "calculated_revenue" if "revenue" in transformed_df.columns or "total_amount" in transformed_df.columns else "revenue"
        transformed_df[rev_col] = (transformed_df[qty_col] * transformed_df[price_col]).round(2)
        transformations_applied[rev_col] = f"Calculated Revenue = ({qty_col} × {price_col})"

        # Net Revenue if Discount exists
        disc_col = _find_matching_col(transformed_df, ["discount_pct", "discount", "discount_rate"])
        if disc_col and pd.api.types.is_numeric_dtype(transformed_df[disc_col]):
            # If discount is > 1 (e.g. 15 for 15%), convert to decimal rate
            disc_rate = transformed_df[disc_col].apply(lambda x: x / 100.0 if x > 1.0 else x)
            transformed_df["discount_amount"] = (transformed_df[rev_col] * disc_rate).round(2)
            transformed_df["net_revenue"] = (transformed_df[rev_col] - transformed_df["discount_amount"]).round(2)
            transformations_applied["net_revenue"] = f"Calculated Net Revenue after {disc_col}"

    # -------------------------------------------------------------
    # 3. Financial Profit & Margin Metrics
    # -------------------------------------------------------------
    rev_target = _find_matching_col(transformed_df, ["gross_revenue", "revenue", "sales", "net_revenue", "calculated_revenue"])
    cost_target = _find_matching_col(transformed_df, ["operating_cost", "cost", "total_cost", "cogs", "expenses"])

    if rev_target and cost_target and pd.api.types.is_numeric_dtype(transformed_df[rev_target]) and pd.api.types.is_numeric_dtype(transformed_df[cost_target]):
        if "profit" not in transformed_df.columns and "net_profit" not in transformed_df.columns:
            transformed_df["gross_profit"] = (transformed_df[rev_target] - transformed_df[cost_target]).round(2)
            # Avoid division by zero
            transformed_df["profit_margin_pct"] = np.where(
                transformed_df[rev_target] > 0,
                ((transformed_df["gross_profit"] / transformed_df[rev_target]) * 100).round(2),
                0.0
            )
            transformations_applied["gross_profit"] = f"Calculated Gross Profit = ({rev_target} - {cost_target})"
            transformations_applied["profit_margin_pct"] = f"Calculated Profit Margin % = (Profit / {rev_target} × 100)"

    # -------------------------------------------------------------
    # 4. Customer & People Data Transformations
    # -------------------------------------------------------------
    fn_col = _find_matching_col(transformed_df, ["first_name", "fname"])
    ln_col = _find_matching_col(transformed_df, ["last_name", "lname"])
    if fn_col and ln_col and "full_name" not in transformed_df.columns:
        transformed_df["full_name"] = (transformed_df[fn_col].fillna("") + " " + transformed_df[ln_col].fillna("")).str.strip()
        transformations_applied["full_name"] = f"Combined '{fn_col}' and '{ln_col}' into 'full_name'"

    # Credit Score Tiering
    credit_col = _find_matching_col(transformed_df, ["credit_score", "cibil_score"])
    if credit_col and pd.api.types.is_numeric_dtype(transformed_df[credit_col]) and "credit_tier" not in transformed_df.columns:
        bins = [-np.inf, 579, 669, 739, 799, np.inf]
        labels = ["Poor (<580)", "Fair (580-669)", "Good (670-739)", "Very Good (740-799)", "Exceptional (800+)"]
        transformed_df["credit_tier"] = pd.cut(transformed_df[credit_col], bins=bins, labels=labels)
        transformations_applied["credit_tier"] = f"Binned '{credit_col}' into standardized credit rating tiers"

    # Experience Level Tiering
    exp_col = _find_matching_col(transformed_df, ["experience_yrs", "experience", "years_experience", "tenure"])
    if exp_col and pd.api.types.is_numeric_dtype(transformed_df[exp_col]) and "experience_level" not in transformed_df.columns:
        bins = [-np.inf, 2, 5, 10, np.inf]
        labels = ["Junior (0-2 yrs)", "Mid-Level (3-5 yrs)", "Senior (6-10 yrs)", "Lead/Principal (10+ yrs)"]
        transformed_df["experience_level"] = pd.cut(transformed_df[exp_col], bins=bins, labels=labels)
        transformations_applied["experience_level"] = f"Binned '{exp_col}' into professional experience levels"

    log_event("SUCCESS", "TRANSFORM", f"Applied {len(transformations_applied)} feature engineering transformations.")
    return transformed_df, transformations_applied


def _find_matching_col(df: pd.DataFrame, keywords: list) -> str:
    """Helper to find column by list of candidate names or substrings."""
    for kw in keywords:
        for col in df.columns:
            col_clean = str(col).lower().strip()
            if col_clean == kw:
                return col
    # Fallback to substring matching
    for kw in keywords:
        for col in df.columns:
            col_clean = str(col).lower().strip()
            if kw in col_clean:
                return col
    return ""
