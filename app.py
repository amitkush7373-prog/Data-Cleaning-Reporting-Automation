"""
Data Cleaning & Reporting Automation — Streamlit Web Application
An enterprise-grade, modern SaaS platform for automated data profiling,
validation, cleaning, transformation, analytics, visualization, and multi-format reporting.
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

# -------------------------------------------------------------
# Centralized SaaS Analytics Design System (CSS)
# -------------------------------------------------------------
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=Inter:wght@300;400;500;600;700&display=swap');

    :root {
        --font-primary: 'Plus Jakarta Sans', 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        --color-bg-gradient: linear-gradient(180deg, #f8fafc 0%, #f1f5f9 50%, #eef2ff 100%);
        --color-surface: #ffffff;
        --color-surface-glass: rgba(255, 255, 255, 0.95);
        --color-border: #e2e8f0;
        --color-text-main: #0f172a;
        --color-text-muted: #64748b;
        --shadow-subtle: 0 4px 20px -2px rgba(15, 23, 42, 0.05);
        --shadow-hover: 0 12px 28px -4px rgba(15, 23, 42, 0.1);
    }

    html, body, [class*="css"] {
        font-family: var(--font-primary);
        color: var(--color-text-main);
    }

    /* Background smoothing */
    [data-testid="stAppViewContainer"] {
        background: var(--color-bg-gradient);
    }

    /* Main Container Padding */
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }

    /* Hero Banner Component */
    .hero-banner {
        background: linear-gradient(135deg, #1e3a8a 0%, #2563eb 55%, #4f46e5 100%);
        border-radius: 16px;
        padding: 28px 32px;
        color: white;
        margin-bottom: 20px;
        box-shadow: 0 10px 25px -5px rgba(37, 99, 235, 0.25);
        position: relative;
        overflow: hidden;
        border: 1px solid rgba(255, 255, 255, 0.15);
    }
    .hero-banner::after {
        content: "";
        position: absolute;
        top: -60%;
        right: -8%;
        width: 380px;
        height: 380px;
        background: radial-gradient(circle, rgba(255,255,255,0.15) 0%, rgba(255,255,255,0) 70%);
        border-radius: 50%;
        pointer-events: none;
    }
    .hero-tags {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 8px;
        flex-wrap: wrap;
    }
    .hero-pill {
        background: rgba(255, 255, 255, 0.18);
        backdrop-filter: blur(8px);
        padding: 4px 12px;
        border-radius: 20px;
        font-size: 11px;
        font-weight: 700;
        letter-spacing: 0.5px;
        text-transform: uppercase;
        color: #ffffff;
        border: 1px solid rgba(255, 255, 255, 0.25);
    }
    .hero-pill-active {
        background: rgba(16, 185, 129, 0.25);
        border-color: rgba(16, 185, 129, 0.5);
    }
    .hero-title {
        font-size: 28px;
        font-weight: 800;
        margin: 0;
        color: white;
        letter-spacing: -0.5px;
        line-height: 1.2;
    }
    .hero-subtitle {
        font-size: 14px;
        color: #e0e7ff;
        margin: 6px 0 0 0;
        font-weight: 400;
        max-width: 850px;
        line-height: 1.5;
    }

    /* Pipeline Stepper Component */
    .pipeline-stepper {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        background: white;
        padding: 12px 18px;
        border-radius: 12px;
        border: 1px solid var(--color-border);
        box-shadow: var(--shadow-subtle);
        margin-bottom: 20px;
        align-items: center;
    }
    .step-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 12px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
        transition: all 0.2s ease;
    }
    .step-done {
        background: #ecfdf5;
        color: #065f46;
        border: 1px solid #a7f3d0;
    }
    .step-active {
        background: linear-gradient(135deg, #2563eb, #1d4ed8);
        color: white;
        box-shadow: 0 2px 8px rgba(37, 99, 235, 0.3);
    }

    /* KPI Grid Cards */
    .kpi-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
        gap: 16px;
        margin-bottom: 22px;
    }
    .kpi-card {
        background: white;
        border-radius: 14px;
        padding: 20px;
        border: 1px solid var(--color-border);
        box-shadow: var(--shadow-subtle);
        position: relative;
        overflow: hidden;
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-3px);
        box-shadow: var(--shadow-hover);
    }
    .kpi-card::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 4px;
    }
    .border-emerald::before { background: linear-gradient(90deg, #10b981, #34d399); }
    .border-blue::before { background: linear-gradient(90deg, #2563eb, #60a5fa); }
    .border-rose::before { background: linear-gradient(90deg, #f43f5e, #fb7185); }
    .border-purple::before { background: linear-gradient(90deg, #7c3aed, #a78bfa); }
    .border-amber::before { background: linear-gradient(90deg, #f59e0b, #fbbf24); }

    .kpi-card-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 6px;
    }
    .kpi-card-label {
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.6px;
        color: var(--color-text-muted);
    }
    .kpi-icon-pill {
        width: 32px;
        height: 32px;
        border-radius: 8px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 16px;
    }
    .kpi-val-number {
        font-size: 26px;
        font-weight: 800;
        color: #0f172a;
        margin: 4px 0;
        letter-spacing: -0.5px;
    }
    .kpi-delta-row {
        font-size: 12px;
        color: var(--color-text-muted);
        display: flex;
        align-items: center;
        gap: 6px;
        font-weight: 500;
    }
    .pill-green {
        background: #dcfce7;
        color: #15803d;
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 11px;
    }
    .pill-blue {
        background: #e0f2fe;
        color: #0369a1;
        padding: 2px 8px;
        border-radius: 12px;
        font-weight: 700;
        font-size: 11px;
    }

    /* Section Cards */
    .saas-box {
        background: white;
        border-radius: 14px;
        padding: 24px;
        border: 1px solid var(--color-border);
        box-shadow: var(--shadow-subtle);
        margin-bottom: 20px;
    }
    .saas-box-header {
        font-size: 16px;
        font-weight: 700;
        color: #0f172a;
        margin-bottom: 16px;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    /* Export Studio Cards */
    .export-box {
        background: white;
        border-radius: 14px;
        padding: 22px;
        border: 1px solid var(--color-border);
        box-shadow: var(--shadow-subtle);
        transition: all 0.2s ease;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        height: 100%;
    }
    .export-box:hover {
        border-color: #93c5fd;
        box-shadow: var(--shadow-hover);
        transform: translateY(-2px);
    }
    .export-icon-box {
        width: 42px;
        height: 42px;
        border-radius: 10px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-size: 22px;
    }

    /* Sidebar Refinement */
    [data-testid="stSidebar"] {
        background-color: #f8fafc;
        border-right: 1px solid #e2e8f0;
    }
    .brand-container {
        padding: 8px 0 16px 0;
        border-bottom: 1px solid #e2e8f0;
        margin-bottom: 16px;
    }
    .brand-title {
        font-size: 18px;
        font-weight: 800;
        color: #1e3a8a;
        margin: 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .brand-caption {
        font-size: 12px;
        color: var(--color-text-muted);
        margin: 4px 0 0 0;
    }

    /* Segmented Navigation Tabs */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #f1f5f9;
        padding: 6px;
        border-radius: 12px;
        border: 1px solid #e2e8f0;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 600;
        font-size: 13px;
        color: #64748b;
        background-color: transparent;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #2563eb !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.1);
    }
</style>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Sidebar: Control Center & Cleaning Configuration
# -------------------------------------------------------------
with st.sidebar:
    st.markdown("""
    <div class="brand-container">
        <h2 class="brand-title">⚡ Control Center</h2>
        <p class="brand-caption">Data Analytics & Reporting SaaS</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("### 📥 1. Ingestion Source")
    sample_choice = st.selectbox(
        "Load Sample Business Dataset:",
        [
            "None (Upload my own file)",
            "Messy Sales Data (CSV)",
            "Messy Customer Data (Excel)",
            "Messy Employee Data (CSV)",
            "Messy Financial Data (Excel)"
        ],
        index=0
    )

    uploaded_file = st.file_uploader(
        "Or Drag & Drop CSV / Excel File:",
        type=["csv", "xlsx", "xls", "txt"],
        help="Supports comma/semicolon CSVs and multi-sheet Excel files."
    )

    selected_sheet = 0
    if uploaded_file and uploaded_file.name.lower().endswith((".xlsx", ".xls")):
        sheets = get_excel_sheet_names(uploaded_file)
        if len(sheets) > 1:
            selected_sheet = st.selectbox("Select Excel Sheet:", sheets)

    st.markdown("---")
    st.markdown("### ⚙️ 2. Cleaning Configuration")

    with st.expander("🛠️ Cleaning Rules", expanded=True):
        opt_std_names = st.checkbox("Standardize Column Names (snake_case)", value=True)
        opt_remove_dups = st.checkbox("Remove Exact Duplicate Rows", value=True)
        opt_convert_types = st.checkbox("Convert Currency / Dates / Booleans", value=True)
        opt_fix_negatives = st.checkbox("Fix Negatives in Positive Fields", value=True)
        opt_std_cats = st.checkbox("Standardize Categorical Casing", value=True)
        opt_handle_missing = st.checkbox("Handle Missing Values", value=True)
        
        num_missing_strat = st.selectbox(
            "Numeric Strategy:",
            ["median", "mean", "zero", "drop_row"],
            index=0
        )
        cat_missing_strat = st.selectbox(
            "Categorical Strategy:",
            ["mode_or_unknown", "mode", "constant_unknown", "drop_row"],
            index=0
        )

    with st.expander("📊 Outlier Handling", expanded=False):
        outlier_method = st.radio("Method:", ["iqr", "zscore"], index=0)
        outlier_action = st.selectbox("Action for Outliers:", ["keep", "cap", "remove"], index=0,
                                      help="'keep' flags safely, 'cap' winsorizes to bounds, 'remove' drops.")

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

    st.markdown("---")
    st.caption("🟢 Pipeline Engine: Operational v1.2")


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
        st.error(f"Sample dataset file not found at '{path}'. Please run generate_sample_data.py.")


