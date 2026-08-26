"""
Comprehensive Pytest Test Suite for Data Cleaning & Reporting Automation.
Tests data loading, validation, cleaning, transformation, analytics,
visualizations, report generation, and edge cases.
"""
import io
import os
import pytest
import pandas as pd
import numpy as np

from src.data_loader import load_data
from src.validator import validate_data
from src.cleaner import (
    standardize_column_names, remove_duplicates, standardize_data_types,
    standardize_categorical_values, fix_invalid_numeric_values,
    handle_missing_values, detect_outliers, handle_outliers, clean_data
)
from src.transformer import transform_data
from src.analyzer import calculate_kpis, generate_statistical_summary, generate_aggregations
from src.insights import generate_insights
from src.report_generator import (
    generate_excel_report, generate_pdf_report, generate_html_report, export_cleaned_data
)


@pytest.fixture
def sample_raw_sales_df():
    return pd.DataFrame({
        "Order ID": ["ORD-101", "ORD-102", "ORD-103", "ORD-103", "ORD-104"],
        "Order Date": ["2026-01-15", "16/02/2026", "2026-03-20", "2026-03-20", "invalid_date"],
        "Customer Name": ["Alice Smith", "Bob Jones", "Charlie Brown", "Charlie Brown", "   "],
        "Region": ["North", "north region", "SOUTH", "SOUTH", "West"],
        "Product Category": ["Electronics", "electronics", "Furniture", "Furniture", "Office Supplies"],
        "Quantity": [2, 5, 10, 10, -3],
        "Unit Price": ["$1,200.50", "₹ 450.00", "150.00", "150.00", "  99.99  "],
        "Discount %": ["10%", "5%", "0%", "0%", "15%"],
        "Gender": ["Female", "M", "Male", "Male", "female"]
    })


def test_standardize_column_names():
    df = pd.DataFrame({"Customer Name": [1], "Discount %": [2], "Cost ($)": [3], "Dup": [4], "Dup": [5]})
    clean_df, mapping = standardize_column_names(df)
    
    assert "customer_name" in clean_df.columns
    assert "discount_pct" in clean_df.columns
    assert "cost_usd" in clean_df.columns
    # Check no duplicate column names exist
    assert len(clean_df.columns) == len(set(clean_df.columns))


def test_remove_duplicates(sample_raw_sales_df):
    clean_df, removed_cnt, remaining_cnt = remove_duplicates(sample_raw_sales_df)
    assert removed_cnt == 1
    assert remaining_cnt == 4
    assert len(clean_df) == 4


def test_standardize_data_types(sample_raw_sales_df):
    df_clean, converted = standardize_data_types(sample_raw_sales_df)
    
    # Unit Price should be converted to numeric float
    assert pd.api.types.is_numeric_dtype(df_clean["Unit Price"])
    assert df_clean["Unit Price"].iloc[0] == 1200.50
    assert df_clean["Unit Price"].iloc[1] == 450.00


def test_fix_invalid_numeric_values(sample_raw_sales_df):
    df_clean, converted = standardize_data_types(sample_raw_sales_df)
    df_fixed, fixed_counts = fix_invalid_numeric_values(df_clean)
    
    # Quantity column negative value (-3) should be converted to positive (3)
    assert (df_fixed["Quantity"] >= 0).all()
    assert df_fixed["Quantity"].iloc[4] == 3


def test_standardize_categorical_values(sample_raw_sales_df):
    df_std, changes = standardize_categorical_values(sample_raw_sales_df)
    
    # Region values 'north region' -> 'North'
    assert "North" in df_std["Region"].values
    # Gender values 'M' -> 'Male'
    assert "Male" in df_std["Gender"].values


def test_handle_missing_values():
    df = pd.DataFrame({
        "num_col": [10.0, 20.0, 30.0, np.nan],
        "cat_col": ["A", "B", "A", np.nan]
    })
    df_imputed, log = handle_missing_values(df, numeric_strategy="median", categorical_strategy="mode")
    
    assert df_imputed["num_col"].isna().sum() == 0
    assert df_imputed["num_col"].iloc[3] == 20.0 # median
    assert df_imputed["cat_col"].isna().sum() == 0
    assert df_imputed["cat_col"].iloc[3] == "A" # mode


