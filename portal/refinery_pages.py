from __future__ import annotations

from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

from portal import db, ui
from src.portal.data_store import (
    CHECKLIST_FILE,
    CHECKLIST_RECORDS_FILE,
    DRAGER_FILE,
    EQUIPMENT_FILE,
    GUIDE_FILE,
    HIERARCHY_FILE,
    INVESTIGATION_FILE,
    KPI_UNIT,
    LAB_FILE,
    LESSONS_FILE,
    NORMAL_MODE,
    OPERATING_MODES_FILE,
    ROUNDS_FILE,
    SCHEDULE_FILE,
    SOP_FILE,
    TAG_REFERENCE_FILE,
    append_rows,
    health_summary,
    limit_status,
    load_csv,
    load_kpis,
    mode_note,
    operating_limits,
    relationship_summary,
    verification_table,
    verify_reading,
)

COLORS = ["#1857C9", "#2F7DE1", "#6B8FD8", "#E8964A", "#C6303E", "#3B9B7A"]


def _safe_metric(value: object, decimals: int = 1, suffix: str = "") -> str:
    if pd.isna(value):
        return "No data"
    return f"{float(value):.{decimals}f}{suffix}"


def _source_banner() -> None:
    st.markdown(
        '<span class="portal-chip demo">RECONSTRUCTED DEMONSTRATION DATA</span> &nbsp; '
        '<span class="small-note">The original calculation logic is preserved. Replace the packaged reconstruction with the repository CSVs before operational use.</span>',
        unsafe_allow_html=True,
    )


def _selected_kpi(df: pd.DataFrame, key: str) -> tuple[pd.Series | None, object | None]:
    dates = sorted(df["date"].dt.date.unique())
    default_date = df[df["operating_mode"] == NORMAL_MODE]["date"].max()
    if pd.isna(default_date):
        default_date = df["date"].max()
    selected_date = st.date_input(
        "Operating date",
        value=default_date.date(),
        min_value=min(dates),
        max_value=max(dates),
        key=key,
    )
    rows = df[df["date"].dt.date == selected_date]
    return (rows.iloc[0] if not rows.empty else None), selected_date


def render_overview(config: dict) -> None:
    ui.hero(config, "Butamer Unit Overview", "A shared operational picture built from process, laboratory and operating-limit logic.")
    _source_banner()
    df = load_kpis()
    if df.empty:
        st.error("No Butamer KPI dataset is available.")
        return
    selected, selected_date = _selected_kpi(df, "refinery_overview_date")
    if selected is None:
        st.error("No KPI record exists for the selected date.")
        return
    note = mode_note(selected_date)
    if note:
        st.warning(f"{note} This date is outside normal operation.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Feed iC4 ratio", _safe_metric(selected.get("feed_ic4_ratio"), 1, "%"))
    c2.metric("Product iC4 ratio", _safe_metric(selected.get("product_ic4_ratio"), 1, "%"))
    c3.metric("iC4 improvement", _safe_metric(selected.get("ic4_improvement"), 1, " pts"))
    c4.metric("Reactor ΔT", _safe_metric(selected.get("reactor_delta_t"), 1, " °C"))

    summary = health_summary(selected)
    status_order = ["Normal", "Monitor", "Action Required", "No Data"]
    counts = summary["Status"].value_counts() if not summary.empty else pd.Series(dtype=int)
    st.markdown("#### Unit health")
    cols = st.columns(4)
    for index, status in enumerate(status_order):
        cols[index].metric(status, int(counts.get(status, 0)))
    left, right = st.columns([1.45, .55])
    with left:
        st.markdown(summary.to_html(index=False, classes="portal-table", border=0), unsafe_allow_html=True)
    with right:
        if summary.empty:
            st.info("No operating limits are configured.")
        else:
            figure = px.pie(
                summary, names="Status", hole=.62,
                color="Status",
                color_discrete_map={"Normal": "#2F8F5B", "Monitor": "#E3A82B", "Action Required": "#C6303E", "No Data": "#8B98A8"},
            )
            figure.update_layout(template="plotly_white", margin=dict(l=5, r=5, t=5, b=5), showlegend=True)
            st.plotly_chart(figure, use_container_width=True)

    normal = df[df["operating_mode"] == NORMAL_MODE]
    st.markdown("#### Performance trend")
    trend = px.line(
        normal, x="date", y=["feed_ic4_ratio", "product_ic4_ratio"], markers=True,
        color_discrete_sequence=COLORS,
        labels={"value": "iC4 ratio (%)", "variable": "Series"},
    )
    trend.update_layout(template="plotly_white", hovermode="x unified", legend_title_text="", margin=dict(l=15, r=15, t=15, b=15))
    st.plotly_chart(trend, use_container_width=True)

    with st.expander("Data scope and operating modes"):
        modes = load_csv(OPERATING_MODES_FILE)
        st.write(f"KPI period: {df['date'].min().date()} to {df['date'].max().date()}")
        st.write(f"Normal-operation records: {len(normal):,} of {len(df):,}")
        if not modes.empty:
            st.markdown(modes.to_html(index=False, classes="portal-table", border=0), unsafe_allow_html=True)
        st.caption("Status is calculated by limit_status using low/high monitor and action limits from config/operating_limits.csv.")


