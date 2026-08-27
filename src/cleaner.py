"""
Data Cleaning & Transformation Engine Module.
Performs automated, deterministic, and configurable cleaning operations:
- Column standardization (snake_case)
- Exact duplicate row removal
- Smart data type casting (currency strings, dates, booleans)
- Missing value imputation (numeric, categorical, datetime, boolean)
- Anomaly correction (negative values in positive fields, whitespace/casing)
- Outlier handling (IQR / Z-Score clipping or removal)
- Produces a comprehensive step-by-step audit changelog
"""
import re
from typing import Dict, Any, List, Tuple, Optional, Union
import pandas as pd
import numpy as np
from src.logger import log_event


def clean_column_names(df: pd.DataFrame) -> Tuple[pd.DataFrame, Dict[str, str]]:
    """
    Standardize all column headers to clean snake_case.
    
    Operations:
    - Strip leading/trailing whitespaces
    - Replace spaces, hyphens, dots, slashes with single underscores
    - Remove special characters (#, $, %, @, etc.)
    - Convert to lowercase
    - Deduplicate identical column names by appending numeric suffix
    
    Returns:
        Tuple of (Cleaned DataFrame, mapping dictionary of original -> new names)
    """
    cleaned_df = df.copy()
    mapping: Dict[str, str] = {}
    seen_names: Dict[str, int] = {}

    for orig_col in cleaned_df.columns:
        col_str = str(orig_col).strip()
        # Replace special separators with underscores
        cleaned_name = re.sub(r"[\s\-\.\/\\\(\)\[\]]+", "_", col_str)
        # Remove non-alphanumeric except underscores
        cleaned_name = re.sub(r"[^a-zA-Z0-9_]", "", cleaned_name)
        # Collapse multiple underscores
        cleaned_name = re.sub(r"_+", "_", cleaned_name).strip("_").lower()

        if not cleaned_name:
            cleaned_name = "unnamed_col"

        # Handle duplicate column names
        if cleaned_name in seen_names:
            seen_names[cleaned_name] += 1
            final_name = f"{cleaned_name}_{seen_names[cleaned_name]}"
        else:
            seen_names[cleaned_name] = 0
            final_name = cleaned_name

        mapping[orig_col] = final_name

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
        # Check if already numeric, datetime, or boolean
        if pd.api.types.is_numeric_dtype(cleaned_df[col]) or pd.api.types.is_datetime64_any_dtype(cleaned_df[col]) or pd.api.types.is_bool_dtype(cleaned_df[col]):
            continue

        series = cleaned_df[col].dropna()
        if series.empty:
            continue

        # Convert to string for regex checks
        str_series = series.astype(str).str.strip()

        # 1. Test Currency / Percentage / Comma-separated numbers
        cleaned_str = str_series.apply(lambda x: currency_regex.sub("", str(x)))
        is_pct = str_series.str.endswith("%").sum() / len(str_series) > 0.5
        if is_pct:
            cleaned_str = cleaned_str.str.replace("%", "", regex=False)

        numeric_success = pd.to_numeric(cleaned_str, errors="coerce")
        valid_ratio = numeric_success.notna().sum() / len(series)

        if valid_ratio >= 0.75:
            col_cleaned = cleaned_df[col].astype(str).apply(lambda x: currency_regex.sub("", str(x)).replace("%", "") if pd.notna(x) else x)
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
            cleaned_series = cleaned_df[col].astype(str).str.strip()
            null_mask = cleaned_series.str.lower().isin(["nan", "none", "null", "n/a", "", "undefined", "<na>"])
            cleaned_series[null_mask] = np.nan
            
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
                old_vals = cleaned_series.copy()
                if "id" in col_key or "code" in col_key or "email" in col_key or "url" in col_key:
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
        if pd.api.types.is_bool_dtype(cleaned_df[col]) or str(cleaned_df[col].dtype).lower() in ["boolean", "bool"]:
            continue
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
    Handle missing values with configurable intelligent strategies and bulletproof type safety.
    
    Strategies:
    - Numeric: 'median', 'mean', 'zero', 'drop_row', 'forward_fill'
    - Categorical: 'mode_or_unknown', 'mode', 'constant_unknown', 'drop_row'
    - Boolean: mode / False
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

        # -------------------------------------------------------------
        # 1. Boolean Columns (Must be handled BEFORE is_numeric_dtype!)
        # -------------------------------------------------------------
        is_bool = (
            pd.api.types.is_bool_dtype(cleaned_df[col]) or
            str(cleaned_df[col].dtype).lower() in ["boolean", "bool"] or
            isinstance(cleaned_df[col].dtype, pd.BooleanDtype)
        )
        if is_bool:
            strat = strategy or categorical_strategy
            if strat == "drop_row":
                cleaned_df = cleaned_df.dropna(subset=[col]).copy()
                imputation_log[col] = {"strategy": "dropped_rows", "dropped_count": missing_count}
            else:
                mode_series = cleaned_df[col].dropna().mode()
                fill_val = bool(mode_series.iloc[0]) if not mode_series.empty else False
                try:
                    cleaned_df[col] = cleaned_df[col].fillna(fill_val)
                except Exception:
                    cleaned_df[col] = cleaned_df[col].astype(object).fillna(fill_val).astype("boolean")
                imputation_log[col] = {"strategy": "boolean_mode", "filled_count": missing_count, "fill_value": fill_val}
            continue

        # -------------------------------------------------------------
        # 2. Categorical (pd.CategoricalDtype) Columns
        # -------------------------------------------------------------
        if isinstance(cleaned_df[col].dtype, pd.CategoricalDtype):
            strat = strategy or categorical_strategy
            if strat == "drop_row":
                cleaned_df = cleaned_df.dropna(subset=[col]).copy()
                imputation_log[col] = {"strategy": "dropped_rows", "dropped_count": missing_count}
            else:
                mode_series = cleaned_df[col].dropna().mode()
                fill_val = mode_series.iloc[0] if not mode_series.empty else "Unknown"
                if fill_val not in cleaned_df[col].cat.categories:
                    cleaned_df[col] = cleaned_df[col].cat.add_categories([fill_val])
                cleaned_df[col] = cleaned_df[col].fillna(fill_val)
                imputation_log[col] = {"strategy": "categorical_mode", "filled_count": missing_count, "fill_value": str(fill_val)}
            continue

        # -------------------------------------------------------------
        # 3. Numeric Columns
        # -------------------------------------------------------------
        if pd.api.types.is_numeric_dtype(cleaned_df[col]):
            strat = strategy or numeric_strategy
            try:
                if strat == "median":
                    med_val = cleaned_df[col].median()
                    fill_val = 0 if pd.isna(med_val) else round(float(med_val), 2)
                    if pd.api.types.is_integer_dtype(cleaned_df[col]):
                        fill_val = int(round(fill_val))
                    cleaned_df[col] = cleaned_df[col].fillna(fill_val)
                    imputation_log[col] = {"strategy": "median", "filled_count": missing_count, "fill_value": fill_val}
                elif strat == "mean":
                    mean_val = cleaned_df[col].mean()
                    fill_val = 0 if pd.isna(mean_val) else round(float(mean_val), 2)
                    if pd.api.types.is_integer_dtype(cleaned_df[col]):
                        fill_val = int(round(fill_val))
                    cleaned_df[col] = cleaned_df[col].fillna(fill_val)
                    imputation_log[col] = {"strategy": "mean", "filled_count": missing_count, "fill_value": fill_val}
                elif strat == "zero":
                    fill_val = 0 if pd.api.types.is_integer_dtype(cleaned_df[col]) else 0.0
                    cleaned_df[col] = cleaned_df[col].fillna(fill_val)
                    imputation_log[col] = {"strategy": "constant (0)", "filled_count": missing_count, "fill_value": 0}
                elif strat == "forward_fill":
                    cleaned_df[col] = cleaned_df[col].ffill().bfill()
                    imputation_log[col] = {"strategy": "forward_fill", "filled_count": missing_count}
                elif strat == "drop_row":
                    cleaned_df = cleaned_df.dropna(subset=[col]).copy()
                    imputation_log[col] = {"strategy": "dropped_rows", "dropped_count": missing_count}
            except Exception:
                cleaned_df[col] = cleaned_df[col].astype(float).fillna(0.0)
                imputation_log[col] = {"strategy": "numeric_safe_fallback", "filled_count": missing_count, "fill_value": 0.0}
            continue

        # -------------------------------------------------------------
        # 4. Datetime Columns
        # -------------------------------------------------------------
        if pd.api.types.is_datetime64_any_dtype(cleaned_df[col]):
            strat = strategy or date_strategy
            if strat == "forward_fill":
                cleaned_df[col] = cleaned_df[col].ffill().bfill()
                imputation_log[col] = {"strategy": "forward_fill", "filled_count": missing_count}
            elif strat == "drop_row":
                cleaned_df = cleaned_df.dropna(subset=[col]).copy()
                imputation_log[col] = {"strategy": "dropped_rows", "dropped_count": missing_count}
            else:
                imputation_log[col] = {"strategy": "retained NaT (safe date handling)", "missing_count": missing_count}
            continue

        # -------------------------------------------------------------
        # 5. Categorical / Text / Object Columns
        # -------------------------------------------------------------
        strat = strategy or categorical_strategy
        if strat == "mode":
            mode_series = cleaned_df[col].mode(dropna=True)
            fill_val = mode_series.iloc[0] if not mode_series.empty else "Unknown"
        elif strat == "mode_or_unknown":
            mode_series = cleaned_df[col].mode(dropna=True)
            fill_val = mode_series.iloc[0] if not mode_series.empty and cleaned_df[col].nunique() < 20 else "Unknown"
        elif strat == "drop_row":
            cleaned_df = cleaned_df.dropna(subset=[col]).copy()
            imputation_log[col] = {"strategy": "dropped_rows", "dropped_count": missing_count}
            continue
        else:
            fill_val = "Unknown"

        try:
            cleaned_df[col] = cleaned_df[col].fillna(fill_val)
        except Exception:
            cleaned_df[col] = cleaned_df[col].astype(str).replace({"nan": fill_val, "None": fill_val, "<NA>": fill_val, "": fill_val})
        imputation_log[col] = {"strategy": strat, "filled_count": missing_count, "fill_value": str(fill_val)}

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
        if pd.api.types.is_bool_dtype(df[col]) or str(df[col].dtype).lower() in ["boolean", "bool"]:
            continue
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
        elif method == "zscore":
            mean = series.mean()
            std = series.std()
            if std == 0 or pd.isna(std):
                continue
            z_scores = ((series - mean) / std).abs()
            outlier_mask = z_scores > threshold
            lower_bound = round(float(mean - (threshold * std)), 2)
            upper_bound = round(float(mean + (threshold * std)), 2)
        else:
            continue

        outlier_count = int(outlier_mask.sum())
        if outlier_count > 0:
            outlier_report[col] = {
                "method": method,
                "outlier_count": outlier_count,
                "outlier_pct": round((outlier_count / len(series)) * 100, 2),
                "lower_bound": lower_bound,
                "upper_bound": upper_bound
            }

    return outlier_report