def test_detect_and_handle_outliers():
    df = pd.DataFrame({"salary": [50000, 52000, 48000, 51000, 49000, 53000, 1000000]})
    outliers = detect_outliers(df, method="iqr")
    assert "salary" in outliers
    assert outliers["salary"]["outlier_count"] == 1
    
    # Test capping
    df_capped, _ = handle_outliers(df, outliers, action="cap")
    assert df_capped["salary"].max() < 1000000
    
    # Test removal
    df_removed, _ = handle_outliers(df, outliers, action="remove")
    assert len(df_removed) == 6


def test_validation_and_quality_score(sample_raw_sales_df):
    report = validate_data(sample_raw_sales_df)
    assert report["total_rows"] == 5
    assert report["total_columns"] == 9
    assert report["quality_score"] > 0
    assert "quality_grade" in report
    assert "dimensions" in report


def test_transformation_features():
    df = pd.DataFrame({
        "order_date": pd.to_datetime(["2026-05-10", "2026-06-15"]),
        "quantity": [3, 4],
        "unit_price": [100.0, 250.0],
        "first_name": ["John", "Jane"],
        "last_name": ["Doe", "Smith"]
    })
    transformed_df, applied = transform_data(df)
    
    assert "order_year" in transformed_df.columns
    assert "revenue" in transformed_df.columns
    assert transformed_df["revenue"].iloc[0] == 300.0
    assert transformed_df["revenue"].iloc[1] == 1000.0
    assert "full_name" in transformed_df.columns
    assert transformed_df["full_name"].iloc[0] == "John Doe"


def test_kpi_and_analyzer():
    df = pd.DataFrame({
        "revenue": [500.0, 1500.0, 2000.0],
        "quantity": [2, 5, 8],
        "product_category": ["Tech", "Tech", "Office"]
    })
    kpis = calculate_kpis(df)
    assert "total_records" in kpis
    assert "total_revenue" in kpis
    assert kpis["total_revenue"]["raw"] == 4000.0
    assert "top_category" in kpis

    summary = generate_statistical_summary(df)
    assert not summary.empty
    assert "revenue" in summary["Column"].values

    aggs = generate_aggregations(df)
    assert "by_category" in aggs


def test_multi_format_report_generation(sample_raw_sales_df, tmp_path):
    # Run full pipeline
    clean_df, audit_log = clean_data(sample_raw_sales_df)
    transformed_df, _ = transform_data(clean_df)
    raw_val = validate_data(sample_raw_sales_df)
    clean_val = validate_data(transformed_df)
    kpis = calculate_kpis(transformed_df)
    aggs = generate_aggregations(transformed_df)
    insights = generate_insights(raw_val, clean_val, audit_log, kpis, aggs)

    # 1. Excel Report
    excel_path = str(tmp_path / "test_report.xlsx")
    generate_excel_report(
        sample_raw_sales_df, transformed_df, raw_val, clean_val,
        audit_log, kpis, aggs, insights, output_path_or_buffer=excel_path
    )
    assert os.path.exists(excel_path)
    assert os.path.getsize(excel_path) > 0

    # 2. PDF Report
    pdf_path = str(tmp_path / "test_report.pdf")
    generate_pdf_report(
        transformed_df, raw_val, clean_val, audit_log, kpis, insights,
        output_path_or_buffer=pdf_path
    )
    assert os.path.exists(pdf_path)
    assert os.path.getsize(pdf_path) > 0

    # 3. HTML Report
    html_path = str(tmp_path / "test_report.html")
    generate_html_report(
        transformed_df, raw_val, clean_val, audit_log, kpis, insights,
        output_path_or_buffer=html_path
    )
    assert os.path.exists(html_path)
    assert os.path.getsize(html_path) > 0

    # 4. CSV Export
    csv_path = str(tmp_path / "cleaned_data.csv")
    export_cleaned_data(transformed_df, filepath_or_buffer=csv_path, file_format="csv")
    assert os.path.exists(csv_path)


def test_edge_case_empty_dataframe():
    empty_df = pd.DataFrame()
    val = validate_data(empty_df)
    assert val["is_empty"] is True
    assert val["quality_score"] == 0.0

    clean_empty, audit = clean_data(empty_df)
    assert len(clean_empty) == 0
