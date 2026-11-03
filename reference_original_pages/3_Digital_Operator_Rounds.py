import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime

from src.portal.data_store import (
    CHECKLIST_FILE,
    CHECKLIST_RECORDS_FILE,
    DRAGER_FILE,
    GUIDE_FILE,
    HIERARCHY_FILE,
    INVESTIGATION_FILE,
    KPI_UNIT,
    LAB_FILE,
    ROUNDS_FILE,
    SCHEDULE_FILE,
    SOP_FILE,
    TAG_REFERENCE_FILE,
    append_rows,
    limit_status,
    load_csv,
    load_kpis,
    operating_limits,
    verification_table,
    verify_reading,
)

# ----------------------------------
# PAGE CONFIG
# ----------------------------------

st.set_page_config(
    page_title="Digital Operator Rounds & Verification",
    page_icon="📝",
    layout="wide"
)

# ----------------------------------
# LOAD DATA
# ----------------------------------

kpi_df = load_kpis()
hierarchy_df = load_csv(HIERARCHY_FILE)
rounds_df = load_csv(ROUNDS_FILE, dates=True)
schedule_df = load_csv(SCHEDULE_FILE, dates=True)
drager_df = load_csv(DRAGER_FILE, dates=True)
lab_df = load_csv(LAB_FILE, dates=True)
investigation_df = load_csv(INVESTIGATION_FILE, dates=True)
checklist_df = load_csv(CHECKLIST_FILE)
tag_df = load_csv(TAG_REFERENCE_FILE)
sop_df = load_csv(SOP_FILE)
guide_df = load_csv(GUIDE_FILE)

# ----------------------------------
# PAGE HEADER
# ----------------------------------

st.title("📝 Digital Operator Rounds & Verification")

st.caption(
    "Digitize field activities while integrating operator observations, "
    "laboratory results, field tests and DCS process data into a single workflow."
)

st.warning(
    "Demonstration data: operator readings, field tests, caustic strength, investigations "
    "and some DCS references on this page are simulated. iC4 ratios and DCS values marked "
    "with a tag are real plant data."
)

if "round_saved" in st.session_state:
    st.success(st.session_state.pop("round_saved"))

st.divider()

# ----------------------------------
# UNIT AND DATE
# ----------------------------------

st.subheader("Unit and Date")

col1, col2, col3, col4 = st.columns(4)

with col1:

    business_unit = st.selectbox(
        "Business Unit",
        sorted(hierarchy_df["business_unit"].unique())
    )

in_business_unit = hierarchy_df[
    hierarchy_df["business_unit"] == business_unit
]

with col2:

    block = st.selectbox(
        "Block",
        sorted(in_business_unit["block"].unique())
    )

in_block = in_business_unit[
    in_business_unit["block"] == block
]

unit_options = sorted(in_block["unit"].unique())

ready_units = in_block[
    in_block["equipment"].isin(tag_df["equipment"])
]["unit"].unique()

with col3:

    unit = st.selectbox(
        "Unit",
        unit_options,
        index=next(
            (
                position
                for position, option in enumerate(unit_options)
                if option in ready_units
            ),
            0
        )
    )

unit_hierarchy = in_block[
    in_block["unit"] == unit
]

unit_equipment = set(unit_hierarchy["equipment"].dropna())


def for_unit(df):

    return df[df["equipment"].isin(unit_equipment)]


schedule_df = for_unit(schedule_df)
rounds_df = for_unit(rounds_df)
investigation_df = for_unit(investigation_df)
lab_df = for_unit(lab_df)
drager_df = for_unit(drager_df)
unit_tag_df = for_unit(tag_df)

if unit != KPI_UNIT:
    kpi_df = kpi_df.iloc[0:0]

available_dates = sorted(
    set(schedule_df["date"].dt.date)
    | set(rounds_df["date"].dt.date)
)

with col4:

    selected_date = st.date_input(
        "Investigation Date",
        value=max(available_dates) if available_dates else datetime.now().date(),
        min_value=min(available_dates) if available_dates else None,
        max_value=max(available_dates) if available_dates else None
    )

schedule_records = schedule_df[
    schedule_df["date"].dt.date == selected_date
]

round_records = rounds_df[
    rounds_df["date"].dt.date == selected_date
]

deviations = investigation_df[
    investigation_df["date"].dt.date == selected_date
]

verification_records = verification_table(round_records)

if not unit_equipment:
    st.info(
        f"{unit} is in the plant hierarchy, but its equipment, tags and records have not "
        "been added yet. Each section below fills in once they are added."
    )
elif schedule_records.empty and round_records.empty:
    st.info(
        f"No round was scheduled or recorded for {unit} on {selected_date}. "
        f"Demonstration rounds exist for: "
        f"{', '.join(str(day) for day in available_dates)}."
    )

