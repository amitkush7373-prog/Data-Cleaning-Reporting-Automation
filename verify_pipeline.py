"""
End-to-End Pipeline Verification Script.
Processes all sample datasets (Sales, Customer, Employee, Financial),
executes the full pipeline, and generates reports.
"""
import os
import sys
from src.data_loader import load_data
from src.validator import validate_data
from src.cleaner import clean_data
from src.transformer import transform_data
from src.analyzer import calculate_kpis, generate_statistical_summary, generate_aggregations
from src.insights import generate_insights
from src.report_generator import (
    generate_excel_report, generate_pdf_report, generate_html_report, export_cleaned_data
)

os.makedirs("reports", exist_ok=True)
os.makedirs("data/processed", exist_ok=True)

sample_files = [
    ("Sales", "data/raw/messy_sales_data.csv"),
    ("Customer", "data/raw/messy_customer_data.xlsx"),
    ("Employee", "data/raw/messy_employee_data.csv"),
    ("Financial", "data/raw/messy_financial_data.xlsx")
]

print("="*70)
print("STARTING END-TO-END AUTOMATION PIPELINE VERIFICATION")
print("="*70)

for name, filepath in sample_files:
    print(f"\n[Processing Dataset: {name}] ({filepath})")
    
    # 1. Ingestion
    raw_df, meta = load_data(filepath, file_name=os.path.basename(filepath))
    assert raw_df is not None, f"Failed to load {name}"
    print(f" -> Loaded: {meta['rows']} rows, {meta['columns']} cols, Size: {meta['file_size_kb']} KB")
    
    # 2. Raw Validation
    raw_val = validate_data(raw_df)
    print(f" -> Initial Health Score: {raw_val['quality_score']}/100 [{raw_val['quality_grade']}]")
    print(f" -> Issues Found: {len(raw_val['issues_summary'])}")
    
    # 3. Cleaning
    clean_df, audit_log = clean_data(raw_df)
    print(f" -> Cleaned Shape: {len(clean_df)} rows, {len(clean_df.columns)} cols")
    print(f" -> Duplicates Removed: {audit_log['duplicates_removed']}, Types Converted: {len(audit_log['types_converted'])}")
    
    # 4. Transformation
    transformed_df, transformations = transform_data(clean_df)
    print(f" -> Transformations Created: {len(transformations)}")
    
    # 5. Post-Cleaning Validation
    clean_val = validate_data(transformed_df)
    print(f" -> Cleaned Health Score: {clean_val['quality_score']}/100 [{clean_val['quality_grade']}]")
    
    # 6. Analytics & KPIs
    kpis = calculate_kpis(transformed_df)
    summary_df = generate_statistical_summary(transformed_df)
    aggs = generate_aggregations(transformed_df)
    print(f" -> KPIs Calculated: {list(kpis.keys())}")
    
    # 7. Insights
    insights = generate_insights(raw_val, clean_val, audit_log, kpis, aggs)
    print(f" -> Insights Generated: {len(insights['quality_insights'])} quality, {len(insights['business_insights'])} business, {len(insights['recommendations'])} recommendations")
    
    # 8. Multi-Format Report Export
    excel_out = f"reports/{name}_Automated_Report.xlsx"
    pdf_out = f"reports/{name}_Executive_Report.pdf"
    html_out = f"reports/{name}_Interactive_Report.html"
    csv_out = f"data/processed/cleaned_{name.lower()}_data.csv"
    
    generate_excel_report(raw_df, transformed_df, raw_val, clean_val, audit_log, kpis, aggs, insights, output_path_or_buffer=excel_out)
    generate_pdf_report(transformed_df, raw_val, clean_val, audit_log, kpis, insights, output_path_or_buffer=pdf_out)
    generate_html_report(transformed_df, raw_val, clean_val, audit_log, kpis, insights, output_path_or_buffer=html_out)
    export_cleaned_data(transformed_df, filepath_or_buffer=csv_out, file_format="csv")
    
    assert os.path.exists(excel_out) and os.path.getsize(excel_out) > 0, f"Excel report failed for {name}"
    assert os.path.exists(pdf_out) and os.path.getsize(pdf_out) > 0, f"PDF report failed for {name}"
    assert os.path.exists(html_out) and os.path.getsize(html_out) > 0, f"HTML report failed for {name}"
    assert os.path.exists(csv_out) and os.path.getsize(csv_out) > 0, f"CSV export failed for {name}"
    
    print(f" -> Reports Generated: Excel ({os.path.getsize(excel_out):,} B), PDF ({os.path.getsize(pdf_out):,} B), HTML ({os.path.getsize(html_out):,} B), CSV ({os.path.getsize(csv_out):,} B)")

print("\n" + "="*70)
print("ALL 4 SAMPLE DATASETS PROCESSED AND VERIFIED SUCCESSFULLY!")
print("="*70)
