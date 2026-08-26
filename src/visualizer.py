"""
Data Visualization Module.
Provides interactive Plotly visualizations for the Streamlit dashboard
and static Matplotlib/Seaborn charts for automated PDF/Executive reports.
"""
import io
from typing import Dict, Any, List, Optional
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import matplotlib
matplotlib.use("Agg") # Non-interactive backend for server/PDF generation
import matplotlib.pyplot as plt
import seaborn as sns


# Set cohesive design theme
PLOTLY_TEMPLATE = "plotly_white"
COLOR_PALETTE = ["#2563eb", "#7c3aed", "#059669", "#d97706", "#dc2626", "#0891b2", "#4f46e5"]


def create_quality_gauge(score: float, grade: str) -> go.Figure:
    """Create an interactive gauge for Data Quality Health Score."""
    fig = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=score,
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Data Health Score: {grade}", 'font': {'size': 20, 'color': '#1e293b'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#64748b"},
            'bar': {'color': "#2563eb"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "#cbd5e1",
            'steps': [
                {'range': [0, 50], 'color': '#fee2e2'},
                {'range': [50, 75], 'color': '#fef3c7'},
                {'range': [75, 90], 'color': '#d1fae5'},
                {'range': [90, 100], 'color': '#bbf7d0'}
            ],
            'threshold': {
                'line': {'color': "#16a34a", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=50, b=20), paper_bgcolor="rgba(0,0,0,0)")
    return fig


def create_before_after_missing_chart(raw_df: pd.DataFrame, clean_df: pd.DataFrame) -> Optional[go.Figure]:
    """Create before vs after comparison bar chart for missing values."""
    if raw_df is None or clean_df is None:
        return None

    raw_missing = raw_df.isna().sum()
    # Map raw columns to snake_case if possible, or display top columns
    top_missing = raw_missing[raw_missing > 0].sort_values(ascending=False).head(10)
    if top_missing.empty:
        return None

    cols = list(top_missing.index)
    raw_counts = [int(top_missing[c]) for c in cols]
    
    # Check matching in clean_df
    clean_counts = []
    for c in cols:
        clean_col = c.strip().lower().replace(" ", "_")
        matched = [col for col in clean_df.columns if clean_col in col]
        if matched:
            clean_counts.append(int(clean_df[matched[0]].isna().sum()))
        else:
            clean_counts.append(0)

    fig = go.Figure(data=[
        go.Bar(name='Before Cleaning', x=cols, y=raw_counts, marker_color='#ef4444'),
        go.Bar(name='After Cleaning', x=cols, y=clean_counts, marker_color='#10b981')
    ])
    fig.update_layout(
        barmode='group',
        title="Missing Values by Column (Before vs After Cleaning)",
        xaxis_title="Column",
        yaxis_title="Missing Count",
        template=PLOTLY_TEMPLATE,
        height=350,
        margin=dict(l=20, r=20, t=50, b=40),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return fig


def create_trend_chart(df: pd.DataFrame, date_col: str, val_col: str) -> Optional[go.Figure]:
    """Create time-series trend line chart with smooth markers."""
    if date_col not in df.columns or val_col not in df.columns:
        return None

    try:
        trend_df = df.groupby(date_col)[val_col].sum().reset_index().sort_values(by=date_col)
        fig = px.line(
            trend_df,
            x=date_col,
            y=val_col,
            markers=True,
            title=f"Trend Analysis: {val_col.replace('_', ' ').title()} over Time",
            color_discrete_sequence=["#2563eb"]
        )
        fig.update_traces(line=dict(width=3), marker=dict(size=8, color="#1e40af"))
        fig.update_layout(template=PLOTLY_TEMPLATE, height=380, margin=dict(l=20, r=20, t=50, b=20))
        return fig
    except Exception:
        return None


def create_category_bar_chart(df: pd.DataFrame, cat_col: str, val_col: str) -> Optional[go.Figure]:
    """Create horizontal or vertical category bar chart."""
    if cat_col not in df.columns or val_col not in df.columns:
        return None

    try:
        agg = df.groupby(cat_col)[val_col].sum().reset_index().sort_values(by=val_col, ascending=True)
        fig = px.bar(
            agg,
            x=val_col,
            y=cat_col,
            orientation="h",
            text_auto=".2s",
            title=f"Performance by {cat_col.replace('_', ' ').title()}",
            color=val_col,
            color_continuous_scale="Blues"
        )
        fig.update_layout(
            template=PLOTLY_TEMPLATE,
            height=380,
            showlegend=False,
            margin=dict(l=20, r=20, t=50, b=20)
        )
        return fig
    except Exception:
        return None


def create_donut_chart(df: pd.DataFrame, cat_col: str, val_col: Optional[str] = None) -> Optional[go.Figure]:
    """Create styled donut chart for distributions."""
    if cat_col not in df.columns:
        return None

    try:
        if val_col and val_col in df.columns and pd.api.types.is_numeric_dtype(df[val_col]):
            agg = df.groupby(cat_col)[val_col].sum().reset_index()
            values_target = val_col
        else:
            agg = df[cat_col].value_counts().reset_index(name="count")
            agg.columns = [cat_col, "count"]
            values_target = "count"

        fig = px.pie(
            agg,
            names=cat_col,
            values=values_target,
            hole=0.45,
            title=f"Distribution by {cat_col.replace('_', ' ').title()}",
            color_discrete_sequence=COLOR_PALETTE
        )
        fig.update_traces(textposition='inside', textinfo='percent+label')
        fig.update_layout(template=PLOTLY_TEMPLATE, height=380, margin=dict(l=20, r=20, t=50, b=20))
        return fig
    except Exception:
        return None


def create_distribution_chart(df: pd.DataFrame, num_col: str) -> Optional[go.Figure]:
    """Create distribution histogram with box plot marginal for outliers."""
    if num_col not in df.columns or not pd.api.types.is_numeric_dtype(df[num_col]):
        return None

    try:
        fig = px.histogram(
            df,
            x=num_col,
            marginal="box",
            nbins=30,
            title=f"Distribution & Outlier Spread: {num_col.replace('_', ' ').title()}",
            color_discrete_sequence=["#7c3aed"]
        )
        fig.update_layout(template=PLOTLY_TEMPLATE, height=380, margin=dict(l=20, r=20, t=50, b=20))
        return fig
    except Exception:
        return None


def create_correlation_heatmap(df: pd.DataFrame) -> Optional[go.Figure]:
    """Create numerical correlation matrix heatmap."""
    num_df = df.select_dtypes(include=[np.number])
    if num_df.shape[1] < 2:
        return None

    corr = num_df.corr().round(2)
    fig = px.imshow(
        corr,
        text_auto=True,
        aspect="auto",
        title="Numerical Features Correlation Matrix",
        color_continuous_scale="RdBu_r"
    )
    fig.update_layout(template=PLOTLY_TEMPLATE, height=400, margin=dict(l=20, r=20, t=50, b=20))
    return fig


# -------------------------------------------------------------
# Static Charts for PDF Generation (Matplotlib / Seaborn)
# -------------------------------------------------------------

def generate_static_summary_plot(df: pd.DataFrame, cat_col: Optional[str] = None, val_col: Optional[str] = None) -> io.BytesIO:
    """Generate static PNG plot buffer for PDF reporting."""
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")
    fig, ax = plt.subplots(figsize=(7, 3.5), dpi=200)

    if cat_col and val_col and cat_col in df.columns and val_col in df.columns:
        agg = df.groupby(cat_col)[val_col].sum().sort_values(ascending=False).head(8)
        sns.barplot(x=agg.values, y=agg.index, ax=ax, palette="Blues_r")
        ax.set_title(f"Top {cat_col.replace('_', ' ').title()} by {val_col.replace('_', ' ').title()}", fontsize=11, fontweight="bold")
        ax.set_xlabel(val_col.replace('_', ' ').title(), fontsize=9)
    else:
        num_cols = df.select_dtypes(include=[np.number]).columns
        if len(num_cols) > 0:
            sns.histplot(df[num_cols[0]].dropna(), kde=True, ax=ax, color="#2563eb")
            ax.set_title(f"Distribution of {num_cols[0].replace('_', ' ').title()}", fontsize=11, fontweight="bold")
        else:
            ax.text(0.5, 0.5, "Data Summary Preview", horizontalalignment='center', verticalalignment='center')

    plt.tight_layout()
    buf = io.BytesIO()
    plt.savefig(buf, format="png", bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf
