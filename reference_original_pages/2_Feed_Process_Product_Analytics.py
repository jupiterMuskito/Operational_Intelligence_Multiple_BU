import streamlit as st
import pandas as pd
import plotly.express as px

from src.portal.data_store import (
    NORMAL_MODE,
    load_kpis,
    mode_note,
    relationship_summary,
)

# ----------------------------------
# PAGE CONFIG
# ----------------------------------

st.set_page_config(
    page_title="Feed → Process → Product Analytics",
    page_icon="📈",
    layout="wide"
)

# ----------------------------------
# HELPERS
# ----------------------------------

def safe_metric(value, decimals=1, suffix=""):

    if pd.isna(value):
        return "No Data"

    return f"{value:.{decimals}f}{suffix}"


def condition_scatter(chart_df, column, name, decimals):

    chart = chart_df[
        [
            "date",
            column,
            "product_ic4_ratio"
        ]
    ].dropna()

    fig = px.scatter(
        chart,
        x=column,
        y="product_ic4_ratio",
        custom_data=["date"],
        labels={
            column: name,
            "product_ic4_ratio": "Product iC4 Ratio (%)"
        }
    )

    fig.update_traces(
        hovertemplate=
        f"{name}: %{{x:.{decimals}f}}<br>"
        "Product iC4 Ratio: %{y:.1f}%<br>"
        "Date: %{customdata[0]|%Y-%m-%d}"
        "<extra></extra>"
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )

# ----------------------------------
# LOAD DATA
# ----------------------------------

df = load_kpis()

if df.empty:
    st.error("No KPI data available.")
    st.stop()

valid_df = df.dropna(
    subset=[
        "reactor_a_delta_t",
        "product_ic4_ratio"
    ]
)

if valid_df.empty:
    st.error("No valid analytical records available.")
    st.stop()

normal_df = valid_df[
    valid_df["operating_mode"] == NORMAL_MODE
]

# ----------------------------------
# HEADER
# ----------------------------------

st.title("📈 Feed → Process → Product Analytics")

st.caption(
    "Understanding how feed quality and operating conditions affect Butamer performance."
)

st.divider()

# ----------------------------------
# DATE FILTER
# ----------------------------------

available_dates = sorted(
    valid_df["date"].dt.date.unique()
)

selected_date = st.date_input(
    "Analysis Date",
    value=normal_df["date"].max().date(),
    min_value=min(available_dates),
    max_value=max(available_dates)
)

selected_rows = valid_df[
    valid_df["date"].dt.date == selected_date
]

if selected_rows.empty:
    st.error(
        "No matched laboratory and DCS data for the selected date. Choose another date."
    )
    st.stop()

selected = selected_rows.iloc[0]

note = mode_note(selected_date)

if note:
    st.warning(
        f"{note} This date does not represent normal performance."
    )

include_other_modes = st.toggle(
    f"Include {len(valid_df) - len(normal_df)} days outside normal operation",
    value=False
)

analysis_df = valid_df if include_other_modes else normal_df

st.caption(
    f"Charts and averages use {len(analysis_df)} days with both laboratory and DCS data. "
    f"The DCS data ends {valid_df['date'].max().date()}, so later laboratory samples are not shown here."
)

# ----------------------------------
# QUALITY SUMMARY
# ----------------------------------

st.subheader("Quality Summary")

c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        "Feed iC4 Ratio",
        safe_metric(
            selected["feed_ic4_ratio"],
            1,
            "%"
        )
    )

with c2:
    st.metric(
        "Product iC4 Ratio",
        safe_metric(
            selected["product_ic4_ratio"],
            1,
            "%"
        )
    )

with c3:
    st.metric(
        "iC4 Improvement",
        safe_metric(
            selected["ic4_improvement"],
            1,
            " pts"
        )
    )

with c4:
    st.metric(
        "Reactor ΔT",
        safe_metric(
            selected["reactor_delta_t"],
            1,
            " °C"
        )
    )

st.divider()

# ----------------------------------
# FEED VS PRODUCT TREND
# ----------------------------------

st.subheader("Feed vs Product Quality Trend")

trend_fig = px.line(
    analysis_df,
    x="date",
    y=[
        "feed_ic4_ratio",
        "product_ic4_ratio"
    ],
    markers=True
)

trend_fig.update_layout(
    legend_title_text=""
)

trend_fig.update_traces(
    hovertemplate=
    "%{fullData.name}: %{y:.1f}%<br>"
    "Date: %{x|%Y-%m-%d}"
    "<extra></extra>"
)

st.plotly_chart(
    trend_fig,
    width="stretch"
)

st.divider()

# ----------------------------------
# REACTOR PERFORMANCE
# ----------------------------------

st.subheader("Reactor Performance Impact")

st.caption(
    "Relationship between Reactor ΔT and Product iC4 Ratio"
)

condition_scatter(
    analysis_df,
    "reactor_delta_t",
    "Reactor ΔT (°C)",
    1
)

