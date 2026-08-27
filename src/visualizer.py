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


# Modern SaaS Color Palette
COLOR_PALETTE = [
    "#3b82f6",  # Vibrant Blue
    "#8b5cf6",  # Royal Violet
    "#10b981",  # Emerald Green
    "#f59e0b",  # Amber Gold
    "#06b6d4",  # Cyan
    "#ec4899",  # Rose Pink
    "#6366f1",  # Indigo
    "#14b8a6"   # Teal
]

PLOTLY_LAYOUT_DEFAULTS = dict(
    font=dict(family="Plus Jakarta Sans, Inter, sans-serif", color="#334155", size=12),
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(l=24, r=24, t=48, b=24),
    xaxis=dict(
        showgrid=True,
        gridcolor="rgba(226, 232, 240, 0.7)",
        zeroline=False,
        linecolor="rgba(203, 213, 225, 0.8)"
    ),
    yaxis=dict(
        showgrid=True,
        gridcolor="rgba(226, 232, 240, 0.7)",
        zeroline=False,
        linecolor="rgba(203, 213, 225, 0.8)"
    ),
    legend=dict(
        bgcolor="rgba(255, 255, 255, 0.8)",
        bordercolor="rgba(226, 232, 240, 0.8)",
        borderwidth=1,
        font=dict(size=11)
    )
)


def create_quality_gauge(score: float, grade: str) -> go.Figure:
    """Create an interactive modern gauge for Data Quality Health Score."""
    # Choose color based on score
    if score >= 90:
        bar_color = "#10b981" # Emerald
    elif score >= 75:
        bar_color = "#3b82f6" # Blue
    elif score >= 50:
        bar_color = "#f59e0b" # Amber
    else:
        bar_color = "#ef4444" # Red

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=score,
        number={'suffix': "/100", 'font': {'size': 32, 'color': '#0f172a', 'family': 'Plus Jakarta Sans, Inter'}},
        domain={'x': [0, 1], 'y': [0, 1]},
        title={'text': f"Health Grade: {grade}", 'font': {'size': 15, 'color': '#475569', 'family': 'Plus Jakarta Sans'}},
        gauge={
            'axis': {'range': [0, 100], 'tickwidth': 1, 'tickcolor': "#94a3b8"},
            'bar': {'color': bar_color, 'thickness': 0.28},
            'bgcolor': "rgba(241, 245, 249, 0.6)",
            'borderwidth': 1.5,
            'bordercolor': "rgba(226, 232, 240, 0.9)",
            'steps': [
                {'range': [0, 50], 'color': 'rgba(254, 226, 226, 0.5)'},
                {'range': [50, 75], 'color': 'rgba(254, 243, 199, 0.5)'},
                {'range': [75, 90], 'color': 'rgba(224, 231, 255, 0.5)'},
                {'range': [90, 100], 'color': 'rgba(209, 250, 229, 0.6)'}
            ],
            'threshold': {
                'line': {'color': "#059669", 'width': 3.5},
                'thickness': 0.8,
                'value': 90
            }
        }
    ))
    fig.update_layout(
        height=260,
        margin=dict(l=20, r=20, t=40, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Plus Jakarta Sans, Inter, sans-serif")
    )
    return fig


def create_before_after_missing_chart(raw_df: pd.DataFrame, clean_df: pd.DataFrame) -> Optional[go.Figure]:
    """Create before vs after comparison bar chart for missing values."""
    if raw_df is None or clean_df is None:
        return None

    raw_missing = raw_df.isna().sum()
    top_missing = raw_missing[raw_missing > 0].sort_values(ascending=False).head(10)
    if top_missing.empty:
        return None

    cols = list(top_missing.index)
    raw_counts = [int(top_missing[c]) for c in cols]
    
    clean_counts = []
    for c in cols:
        clean_col = c.strip().lower().replace(" ", "_")
        matched = [col for col in clean_df.columns if clean_col in col]
        if matched:
            clean_counts.append(int(clean_df[matched[0]].isna().sum()))
        else:
            clean_counts.append(0)

    fig = go.Figure(data=[
        go.Bar(
            name='Before Cleaning (Raw)',
            x=cols,
            y=raw_counts,
            marker_color='#f43f5e', # Coral Rose
            marker_line_color='rgba(225, 29, 72, 0.3)',
            marker_line_width=1,
            opacity=0.9
        ),
        go.Bar(
            name='After Cleaning (Cleaned)',
            x=cols,
            y=clean_counts,
            marker_color='#10b981', # Emerald Green
            marker_line_color='rgba(5, 150, 105, 0.3)',
            marker_line_width=1,
            opacity=0.95
        )
    ])
    fig.update_layout(
        barmode='group',
        title=dict(text="Missing Values by Column (Before vs After)", font=dict(size=14, color="#1e293b", family="Plus Jakarta Sans")),
        xaxis_title="Column",
        yaxis_title="Missing Cell Count",
        height=360,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        **PLOTLY_LAYOUT_DEFAULTS
    )
    return fig


def create_trend_chart(df: pd.DataFrame, date_col: str, val_col: str) -> Optional[go.Figure]:
    """Create time-series trend line chart with smooth markers and gradient area."""
    if date_col not in df.columns or val_col not in df.columns:
        return None

    try:
        trend_df = df.groupby(date_col)[val_col].sum().reset_index().sort_values(by=date_col)
        fig = go.Figure()
        
        # Area fill under line
        fig.add_trace(go.Scatter(
            x=trend_df[date_col],
            y=trend_df[val_col],
            mode='lines+markers',
            name=val_col.replace('_', ' ').title(),
            line=dict(color='#3b82f6', width=3, shape='spline'),
            marker=dict(size=8, color='#1d4ed8', symbol='circle', line=dict(color='#ffffff', width=1.5)),
            fill='tozeroy',
            fillcolor='rgba(59, 130, 246, 0.08)'
        ))

        fig.update_layout(
            title=dict(text=f"Trend Analysis: {val_col.replace('_', ' ').title()} over Time", font=dict(size=14, color="#1e293b", family="Plus Jakarta Sans")),
            height=380,
            showlegend=False,
            **PLOTLY_LAYOUT_DEFAULTS
        )
        return fig
    except Exception:
        return None


def create_category_bar_chart(df: pd.DataFrame, cat_col: str, val_col: str) -> Optional[go.Figure]:
    """Create horizontal category bar chart with modern styling."""
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
            title=f"Performance Breakdown by {cat_col.replace('_', ' ').title()}",
            color=val_col,
            color_continuous_scale=[[0, "#93c5fd"], [0.5, "#3b82f6"], [1, "#1e40af"]]
        )
        fig.update_traces(
            textposition='outside',
            cliponaxis=False,
            marker_line_color='rgba(37, 99, 235, 0.2)',
            marker_line_width=1
        )
        fig.update_layout(
            height=380,
            showlegend=False,
            coloraxis_showscale=False,
            title=dict(text=f"Performance Breakdown by {cat_col.replace('_', ' ').title()}", font=dict(size=14, color="#1e293b", family="Plus Jakarta Sans")),
            **PLOTLY_LAYOUT_DEFAULTS
        )
        return fig
    except Exception:
        return None


