import streamlit as st
import pandas as pd

from src.portal.data_store import (
    NORMAL_MODE,
    load_csv,
    load_kpis,
    OPERATING_MODES_FILE,
)

st.set_page_config(
    page_title="Digital Operator Rounds & SOP Portal",
    page_icon="🏭",
    layout="wide"
)

st.title("Digital Operator Rounds & SOP Portal")

st.caption(
    "Dangote Digital Force proof of concept | Refinery → Alkylation → Butamer"
)

st.write(
    "One platform for DCS data, laboratory results, operator rounds, "
    "field verification and operational knowledge. Butamer is the pilot "
    "unit, and the same structure can extend to other units and blocks."
)

st.divider()

# ----------------------------------
# DATA AT A GLANCE
# ----------------------------------

kpi_df = load_kpis()

normal_df = kpi_df[
    kpi_df["operating_mode"] == NORMAL_MODE
]

process_df = normal_df.dropna(
    subset=["reactor_a_delta_t"]
)

st.subheader("Butamer at a Glance")

c1, c2, c3, c4 = st.columns(4)

c1.metric(
    "Average Feed iC4 Ratio",
    f"{normal_df['feed_ic4_ratio'].mean():.1f}%"
)

c2.metric(
    "Average Product iC4 Ratio",
    f"{normal_df['product_ic4_ratio'].mean():.1f}%"
)

c3.metric(
    "Average iC4 Improvement",
    f"{normal_df['ic4_improvement'].mean():.1f} pts"
)

c4.metric(
    "Days with Lab and Process Data",
    len(process_df)
)

modes = load_csv(OPERATING_MODES_FILE)

for _, mode in modes.iterrows():

    st.caption(
        f"Averages exclude {mode['start_date']} to {mode['end_date']}: "
        f"{mode['mode'].lower()}."
    )

st.caption(
    f"Laboratory data: {kpi_df['date'].min().date()} to {kpi_df['date'].max().date()}. "
    f"DCS data ends {process_df['date'].max().date()}."
)

st.divider()

# ----------------------------------
# NAVIGATION
# ----------------------------------

st.subheader("Explore the Portal")

left, right = st.columns(2)

with left:

    st.page_link(
        "pages/1_Unit_Overview.py",
        label="Monitor: Unit Overview",
        icon="🏭"
    )

    st.page_link(
        "pages/2_Feed_Process_Product_Analytics.py",
        label="Analyze: Feed → Process → Product",
        icon="📈"
    )

with right:

    st.page_link(
        "pages/3_Digital_Operator_Rounds.py",
        label="Verify: Digital Operator Rounds",
        icon="📝"
    )

    st.page_link(
        "pages/4_SOP_Knowledge_Portal.py",
        label="Learn: SOP & Knowledge Portal",
        icon="📚"
    )

st.divider()

# ----------------------------------
# DATA SOURCES
# ----------------------------------

st.subheader("What Is Real and What Is Simulated")

st.dataframe(
    pd.DataFrame(
        [
            {"Data": "DCS process values", "Source": "Real plant export"},
            {"Data": "Feed and product iC4 ratios", "Source": "Real laboratory data"},
            {"Data": "Operating mode dates", "Source": "Process engineer review"},
            {"Data": "Operator readings and checklists", "Source": "Simulated"},
            {"Data": "Dräger tests and caustic strength", "Source": "Simulated"},
            {"Data": "DCS references with no usable tag", "Source": "Simulated"},
            {"Data": "Investigations, SOP listing and lessons learned", "Source": "Sample content"},
        ]
    ),
    width="stretch",
    hide_index=True
)