def _condition_scatter(frame: pd.DataFrame, column: str, name: str, decimals: int) -> None:
    chart = frame[["date", column, "product_ic4_ratio"]].dropna()
    if chart.empty:
        st.info(f"No matched records for {name}.")
        return
    fig = px.scatter(
        chart, x=column, y="product_ic4_ratio", custom_data=["date"],
        labels={column: name, "product_ic4_ratio": "Product iC4 ratio (%)"},
        color_discrete_sequence=COLORS,
    )
    fig.update_traces(hovertemplate=f"{name}: %{{x:.{decimals}f}}<br>Product iC4 ratio: %{{y:.1f}}%<br>Date: %{{customdata[0]|%Y-%m-%d}}<extra></extra>")
    fig.update_layout(template="plotly_white", margin=dict(l=15, r=15, t=15, b=15))
    st.plotly_chart(fig, use_container_width=True)


def render_analytics(config: dict) -> None:
    ui.hero(config, "Feed → Process → Product Analytics", "Understand how feed quality and operating conditions move with Butamer product quality.")
    _source_banner()
    df = load_kpis()
    if df.empty:
        st.error("No KPI data is available.")
        return
    valid_df = df.dropna(subset=["reactor_a_delta_t", "product_ic4_ratio"])
    if valid_df.empty:
        st.error("No valid matched laboratory and DCS records are available.")
        return
    normal_df = valid_df[valid_df["operating_mode"] == NORMAL_MODE]
    dates = sorted(valid_df["date"].dt.date.unique())
    selected_date = st.date_input(
        "Analysis date", value=normal_df["date"].max().date(), min_value=min(dates), max_value=max(dates), key="refinery_analysis_date"
    )
    selected_rows = valid_df[valid_df["date"].dt.date == selected_date]
    if selected_rows.empty:
        st.error("No matched laboratory and DCS data exists for the selected date.")
        return
    selected = selected_rows.iloc[0]
    note = mode_note(selected_date)
    if note:
        st.warning(f"{note} This date does not represent normal performance.")
    include_other = st.toggle(f"Include {len(valid_df) - len(normal_df)} days outside normal operation", value=False)
    analysis_df = valid_df if include_other else normal_df
    st.caption(f"Charts and averages use {len(analysis_df)} days with both laboratory and DCS data. DCS data ends {valid_df['date'].max().date()}.")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Feed iC4 ratio", _safe_metric(selected["feed_ic4_ratio"], 1, "%"))
    c2.metric("Product iC4 ratio", _safe_metric(selected["product_ic4_ratio"], 1, "%"))
    c3.metric("iC4 improvement", _safe_metric(selected["ic4_improvement"], 1, " pts"))
    c4.metric("Reactor ΔT", _safe_metric(selected["reactor_delta_t"], 1, " °C"))

    st.markdown("#### Feed and product quality trend")
    trend = px.line(analysis_df, x="date", y=["feed_ic4_ratio", "product_ic4_ratio"], markers=True, color_discrete_sequence=COLORS)
    trend.update_layout(template="plotly_white", hovermode="x unified", legend_title_text="", margin=dict(l=15, r=15, t=15, b=15))
    st.plotly_chart(trend, use_container_width=True)

    st.markdown("#### Process relationships")
    reactor_tab, h2_tab, pressure_tab, moisture_tab = st.tabs(["Reactor ΔT", "Hydrogen flow", "Stabilizer pressure", "Drier moisture"])
    with reactor_tab:
        _condition_scatter(analysis_df, "reactor_delta_t", "Reactor ΔT (°C)", 1)
    with h2_tab:
        _condition_scatter(analysis_df, "Makeup Hydrogen Flow_feed", "Hydrogen flow", 1)
    with pressure_tab:
        _condition_scatter(analysis_df, "Stabiliser Pressure_feed", "Stabilizer pressure", 2)
    with moisture_tab:
        _condition_scatter(analysis_df, "Butane Drier Moisture Analyzer_feed", "Drier moisture", 3)

    relationships = relationship_summary(
        analysis_df,
        {
            "Reactor ΔT": "reactor_delta_t",
            "Reactor ΔP": "reactor_delta_p",
            "Hydrogen Flow": "Makeup Hydrogen Flow_feed",
            "Stabilizer Pressure": "Stabiliser Pressure_feed",
            "Drier Moisture": "Butane Drier Moisture Analyzer_feed",
            "Feed iC4 Ratio": "feed_ic4_ratio",
        },
    )
    st.markdown("#### What conditions link to product quality?")
    st.dataframe(relationships, use_container_width=True, hide_index=True)
    st.caption("The preserved relationship_summary function ranks absolute correlation and labels it weak, moderate or strong. Correlation does not establish cause.")

    table = analysis_df[["date", "operating_mode", "feed_ic4_ratio", "product_ic4_ratio", "ic4_improvement", "reactor_delta_t", "Makeup Hydrogen Flow_feed"]].sort_values("date", ascending=False)
    st.markdown("#### Daily performance")
    st.dataframe(table, use_container_width=True, hide_index=True)
    best = analysis_df.loc[analysis_df["ic4_improvement"].idxmax()]
    st.success(f"Highest iC4 improvement in this view: {best['ic4_improvement']:.1f} pts on {best['date'].date()}.")


