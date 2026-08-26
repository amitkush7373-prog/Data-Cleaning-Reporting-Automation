"""
Automatic and Configurable Data Cleaning Pipeline Module.
Implements standardized naming, duplicate removal, currency/type conversion,
missing value imputation, categorical normalization, outlier handling,
and complete audit log generation.
"""
import re
from typing import Dict, Any, List, Optional, Tuple, Union
import pandas as pd
import numpy as np
from src.logger import log_event


def standardize_column_names(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Standardize all column names into clean snake_case format.
    - Strips whitespace
    - Replaces symbols (%, #, $, etc.) with descriptive text or underscores
    - Resolves collisions with suffixes (_1, _2)
    
    Returns:
        Tuple of (DataFrame with new columns, mapping dictionary of old_name -> new_name)
    """
    cleaned_df = df.copy()
    mapping = {}
    seen_names = {}

    for col in cleaned_df.columns:
        original = str(col)
        # Handle symbols
        s = original.strip()
        s = s.replace("%", " pct ").replace("#", " num ").replace("$", " usd ").replace("₹", " inr ")
        s = s.replace("&", " and ").replace("@", " at ").replace("/", "_").replace("\\", "_")
        # Replace non-alphanumeric with underscore
        s = re.sub(r"[^\w\s]", "_", s)
        # Convert to snake_case
        s = re.sub(r"[\s_]+", "_", s).strip("_").lower()
        if not s:
            s = "unnamed_column"

        # Avoid collisions
        if s in seen_names:
            seen_names[s] += 1
            final_name = f"{s}_{seen_names[s]}"
        else:
            seen_names[s] = 0
            final_name = s

        mapping[original] = final_name

    cleaned_df.rename(columns=mapping, inplace=True)
    return cleaned_df, mapping


def remove_duplicates(df: pd.DataFrame, subset: Optional[List[str]] = None) -> Tuple[pd.DataFrame, int, int]:
    """
    Remove duplicate rows from dataset.
    
    Returns:
        Tuple of (Cleaned DataFrame, duplicates_removed_count, remaining_rows_count)
    """
    initial_count = len(df)
    cleaned_df = df.drop_duplicates(subset=subset).copy()
    removed = initial_count - len(cleaned_df)
    return cleaned_df, removed, len(cleaned_df)


def standardize_data_types(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Automatically detect and convert messy data types:
    - Currency strings (₹, $, €, £, commas) -> Float / Int
    - Percentages (15%) -> Float (15.0 or 0.15)
    - Date strings -> Datetime (coercing invalid values to NaT)
    - Boolean strings (yes/no, true/false) -> Boolean
    """
    cleaned_df = df.copy()
    converted_cols = {}
    currency_regex = re.compile(r"[\$₹€£¥,\s]")

    for col in cleaned_df.columns:
        # Check if already numeric or datetime
        if pd.api.types.is_numeric_dtype(cleaned_df[col]) or pd.api.types.is_datetime64_any_dtype(cleaned_df[col]):
            continue

        series = cleaned_df[col].dropna()
        if series.empty:
            continue

        # Convert to string for regex checks
        str_series = series.astype(str).str.strip()

        # 1. Test Currency / Percentage / Comma-separated numbers
        # Filter out obvious non-numeric text
        cleaned_str = str_series.apply(lambda x: currency_regex.sub("", str(x)))
        # Check if percentage
        is_pct = str_series.str.endswith("%").sum() / len(str_series) > 0.5
        if is_pct:
            cleaned_str = cleaned_str.str.replace("%", "", regex=False)

        numeric_success = pd.to_numeric(cleaned_str, errors="coerce")
        valid_ratio = numeric_success.notna().sum() / len(series)

        if valid_ratio >= 0.75:
            # Apply numeric conversion across entire column
            col_cleaned = cleaned_df[col].astype(str).apply(lambda x: currency_regex.sub("", str(x)).replace("%", "") if pd.notna(x) else x)
            # Retain NaN
            converted_num = pd.to_numeric(col_cleaned, errors="coerce")
            cleaned_df[col] = converted_num
            converted_cols[col] = "Float (Cleaned from Currency/Formatted Text)"
            continue

        # 2. Test Datetime conversion
        date_candidates = str_series.head(50)
        date_match_count = sum(1 for v in date_candidates if _is_date_string(v))
        if date_match_count / len(date_candidates) >= 0.6:
            try:
                parsed_dates = pd.to_datetime(cleaned_df[col], errors="coerce", format="mixed")
            except Exception:
                parsed_dates = pd.to_datetime(cleaned_df[col], errors="coerce")
            if parsed_dates.notna().sum() / len(series) >= 0.5:
                cleaned_df[col] = parsed_dates
                converted_cols[col] = "Datetime (Parsed multi-format dates)"
                continue

        # 3. Test Boolean conversion
        bool_map = {
            "true": True, "yes": True, "y": True, "1": True, "1.0": True, "t": True,
            "false": False, "no": False, "n": False, "0": False, "0.0": False, "f": False
        }
        lower_series = str_series.str.lower()
        if lower_series.isin(bool_map.keys()).sum() / len(str_series) >= 0.85:
            cleaned_df[col] = lower_series.map(bool_map).astype("boolean")
            converted_cols[col] = "Boolean (Standardized yes/no/1/0)"
            continue

    return cleaned_df, converted_cols


def standardize_categorical_values(
    df: pd.DataFrame, 
    custom_mappings: Optional[Dict[str, Dict[str, str]]] = None
) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Standardize text/categorical columns:
    - Strip whitespace
    - Normalize empty strings to np.nan
    - Apply rule-based dictionary maps for known business domains (Gender, Region, Status, etc.)
    - Title Case standard text columns where appropriate
    """
    cleaned_df = df.copy()
    changes_count = {}

    # Domain-specific standardizers
    standard_rules = {
        "gender": {
            "m": "Male", "male": "Male", "m.": "Male", "man": "Male",
            "f": "Female", "female": "Female", "f.": "Female", "woman": "Female",
            "other": "Other", "unknown": "Unknown"
        },
        "region": {
            "north": "North", "north region": "North", "northern": "North",
            "south": "South", "south region": "South", "southern": "South",
            "east": "East", "east region": "East", "eastern": "East",
            "west": "West", "west region": "West", "western": "West",
            "central": "Central"
        },
        "account_status": {
            "active": "Active", "act": "Active", "enabled": "Active",
            "inactive": "Inactive", "inact": "Inactive", "disabled": "Inactive",
            "pending": "Pending", "suspended": "Suspended"
        },
        "status": {
            "active": "Active", "inactive": "Inactive", "pending": "Pending", "draft": "Draft", "audited": "Audited"
        },
        "payment_method": {
            "upi": "UPI", "credit card": "Credit Card", "cc": "Credit Card",
            "debit card": "Debit Card", "dc": "Debit Card", "net banking": "Net Banking",
            "cash on delivery": "Cash on Delivery", "cod": "Cash on Delivery"
        },
        "customer_segment": {
            "consumer": "Consumer", "corporate": "Corporate", "home office": "Home Office", "sme": "SME"
        }
    }

    if custom_mappings:
        standard_rules.update(custom_mappings)

    for col in cleaned_df.columns:
        if cleaned_df[col].dtype == "object" or isinstance(cleaned_df[col].dtype, pd.StringDtype):
            # Clean whitespace and empty strings
            cleaned_series = cleaned_df[col].astype(str).str.strip()
            # Convert stringified "None", "nan", "null", "" to NaN
            null_mask = cleaned_series.str.lower().isin(["nan", "none", "null", "n/a", "", "undefined"])
            cleaned_series[null_mask] = np.nan
            
            # Check for domain rule matches
            col_key = col.lower().replace(" ", "_")
            matched_rule = None
            for rule_key, rule_dict in standard_rules.items():
                if rule_key in col_key or col_key in rule_key:
                    matched_rule = rule_dict
                    break

            if matched_rule:
                def map_val(x):
                    if pd.isna(x):
                        return x
                    key = str(x).strip().lower()
                    return matched_rule.get(key, str(x).strip().title())

                old_vals = cleaned_series.copy()
                cleaned_df[col] = cleaned_series.apply(map_val)
                diff = (old_vals != cleaned_df[col]).sum()
                if diff > 0:
                    changes_count[col] = int(diff)
            else:
                # Default clean title casing if values are text
                old_vals = cleaned_series.copy()
                # If column looks like ID/Code, don't title case
                if "id" in col_key or "code" in col_key or "email" in col_key:
                    cleaned_df[col] = cleaned_series
                else:
                    cleaned_df[col] = cleaned_series.apply(lambda x: x.title() if pd.notna(x) and isinstance(x, str) else x)
                diff = (old_vals != cleaned_df[col]).sum()
                if diff > 0:
                    changes_count[col] = int(diff)

    return cleaned_df, changes_count


def fix_invalid_numeric_values(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, int]]:
    """
    Fix negative values in strictly positive fields (e.g. price, quantity, salary, age).
    Converts negative values to their absolute value.
    """
    cleaned_df = df.copy()
    fixed_counts = {}
    positive_keywords = ["price", "unit_price", "quantity", "qty", "amount", "salary", "income", 
                         "age", "revenue", "cost", "spend", "sales", "experience"]

    for col in cleaned_df.select_dtypes(include=[np.number]).columns:
        col_lower = str(col).lower().replace(" ", "_")
        if any(kw in col_lower for kw in positive_keywords):
            neg_mask = cleaned_df[col] < 0
            count = int(neg_mask.sum())
            if count > 0:
                cleaned_df.loc[neg_mask, col] = cleaned_df.loc[neg_mask, col].abs()
                fixed_counts[col] = count

    return cleaned_df, fixed_counts


def handle_missing_values(
    df: pd.DataFrame,
    numeric_strategy: str = "median",
    categorical_strategy: str = "mode_or_unknown",
    date_strategy: str = "keep_nat",
    custom_col_strategies: Optional[Dict[str, str]] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Handle missing values with configurable intelligent strategies.
    
    Strategies:
    - Numeric: 'median', 'mean', 'zero', 'drop_row', 'forward_fill'
    - Categorical: 'mode_or_unknown', 'mode', 'constant_unknown', 'drop_row'
    - Date: 'keep_nat', 'forward_fill', 'drop_row'
    
    Returns:
        Tuple of (Cleaned DataFrame, summary_dict of imputation actions)
    """
    cleaned_df = df.copy()
    imputation_log: Dict[str, Any] = {}

    for col in cleaned_df.columns:
        missing_count = int(cleaned_df[col].isna().sum())
        if missing_count == 0:
            continue

        strategy = (custom_col_strategies or {}).get(col)

        # 1. Numeric Columns
        if pd.api.types.is_numeric_dtype(cleaned_df[col]):
            strat = strategy or numeric_strategy
            if strat == "median":
                med_val = cleaned_df[col].median()
                fill_val = 0 if pd.isna(med_val) else round(float(med_val), 2)
                cleaned_df[col] = cleaned_df[col].fillna(fill_val)
                imputation_log[col] = {"strategy": "median", "filled_count": missing_count, "fill_value": fill_val}
            elif strat == "mean":
                mean_val = cleaned_df[col].mean()
                fill_val = 0 if pd.isna(mean_val) else round(float(mean_val), 2)
                cleaned_df[col] = cleaned_df[col].fillna(fill_val)
                imputation_log[col] = {"strategy": "mean", "filled_count": missing_count, "fill_value": fill_val}
            elif strat == "zero":
                cleaned_df[col] = cleaned_df[col].fillna(0)
                imputation_log[col] = {"strategy": "constant (0)", "filled_count": missing_count, "fill_value": 0}
            elif strat == "forward_fill":
                cleaned_df[col] = cleaned_df[col].ffill().bfill()
                imputation_log[col] = {"strategy": "forward_fill", "filled_count": missing_count}
            elif strat == "drop_row":
                cleaned_df = cleaned_df.dropna(subset=[col]).copy()
                imputation_log[col] = {"strategy": "dropped_rows", "dropped_count": missing_count}

        # 2. Datetime Columns
        elif pd.api.types.is_datetime64_any_dtype(cleaned_df[col]):
            strat = strategy or date_strategy
            if strat == "forward_fill":
                cleaned_df[col] = cleaned_df[col].ffill().bfill()
                imputation_log[col] = {"strategy": "forward_fill", "filled_count": missing_count}
            elif strat == "drop_row":
                cleaned_df = cleaned_df.dropna(subset=[col]).copy()
                imputation_log[col] = {"strategy": "dropped_rows", "dropped_count": missing_count}
            else:
                imputation_log[col] = {"strategy": "retained NaT (safe date handling)", "missing_count": missing_count}

        # 3. Categorical / Text Columns
        else:
            strat = strategy or categorical_strategy
            if strat == "mode":
                mode_series = cleaned_df[col].mode(dropna=True)
                fill_val = mode_series.iloc[0] if not mode_series.empty else "Unknown"
                cleaned_df[col] = cleaned_df[col].fillna(fill_val)
                imputation_log[col] = {"strategy": "mode", "filled_count": missing_count, "fill_value": fill_val}
            elif strat == "mode_or_unknown":
                mode_series = cleaned_df[col].mode(dropna=True)
                fill_val = mode_series.iloc[0] if not mode_series.empty and cleaned_df[col].nunique() < 20 else "Unknown"
                cleaned_df[col] = cleaned_df[col].fillna(fill_val)
                imputation_log[col] = {"strategy": "mode_or_unknown", "filled_count": missing_count, "fill_value": fill_val}
            elif strat == "drop_row":
                cleaned_df = cleaned_df.dropna(subset=[col]).copy()
                imputation_log[col] = {"strategy": "dropped_rows", "dropped_count": missing_count}
            else:
                cleaned_df[col] = cleaned_df[col].fillna("Unknown")
                imputation_log[col] = {"strategy": "constant ('Unknown')", "filled_count": missing_count, "fill_value": "Unknown"}

    return cleaned_df, imputation_log


def detect_outliers(
    df: pd.DataFrame,
    method: str = "iqr",
    threshold: float = 1.5
) -> Dict[str, Dict[str, Any]]:
    """
    Detect outliers for numerical columns using IQR or Z-Score.
    
    Args:
        df: Input DataFrame
        method: 'iqr' or 'zscore'
        threshold: multiplier (1.5 for standard IQR, 3.0 for Z-score)
        
    Returns:
        Dictionary mapping column -> outlier statistics
    """
    outlier_report: Dict[str, Dict[str, Any]] = {}
    num_cols = df.select_dtypes(include=[np.number]).columns

    for col in num_cols:
        series = df[col].dropna()
        if len(series) < 5 or series.nunique() <= 2:
            continue

        if method == "iqr":
            q1 = series.quantile(0.25)
            q3 = series.quantile(0.75)
            iqr = q3 - q1
            if iqr == 0:
                continue
            lower_bound = round(float(q1 - (threshold * iqr)), 2)
            upper_bound = round(float(q3 + (threshold * iqr)), 2)
            outlier_mask = (series < lower_bound) | (series > upper_bound)
        else: # Z-Score
            mean = series.mean()
            std = series.std()
            if std == 0 or pd.isna(std):
                continue
            lower_bound = round(float(mean - (threshold * std)), 2)
            upper_bound = round(float(mean + (threshold * std)), 2)
            z_scores = ((series - mean) / std).abs()
            outlier_mask = z_scores > threshold

        outlier_count = int(outlier_mask.sum())
        if outlier_count > 0:
            outlier_report[col] = {
                "outlier_count": outlier_count,
                "outlier_pct": round((outlier_count / len(series)) * 100, 2),
                "lower_bound": lower_bound,
                "upper_bound": upper_bound,
                "sample_outlier_values": [round(float(x), 2) for x in series[outlier_mask].head(5).tolist()]
            }

    return outlier_report


def handle_outliers(
    df: pd.DataFrame,
    outlier_report: Dict[str, Dict[str, Any]],
    action: str = "keep"
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Handle detected outliers:
    - 'keep': Do nothing (safe default, logs presence)
    - 'cap': Winsorize / clip values to lower and upper bounds
    - 'remove': Drop rows containing outliers
    """
    cleaned_df = df.copy()
    action_log = {}

    if not outlier_report or action == "keep":
        return cleaned_df, {"action": "keep", "details": "Retained detected outliers in dataset."}

    if action == "cap":
        for col, stats in outlier_report.items():
            if col in cleaned_df.columns:
                lower = stats["lower_bound"]
                upper = stats["upper_bound"]
                cleaned_df[col] = cleaned_df[col].clip(lower=lower, upper=upper)
                action_log[col] = f"Capped {stats['outlier_count']} values to [{lower}, {upper}]"
        return cleaned_df, {"action": "cap", "details": action_log}

    if action == "remove":
        drop_indices = set()
        for col, stats in outlier_report.items():
            if col in cleaned_df.columns:
                mask = (cleaned_df[col] < stats["lower_bound"]) | (cleaned_df[col] > stats["upper_bound"])
                drop_indices.update(cleaned_df[mask].index)
        
        cleaned_df = cleaned_df.drop(index=list(drop_indices)).copy()
        return cleaned_df, {"action": "remove", "dropped_rows": len(drop_indices)}

    return cleaned_df, {"action": "keep", "details": "Retained outliers"}


def clean_data(
    df: pd.DataFrame,
    options: Optional[Dict[str, Any]] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Full automated end-to-end cleaning pipeline.
    
    Options dictionary:
    - standardize_names (bool): default True
    - remove_dups (bool): default True
    - convert_types (bool): default True
    - fix_negatives (bool): default True
    - standardize_cats (bool): default True
    - handle_missing (bool): default True
    - numeric_missing_strategy (str): 'median', 'mean', 'zero', 'drop_row'
    - categorical_missing_strategy (str): 'mode_or_unknown', 'mode', 'constant_unknown'
    - outlier_method (str): 'iqr' or 'zscore'
    - outlier_action (str): 'keep', 'cap', 'remove'
    
    Returns:
        Tuple of (Cleaned DataFrame, Audit Log Dictionary)
    """
    opts = options or {}
    standardize_names_opt = opts.get("standardize_names", True)
    remove_dups_opt = opts.get("remove_dups", True)
    convert_types_opt = opts.get("convert_types", True)
    fix_negatives_opt = opts.get("fix_negatives", True)
    standardize_cats_opt = opts.get("standardize_cats", True)
    handle_missing_opt = opts.get("handle_missing", True)
    num_missing_strat = opts.get("numeric_missing_strategy", "median")
    cat_missing_strat = opts.get("categorical_missing_strategy", "mode_or_unknown")
    outlier_method = opts.get("outlier_method", "iqr")
    outlier_action = opts.get("outlier_action", "keep")

    audit_log: Dict[str, Any] = {
        "initial_rows": len(df),
        "initial_columns": len(df.columns),
        "steps_executed": [],
        "column_renaming": {},
        "duplicates_removed": 0,
        "types_converted": {},
        "negatives_fixed": {},
        "categories_standardized": {},
        "missing_imputed": {},
        "outlier_detection": {},
        "outlier_handling": {},
        "final_rows": 0,
        "final_columns": 0
    }

    cleaned_df = df.copy()

    # Step 1: Standardize Column Names
    if standardize_names_opt:
        cleaned_df, rename_map = standardize_column_names(cleaned_df)
        audit_log["column_renaming"] = rename_map
        audit_log["steps_executed"].append(f"Standardized {len(rename_map)} column names into clean snake_case.")
        log_event("INFO", "CLEAN", "Column names standardized.")

    # Step 2: Remove Exact Duplicates
    if remove_dups_opt:
        cleaned_df, dups_removed, _ = remove_duplicates(cleaned_df)
        audit_log["duplicates_removed"] = dups_removed
        if dups_removed > 0:
            audit_log["steps_executed"].append(f"Removed {dups_removed} exact duplicate records.")
            log_event("INFO", "CLEAN", f"Removed {dups_removed} duplicate rows.")

    # Step 3: Standardize Data Types (Currency, Percentages, Dates, Booleans)
    if convert_types_opt:
        cleaned_df, converted_types = standardize_data_types(cleaned_df)
        audit_log["types_converted"] = converted_types
        if converted_types:
            audit_log["steps_executed"].append(f"Converted {len(converted_types)} columns to appropriate numeric/date/boolean types.")
            log_event("INFO", "CLEAN", f"Converted data types: {list(converted_types.keys())}")

    # Step 4: Fix Invalid Negative Values in Positive Fields
    if fix_negatives_opt:
        cleaned_df, neg_fixed = fix_invalid_numeric_values(cleaned_df)
        audit_log["negatives_fixed"] = neg_fixed
        if neg_fixed:
            total_fixed = sum(neg_fixed.values())
            audit_log["steps_executed"].append(f"Corrected {total_fixed} negative values across {len(neg_fixed)} positive columns.")
            log_event("INFO", "CLEAN", f"Fixed negative values in {neg_fixed}")

    # Step 5: Standardize Categorical Values & Trim Whitespace
    if standardize_cats_opt:
        cleaned_df, cat_changes = standardize_categorical_values(cleaned_df)
        audit_log["categories_standardized"] = cat_changes
        if cat_changes:
            audit_log["steps_executed"].append(f"Normalized casing and categorical variants across {len(cat_changes)} text columns.")
            log_event("INFO", "CLEAN", "Categorical normalization completed.")

    # Step 6: Handle Missing Values
    if handle_missing_opt:
        cleaned_df, missing_actions = handle_missing_values(
            cleaned_df,
            numeric_strategy=num_missing_strat,
            categorical_strategy=cat_missing_strat
        )
        audit_log["missing_imputed"] = missing_actions
        if missing_actions:
            audit_log["steps_executed"].append(f"Handled missing values across {len(missing_actions)} columns using intelligent imputation.")
            log_event("INFO", "CLEAN", f"Imputed missing values across {len(missing_actions)} columns.")

    # Step 7: Outlier Detection and Handling
    outlier_report = detect_outliers(cleaned_df, method=outlier_method)
    audit_log["outlier_detection"] = outlier_report
    if outlier_report:
        cleaned_df, outlier_action_res = handle_outliers(cleaned_df, outlier_report, action=outlier_action)
        audit_log["outlier_handling"] = outlier_action_res
        audit_log["steps_executed"].append(f"Detected outliers in {len(outlier_report)} numeric columns (Action: {outlier_action}).")
        log_event("INFO", "CLEAN", f"Outliers processed with action '{outlier_action}'.")

    # Final counts
    audit_log["final_rows"] = len(cleaned_df)
    audit_log["final_columns"] = len(cleaned_df.columns)
    log_event("SUCCESS", "CLEAN", f"Cleaning completed successfully. Shape changed from ({audit_log['initial_rows']}, {audit_log['initial_columns']}) to ({audit_log['final_rows']}, {audit_log['final_columns']}).")

    return cleaned_df, audit_log


def _is_date_string(val: Any) -> bool:
    """Helper to detect date strings."""
    if not isinstance(val, str) or len(val.strip()) < 6:
        return False
    val = val.strip()
    return bool(re.match(r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}|^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}", val))