st.divider()

# ----------------------------------
# OPERATING CONDITIONS IMPACT
# ----------------------------------

st.subheader("Operating Conditions vs Product Quality")

tab1, tab2, tab3 = st.tabs(
    [
        "Hydrogen Flow",
        "Stabilizer Pressure",
        "Drier Moisture"
    ]
)

with tab1:
    condition_scatter(
        analysis_df,
        "Makeup Hydrogen Flow_feed",
        "Hydrogen Flow",
        1
    )

with tab2:
    condition_scatter(
        analysis_df,
        "Stabiliser Pressure_feed",
        "Stabilizer Pressure",
        2
    )

with tab3:
    condition_scatter(
        analysis_df,
        "Butane Drier Moisture Analyzer_feed",
        "Drier Moisture",
        3
    )

st.divider()

# ----------------------------------
# WHAT THE DATA SHOWS
# ----------------------------------

st.subheader("What Conditions Link to Product Quality?")

relationships = relationship_summary(
    analysis_df,
    {
        "Reactor ΔT": "reactor_delta_t",
        "Reactor ΔP": "reactor_delta_p",
        "Hydrogen Flow": "Makeup Hydrogen Flow_feed",
        "Stabilizer Pressure": "Stabiliser Pressure_feed",
        "Drier Moisture": "Butane Drier Moisture Analyzer_feed",
        "Feed iC4 Ratio": "feed_ic4_ratio",
    }
)

st.dataframe(
    relationships,
    width="stretch",
    hide_index=True
)

st.caption(
    "Strongest first. Correlation (r) runs from -1 to +1 and shows values moving together, not cause."
)

st.divider()

# ----------------------------------
# DAILY PERFORMANCE TABLE
# ----------------------------------

st.subheader("Daily Performance")

table_df = analysis_df[
    [
        "date",
        "operating_mode",
        "feed_ic4_ratio",
        "product_ic4_ratio",
        "ic4_improvement",
        "reactor_delta_t",
        "Makeup Hydrogen Flow_feed"
    ]
].copy()

table_df = table_df.sort_values(
    "date",
    ascending=False
)

table_df = table_df.rename(
    columns={
        "date": "Date",
        "operating_mode": "Operating Mode",
        "feed_ic4_ratio": "Feed iC4 Ratio (%)",
        "product_ic4_ratio": "Product iC4 Ratio (%)",
        "ic4_improvement": "Improvement (pts)",
        "reactor_delta_t": "Reactor ΔT (°C)",
        "Makeup Hydrogen Flow_feed": "Hydrogen Flow",
    }
)

st.dataframe(
    table_df.style.format(
        precision=1,
        subset=[
            "Feed iC4 Ratio (%)",
            "Product iC4 Ratio (%)",
            "Improvement (pts)",
            "Reactor ΔT (°C)",
            "Hydrogen Flow",
        ]
    ).format(
        lambda value: value.date().isoformat(),
        subset=["Date"]
    ).highlight_max(
        subset=["Improvement (pts)"],
        color="#b7e4c7"
    ).highlight_min(
        subset=["Improvement (pts)"],
        color="#f8c9c4"
    ),
    width="stretch",
    hide_index=True
)

st.caption(
    "Highest and lowest improvement are highlighted."
)

st.divider()

# ----------------------------------
# ENGINEERING INSIGHTS
# ----------------------------------

st.subheader("Engineering Insights")

best_day = analysis_df.loc[
    analysis_df["ic4_improvement"].idxmax()
]

st.success(
    f"""
Highest iC4 improvement recorded

Date: {best_day['date'].date()}

Improvement: {best_day['ic4_improvement']:.1f} pts
"""
)

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Average Feed iC4 Ratio",
        f"{analysis_df['feed_ic4_ratio'].mean():.1f}%"
    )

with col2:
    st.metric(
        "Average Product iC4 Ratio",
        f"{analysis_df['product_ic4_ratio'].mean():.1f}%"
    )

with col3:
    st.metric(
        "Average Reactor ΔT",
        f"{analysis_df['reactor_delta_t'].mean():.1f} °C"
    )

st.divider()

# ----------------------------------
# DATA VALIDATION
# ----------------------------------

with st.expander("🔍 Data Validation"):

    st.write(
        f"Selected Date: {selected_date}"
    )

    st.write(
        f"Operating Mode: {selected['operating_mode']}"
    )

    st.write(
        f"Feed iC4 Ratio: "
        f"{safe_metric(selected['feed_ic4_ratio'],1,'%')}"
    )

    st.write(
        f"Product iC4 Ratio: "
        f"{safe_metric(selected['product_ic4_ratio'],1,'%')}"
    )

    st.write(
        f"Improvement: "
        f"{safe_metric(selected['ic4_improvement'],1,' pts')}"
    )

    st.write(
        f"Reactor ΔT: "
        f"{safe_metric(selected['reactor_delta_t'],1,' °C')}"
    )