def _refinery_context() -> tuple[pd.DataFrame, ...]:
    return (
        load_kpis(), load_csv(HIERARCHY_FILE), load_csv(ROUNDS_FILE, dates=True),
        load_csv(SCHEDULE_FILE, dates=True), load_csv(DRAGER_FILE, dates=True),
        load_csv(LAB_FILE, dates=True), load_csv(INVESTIGATION_FILE, dates=True),
        load_csv(CHECKLIST_FILE), load_csv(TAG_REFERENCE_FILE), load_csv(SOP_FILE), load_csv(GUIDE_FILE),
    )


def render_rounds(config: dict) -> None:
    ui.hero(config, "Digital Operator Rounds & Verification", "Complete the schedule, record checklist evidence, compare field and DCS readings, and retain the investigation trail.")
    _source_banner()
    (kpi_df, hierarchy_df, rounds_df, schedule_df, drager_df, lab_df, investigation_df,
     checklist_df, tag_df, sop_df, guide_df) = _refinery_context()
    if hierarchy_df.empty:
        st.error("The master hierarchy is not available.")
        return
    refinery_name = "Refinery" if "Refinery" in hierarchy_df["business_unit"].astype(str).unique() else hierarchy_df["business_unit"].iloc[0]
    hierarchy_df = hierarchy_df[hierarchy_df["business_unit"] == refinery_name]
    c1, c2, c3 = st.columns(3)
    block = c1.selectbox("Block", sorted(hierarchy_df["block"].dropna().unique()))
    in_block = hierarchy_df[hierarchy_df["block"] == block]
    units = sorted(in_block["unit"].dropna().unique())
    ready = in_block[in_block["equipment"].isin(tag_df["equipment"] if not tag_df.empty else [])]["unit"].unique()
    unit = c2.selectbox("Unit", units, index=next((i for i, name in enumerate(units) if name in ready), 0))
    unit_hierarchy = in_block[in_block["unit"] == unit]
    unit_equipment = set(unit_hierarchy["equipment"].dropna())

    def for_unit(frame: pd.DataFrame) -> pd.DataFrame:
        return frame[frame["equipment"].isin(unit_equipment)] if not frame.empty and "equipment" in frame.columns else frame.iloc[0:0]

    schedule_df, rounds_df = for_unit(schedule_df), for_unit(rounds_df)
    drager_df, lab_df, investigation_df = for_unit(drager_df), for_unit(lab_df), for_unit(investigation_df)
    unit_tag_df = for_unit(tag_df)
    if unit != KPI_UNIT:
        kpi_df = kpi_df.iloc[0:0]
    available_dates = sorted(set(schedule_df["date"].dt.date) | set(rounds_df["date"].dt.date)) if not schedule_df.empty or not rounds_df.empty else []
    selected_date = c3.date_input(
        "Round date", value=max(available_dates) if available_dates else datetime.now().date(),
        min_value=min(available_dates) if available_dates else None,
        max_value=max(available_dates) if available_dates else None,
    )
    schedule_records = schedule_df[schedule_df["date"].dt.date == selected_date] if not schedule_df.empty else schedule_df
    round_records = rounds_df[rounds_df["date"].dt.date == selected_date] if not rounds_df.empty else rounds_df
    deviations = investigation_df[investigation_df["date"].dt.date == selected_date] if not investigation_df.empty else investigation_df
    verification_records = verification_table(round_records) if not round_records.empty else pd.DataFrame()

    expected_set = set(zip(schedule_records.get("equipment", []), schedule_records.get("parameter", [])))
    recorded_set = set(zip(round_records.get("equipment", []), round_records.get("parameter", [])))
    completed_set, off_schedule_set, missing_set = expected_set & recorded_set, recorded_set - expected_set, expected_set - recorded_set
    expected_measurements, completed_measurements = len(expected_set), len(completed_set)
    completion = completed_measurements / expected_measurements * 100 if expected_measurements else 0
    critical_missing = 0
    if not schedule_records.empty:
        critical_missing = len(schedule_records[(schedule_records["criticality"] == "High") & schedule_records[["equipment", "parameter"]].apply(tuple, axis=1).isin(missing_set)])
    open_deviations = len(verification_records[verification_records["Status"].isin(["Monitor", "Critical"])]) if not verification_records.empty else 0
    pending_actions = len(deviations[deviations["status"] == "Open"]) if not deviations.empty else 0

    metrics = st.columns(7)
    for col, label, value in zip(metrics, ["Expected", "Completed", "Completion", "Missing", "Critical missing", "Open deviations", "Pending actions"],
                                 [expected_measurements, completed_measurements, f"{completion:.1f}%", len(missing_set), critical_missing, open_deviations, pending_actions]):
        col.metric(label, value)

    summary_tab, entry_tab, evidence_tab, investigation_tab = st.tabs(["Schedule & compliance", "Enter reading", "Field / lab / DCS", "Investigations"])
    with summary_tab:
        if schedule_records.empty:
            st.info("No measurement schedule exists for this date and unit.")
        else:
            st.dataframe(schedule_records[["equipment", "parameter", "expected_entries", "criticality"]], use_container_width=True, hide_index=True)
            compliance = schedule_records[["equipment", "parameter", "criticality"]].copy()
            compliance["status"] = compliance[["equipment", "parameter"]].apply(lambda row: "Complete" if tuple(row) in completed_set else "Missing", axis=1)
            st.dataframe(compliance, use_container_width=True, hide_index=True)
        if off_schedule_set:
            st.caption("Recorded but not scheduled: " + ", ".join(f"{e} – {p}" for e, p in sorted(off_schedule_set)))

    with entry_tab:
        in_unit = unit_hierarchy[unit_hierarchy["equipment"].isin(tag_df["equipment"] if not tag_df.empty else [])]
        if in_unit.empty:
            st.info("Round entry opens when equipment and tag references are configured for this unit.")
        else:
            e1, e2 = st.columns(2)
            section = e1.selectbox("Section", sorted(in_unit["section"].dropna().unique()))
            equipment = e2.selectbox("Equipment", sorted(in_unit[in_unit["section"] == section]["equipment"].dropna().unique()))
            parameters = tag_df[tag_df["equipment"] == equipment]
            parameter = st.selectbox("Parameter", parameters["parameter"].tolist())
            selected_parameter = parameters[parameters["parameter"] == parameter].iloc[0]
            uom = selected_parameter["unit_of_measure"] if pd.notna(selected_parameter["unit_of_measure"]) else ""
            checks: dict[str, bool] = {}
            selected_checklist = checklist_df[checklist_df["equipment"] == equipment] if not checklist_df.empty else checklist_df
            if not selected_checklist.empty:
                st.markdown("**Inspection checklist**")
                for item in selected_checklist["check_item"]:
                    checks[item] = st.checkbox(item, key=f"refinery_{equipment}_{item}")
            with st.form("refinery_round_form", clear_on_submit=True):
                recorded_by = st.text_input("Recorded by", value=st.session_state.get("display_name", ""))
                field_value = st.number_input(f"Field reading ({uom})" if uom else "Field reading", value=None, placeholder="Enter reading")
                remarks = st.text_area("Remarks")
                submit = st.form_submit_button("Save verified entry", type="primary")
            if submit:
                if not recorded_by.strip() or field_value is None:
                    st.error("Enter the recorder name and field reading.")
                else:
                    recorded_at = datetime.now().strftime("%Y-%m-%d %H:%M")
                    result = verify_reading(equipment, parameter, selected_date, field_value)
                    append_rows(ROUNDS_FILE, [{
                        "date": selected_date, "business_unit": refinery_name, "block": block, "unit": unit,
                        "section": section, "equipment": equipment, "parameter": parameter, "field_value": field_value,
                        "unit_of_measure": uom, "status": result["status"], "remarks": remarks,
                        "recorded_by": recorded_by.strip(), "recorded_at": recorded_at,
                    }])
                    if checks:
                        append_rows(CHECKLIST_RECORDS_FILE, [{"date": selected_date, "equipment": equipment, "check_item": item,
                                                             "checked": checked, "recorded_by": recorded_by.strip(), "recorded_at": recorded_at}
                                                            for item, checked in checks.items()])
                    db.log_action(st.session_state.username, st.session_state.role, "refinery", "refinery_round_saved",
                                  {"equipment": equipment, "parameter": parameter, "status": result["status"]})
                    st.success(f"Saved {equipment} – {parameter}. Field vs DCS status: {result['status']}.")

    with evidence_tab:
        st.markdown("#### Operator field measurements")
        if round_records.empty:
            st.info("No field measurements exist for this date.")
        else:
            st.dataframe(round_records[["equipment", "parameter", "field_value", "unit_of_measure", "status", "remarks", "recorded_by", "recorded_at"]], use_container_width=True, hide_index=True)
        st.markdown("#### Laboratory integration")
        lab_rows: list[dict] = []
        kpi_row = kpi_df[kpi_df["date"].dt.date == selected_date] if not kpi_df.empty else kpi_df
        if not kpi_row.empty:
            lab_rows.extend([
                {"Sample Point": "DB OH (Feed)", "Parameter": "iC4 Ratio", "Value": round(kpi_row.iloc[0]["feed_ic4_ratio"], 1), "Unit": "%", "Source": "Laboratory data"},
                {"Sample Point": "Stabilizer Bottom (Product)", "Parameter": "iC4 Ratio", "Value": round(kpi_row.iloc[0]["product_ic4_ratio"], 1), "Unit": "%", "Source": "Laboratory data"},
            ])
        lab_records = lab_df[lab_df["date"].dt.date == selected_date] if not lab_df.empty else lab_df
        for _, record in lab_records.iterrows():
            lab_rows.append({"Sample Point": record["sample_point"], "Parameter": record["parameter"], "Value": record["value"], "Unit": record["unit"], "Source": "Simulated"})
        if lab_rows:
            st.dataframe(pd.DataFrame(lab_rows), use_container_width=True, hide_index=True)
        caustic = lab_records[lab_records["parameter"] == "Caustic Strength"] if not lab_records.empty else lab_records
        if not caustic.empty:
            caustic_limit = next(limit for limit in operating_limits() if limit["key"] == "caustic_strength")
            st.metric("Caustic strength status", limit_status(caustic.iloc[0]["value"], caustic_limit))
        st.markdown("#### Field vs DCS verification")
        if verification_records.empty:
            st.info("No verification records exist for this date.")
        else:
            st.dataframe(verification_records, use_container_width=True, hide_index=True)
        st.markdown("#### Equipment tag reference")
        if not unit_tag_df.empty:
            st.dataframe(unit_tag_df[["equipment", "parameter", "tag", "description", "tag_status"]], use_container_width=True, hide_index=True)
        st.markdown("#### Dräger test trend")
        if drager_df.empty:
            st.info("No Dräger tests exist for this unit.")
        else:
            fig = px.line(drager_df, x="date", y="hcl_ppm", color="test_location", markers=True, color_discrete_sequence=COLORS)
            fig.update_layout(template="plotly_white", margin=dict(l=15, r=15, t=15, b=15))
            st.plotly_chart(fig, use_container_width=True)

    with investigation_tab:
        if deviations.empty:
            st.info("No investigation records exist for this unit and date.")
        else:
            view = deviations.copy()
            view["date"] = view["date"].dt.date
            st.dataframe(view[["date", "area", "observation", "priority", "status"]], use_container_width=True, hide_index=True)
            selected_issue = st.selectbox("Investigation", deviations["observation"].tolist())
            issue = deviations[deviations["observation"] == selected_issue].iloc[0]
            st.markdown(f"**Possible cause**  \n{issue['possible_cause']}  \n\n**Recommended action**  \n{issue['recommended_action']}")
            related_sop = sop_df[sop_df["sop_id"] == issue["related_sop"]] if not sop_df.empty else sop_df
            if not related_sop.empty:
                st.info(f"Related SOP: {related_sop.iloc[0]['sop_id']} – {related_sop.iloc[0]['title']}")
            related_guide = guide_df[guide_df["issue"] == issue["related_issue"]] if not guide_df.empty else guide_df
            if not related_guide.empty:
                st.info(f"Related guide: {related_guide.iloc[0]['issue']}")


