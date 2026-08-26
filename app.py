"""
Data Cleaning & Reporting Automation — Streamlit Web Application
An end-to-end automated platform for data ingestion, quality validation,
cleaning, transformation, analytics, visualization, and multi-format reporting.
"""
import os
import io
import time
import pandas as pd
import numpy as np
import streamlit as st

# Custom modules
from src.data_loader import load_data, get_excel_sheet_names
from src.validator import validate_data
from src.cleaner import clean_data
from src.transformer import transform_data
from src.analyzer import calculate_kpis, generate_statistical_summary, generate_aggregations
from src.visualizer import (
    create_quality_gauge, create_before_after_missing_chart,
    create_trend_chart, create_category_bar_chart, create_donut_chart,
    create_distribution_chart, create_correlation_heatmap
)
from src.insights import generate_insights
from src.report_generator import (
    generate_excel_report, generate_pdf_report, generate_html_report, export_cleaned_data
)
from src.logger import log_event, get_audit_trail, clear_audit_trail


# -------------------------------------------------------------
# Streamlit App Configuration & Styling
# -------------------------------------------------------------
st.set_page_config(
    page_title="Data Cleaning & Reporting Automation",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for Modern, Sleek, Professional Interface
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

    html, body, [class*="css"] {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    
    /* Header Container */
    .main-header {
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 50%, #3b82f6 100%);
        padding: 24px 30px;
        border-radius: 14px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 4px 14px 0 rgba(37, 99, 235, 0.2);
    }
    .main-header h1 {
        font-size: 28px;
        font-weight: 700;
        margin: 0;
        color: white;
        letter-spacing: -0.5px;
    }
    .main-header p {
        font-size: 14px;
        color: #e0e7ff;
        margin: 6px 0 0 0;
        font-weight: 400;
    }

    /* Metric Cards */
    .metric-card {
        background: white;
        border-radius: 10px;
        padding: 16px 20px;
        border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.08);
    }
    .metric-title {
        font-size: 12px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: 700;
        color: #0f172a;
        margin: 4px 0;
    }
    .metric-delta {
        font-size: 11px;
        font-weight: 500;
    }
    .delta-positive { color: #16a34a; }
    .delta-neutral { color: #64748b; }

    /* Workflow Pipeline Steps */
    .step-pill {
        display: inline-block;
        padding: 4px 10px;
        background: #f1f5f9;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        color: #334155;
        margin-right: 6px;
        margin-bottom: 8px;
    }
    .step-pill.active {
        background: #2563eb;
        color: white;
    }

    /* Card Containers */
    .custom-card {
        background: white;
        border-radius: 10px;
        padding: 20px;
        border: 1px solid #e2e8f0;
        margin-bottom: 20px;
    }

    /* Section Subheaders */
    .section-title {
        font-size: 16px;
        font-weight: 600;
        color: #1e293b;
        margin-bottom: 12px;
        border-left: 4px solid #2563eb;
        padding-left: 8px;
    }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Application Header
# -------------------------------------------------------------
st.markdown("""
<div class="main-header">
    <h1>⚡ Data Cleaning & Reporting Automation</h1>
    <p>Automate data validation, cleaning, transformation, analysis, visual summaries, and executive reports.</p>
</div>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Sidebar: Ingestion, Sample Data, Cleaning Configuration
# -------------------------------------------------------------
st.sidebar.title("🛠️ Control Center")

st.sidebar.markdown("### 1. Data Ingestion")
sample_choice = st.sidebar.selectbox(
    "Load Sample Business Dataset:",
    [
        "None (Upload my own file)",
        "Messy Sales Data (CSV)",
        "Messy Customer Data (Excel)",
        "Messy Employee Data (CSV)",
        "Messy Financial Data (Excel)"
    ]
)

uploaded_file = st.sidebar.file_uploader(
    "Or upload your CSV / Excel file:",
    type=["csv", "xlsx", "xls", "txt"],
    help="Supports comma/semicolon CSVs and multi-sheet Excel files."
)

# Sheet selection for Excel
selected_sheet = 0
if uploaded_file and uploaded_file.name.lower().endswith((".xlsx", ".xls")):
    sheets = get_excel_sheet_names(uploaded_file)
    if len(sheets) > 1:
        selected_sheet = st.sidebar.selectbox("Select Excel Sheet:", sheets)

st.sidebar.markdown("---")
st.sidebar.markdown("### 2. Cleaning Configuration")

with st.sidebar.expander("⚙️ Pipeline Rules & Defaults", expanded=True):
    opt_std_names = st.checkbox("Standardize Column Names (snake_case)", value=True)
    opt_remove_dups = st.checkbox("Remove Exact Duplicate Rows", value=True)
    opt_convert_types = st.checkbox("Convert Currency / Date / Booleans", value=True)
    opt_fix_negatives = st.checkbox("Fix Negative Values in Positive Fields", value=True)
    opt_std_cats = st.checkbox("Standardize Categorical Casing & Domains", value=True)
    opt_handle_missing = st.checkbox("Handle Missing Values", value=True)
    
    num_missing_strat = st.selectbox(
        "Numeric Missing Strategy:",
        ["median", "mean", "zero", "drop_row"],
        index=0
    )
    cat_missing_strat = st.selectbox(
        "Categorical Missing Strategy:",
        ["mode_or_unknown", "mode", "constant_unknown", "drop_row"],
        index=0
    )

with st.sidebar.expander("📊 Outlier Handling", expanded=False):
    outlier_method = st.radio("Detection Method:", ["iqr", "zscore"], index=0)
    outlier_action = st.selectbox("Action for Detected Outliers:", ["keep", "cap", "remove"], index=0,
                                  help="'keep' flags them safely, 'cap' clips them to bounds, 'remove' drops them.")

cleaning_options = {
    "standardize_names": opt_std_names,
    "remove_dups": opt_remove_dups,
    "convert_types": opt_convert_types,
    "fix_negatives": opt_fix_negatives,
    "standardize_cats": opt_std_cats,
    "handle_missing": opt_handle_missing,
    "numeric_missing_strategy": num_missing_strat,
    "categorical_missing_strategy": cat_missing_strat,
    "outlier_method": outlier_method,
    "outlier_action": outlier_action
}


# -------------------------------------------------------------
# Data Loading Logic
# -------------------------------------------------------------
raw_df = None
file_meta = {}

if uploaded_file is not None:
    raw_df, file_meta = load_data(
        file_source=uploaded_file,
        file_name=uploaded_file.name,
        sheet_name=selected_sheet
    )
elif sample_choice != "None (Upload my own file)":
    sample_paths = {
        "Messy Sales Data (CSV)": "data/raw/messy_sales_data.csv",
        "Messy Customer Data (Excel)": "data/raw/messy_customer_data.xlsx",
        "Messy Employee Data (CSV)": "data/raw/messy_employee_data.csv",
        "Messy Financial Data (Excel)": "data/raw/messy_financial_data.xlsx"
    }
    path = sample_paths[sample_choice]
    if os.path.exists(path):
        raw_df, file_meta = load_data(path, file_name=os.path.basename(path))
    else:
        st.error(f"Sample dataset file not found at '{path}'. Please run the sample data generator.")


# -------------------------------------------------------------
# Main Application Flow
# -------------------------------------------------------------
if raw_df is None or raw_df.empty:
    st.info("👋 Welcome! Please upload a CSV / Excel file or select one of the realistic sample business datasets from the sidebar to begin.")
    
    st.markdown("### 🚀 Automated Workflow Demonstration")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        **1. Ingestion & Validation**
        - Multi-format loader (CSV/Excel)
        - Data quality health scoring
        - Missingness & duplicate detection
        """)
    with col2:
        st.markdown("""
        **2. Intelligent Cleaning**
        - snake_case standardization
        - Currency symbol & comma stripping
        - Multi-format date parsing
        """)
    with col3:
        st.markdown("""
        **3. Analytics & Charts**
        - Dynamic business KPI engine
        - Interactive Plotly visualizations
        - Outlier spread & distributions
        """)
    with col4:
        st.markdown("""
        **4. Executive Reporting**
        - Styled Multi-Sheet Excel (.xlsx)
        - Executive PDF Business Report
        - Interactive HTML & Clean CSV
        """)
    st.stop()

# -------------------------------------------------------------
# Pipeline Execution (Validation -> Cleaning -> Transformation -> Analysis -> Insights)
# -------------------------------------------------------------

# Step 1: Raw Validation
raw_validation = validate_data(raw_df)

# Step 2: Automated Cleaning
clean_df, audit_log = clean_data(raw_df, cleaning_options)

# Step 3: Transformation & Feature Engineering
transformed_df, transformations = transform_data(clean_df)

# Step 4: Cleaned Validation
clean_validation = validate_data(transformed_df)

# Step 5: KPIs & Statistical Aggregations
kpis = calculate_kpis(transformed_df)
stat_summary = generate_statistical_summary(transformed_df)
aggregations = generate_aggregations(transformed_df)

# Step 6: Automated Insights Engine
insights = generate_insights(raw_validation, clean_validation, audit_log, kpis, aggregations)


# -------------------------------------------------------------
# Progress Pipeline Badge Bar
# -------------------------------------------------------------
st.markdown("""
<div style="margin-bottom: 15px;">
    <span class="step-pill active">1. Ingestion ✅</span>
    <span class="step-pill active">2. Validation ✅</span>
    <span class="step-pill active">3. Cleaning ✅</span>
    <span class="step-pill active">4. Transformation ✅</span>
    <span class="step-pill active">5. KPIs & Analytics ✅</span>
    <span class="step-pill active">6. Visual Summary ✅</span>
    <span class="step-pill active">7. Insights ✅</span>
    <span class="step-pill active">8. Multi-Format Export ✅</span>
</div>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Quick Scorecard Hero Metrics
# -------------------------------------------------------------
col_m1, col_m2, col_m3, col_m4, col_m5 = st.columns(5)

raw_score = raw_validation.get("quality_score", 0.0)
clean_score = clean_validation.get("quality_score", 100.0)
score_diff = clean_score - raw_score

with col_m1:
    st.metric(
        label="Data Health Score",
        value=f"{clean_score:.0f}/100",
        delta=f"+{score_diff:.1f} pts ({clean_validation.get('quality_grade', '')})",
        delta_color="normal"
    )

with col_m2:
    dups_removed = audit_log.get("duplicates_removed", 0)
    st.metric(
        label="Total Active Rows",
        value=f"{len(transformed_df):,}",
        delta=f"-{dups_removed} duplicates" if dups_removed > 0 else "0 duplicates",
        delta_color="inverse" if dups_removed > 0 else "off"
    )

with col_m3:
    raw_missing = raw_validation.get("missing_report", {}).get("total_missing", 0)
    clean_missing = clean_validation.get("missing_report", {}).get("total_missing", 0)
    st.metric(
        label="Missing Cells",
        value=f"{clean_missing:,}",
        delta=f"-{raw_missing - clean_missing:,} resolved" if raw_missing > 0 else "0 missing",
        delta_color="inverse" if raw_missing > 0 else "off"
    )

with col_m4:
    st.metric(
        label="Columns Processed",
        value=f"{len(transformed_df.columns)}",
        delta=f"+{len(transformations)} engineered" if transformations else "Standardized",
        delta_color="normal"
    )

with col_m5:
    rev_kpi = kpis.get("total_revenue", {}).get("value", "N/A")
    st.metric(
        label="Total Business Value",
        value=rev_kpi,
        delta=kpis.get("top_category", {}).get("label", "Automated"),
        delta_color="off"
    )

st.markdown("<br>", unsafe_allow_html=True)


# -------------------------------------------------------------
# Main Dashboard Tabs
# -------------------------------------------------------------
tab_overview, tab_quality, tab_cleaning, tab_kpi, tab_charts, tab_insights, tab_export, tab_logs = st.tabs([
    "📋 Data Overview",
    "🩺 Quality Diagnostics",
    "✨ Cleaning & Audit Log",
    "📈 KPIs & Analytics",
    "📊 Visual Summary",
    "💡 Automated Insights",
    "📥 Export & Reports",
    "📜 Pipeline Logs"
])


# -------------------------------------------------------------
# Tab 1: Data Overview
# -------------------------------------------------------------
with tab_overview:
    st.markdown('<div class="section-title">Dataset Profile & Interactive Explorer</div>', unsafe_allow_html=True)
    
    col_info1, col_info2, col_info3 = st.columns([1, 1, 2])
    with col_info1:
        st.write(f"**File Name:** `{file_meta.get('file_name', 'Unknown')}`")
        st.write(f"**Format:** `{file_meta.get('file_type', 'CSV')}`")
    with col_info2:
        st.write(f"**Size on Disk:** `{file_meta.get('file_size_kb', 0)} KB`")
        st.write(f"**Memory Footprint:** `{file_meta.get('memory_kb', 0)} KB`")
    with col_info3:
        st.write(f"**Initial Shape:** `{raw_validation['total_rows']} rows × {raw_validation['total_columns']} columns`")
        st.write(f"**Cleaned Shape:** `{clean_validation['total_rows']} rows × {clean_validation['total_columns']} columns`")

    st.markdown("---")

    col_view_opt1, col_view_opt2 = st.columns([1, 3])
    with col_view_opt1:
        view_mode = st.radio("Dataset View Mode:", ["Cleaned & Transformed Data", "Raw Uploaded Data"], horizontal=True)
    
    active_df = transformed_df if view_mode == "Cleaned & Transformed Data" else raw_df

    # Search & Filter Controls
    with col_view_opt2:
        search_query = st.text_input("🔍 Search rows (text filter across all columns):", placeholder="Type customer, category, ID...")

    filtered_df = active_df
    if search_query:
        mask = active_df.astype(str).apply(lambda row: row.str.contains(search_query, case=False).any(), axis=1)
        filtered_df = active_df[mask]

    # Pagination
    page_size = 15
    total_pages = max(1, (len(filtered_df) - 1) // page_size + 1)
    
    col_pg1, col_pg2, col_pg3 = st.columns([1, 2, 2])
    with col_pg1:
        page = st.number_input("Page:", min_value=1, max_value=total_pages, value=1, step=1)
    with col_pg2:
        st.caption(f"Showing rows {(page-1)*page_size + 1} to {min(page*page_size, len(filtered_df))} of {len(filtered_df):,} rows")

    start_idx = (page - 1) * page_size
    end_idx = start_idx + page_size
    st.dataframe(filtered_df.iloc[start_idx:end_idx], use_container_width=True)


# -------------------------------------------------------------
# Tab 2: Quality Diagnostics
# -------------------------------------------------------------
with tab_quality:
    st.markdown('<div class="section-title">Comprehensive Data Quality Health Assessment</div>', unsafe_allow_html=True)
    
    col_q1, col_q2 = st.columns([1, 2])
    with col_q1:
        gauge_fig = create_quality_gauge(raw_score, raw_validation.get("quality_grade", ""))
        st.plotly_chart(gauge_fig, use_container_width=True)
        
        dims = raw_validation.get("dimensions", {})
        st.markdown(f"""
        **Quality Dimensions Breakdown:**
        - **Completeness:** `{dims.get('completeness', 0)}%`
        - **Uniqueness:** `{dims.get('uniqueness', 0)}%`
        - **Validity:** `{dims.get('validity', 0)}%`
        - **Consistency:** `{dims.get('consistency', 0)}%`
        """)

    with col_q2:
        st.markdown("**Identified Data Hygiene Issues:**")
        for issue in raw_validation.get("issues_summary", []):
            st.warning(f"⚠️ {issue}")

    st.markdown("---")
    st.markdown('<div class="section-title">Column Missingness & Cardinality Breakdown</div>', unsafe_allow_html=True)
    
    # Missingness Table
    missing_table_rows = []
    r_missing_cols = raw_validation.get("missing_report", {}).get("columns", {})
    cardinality = raw_validation.get("cardinality", {})
    inferred = raw_validation.get("inferred_types", {})

    for col in raw_df.columns:
        m_info = r_missing_cols.get(col, {"count": 0, "pct": 0.0})
        c_info = cardinality.get(col, {"unique_count": 0, "unique_pct": 0.0})
        missing_table_rows.append({
            "Column Name": col,
            "Raw Missing Count": m_info["count"],
            "Missing %": f"{m_info['pct']}%",
            "Unique Values": c_info["unique_count"],
            "Inferred Semantic Type": inferred.get(col, "standard"),
            "Original Data Type": str(raw_df[col].dtype)
        })

    st.dataframe(pd.DataFrame(missing_table_rows), use_container_width=True)


# -------------------------------------------------------------
# Tab 3: Cleaning Studio & Audit Log
# -------------------------------------------------------------
with tab_cleaning:
    st.markdown('<div class="section-title">Before vs After Cleaning Comparison</div>', unsafe_allow_html=True)
    
    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    with col_c1:
        st.metric("Missing Values", f"{clean_validation['missing_report']['total_missing']}", f"-{raw_missing - clean_missing} resolved", delta_color="inverse")
    with col_c2:
        st.metric("Duplicate Rows", f"{clean_validation['duplicate_report']['duplicate_count']}", f"-{dups_removed} removed", delta_color="inverse")
    with col_c3:
        st.metric("Columns Standardized", f"{len(audit_log.get('column_renaming', {}))}", "snake_case applied")
    with col_c4:
        st.metric("Features Engineered", f"{len(transformations)}", "Domain transformations")

    # Missing value visual comparison
    missing_chart = create_before_after_missing_chart(raw_df, clean_df)
    if missing_chart:
        st.plotly_chart(missing_chart, use_container_width=True)

    st.markdown("---")
    st.markdown('<div class="section-title">Step-by-Step Cleaning Audit Changelog</div>', unsafe_allow_html=True)
    
    for idx, step in enumerate(audit_log.get("steps_executed", []), start=1):
        st.markdown(f"**Step {idx}:** {step}")

    with st.expander("🔍 View Column Renaming Mapping (Original → snake_case)"):
        st.json(audit_log.get("column_renaming", {}))

    if audit_log.get("types_converted"):
        with st.expander("🔍 View Data Type Conversions"):
            st.json(audit_log.get("types_converted", {}))

    if audit_log.get("outlier_detection"):
        with st.expander("🔍 View Outlier Detection Details (Bounds & Counts)"):
            st.json(audit_log.get("outlier_detection", {}))


# -------------------------------------------------------------
# Tab 4: KPIs & Analytics
# -------------------------------------------------------------
with tab_kpi:
    st.markdown('<div class="section-title">Dynamic Business KPI Intelligence</div>', unsafe_allow_html=True)
    
    # KPI Grid
    kpi_cols = st.columns(len(kpis) if len(kpis) <= 4 else 4)
    for idx, (k_name, k_info) in enumerate(kpis.items()):
        col_idx = idx % 4
        with kpi_cols[col_idx]:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-title">{k_info.get('label', k_name)}</div>
                <div class="metric-value">{k_info.get('value', '')}</div>
                <div class="metric-delta delta-neutral">{k_info.get('description', '')}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">Numerical Extended Statistical Summary</div>', unsafe_allow_html=True)
    
    if not stat_summary.empty:
        st.dataframe(stat_summary, use_container_width=True)
    else:
        st.info("No numeric columns available for statistical profiling.")

    st.markdown("---")
    st.markdown('<div class="section-title">Grouped Dimensional Breakdowns</div>', unsafe_allow_html=True)
    
    if aggregations:
        agg_tab_names = [k.replace("_", " ").title() for k in aggregations.keys()]
        agg_tabs = st.tabs(agg_tab_names)
        for t_idx, (agg_key, agg_df) in enumerate(aggregations.items()):
            with agg_tabs[t_idx]:
                st.dataframe(agg_df, use_container_width=True)
    else:
        st.info("No categorical dimensions found for grouped breakdowns.")


# -------------------------------------------------------------
# Tab 5: Visual Summary
# -------------------------------------------------------------
with tab_charts:
    st.markdown('<div class="section-title">Interactive Visual Analytics & Distributions</div>', unsafe_allow_html=True)
    
    col_ch1, col_ch2 = st.columns(2)

    # 1. Trend Chart
    with col_ch1:
        time_col = None
        for tc in ["order_month_year", "month_year", "order_date", "signup_date", "fiscal_quarter"]:
            if tc in transformed_df.columns:
                time_col = tc
                break
        
        num_col = None
        for nc in ["calculated_revenue", "net_revenue", "revenue", "gross_revenue", "total_amount", "salary", "annual_income"]:
            if nc in transformed_df.columns and pd.api.types.is_numeric_dtype(transformed_df[nc]):
                num_col = nc
                break
        
        if not num_col:
            num_cols = transformed_df.select_dtypes(include=[np.number]).columns
            num_col = num_cols[0] if len(num_cols) > 0 else None

        if time_col and num_col:
            trend_fig = create_trend_chart(transformed_df, time_col, num_col)
            if trend_fig:
                st.plotly_chart(trend_fig, use_container_width=True)
            else:
                st.info("Time-series trend could not be plotted.")
        else:
            st.info("No date/time column detected for trend plotting.")

    # 2. Category Performance Chart
    with col_ch2:
        cat_col = None
        for cc in ["product_category", "category", "department", "business_unit", "customer_segment"]:
            if cc in transformed_df.columns:
                cat_col = cc
                break
        
        if cat_col and num_col:
            cat_fig = create_category_bar_chart(transformed_df, cat_col, num_col)
            if cat_fig:
                st.plotly_chart(cat_fig, use_container_width=True)
        elif cat_col:
            donut_fig = create_donut_chart(transformed_df, cat_col)
            if donut_fig:
                st.plotly_chart(donut_fig, use_container_width=True)

    col_ch3, col_ch4 = st.columns(2)

    # 3. Regional / Donut Distribution Chart
    with col_ch3:
        reg_col = None
        for rc in ["region", "location", "city", "gender", "status", "payment_method"]:
            if rc in transformed_df.columns:
                reg_col = rc
                break
        
        if reg_col:
            donut_fig = create_donut_chart(transformed_df, reg_col, num_col)
            if donut_fig:
                st.plotly_chart(donut_fig, use_container_width=True)

    # 4. Outlier & Distribution Histogram
    with col_ch4:
        if num_col:
            dist_fig = create_distribution_chart(transformed_df, num_col)
            if dist_fig:
                st.plotly_chart(dist_fig, use_container_width=True)

    # 5. Correlation Heatmap
    st.markdown("---")
    corr_fig = create_correlation_heatmap(transformed_df)
    if corr_fig:
        st.plotly_chart(corr_fig, use_container_width=True)


# -------------------------------------------------------------
# Tab 6: Automated Insights
# -------------------------------------------------------------
with tab_insights:
    st.markdown('<div class="section-title">Automated Business Intelligence & Strategic Recommendations</div>', unsafe_allow_html=True)
    
    col_ins1, col_ins2 = st.columns(2)
    with col_ins1:
        st.markdown("#### 🩺 Data Quality & Hygiene Insights")
        for q_ins in insights.get("quality_insights", []):
            st.success(f"✔️ {q_ins}")

        st.markdown("#### 🔍 Anomaly & Outlier Diagnostics")
        for a_ins in insights.get("anomaly_insights", []):
            st.info(f"📊 {a_ins}")

    with col_ins2:
        st.markdown("#### 📈 Business Performance Findings")
        for b_ins in insights.get("business_insights", []):
            st.markdown(f"💡 **Finding:** {b_ins}")

        st.markdown("#### 🎯 Strategic Actionable Recommendations")
        for r_ins in insights.get("recommendations", []):
            st.warning(f"🚀 **Action:** {r_ins}")


# -------------------------------------------------------------
# Tab 7: Multi-Format Export Studio
# -------------------------------------------------------------
with tab_export:
    st.markdown('<div class="section-title">Multi-Format Export Studio</div>', unsafe_allow_html=True)
    st.write("Generate and download publication-ready reports and clean data in multiple formats.")

    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        st.markdown("### 📊 Styled Multi-Sheet Excel Report")
        st.write("Contains separate formatted sheets: Executive Summary, Quality Scorecard, Cleaning Audit Log, KPIs, and Cleaned Data.")
        
        with st.spinner("Compiling styled Excel workbook..."):
            excel_report_bytes = generate_excel_report(
                raw_df, transformed_df, raw_validation, clean_validation,
                audit_log, kpis, aggregations, insights
            )

        st.download_button(
            label="📥 Download Styled Excel Report (.xlsx)",
            data=excel_report_bytes,
            file_name=f"Automated_Report_{file_meta.get('file_name', 'data').split('.')[0]}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 📄 Executive PDF Business Report")
        st.write("Formal PDF document with cover title, Executive Summary, Scorecard, KPI grid, embedded chart, and recommendations.")
        
        with st.spinner("Generating Executive PDF..."):
            pdf_report_bytes = generate_pdf_report(
                transformed_df, raw_validation, clean_validation,
                audit_log, kpis, insights
            )

        st.download_button(
            label="📥 Download Executive PDF Report (.pdf)",
            data=pdf_report_bytes,
            file_name=f"Executive_Summary_{file_meta.get('file_name', 'data').split('.')[0]}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    with col_exp2:
        st.markdown("### 🌐 Standalone Interactive HTML Report")
        st.write("Responsive single-page web report with KPI cards, audit summary, insights, and data preview.")
        
        html_report_bytes = generate_html_report(
            transformed_df, raw_validation, clean_validation,
            audit_log, kpis, insights
        )

        st.download_button(
            label="📥 Download Interactive HTML Report (.html)",
            data=html_report_bytes,
            file_name=f"Executive_Report_{file_meta.get('file_name', 'data').split('.')[0]}.html",
            mime="text/html",
            use_container_width=True
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("### 💾 Cleaned Dataset Exports")
        st.write("Direct raw cleaned dataset files for downstream SQL databases or ML pipelines.")
        
        col_c_csv, col_c_xls = st.columns(2)
        with col_c_csv:
            csv_clean_bytes = export_cleaned_data(transformed_df, file_format="csv")
            st.download_button(
                label="📥 Cleaned CSV (.csv)",
                data=csv_clean_bytes,
                file_name=f"cleaned_{file_meta.get('file_name', 'data').split('.')[0]}.csv",
                mime="text/csv",
                use_container_width=True
            )
        with col_c_xls:
            xls_clean_bytes = export_cleaned_data(transformed_df, file_format="xlsx")
            st.download_button(
                label="📥 Cleaned Excel (.xlsx)",
                data=xls_clean_bytes,
                file_name=f"cleaned_{file_meta.get('file_name', 'data').split('.')[0]}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )


# -------------------------------------------------------------
# Tab 8: System Logs
# -------------------------------------------------------------
with tab_logs:
    st.markdown('<div class="section-title">Operational Pipeline Logs & Execution Audit</div>', unsafe_allow_html=True)
    
    logs_data = get_audit_trail()
    if logs_data:
        logs_df = pd.DataFrame(logs_data)
        st.dataframe(logs_df, use_container_width=True)
    else:
        st.info("No active logs recorded.")
    
    if st.button("Clear In-Memory Audit Logs"):
        clear_audit_trail()
        st.rerun()