st.divider()

# ----------------------------------
# ROUND SUMMARY
# ----------------------------------

st.subheader("Round Performance Summary")

expected_set = set(
    zip(
        schedule_records["equipment"],
        schedule_records["parameter"]
    )
)

recorded_set = set(
    zip(
        round_records["equipment"],
        round_records["parameter"]
    )
)

completed_set = expected_set & recorded_set
off_schedule_set = recorded_set - expected_set
missing_set = expected_set - recorded_set

expected_measurements = len(expected_set)
completed_measurements = len(completed_set)

completion_pct = (
    completed_measurements / expected_measurements * 100
    if expected_measurements > 0
    else 0
)

critical_missing = len(
    schedule_records[
        (schedule_records["criticality"] == "High")
        & (
            schedule_records[["equipment", "parameter"]]
            .apply(tuple, axis=1)
            .isin(missing_set)
        )
    ]
) if not schedule_records.empty else 0

open_deviations = len(
    verification_records[
        verification_records["Status"].isin(["Monitor", "Critical"])
    ]
) if not verification_records.empty else 0

pending_actions = len(
    deviations[deviations["status"] == "Open"]
)

c1, c2, c3, c4, c5, c6, c7 = st.columns(7)

c1.metric("Expected", expected_measurements)
c2.metric("Completed", completed_measurements)
c3.metric("Completion %", f"{completion_pct:.1f}%")
c4.metric("Missing", len(missing_set))
c5.metric("Critical Missing", critical_missing)
c6.metric("Open Deviations", open_deviations)
c7.metric("Pending Actions", pending_actions)

# ----------------------------------
# MEASUREMENT SCHEDULE
# ----------------------------------

st.divider()

st.subheader("Measurement Schedule")

st.dataframe(
    schedule_records[
        [
            "equipment",
            "parameter",
            "expected_entries",
            "criticality"
        ]
    ],
    width="stretch",
    hide_index=True
)

# ----------------------------------
# MEASUREMENT COMPLIANCE
# ----------------------------------

st.divider()

st.subheader("Measurement Compliance")

for equipment_name, parameter_name in sorted(expected_set):

    if (equipment_name, parameter_name) in completed_set:
        st.success(f"✅ {equipment_name} - {parameter_name}")
    else:
        st.error(f"❌ {equipment_name} - {parameter_name}")

if off_schedule_set:

    st.caption(
        "Recorded but not scheduled (not counted towards completion): "
        + ", ".join(
            f"{equipment_name} - {parameter_name}"
            for equipment_name, parameter_name in sorted(off_schedule_set)
        )
    )

# ----------------------------------
# ROUND ENTRY
# ----------------------------------

st.divider()

st.subheader("Operator Round Entry")

in_unit = unit_hierarchy[
    unit_hierarchy["equipment"].isin(tag_df["equipment"])
]

if in_unit.empty:

    st.info(
        f"Round entry for {unit} opens once its equipment and tags are added."
    )