def create_donut_chart(df: pd.DataFrame, cat_col: str, val_col: Optional[str] = None) -> Optional[go.Figure]:
    """Create styled donut chart for distributions with center hole."""
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
            hole=0.55,
            title=f"Distribution by {cat_col.replace('_', ' ').title()}",
            color_discrete_sequence=COLOR_PALETTE
        )
        fig.update_traces(
            textposition='outside',
            textinfo='percent+label',
            marker=dict(line=dict(color='#ffffff', width=2))
        )
        fig.update_layout(
            height=380,
            title=dict(text=f"Distribution by {cat_col.replace('_', ' ').title()}", font=dict(size=14, color="#1e293b", family="Plus Jakarta Sans")),
            showlegend=False,
            **PLOTLY_LAYOUT_DEFAULTS
        )
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
            title=f"Distribution & Outliers: {num_col.replace('_', ' ').title()}",
            color_discrete_sequence=["#8b5cf6"]
        )
        fig.update_traces(
            marker=dict(line=dict(color='#6d28d9', width=1), opacity=0.85)
        )
        fig.update_layout(
            height=380,
            title=dict(text=f"Distribution & Outliers: {num_col.replace('_', ' ').title()}", font=dict(size=14, color="#1e293b", family="Plus Jakarta Sans")),
            **PLOTLY_LAYOUT_DEFAULTS
        )
        return fig
    except Exception:
        return None


def create_correlation_heatmap(df: pd.DataFrame) -> Optional[go.Figure]:
    """Create numerical correlation matrix heatmap with clean palette."""
    num_df = df.select_dtypes(include=[np.number])
    if num_df.shape[1] < 2:
        return None

    corr = num_df.corr().round(2)
    fig = px.imshow(
        corr,
        text_auto=True,
        aspect="auto",
        title="Numerical Features Correlation Matrix",
        color_continuous_scale=[[0, "#ef4444"], [0.5, "#f8fafc"], [1, "#3b82f6"]]
    )
    fig.update_layout(
        height=400,
        title=dict(text="Numerical Features Correlation Matrix", font=dict(size=14, color="#1e293b", family="Plus Jakarta Sans")),
        **PLOTLY_LAYOUT_DEFAULTS
    )
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