def handle_outliers(
    df: pd.DataFrame,
    outlier_report: Dict[str, Dict[str, Any]],
    action: str = "keep"
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Handle detected outliers:
    - 'keep': Flag and retain original values
    - 'cap': Winsorize / clip values to lower and upper bounds
    - 'remove': Drop rows containing outlier values
    """
    cleaned_df = df.copy()
    actions_taken: Dict[str, Any] = {}

    if action == "keep" or not outlier_report:
        return cleaned_df, {"action": "kept_all", "columns_affected": list(outlier_report.keys())}

    for col, stats in outlier_report.items():
        if col not in cleaned_df.columns:
            continue

        lower = stats["lower_bound"]
        upper = stats["upper_bound"]

        if action == "cap":
            clipped_series = cleaned_df[col].clip(lower=lower, upper=upper)
            changed = (cleaned_df[col] != clipped_series).sum()
            cleaned_df[col] = clipped_series
            actions_taken[col] = {"action": "capped", "clipped_count": int(changed), "bounds": [lower, upper]}

        elif action == "remove":
            mask = (cleaned_df[col] >= lower) & (cleaned_df[col] <= upper) | (cleaned_df[col].isna())
            initial_len = len(cleaned_df)
            cleaned_df = cleaned_df[mask].copy()
            actions_taken[col] = {"action": "removed_rows", "dropped_rows": initial_len - len(cleaned_df)}

    return cleaned_df, actions_taken


def clean_data(
    df: pd.DataFrame,
    options: Optional[Dict[str, Any]] = None
) -> Tuple[pd.DataFrame, Dict[str, Any]]:
    """
    Master automated pipeline orchestrator for data cleaning.
    Executes all cleaning steps deterministically and produces an audit trail.
    
    Default options:
    - standardize_names: True
    - remove_dups: True
    - convert_types: True
    - fix_negatives: True
    - standardize_cats: True
    - handle_missing: True
    - numeric_missing_strategy: 'median'
    - categorical_missing_strategy: 'mode_or_unknown'
    - outlier_method: 'iqr'
    - outlier_action: 'keep'
    """
    if df is None or df.empty:
        return df, {"status": "empty_dataset"}

    opts = options or {}
    cleaned_df = df.copy()
    audit_log: Dict[str, Any] = {
        "initial_shape": (len(df), len(df.columns)),
        "steps_executed": []
    }

    # Step 1: Standardize Column Names
    if opts.get("standardize_names", True):
        cleaned_df, name_mapping = clean_column_names(cleaned_df)
        audit_log["column_renaming"] = name_mapping
        audit_log["steps_executed"].append(f"Standardized {len(name_mapping)} column headers to snake_case.")
        log_event("INFO", "CLEAN", f"Standardized {len(name_mapping)} column names.")

    # Step 2: Remove Exact Duplicates
    if opts.get("remove_dups", True):
        cleaned_df, dups_removed, remaining = remove_duplicates(cleaned_df)
        audit_log["duplicates_removed"] = dups_removed
        if dups_removed > 0:
            audit_log["steps_executed"].append(f"Removed {dups_removed} duplicate rows ({remaining} rows remaining).")
            log_event("INFO", "CLEAN", f"Removed {dups_removed} duplicate rows.")

    # Step 3: Type Conversions & Currency Parsing
    if opts.get("convert_types", True):
        cleaned_df, converted_types = standardize_data_types(cleaned_df)
        audit_log["types_converted"] = converted_types
        if converted_types:
            audit_log["steps_executed"].append(f"Parsed and converted data types for {len(converted_types)} columns.")
            log_event("INFO", "CLEAN", f"Converted types for columns: {list(converted_types.keys())}")

    # Step 4: Fix Negatives in Strictly Positive Fields
    if opts.get("fix_negatives", True):
        cleaned_df, fixed_negs = fix_invalid_numeric_values(cleaned_df)
        audit_log["negatives_fixed"] = fixed_negs
        if fixed_negs:
            total_fixed = sum(fixed_negs.values())
            audit_log["steps_executed"].append(f"Corrected {total_fixed} negative values across {len(fixed_negs)} numeric fields.")
            log_event("INFO", "CLEAN", f"Fixed negative values in: {fixed_negs}")

    # Step 5: Standardize Categorical Values & Text Domains
    if opts.get("standardize_cats", True):
        cleaned_df, cat_changes = standardize_categorical_values(cleaned_df)
        audit_log["categorical_standardized"] = cat_changes
        if cat_changes:
            total_std = sum(cat_changes.values())
            audit_log["steps_executed"].append(f"Standardized casing and text domains across {len(cat_changes)} categorical columns ({total_std} values adjusted).")
            log_event("INFO", "CLEAN", f"Standardized categories: {cat_changes}")

    # Step 6: Handle Missing Values
    if opts.get("handle_missing", True):
        cleaned_df, imp_log = handle_missing_values(
            cleaned_df,
            numeric_strategy=opts.get("numeric_missing_strategy", "median"),
            categorical_strategy=opts.get("categorical_missing_strategy", "mode_or_unknown")
        )
        audit_log["missing_value_imputation"] = imp_log
        if imp_log:
            audit_log["steps_executed"].append(f"Handled missing values across {len(imp_log)} columns using intelligent imputation strategies.")
            log_event("INFO", "CLEAN", f"Imputed columns: {list(imp_log.keys())}")

    # Step 7: Outlier Detection and Handling
    outlier_method = opts.get("outlier_method", "iqr")
    outlier_action = opts.get("outlier_action", "keep")
    outlier_report = detect_outliers(cleaned_df, method=outlier_method)
    audit_log["outlier_detection"] = outlier_report

    if outlier_action != "keep" and outlier_report:
        cleaned_df, outlier_actions = handle_outliers(cleaned_df, outlier_report, action=outlier_action)
        audit_log["outlier_actions"] = outlier_actions
        audit_log["steps_executed"].append(f"Applied outlier action '{outlier_action}' across {len(outlier_actions)} columns.")
        log_event("INFO", "CLEAN", f"Outlier action '{outlier_action}' applied.")

    audit_log["final_shape"] = (len(cleaned_df), len(cleaned_df.columns))
    return cleaned_df, audit_log


# -------------------------------------------------------------
# Internal Helper Functions
# -------------------------------------------------------------

def _is_date_string(val: str) -> bool:
    """Check if a string resembles a common date format."""
    if not isinstance(val, str) or len(val.strip()) < 6:
        return False
    val_clean = val.strip()
    date_patterns = [
        r"^\d{4}[-/.]\d{1,2}[-/.]\d{1,2}", # YYYY-MM-DD
        r"^\d{1,2}[-/.]\d{1,2}[-/.]\d{2,4}", # DD-MM-YYYY or MM-DD-YYYY
        r"^[a-zA-Z]{3,9}\s+\d{1,2},?\s+\d{4}", # Month DD, YYYY
        r"^\d{1,2}\s+[a-zA-Z]{3,9}\s+\d{4}" # DD Month YYYY
    ]
    return any(re.match(p, val_clean) for p in date_patterns)