else:

    col1, col2 = st.columns(2)

    with col1:

        section = st.selectbox(
            "Section",
            sorted(in_unit["section"].unique())
        )

    with col2:

        equipment = st.selectbox(
            "Equipment",
            sorted(
                in_unit[
                    in_unit["section"] == section
                ]["equipment"].unique()
            )
        )

    equipment_parameters = tag_df[
        tag_df["equipment"] == equipment
    ]

    parameter = st.selectbox(
        "Parameter",
        equipment_parameters["parameter"].tolist()
    )

    selected_parameter = equipment_parameters[
        equipment_parameters["parameter"] == parameter
    ].iloc[0]

    unit_of_measure = (
        selected_parameter["unit_of_measure"]
        if pd.notna(selected_parameter["unit_of_measure"])
        else ""
    )

    # ----------------------------------
    # DYNAMIC CHECKLIST
    # ----------------------------------

    st.markdown("### Inspection Checklist")

    checklist_results = {}

    selected_checklist = checklist_df[
        checklist_df["equipment"] == equipment
    ]

    if selected_checklist.empty:
        st.info("No checklist configured for selected equipment.")

    for item in selected_checklist["check_item"]:

        checklist_results[item] = st.checkbox(
            item,
            key=f"{equipment}_{item}"
        )

    # ----------------------------------
    # FIELD DATA ENTRY FORM
    # ----------------------------------

    with st.form("round_form"):

        st.markdown("### Field Measurement")

        recorded_by = st.text_input("Recorded By")

        field_value = st.number_input(
            f"Field Reading ({unit_of_measure})" if unit_of_measure else "Field Reading",
            value=None,
            placeholder="Enter reading"
        )

        remarks = st.text_area("Remarks")

        submit = st.form_submit_button("Save Entry")

    if submit:

        if not recorded_by.strip():

            st.error("Enter the name of the person recording this reading.")

        elif field_value is None:

            st.error("Enter the field reading before saving.")

        else:

            with st.spinner("Saving entry..."):

                recorded_at = datetime.now().strftime("%Y-%m-%d %H:%M")

                check = verify_reading(
                    equipment,
                    parameter,
                    selected_date,
                    field_value
                )

                append_rows(
                    ROUNDS_FILE,
                    [
                        {
                            "date": selected_date,
                            "business_unit": business_unit,
                            "block": block,
                            "unit": unit,
                            "section": section,
                            "equipment": equipment,
                            "parameter": parameter,
                            "field_value": field_value,
                            "unit_of_measure": unit_of_measure,
                            "status": check["status"],
                            "remarks": remarks,
                            "recorded_by": recorded_by.strip(),
                            "recorded_at": recorded_at,
                        }
                    ]
                )

                if checklist_results:

                    append_rows(
                        CHECKLIST_RECORDS_FILE,
                        [
                            {
                                "date": selected_date,
                                "equipment": equipment,
                                "check_item": item,
                                "checked": checked,
                                "recorded_by": recorded_by.strip(),
                                "recorded_at": recorded_at,
                            }
                            for item, checked in checklist_results.items()
                        ]
                    )

            st.session_state["round_saved"] = (
                f"Saved {equipment} - {parameter}. "
                f"Field vs DCS status: {check['status']}."
            )

            st.rerun()

# ----------------------------------
# FIELD MEASUREMENTS
# ----------------------------------

st.subheader("Operator Field Measurements")

if not round_records.empty:

    st.caption("Data Source: OPERATOR ROUNDS (simulated demonstration entries)")

    st.dataframe(
        round_records[
            [
                "equipment",
                "parameter",
                "field_value",
                "unit_of_measure",
                "status",
                "remarks",
                "recorded_by",
                "recorded_at",
            ]
        ],
        width="stretch",
        hide_index=True
    )

else:

    st.info("No field measurements available.")

st.divider()

# ----------------------------------
# LABORATORY INTEGRATION
# ----------------------------------

st.subheader("Laboratory Integration")

st.info(
    "Laboratory personnel will enter results through a dedicated Laboratory Data Entry page. "
    "Results then become available across the platform for process monitoring, KPI "
    "calculation, verification, troubleshooting and analytics."
)

lab_rows = []

kpi_row = kpi_df[
    kpi_df["date"].dt.date == selected_date
]

if not kpi_row.empty:

    lab_rows.extend(
        [
            {
                "Sample Point": "DB OH (Feed)",
                "Parameter": "iC4 Ratio",
                "Value": round(kpi_row.iloc[0]["feed_ic4_ratio"], 1),
                "Unit": "%",
                "Source": "Laboratory data",
            },
            {
                "Sample Point": "Stabilizer Bottom (Product)",
                "Parameter": "iC4 Ratio",
                "Value": round(kpi_row.iloc[0]["product_ic4_ratio"], 1),
                "Unit": "%",
                "Source": "Laboratory data",
            },
        ]
    )

lab_records = lab_df[
    lab_df["date"].dt.date == selected_date
]

for _, record in lab_records.iterrows():

    lab_rows.append(
        {
            "Sample Point": record["sample_point"],
            "Parameter": record["parameter"],
            "Value": record["value"],
            "Unit": record["unit"],
            "Source": "Simulated",
        }
    )

if lab_rows:

    st.dataframe(
        pd.DataFrame(lab_rows),
        width="stretch",
        hide_index=True
    )

else:

    st.info("No laboratory results available.")

caustic = lab_records[
    lab_records["parameter"] == "Caustic Strength"
]

if not caustic.empty:

    caustic_limit = next(
        limit
        for limit in operating_limits()
        if limit["key"] == "caustic_strength"
    )

    st.metric(
        "Caustic Strength Status",
        limit_status(caustic.iloc[0]["value"], caustic_limit)
    )

st.divider()

# ----------------------------------
# DRAGER TESTS
# ----------------------------------

st.subheader("Dräger Test Results")

if not drager_df.empty:

    st.caption("Data Source: FIELD TESTS (simulated)")

    fig = px.line(
        drager_df,
        x="date",
        y="hcl_ppm",
        color="test_location",
        markers=True
    )

    fig.update_traces(
        hovertemplate=
        "Date: %{x|%Y-%m-%d}<br>"
        "HCl: %{y:.0f} ppm"
        "<extra></extra>"
    )

    st.plotly_chart(
        fig,
        width="stretch"
    )