# -------------------------------------------------------------
# Application Header / Hero Banner
# -------------------------------------------------------------
st.markdown("""
<div class="hero-banner">
    <div class="hero-tags">
        <span class="hero-pill">⚡ Automated Analytics Engine</span>
        <span class="hero-pill hero-pill-active">🟢 Status: Pipeline Ready</span>
    </div>
    <h1 class="hero-title">Data Cleaning & Reporting Automation</h1>
    <p class="hero-subtitle">
        Automate raw data validation, intelligent cleaning, feature engineering, dynamic business KPIs, 
        interactive visual distributions, and publication-ready multi-format report exports in one click.
    </p>
</div>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Empty State / Landing Guide
# -------------------------------------------------------------
if raw_df is None or raw_df.empty:
    st.markdown("""
    <div class="saas-box" style="text-align: center; padding: 40px 20px;">
        <div style="font-size: 48px; margin-bottom: 12px;">📊</div>
        <h2 style="font-size: 22px; font-weight: 700; color: #0f172a; margin-bottom: 8px;">Ready to Clean & Analyze Your Dataset</h2>
        <p style="color: #64748b; font-size: 14px; max-width: 600px; margin: 0 auto 24px auto;">
            Upload your CSV or Excel business dataset from the sidebar, or select one of our pre-built realistic messy datasets to explore the automated workflow.
        </p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown("""
        <div class="saas-box">
            <div style="font-size: 24px; margin-bottom: 8px;">🩺</div>
            <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px;">1. Quality Diagnostics</div>
            <p style="font-size: 12px; color: #64748b; margin: 0;">0-100% Data Health Scorecard, missingness & duplicate anomaly checks.</p>
        </div>
        """, unsafe_allow_html=True)
    with col2:
        st.markdown("""
        <div class="saas-box">
            <div style="font-size: 24px; margin-bottom: 8px;">✨</div>
            <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px;">2. Smart Cleaning</div>
            <p style="font-size: 12px; color: #64748b; margin: 0;">snake_case names, currency stripping, multi-format dates, type casting.</p>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown("""
        <div class="saas-box">
            <div style="font-size: 24px; margin-bottom: 8px;">📈</div>
            <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px;">3. KPI Intelligence</div>
            <p style="font-size: 12px; color: #64748b; margin: 0;">Auto-discovered metrics, group-by breakdowns, and statistical summaries.</p>
        </div>
        """, unsafe_allow_html=True)
    with col4:
        st.markdown("""
        <div class="saas-box">
            <div style="font-size: 24px; margin-bottom: 8px;">📑</div>
            <div style="font-weight: 700; font-size: 14px; margin-bottom: 4px;">4. Multi-Format Export</div>
            <p style="font-size: 12px; color: #64748b; margin: 0;">Styled Excel (.xlsx), Executive PDF, standalone HTML, and clean CSV.</p>
        </div>
        """, unsafe_allow_html=True)
    st.stop()


# -------------------------------------------------------------
# Execute Complete Pipeline
# -------------------------------------------------------------
raw_validation = validate_data(raw_df)
clean_df, audit_log = clean_data(raw_df, cleaning_options)
transformed_df, transformations = transform_data(clean_df)
clean_validation = validate_data(transformed_df)
kpis = calculate_kpis(transformed_df)
stat_summary = generate_statistical_summary(transformed_df)
aggregations = generate_aggregations(transformed_df)
insights = generate_insights(raw_validation, clean_validation, audit_log, kpis, aggregations)


# -------------------------------------------------------------
# Horizontal Pipeline Stepper Tracker
# -------------------------------------------------------------
st.markdown("""
<div class="pipeline-stepper">
    <span class="step-badge step-done">✔ 1. Ingestion</span>
    <span class="step-badge step-done">✔ 2. Validation</span>
    <span class="step-badge step-done">✔ 3. Cleaning</span>
    <span class="step-badge step-done">✔ 4. Transformation</span>
    <span class="step-badge step-done">✔ 5. KPIs & Analytics</span>
    <span class="step-badge step-done">✔ 6. Visual Summary</span>
    <span class="step-badge step-done">✔ 7. Insights</span>
    <span class="step-badge step-active">⚡ 8. Multi-Format Export Ready</span>
</div>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Colorful SaaS KPI Scorecards
# -------------------------------------------------------------
raw_score = raw_validation.get("quality_score", 0.0)
clean_score = clean_validation.get("quality_score", 100.0)
score_diff = clean_score - raw_score
dups_removed = audit_log.get("duplicates_removed", 0)
raw_missing = raw_validation.get("missing_report", {}).get("total_missing", 0)
clean_missing = clean_validation.get("missing_report", {}).get("total_missing", 0)
rev_kpi = kpis.get("total_revenue", {}).get("value", "N/A")
top_cat_label = kpis.get("top_category", {}).get("label", "Automated")

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card border-emerald">
        <div class="kpi-card-header">
            <span class="kpi-card-label">Health Score</span>
            <div class="kpi-icon-pill" style="background: #d1fae5; color: #065f46;">🩺</div>
        </div>
        <div class="kpi-val-number">{clean_score:.0f}/100</div>
        <div class="kpi-delta-row">
            <span class="pill-green">+{score_diff:.1f} pts</span> {clean_validation.get('quality_grade', '')}
        </div>
    </div>
    <div class="kpi-card border-blue">
        <div class="kpi-card-header">
            <span class="kpi-card-label">Active Records</span>
            <div class="kpi-icon-pill" style="background: #dbeafe; color: #1e40af;">📋</div>
        </div>
        <div class="kpi-val-number">{len(transformed_df):,}</div>
        <div class="kpi-delta-row">
            <span class="pill-blue">-{dups_removed} dups</span> Raw: {raw_validation.get('total_rows', 0):,}
        </div>
    </div>
    <div class="kpi-card border-rose">
        <div class="kpi-card-header">
            <span class="kpi-card-label">Missing Cells</span>
            <div class="kpi-icon-pill" style="background: #ffe4e6; color: #9f1239;">✨</div>
        </div>
        <div class="kpi-val-number">{clean_missing:,}</div>
        <div class="kpi-delta-row">
            <span class="pill-green">100% Resolved</span> Was {raw_missing:,}
        </div>
    </div>
    <div class="kpi-card border-purple">
        <div class="kpi-card-header">
            <span class="kpi-card-label">Processed Columns</span>
            <div class="kpi-icon-pill" style="background: #ede9fe; color: #5b21b6;">⚙️</div>
        </div>
        <div class="kpi-val-number">{len(transformed_df.columns)}</div>
        <div class="kpi-delta-row">
            <span class="pill-blue">+{len(transformations)} engineered</span> Standardized
        </div>
    </div>
    <div class="kpi-card border-amber">
        <div class="kpi-card-header">
            <span class="kpi-card-label">Business Value</span>
            <div class="kpi-icon-pill" style="background: #fef3c7; color: #92400e;">💎</div>
        </div>
        <div class="kpi-val-number" style="font-size: 22px;">{rev_kpi}</div>
        <div class="kpi-delta-row" style="white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
            {top_cat_label}
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# -------------------------------------------------------------
# Main Navigation Tabs
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
    st.markdown('<div class="saas-box">', unsafe_allow_html=True)
    st.markdown('<div class="saas-box-header">📁 Ingestion Profile & Interactive Explorer</div>', unsafe_allow_html=True)
    
    col_info1, col_info2, col_info3 = st.columns([1, 1, 2])
    with col_info1:
        st.write(f"**File Name:** `{file_meta.get('file_name', 'Unknown')}`")
        st.write(f"**File Format:** `{file_meta.get('file_type', 'CSV')}`")
    with col_info2:
        st.write(f"**File Size:** `{file_meta.get('file_size_kb', 0)} KB`")
        st.write(f"**Memory Size:** `{file_meta.get('memory_kb', 0)} KB`")
    with col_info3:
        st.write(f"**Raw Dimensions:** `{raw_validation['total_rows']:,} rows × {raw_validation['total_columns']} columns`")
        st.write(f"**Processed Dimensions:** `{clean_validation['total_rows']:,} rows × {clean_validation['total_columns']} columns`")

    st.markdown("---")

    col_view_opt1, col_view_opt2 = st.columns([1, 3])
    with col_view_opt1:
        view_mode = st.radio("View Mode:", ["Cleaned & Transformed", "Raw Uploaded"], horizontal=True)
    
    active_df = transformed_df if view_mode == "Cleaned & Transformed" else raw_df

    with col_view_opt2:
        search_query = st.text_input("🔍 Quick Search Filter (across all attributes):", placeholder="Type keywords, names, categories, codes...")

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
    st.markdown('</div>', unsafe_allow_html=True)


# -------------------------------------------------------------
# Tab 2: Quality Diagnostics
# -------------------------------------------------------------
with tab_quality:
    col_q1, col_q2 = st.columns([1, 2])
    with col_q1:
        st.markdown('<div class="saas-box">', unsafe_allow_html=True)
        st.markdown('<div class="saas-box-header">🩺 Health Score Breakdown</div>', unsafe_allow_html=True)
        gauge_fig = create_quality_gauge(raw_score, raw_validation.get("quality_grade", ""))
        st.plotly_chart(gauge_fig, use_container_width=True)
        
        dims = raw_validation.get("dimensions", {})
        st.markdown(f"""
        **Quality Dimensions Scorecard:**
        - **Completeness:** `{dims.get('completeness', 0)}%`
        - **Uniqueness:** `{dims.get('uniqueness', 0)}%`
        - **Validity:** `{dims.get('validity', 0)}%`
        - **Consistency:** `{dims.get('consistency', 0)}%`
        """)
        st.markdown('</div>', unsafe_allow_html=True)

    with col_q2:
        st.markdown('<div class="saas-box">', unsafe_allow_html=True)
        st.markdown('<div class="saas-box-header">⚠️ Identified Data Quality Issues</div>', unsafe_allow_html=True)
        for issue in raw_validation.get("issues_summary", []):
            st.warning(f"• {issue}")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="saas-box">', unsafe_allow_html=True)
    st.markdown('<div class="saas-box-header">📊 Column Missingness, Cardinality & Inferred Semantic Types</div>', unsafe_allow_html=True)
    
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
    st.markdown('</div>', unsafe_allow_html=True)


# -------------------------------------------------------------
# Tab 3: Cleaning Studio & Audit Log
# -------------------------------------------------------------
with tab_cleaning:
    st.markdown('<div class="saas-box">', unsafe_allow_html=True)
    st.markdown('<div class="saas-box-header">✨ Before vs After Cleaning Comparison</div>', unsafe_allow_html=True)
    
    col_c1, col_c2, col_c3, col_c4 = st.columns(4)
    with col_c1:
        st.metric("Missing Cells", f"{clean_validation['missing_report']['total_missing']}", f"-{raw_missing - clean_missing} resolved", delta_color="inverse")
    with col_c2:
        st.metric("Duplicate Records", f"{clean_validation['duplicate_report']['duplicate_count']}", f"-{dups_removed} removed", delta_color="inverse")
    with col_c3:
        st.metric("Column Headers", f"{len(audit_log.get('column_renaming', {}))}", "snake_case standardized")
    with col_c4:
        st.metric("Engineered Features", f"{len(transformations)}", "Domain transformations")

    missing_chart = create_before_after_missing_chart(raw_df, clean_df)
    if missing_chart:
        st.plotly_chart(missing_chart, use_container_width=True)
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="saas-box">', unsafe_allow_html=True)
    st.markdown('<div class="saas-box-header">📜 Step-by-Step Cleaning Audit Changelog</div>', unsafe_allow_html=True)
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
    st.markdown('</div>', unsafe_allow_html=True)


# -------------------------------------------------------------
# Tab 4: KPIs & Analytics
# -------------------------------------------------------------
with tab_kpi:
    st.markdown('<div class="saas-box">', unsafe_allow_html=True)
    st.markdown('<div class="saas-box-header">📈 Dynamic Business Performance Intelligence</div>', unsafe_allow_html=True)
    
    kpi_cols = st.columns(len(kpis) if len(kpis) <= 4 else 4)
    for idx, (k_name, k_info) in enumerate(kpis.items()):
        col_idx = idx % 4
        with kpi_cols[col_idx]:
            st.markdown(f"""
            <div class="kpi-card border-blue" style="margin-bottom: 12px;">
                <div class="kpi-card-label">{k_info.get('label', k_name)}</div>
                <div class="kpi-val-number" style="font-size: 20px;">{k_info.get('value', '')}</div>
                <div class="kpi-delta-row">{k_info.get('description', '')}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<div class="saas-box-header">🔢 Extended 5-Number Statistical Summary</div>', unsafe_allow_html=True)
    if not stat_summary.empty:
        st.dataframe(stat_summary, use_container_width=True)
    else:
        st.info("No numeric columns available for statistical summary.")

    st.markdown("---")
    st.markdown('<div class="saas-box-header">📑 Dimensional Grouped Breakdowns</div>', unsafe_allow_html=True)
    if aggregations:
        agg_tab_names = [k.replace("_", " ").title() for k in aggregations.keys()]
        agg_tabs = st.tabs(agg_tab_names)
        for t_idx, (agg_key, agg_df) in enumerate(aggregations.items()):
            with agg_tabs[t_idx]:
                st.dataframe(agg_df, use_container_width=True)
    else:
        st.info("No categorical dimensions found for grouped breakdowns.")
    st.markdown('</div>', unsafe_allow_html=True)


# -------------------------------------------------------------
# Tab 5: Visual Summary
# -------------------------------------------------------------
with tab_charts:
    st.markdown('<div class="saas-box">', unsafe_allow_html=True)
    st.markdown('<div class="saas-box-header">📊 Interactive Visual Analytics & Distributions</div>', unsafe_allow_html=True)
    
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
    st.markdown('</div>', unsafe_allow_html=True)


# -------------------------------------------------------------
# Tab 6: Automated Insights
# -------------------------------------------------------------
with tab_insights:
    col_ins1, col_ins2 = st.columns(2)
    with col_ins1:
        st.markdown('<div class="saas-box">', unsafe_allow_html=True)
        st.markdown('<div class="saas-box-header">🩺 Data Quality & Hygiene Highlights</div>', unsafe_allow_html=True)
        for q_ins in insights.get("quality_insights", []):
            st.success(f"✔️ {q_ins}")

        st.markdown('<div class="saas-box-header" style="margin-top: 20px;">🔍 Anomaly & Outlier Diagnostics</div>', unsafe_allow_html=True)
        for a_ins in insights.get("anomaly_insights", []):
            st.info(f"📊 {a_ins}")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_ins2:
        st.markdown('<div class="saas-box">', unsafe_allow_html=True)
        st.markdown('<div class="saas-box-header">📈 Business Performance Findings</div>', unsafe_allow_html=True)
        for b_ins in insights.get("business_insights", []):
            st.markdown(f"💡 **Finding:** {b_ins}")

        st.markdown('<div class="saas-box-header" style="margin-top: 20px;">🎯 Strategic Actionable Recommendations</div>', unsafe_allow_html=True)
        for r_ins in insights.get("recommendations", []):
            st.warning(f"🚀 **Action:** {r_ins}")
        st.markdown('</div>', unsafe_allow_html=True)


# -------------------------------------------------------------
# Tab 7: Multi-Format Export Studio
# -------------------------------------------------------------
with tab_export:
    st.markdown('<div class="saas-box">', unsafe_allow_html=True)
    st.markdown('<div class="saas-box-header">📥 Multi-Format Publication-Ready Export Studio</div>', unsafe_allow_html=True)
    st.write("Generate and download publication-ready reports and clean datasets in industry-standard formats.")
    
    col_e1, col_e2, col_e3, col_e4 = st.columns(4)

    # 1. Styled Excel Report
    with col_e1:
        st.markdown("""
        <div class="export-box">
            <div>
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="export-icon-box" style="background: #dcfce7; color: #15803d;">📊</div>
                    <div style="font-weight: 700; font-size: 16px;">Excel Report</div>
                </div>
                <div style="font-size: 13px; color: #64748b; line-height: 1.4; margin-bottom: 14px;">
                    Multi-sheet styled workbook (.xlsx) with Executive Summary, Data Quality, Audit Trail, KPIs, and Clean Data.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        with st.spinner("Compiling Excel..."):
            excel_bytes = generate_excel_report(
                raw_df, transformed_df, raw_validation, clean_validation,
                audit_log, kpis, aggregations, insights
            )
        st.download_button(
            label="📥 Download Excel (.xlsx)",
            data=excel_bytes,
            file_name=f"Report_{file_meta.get('file_name', 'data').split('.')[0]}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    # 2. Executive PDF Report
    with col_e2:
        st.markdown("""
        <div class="export-box">
            <div>
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="export-icon-box" style="background: #fee2e2; color: #b91c1c;">📄</div>
                    <div style="font-weight: 700; font-size: 16px;">PDF Summary</div>
                </div>
                <div style="font-size: 13px; color: #64748b; line-height: 1.4; margin-bottom: 14px;">
                    Formal business report (.pdf) with executive scorecard, KPI grid, chart snapshot, and recommendations.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        with st.spinner("Compiling PDF..."):
            pdf_bytes = generate_pdf_report(
                transformed_df, raw_validation, clean_validation,
                audit_log, kpis, insights
            )
        st.download_button(
            label="📥 Download PDF (.pdf)",
            data=pdf_bytes,
            file_name=f"Executive_Summary_{file_meta.get('file_name', 'data').split('.')[0]}.pdf",
            mime="application/pdf",
            use_container_width=True
        )

    # 3. Interactive HTML Report
    with col_e3:
        st.markdown("""
        <div class="export-box">
            <div>
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="export-icon-box" style="background: #e0e7ff; color: #4338ca;">🌐</div>
                    <div style="font-weight: 700; font-size: 16px;">HTML Report</div>
                </div>
                <div style="font-size: 13px; color: #64748b; line-height: 1.4; margin-bottom: 14px;">
                    Standalone responsive web report (.html) with CSS metric cards, audit summary, and data preview.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        html_bytes = generate_html_report(
            transformed_df, raw_validation, clean_validation,
            audit_log, kpis, insights
        )
        st.download_button(
            label="📥 Download HTML (.html)",
            data=html_bytes,
            file_name=f"Executive_Report_{file_meta.get('file_name', 'data').split('.')[0]}.html",
            mime="text/html",
            use_container_width=True
        )

    # 4. Cleaned CSV & Excel Dataset
    with col_e4:
        st.markdown("""
        <div class="export-box">
            <div>
                <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 10px;">
                    <div class="export-icon-box" style="background: #fef3c7; color: #b45309;">💾</div>
                    <div style="font-weight: 700; font-size: 16px;">Clean Dataset</div>
                </div>
                <div style="font-size: 13px; color: #64748b; line-height: 1.4; margin-bottom: 14px;">
                    Direct raw cleaned data files ready for SQL databases, ML training, PowerBI, or Tableau.
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        csv_bytes = export_cleaned_data(transformed_df, file_format="csv")
        st.download_button(
            label="📥 Cleaned CSV (.csv)",
            data=csv_bytes,
            file_name=f"cleaned_{file_meta.get('file_name', 'data').split('.')[0]}.csv",
            mime="text/csv",
            use_container_width=True
        )
    st.markdown('</div>', unsafe_allow_html=True)


# -------------------------------------------------------------
# Tab 8: System Logs
# -------------------------------------------------------------
with tab_logs:
    st.markdown('<div class="saas-box">', unsafe_allow_html=True)
    st.markdown('<div class="saas-box-header">📜 Operational Pipeline Logs & Execution Audit</div>', unsafe_allow_html=True)
    
    logs_data = get_audit_trail()
    if logs_data:
        logs_df = pd.DataFrame(logs_data)
        st.dataframe(logs_df, use_container_width=True)
    else:
        st.info("No active logs recorded.")
    
    if st.button("Clear In-Memory Audit Logs"):
        clear_audit_trail()
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
