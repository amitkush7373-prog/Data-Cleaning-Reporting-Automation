"""
Data Validation & Quality Assessment Module.
Performs comprehensive data profiling, missingness diagnostics, duplicate detection,
type inference, anomaly detection, and computes an overall Data Health Score (0-100%).
"""
import re
from typing import Dict, Any, List
import pandas as pd
import numpy as np
from src.logger import log_event


def validate_data(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Perform deep validation and data-quality assessment on a DataFrame.
    
    Args:
        df: Input pandas DataFrame
        
    Returns:
        Dictionary containing quality metrics, issue breakdown, column profiles,
        and overall health scores.
    """
    if df is None or df.empty:
        return {
            "total_rows": 0,
            "total_columns": 0,
            "total_cells": 0,
            "quality_score": 0.0,
            "quality_grade": "N/A",
            "is_empty": True,
            "issues_summary": ["Dataset is empty."],
            "missing_report": {},
            "duplicate_report": {},
            "column_types": {},
            "inferred_types": {},
            "invalid_values": {},
            "cardinality": {},
            "dimensions": {"completeness": 0, "uniqueness": 0, "validity": 0, "consistency": 0}
        }

    total_rows = len(df)
    total_cols = len(df.columns)
    total_cells = total_rows * total_cols
    issues: List[str] = []

    # -------------------------------------------------------------
    # 1. Missing Values Diagnostic
    # -------------------------------------------------------------
    missing_counts = df.isna().sum().to_dict()
    missing_pcts = {col: round((cnt / total_rows) * 100, 2) for col, cnt in missing_counts.items()}
    total_missing = int(df.isna().sum().sum())
    total_missing_pct = round((total_missing / total_cells) * 100, 2) if total_cells > 0 else 0.0

    cols_with_missing = {col: {"count": missing_counts[col], "pct": missing_pcts[col]} 
                         for col in df.columns if missing_counts[col] > 0}

    if total_missing > 0:
        issues.append(f"Found {total_missing:,} missing values across {len(cols_with_missing)} columns ({total_missing_pct}% of total cells).")

    # -------------------------------------------------------------
    # 2. Duplicate Rows Diagnostic
    # -------------------------------------------------------------
    duplicate_rows_count = int(df.duplicated().sum())
    duplicate_pct = round((duplicate_rows_count / total_rows) * 100, 2) if total_rows > 0 else 0.0

    if duplicate_rows_count > 0:
        issues.append(f"Found {duplicate_rows_count:,} exact duplicate rows ({duplicate_pct}% of dataset).")

    # -------------------------------------------------------------
    # 3. Data Types & Semantic Inference
    # -------------------------------------------------------------
    actual_dtypes = {str(col): str(dtype) for col, dtype in df.dtypes.items()}
    
    numeric_cols = list(df.select_dtypes(include=[np.number]).columns)
    text_cols = list(df.select_dtypes(include=["object", "string"]).columns)
    datetime_cols = list(df.select_dtypes(include=["datetime", "datetimetz"]).columns)
    bool_cols = list(df.select_dtypes(include=["bool"]).columns)

    # Inferred types for dirty object columns
    inferred_types = {}
    dirty_currency_cols = []
    dirty_date_cols = []
    dirty_bool_cols = []

    currency_symbols_regex = re.compile(r"[\$₹€£¥,%\s]")

    for col in text_cols:
        series_clean = df[col].dropna().astype(str).str.strip()
        if series_clean.empty:
            inferred_types[col] = "empty_text"
            continue

        sample = series_clean.head(50)
        
        # Test currency / formatted numeric
        cleaned_num = sample.apply(lambda x: currency_symbols_regex.sub("", x))
        numeric_match_count = sum(1 for val in cleaned_num if _is_convertible_to_float(val))
        if numeric_match_count / len(sample) >= 0.7:
            inferred_types[col] = "numeric_string (currency/formatted)"
            dirty_currency_cols.append(col)
            continue

        # Test date strings
        date_match_count = sum(1 for val in sample if _is_likely_date(val))
        if date_match_count / len(sample) >= 0.7:
            inferred_types[col] = "datetime_string"
            dirty_date_cols.append(col)
            continue

        # Test boolean strings
        bool_match_count = sum(1 for val in sample if val.lower() in ["true", "false", "yes", "no", "y", "n", "0", "1"])
        if bool_match_count / len(sample) >= 0.85:
            inferred_types[col] = "boolean_string"
            dirty_bool_cols.append(col)
            continue

        inferred_types[col] = "text_categorical"

    if dirty_currency_cols:
        issues.append(f"Columns formatted as text with currency/symbols: {', '.join(dirty_currency_cols)}")
    if dirty_date_cols:
        issues.append(f"Unparsed date columns: {', '.join(dirty_date_cols)}")

    # -------------------------------------------------------------
    # 4. Cardinality & Unique Values
    # -------------------------------------------------------------
    cardinality = {}
    constant_cols = []
    for col in df.columns:
        unique_cnt = int(df[col].nunique(dropna=True))
        cardinality[col] = {
            "unique_count": unique_cnt,
            "unique_pct": round((unique_cnt / total_rows) * 100, 2) if total_rows > 0 else 0.0,
            "sample_values": [str(v) for v in df[col].dropna().unique()[:5]]
        }
        if unique_cnt <= 1 and total_rows > 1:
            constant_cols.append(col)

    if constant_cols:
        issues.append(f"Constant/Zero-variance columns (single unique value): {', '.join(constant_cols)}")

    # -------------------------------------------------------------
    # 5. Invalid & Suspicious Values
    # -------------------------------------------------------------
    invalid_findings: Dict[str, Any] = {}
    
    # 5a. Negative values in columns expected to be positive (price, qty, age, salary, cost, revenue)
    positive_keywords = ["price", "unit_price", "quantity", "qty", "amount", "salary", "income", 
                         "age", "revenue", "cost", "spend", "sales", "experience"]
    negative_value_counts = {}
    for col in df.columns:
        col_lower = str(col).lower().replace(" ", "_")
        if any(kw in col_lower for kw in positive_keywords):
            # Check if numeric
            if col in numeric_cols:
                neg_count = int((df[col] < 0).sum())
                if neg_count > 0:
                    negative_value_counts[col] = neg_count
            elif col in dirty_currency_cols:
                # check parsed numeric negatives
                cleaned_series = df[col].dropna().astype(str).str.replace(r"[^\d.-]", "", regex=True)
                numeric_parsed = pd.to_numeric(cleaned_series, errors="coerce")
                neg_count = int((numeric_parsed < 0).sum())
                if neg_count > 0:
                    negative_value_counts[col] = neg_count

    if negative_value_counts:
        invalid_findings["negative_values"] = negative_value_counts
        issues.append(f"Found negative values in strictly positive fields: {negative_value_counts}")

    # 5b. Blank / Whitespace-only text values
    whitespace_counts = {}
    for col in text_cols:
        ws_count = int((df[col].astype(str).str.strip() == "").sum() - df[col].isna().sum())
        if ws_count > 0:
            whitespace_counts[col] = ws_count

    if whitespace_counts:
        invalid_findings["whitespace_only"] = whitespace_counts
        issues.append(f"Found blank/whitespace-only text strings in: {whitespace_counts}")

    # 5c. Column naming inconsistencies (spaces, special chars, uppercase)
    non_standard_columns = []
    for col in df.columns:
        col_str = str(col)
        if " " in col_str or any(c in col_str for c in ["-", "(", ")", "%", "#", "$", "/", "\\"]) or col_str != col_str.lower():
            non_standard_columns.append(col_str)

    if non_standard_columns:
        issues.append(f"{len(non_standard_columns)} columns have non-standard naming (spaces, mixed-case, or special characters).")

    # -------------------------------------------------------------
    # 6. Quality Health Score Calculation (0 - 100%)
    # -------------------------------------------------------------
    # Completeness (35% weight): penalize missing values
    completeness_score = max(0.0, 100.0 - total_missing_pct * 2.0)
    
    # Uniqueness (25% weight): penalize duplicate rows
    uniqueness_score = max(0.0, 100.0 - duplicate_pct * 3.0)
    
    # Validity (25% weight): penalize negative anomalies & blank strings
    total_invalid_items = sum(negative_value_counts.values()) + sum(whitespace_counts.values())
    invalid_pct = (total_invalid_items / total_cells) * 100 if total_cells > 0 else 0.0
    validity_score = max(0.0, 100.0 - invalid_pct * 10.0)
    
    # Consistency (15% weight): column names + unparsed dirty types
    uncleaned_types_count = len(dirty_currency_cols) + len(dirty_date_cols)
    consistency_pen = (len(non_standard_columns) / max(total_cols, 1) * 30) + (uncleaned_types_count * 15)
    consistency_score = max(0.0, 100.0 - consistency_pen)

    overall_score = round(
        (completeness_score * 0.35) + 
        (uniqueness_score * 0.25) + 
        (validity_score * 0.25) + 
        (consistency_score * 0.15), 
        1
    )
    overall_score = max(0.0, min(100.0, overall_score))

    # Determine Grade
    if overall_score >= 90:
        grade = "A+ (Excellent)"
    elif overall_score >= 80:
        grade = "A (Good)"
    elif overall_score >= 70:
        grade = "B (Acceptable)"
    elif overall_score >= 50:
        grade = "C (Needs Attention)"
    else:
        grade = "D (Critical Data Quality Issues)"

    log_event("INFO", "VALIDATE", f"Validation complete. Overall Health Score: {overall_score}/100 [{grade}]. Found {len(issues)} issue categories.")

    return {
        "total_rows": total_rows,
        "total_columns": total_cols,
        "total_cells": total_cells,
        "quality_score": overall_score,
        "quality_grade": grade,
        "is_empty": False,
        "issues_summary": issues if issues else ["No major data quality issues detected."],
        "missing_report": {
            "total_missing": total_missing,
            "total_missing_pct": total_missing_pct,
            "columns": cols_with_missing
        },
        "duplicate_report": {
            "duplicate_count": duplicate_rows_count,
            "duplicate_pct": duplicate_pct
        },
        "column_types": {
            "numeric": numeric_cols,
            "text": text_cols,
            "datetime": datetime_cols,
            "boolean": bool_cols,
            "raw_dtypes": actual_dtypes
        },
        "inferred_types": inferred_types,
        "invalid_values": invalid_findings,
        "non_standard_columns": non_standard_columns,
        "cardinality": cardinality,
        "dimensions": {
            "completeness": round(completeness_score, 1),
            "uniqueness": round(uniqueness_score, 1),
            "validity": round(validity_score, 1),
            "consistency": round(consistency_score, 1)
        }
    }


def _is_convertible_to_float(val: Any) -> bool:
    """Check if value can be converted to float after stripping currency/separators."""
    try:
        if val is None or val == "" or str(val).lower() in ["nan", "none", "null", "n/a"]:
            return False
        float(str(val))
        return True
    except ValueError:
        return False


def _is_likely_date(val: Any) -> bool:
    """Check if a string looks like a date pattern."""
    if not isinstance(val, str) or len(val.strip()) < 6:
        return False
    val = val.strip()
    date_patterns = [
        r"^\d{4}[-/]\d{1,2}[-/]\d{1,2}",        # 2026-08-15
        r"^\d{1,2}[-/]\d{1,2}[-/]\d{2,4}",        # 15/08/2026 or 08/15/2026
        r"^[A-Za-z]{3,9}\s+\d{1,2},\s*\d{4}",     # Aug 15, 2026
        r"^\d{1,2}\s+[A-Za-z]{3,9}\s+\d{4}"      # 15 Aug 2026
    ]
    return any(re.match(p, val) for p in date_patterns)