else:

    st.info("No Dräger tests recorded for this unit.")

st.divider()

# ----------------------------------
# FIELD VS DCS
# ----------------------------------

st.subheader("Field vs DCS Verification")

if not verification_records.empty:

    st.caption(
        "Field readings are compared with the daily average of the DCS tag where one "
        "is available. Differences and statuses are calculated using config/verification_limits.csv."
    )

    st.dataframe(
        verification_records,
        width="stretch",
        hide_index=True
    )

else:

    st.info("No verification records available.")

st.markdown(
    """
### Why This Matters

✓ Instrument Drift Detection

✓ Faulty Transmitter Detection

✓ Plugged Impulse Line Detection

✓ Process Data Validation

✓ Maintenance Planning

✓ Improved Process Reliability
"""
)

# ----------------------------------
# EQUIPMENT TAG REFERENCE
# ----------------------------------

st.divider()

st.subheader("Equipment Tag Reference")

st.caption(
    "Routine reporting improves operator familiarity with plant equipment, "
    "instrumentation tags and process variables."
)

st.dataframe(
    unit_tag_df[
        [
            "equipment",
            "parameter",
            "tag",
            "description",
            "tag_status",
        ]
    ],
    width="stretch",
    hide_index=True
)

st.divider()

# ----------------------------------
# DEVIATIONS
# ----------------------------------

st.subheader("Deviations & Observations")

st.dataframe(
    deviations.assign(date=deviations["date"].dt.date)[
        [
            "date",
            "area",
            "observation",
            "priority",
            "status",
        ]
    ],
    width="stretch",
    hide_index=True
)

st.divider()

# ----------------------------------
# INVESTIGATION HISTORY
# ----------------------------------

st.subheader("Investigation Record")

if not deviations.empty:

    selected_issue = st.selectbox(
        "Select Investigation",
        deviations["observation"]
    )

    issue = deviations[
        deviations["observation"] == selected_issue
    ].iloc[0]

    st.markdown(
        f"""
### Possible Cause

{issue['possible_cause']}

### Recommended Action

{issue['recommended_action']}
"""
    )

    st.markdown("### Related Knowledge")

    related_sop = sop_df[
        sop_df["sop_id"] == issue["related_sop"]
    ]

    if not related_sop.empty:
        st.write(
            f"SOP: {related_sop.iloc[0]['sop_id']} - {related_sop.iloc[0]['title']}"
        )

    related_guide = guide_df[
        guide_df["issue"] == issue["related_issue"]
    ]

    if not related_guide.empty:
        st.write(
            f"Troubleshooting: {related_guide.iloc[0]['issue']} - "
            f"{related_guide.iloc[0]['recommended_actions']}"
        )

    if related_sop.empty and related_guide.empty:
        st.caption("No related SOP or troubleshooting guide is linked yet.")

    st.page_link(
        "pages/4_SOP_Knowledge_Portal.py",
        label="Open SOP & Knowledge Portal",
        icon="📚"
    )

else:

    st.info("No investigations recorded for this date.")

st.divider()

# ----------------------------------
# OPERATIONS INTELLIGENCE VALUE
# ----------------------------------

st.subheader("Operations Intelligence Value")

col1, col2 = st.columns(2)

with col1:

    st.success(
        """
✓ Operator Accountability

✓ Equipment Familiarity

✓ Tag Familiarity

✓ Compliance Monitoring

✓ Knowledge Retention
"""
    )

with col2:

    st.success(
        """
✓ Fault Detection

✓ Audit Trail

✓ KPI Evaluation

✓ Data Collection

✓ Optimization Readiness
"""
    )

st.divider()

# ----------------------------------
# DATA SEPARATION MODEL
# ----------------------------------

st.subheader("Data Source Architecture")

st.markdown(
    """
### DCS DATA

- Flows
- Temperatures
- Pressures
- Levels
- Analyzer Values
- PERC Injection Rate

### LABORATORY DATA

- DB OH Composition
- Stabilizer Bottom Composition
- Caustic Strength
- Sample Results

### OPERATOR ROUND DATA

- Local Gauge Readings
- Local Temperatures
- Local Levels
- Visual Inspections
- Pump Checks
- Leak Checks
- Remarks

### FIELD TESTS

- HCl Dräger Tests
- Verification Measurements
"""
)

st.divider()

with st.expander("About This Page"):

    st.markdown(
        """
This page demonstrates how the platform combines:

✅ Operator Round Data

✅ Laboratory Results

✅ Dräger Tests

✅ DCS Process Data

✅ Field Verification

✅ Troubleshooting Records

into a single operational workflow.
"""
    )