def _keyword_filter(frame: pd.DataFrame, keyword: str) -> pd.DataFrame:
    if frame.empty or not keyword:
        return frame
    mask = frame.astype(str).apply(lambda column: column.str.contains(keyword, case=False, na=False, regex=False)).any(axis=1)
    return frame[mask]


def render_knowledge(config: dict) -> None:
    ui.hero(config, "SOP & Knowledge Portal", "Search equipment references, SOP metadata, troubleshooting guidance and lessons learned in one controlled workspace.")
    st.warning("The reconstructed library is illustrative. Replace it with approved controlled documents before operational use.")
    equipment = load_csv(EQUIPMENT_FILE)
    sops = load_csv(SOP_FILE)
    guides = load_csv(GUIDE_FILE)
    lessons = load_csv(LESSONS_FILE)
    search = st.text_input("Search all refinery knowledge", placeholder="Equipment, tag, SOP, issue or lesson")
    equipment_results, sop_results = _keyword_filter(equipment, search), _keyword_filter(sops, search)
    guide_results, lesson_results = _keyword_filter(guides, search), _keyword_filter(lessons, search)
    eq_tab, sop_tab, guide_tab, lesson_tab = st.tabs(["Equipment", "SOP library", "Troubleshooting", "Lessons learned"])
    with eq_tab:
        if equipment_results.empty:
            st.info("No equipment records match.")
        else:
            sections = ["All"] + sorted(equipment_results["section"].dropna().unique().tolist())
            section = st.selectbox("Section", sections)
            view = equipment_results if section == "All" else equipment_results[equipment_results["section"] == section]
            st.dataframe(view, use_container_width=True, hide_index=True)
    with sop_tab:
        if sop_results.empty:
            st.info("No SOP records match.")
        else:
            display = sop_results.drop(columns=["document_path"], errors="ignore")
            st.dataframe(display, use_container_width=True, hide_index=True)
            for _, row in sop_results[sop_results.get("document_path", pd.Series(dtype=str)).fillna("") != ""].iterrows():
                from src.portal.data_store import ROOT
                document = ROOT / row["document_path"]
                if document.exists():
                    st.download_button(f"Open {row['sop_id']} – {row['title']}", document.read_bytes(), file_name=document.name)
    with guide_tab:
        if guide_results.empty:
            st.info("No troubleshooting records match.")
        else:
            st.dataframe(guide_results, use_container_width=True, hide_index=True)
            issue_name = st.selectbox("Troubleshooting topic", guide_results["issue"].tolist())
            issue = guide_results[guide_results["issue"] == issue_name].iloc[0]
            st.markdown(f"**Symptoms**  \n{issue['symptoms']}  \n\n**Possible causes**  \n{issue['possible_causes']}  \n\n**Recommended actions**  \n{issue['recommended_actions']}")
    with lesson_tab:
        if lesson_results.empty:
            st.info("No lessons match.")
        else:
            st.dataframe(lesson_results, use_container_width=True, hide_index=True)
            title = st.selectbox("Lesson", lesson_results["title"].tolist())
            lesson = lesson_results[lesson_results["title"] == title].iloc[0]
            st.markdown(f"**Observation**  \n{lesson['observation']}  \n\n**Resolution**  \n{lesson['resolution']}  \n\n**Recommendation**  \n{lesson['recommendation']}")
