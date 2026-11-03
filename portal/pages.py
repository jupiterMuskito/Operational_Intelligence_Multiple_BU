from __future__ import annotations

import io
import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from portal import config_store, db, ui

PLOT_COLORS = ["#1857C9", "#2F7DE1", "#6B8FD8", "#E8964A", "#C6303E", "#3B9B7A"]


def _identity() -> tuple[str, str, str]:
    return (
        str(st.session_state.get("username", "unknown")),
        str(st.session_state.get("role", "operator")),
        str(st.session_state.get("business_unit", "")),
    )


def _load_data(config: dict[str, Any]) -> pd.DataFrame:
    try:
        return config_store.load_process_data(config)
    except config_store.ConfigError as exc:
        st.error(str(exc))
        return pd.DataFrame()


def _dated_frame(frame: pd.DataFrame, config: dict[str, Any], key: str) -> pd.DataFrame:
    date_column = str(config.get("data", {}).get("date_column", "date"))
    if frame.empty or date_column not in frame.columns:
        return frame
    parsed = pd.to_datetime(frame[date_column], errors="coerce")
    valid = parsed.dropna()
    if valid.empty:
        return frame
    selected = st.date_input(
        "Period",
        value=(valid.min().date(), valid.max().date()),
        min_value=valid.min().date(),
        max_value=valid.max().date(),
        key=key,
    )
    if not isinstance(selected, (tuple, list)) or len(selected) != 2:
        return frame
    start, end = selected
    return frame.loc[parsed.dt.date.between(start, end)].copy()


def _metric_value(frame: pd.DataFrame, item: dict[str, Any]) -> float | int | None:
    column = item.get("column", "")
    aggregate = str(item.get("aggregate", "mean")).lower()
    if aggregate == "count":
        return int(len(frame))
    if column not in frame.columns:
        return None
    series = pd.to_numeric(frame[column], errors="coerce").dropna()
    if series.empty:
        return None
    if aggregate == "latest":
        return float(series.iloc[-1])
    if aggregate == "sum":
        return float(series.sum())
    if aggregate == "min":
        return float(series.min())
    if aggregate == "max":
        return float(series.max())
    return float(series.mean())


def _metric_delta(value: float | int | None, item: dict[str, Any]) -> str | None:
    target = item.get("target")
    if value is None or target is None:
        return None
    return f"{float(value) - float(target):+.1f} vs target"


def _data_badge(config: dict[str, Any]) -> None:
    info = config.get("data", {})
    demo = bool(info.get("is_demo", False))
    css = "demo" if demo else "live"
    label = "DEMONSTRATION DATA" if demo else "ADMIN-SUPPLIED DATA"
    st.markdown(
        f'<span class="portal-chip {css}">{label}</span> &nbsp; '
        f'<span class="small-note">{info.get("source_label", "Source not configured")}</span>',
        unsafe_allow_html=True,
    )


def render_home(slug: str, config: dict[str, Any]) -> None:
    nav = config["navigation"]
    ui.hero(config, config.get("home_title", f"{config['name']} Operations Center"),
            config.get("home_subtitle", "One operational workspace for monitoring, field verification, knowledge and learning."))
    _data_badge(config)
    frame = _load_data(config)
    if frame.empty:
        st.warning("No operational dataset is connected. An administrator can upload one on the Admin page.")
    else:
        mode_column = config.get("data", {}).get("mode_column", "")
        normal_mode = config.get("data", {}).get("normal_mode", "")
        kpi_frame = frame
        if mode_column in frame.columns and normal_mode:
            kpi_frame = frame[frame[mode_column].astype(str) == str(normal_mode)]
        st.subheader(config.get("kpi_section_title", "Operations at a glance"))
        metrics = config.get("kpis", [])[:6]
        columns = st.columns(min(3, max(1, len(metrics))))
        for index, item in enumerate(metrics):
            value = _metric_value(kpi_frame, item)
            formatted = ui.fmt_number(value, int(item.get("decimals", 1)))
            unit = str(item.get("unit", ""))
            columns[index % len(columns)].metric(
                str(item.get("label", item.get("column", "KPI"))),
                f"{formatted}{(' ' + unit) if unit else ''}",
                _metric_delta(value, item),
            )
        if mode_column in frame.columns and normal_mode and len(kpi_frame) != len(frame):
            st.caption(f"KPI summary uses {len(kpi_frame):,} rows in {normal_mode} mode; {len(frame) - len(kpi_frame):,} non-normal rows are excluded.")

    st.subheader("Operational workspace")
    items = [
        (nav.get("overview", "Overview"), "Shared unit health, current status and priority exceptions.", "MONITOR"),
        (nav.get("analytics", "Analytics"), "Connect feed, process and product performance in one analytical view.", "ANALYZE"),
        (nav.get("rounds", "Digital rounds"), "Capture field observations, compare local and control-room readings, and keep history.", "VERIFY"),
        (nav.get("sops", "SOP & knowledge"), "Find controlled procedures, guidance and unit-specific learning resources.", "LEARN"),
        (nav.get("events", "Events"), "Record operational changes, actions and investigation context.", "IMPROVE"),
    ]
    columns = st.columns(3)
    for index, (title, text, badge) in enumerate(items):
        columns[index % 3].markdown(ui.card(title, text, badge), unsafe_allow_html=True)
        if index % 3 == 2:
            st.write("")

    st.subheader("Current context")
    context = config.get("context", {})
    c1, c2, c3 = st.columns(3)
    c1.markdown(ui.card("Business unit", config["name"], "BU"), unsafe_allow_html=True)
    c2.markdown(ui.card("Operational scope", " → ".join(config.get("hierarchy", [])), "SCOPE"), unsafe_allow_html=True)
    c3.markdown(ui.card("Data governance", context.get("governance", "Admin uploads, audit trail and explicit source labels."), "CONTROL"), unsafe_allow_html=True)


def render_analytics(slug: str, config: dict[str, Any]) -> None:
    ui.hero(config, config["navigation"].get("analytics", "Operations Analytics"),
            config.get("analytics_subtitle", "Explore time trends, operating modes, relationships and quality outcomes."))
    _data_badge(config)
    frame = _load_data(config)
    if frame.empty:
        st.info("Upload a CSV or Excel dataset from Admin → Data to activate analytics.")
        return
    filtered = _dated_frame(frame, config, f"analytics_period_{slug}")
    mode_column = config.get("data", {}).get("mode_column", "")
    if mode_column in filtered.columns:
        modes = sorted(filtered[mode_column].dropna().astype(str).unique().tolist())
        selected_modes = st.multiselect("Operating mode", modes, default=modes, key=f"mode_{slug}")
        if selected_modes:
            filtered = filtered[filtered[mode_column].astype(str).isin(selected_modes)]
    numeric = [column for column in filtered.columns if pd.to_numeric(filtered[column], errors="coerce").notna().mean() >= 0.7]
    preferred = [item.get("column") for item in config.get("kpis", []) if item.get("column") in numeric]
    metrics = st.multiselect("Metrics", numeric, default=preferred[:4], key=f"metrics_{slug}")
    date_column = config.get("data", {}).get("date_column", "date")
    if metrics and date_column in filtered.columns:
        plot = filtered[[date_column] + metrics].copy()
        plot[date_column] = pd.to_datetime(plot[date_column], errors="coerce")
        for metric in metrics:
            plot[metric] = pd.to_numeric(plot[metric], errors="coerce")
        fig = px.line(plot, x=date_column, y=metrics, color_discrete_sequence=PLOT_COLORS)
        fig.update_layout(template="plotly_white", hovermode="x unified", legend_title_text="", margin=dict(l=15, r=15, t=20, b=15))
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Choose one or more numeric metrics to draw the time series.")

    relationship = config.get("analytics", {}).get("relationship", {})
    x_column, y_column = relationship.get("x", ""), relationship.get("y", "")
    left, right = st.columns([1.15, .85])
    with left:
        if x_column in filtered.columns and y_column in filtered.columns:
            scatter = px.scatter(
                filtered, x=x_column, y=y_column,
                color=mode_column if mode_column in filtered.columns else None,
                trendline="ols" if len(filtered) >= 3 else None,
                color_discrete_sequence=PLOT_COLORS,
                title=relationship.get("title", f"{x_column} vs {y_column}"),
            )
            scatter.update_layout(template="plotly_white", margin=dict(l=15, r=15, t=50, b=15))
            st.plotly_chart(scatter, use_container_width=True)
        else:
            st.info("Configure an x/y relationship in the business-unit JSON to add a diagnostic plot.")
    with right:
        st.markdown("#### Data quality")
        st.metric("Rows in view", f"{len(filtered):,}")
        st.metric("Columns", f"{len(filtered.columns):,}")
        missing = int(filtered.isna().sum().sum())
        cells = max(1, filtered.shape[0] * filtered.shape[1])
        st.metric("Missing cells", f"{missing:,}", f"{missing / cells * 100:.1f}%")
    st.markdown("#### Analytical table")
    st.dataframe(filtered, use_container_width=True, hide_index=True)
    st.download_button("Download filtered CSV", filtered.to_csv(index=False).encode("utf-8"),
                       f"{slug}_analytics.csv", "text/csv")


def render_rounds(slug: str, config: dict[str, Any]) -> None:
    ui.hero(config, config["navigation"].get("rounds", "Digital Operator Rounds"),
            "Record field condition, verify instruments and make round completion visible across shifts.")
    submit_tab, history_tab = st.tabs(["Complete round", "Round history"])
    frame = _load_data(config)
    latest = frame.iloc[-1] if not frame.empty else pd.Series(dtype=object)
    fields = config.get("rounds", {}).get("fields", [])
    username, role, _ = _identity()
    with submit_tab:
        if not fields:
            st.info("No round fields are configured for this business unit. An administrator can import a configuration template.")
        else:
            with st.form(f"round_form_{slug}", clear_on_submit=True):
                h1, h2, h3 = st.columns(3)
                round_date = h1.date_input("Round date", value=date.today())
                shift = h2.selectbox("Shift", config.get("rounds", {}).get("shifts", ["Day", "Night"]))
                unit_name = h3.selectbox("Area / unit", config.get("rounds", {}).get("units", config.get("hierarchy", [])[-1:]))
                st.markdown("#### Instrument verification")
                readings: dict[str, dict[str, Any]] = {}
                for index, item in enumerate(fields):
                    c1, c2, c3, c4 = st.columns([1.45, 1, 1, .8])
                    label = str(item.get("label", item.get("tag", f"Field {index + 1}")))
                    tag = str(item.get("tag", f"field_{index}"))
                    dcs_column = str(item.get("dcs_column", ""))
                    dcs_value = pd.to_numeric(pd.Series([latest.get(dcs_column)]), errors="coerce").iloc[0] if dcs_column else float("nan")
                    default = float(dcs_value) if pd.notna(dcs_value) else float(item.get("default", 0.0))
                    c1.markdown(f"**{label}**  \n`{tag}` · {item.get('unit', '')}")
                    field_value = c2.number_input("Field reading", value=default, key=f"{slug}_{tag}", label_visibility="collapsed")
                    c3.text_input("DCS reference", value=(f"{dcs_value:.2f}" if pd.notna(dcs_value) else "Not connected"), disabled=True,
                                  key=f"dcs_{slug}_{tag}", label_visibility="collapsed")
                    tolerance = float(item.get("tolerance", 0.0))
                    difference = abs(float(field_value) - float(dcs_value)) if pd.notna(dcs_value) else None
                    state = "Within tolerance" if difference is not None and difference <= tolerance else ("Review" if difference is not None else "No reference")
                    c4.caption(state)
                    readings[tag] = {"label": label, "field": field_value, "dcs": None if pd.isna(dcs_value) else float(dcs_value),
                                     "tolerance": tolerance, "difference": difference, "state": state}
                st.markdown("#### Field condition")
                q1, q2, q3, q4 = st.columns(4)
                condition = q1.selectbox("Equipment condition", ["Normal", "Attention required", "Unavailable"])
                leaks = q2.selectbox("Leaks", ["None observed", "Minor", "Significant"])
                housekeeping = q3.selectbox("Housekeeping", ["Satisfactory", "Action required"])
                safety = q4.selectbox("Safety observation", ["No issue", "At-risk condition", "Positive observation"])
                comments = st.text_area("Comments / handover note")
                submitted = st.form_submit_button("Submit round", type="primary")
            if submitted:
                deviations = sum(1 for reading in readings.values() if reading["state"] == "Review")
                status = "Action required" if deviations or condition != "Normal" or leaks == "Significant" or safety == "At-risk condition" else "Complete"
                payload = {"round_date": str(round_date), "readings": readings, "condition": condition,
                           "leaks": leaks, "housekeeping": housekeeping, "safety": safety}
                db.save_round(slug, username, shift, unit_name, status, deviations, payload, comments)
                db.log_action(username, role, slug, "round_submitted", {"unit": unit_name, "status": status, "deviations": deviations})
                st.success(f"Round saved: {status}. {deviations} instrument deviation(s) flagged.")
    with history_tab:
        history = db.rounds_frame(slug)
        if history.empty:
            st.info("No rounds have been submitted for this business unit.")
        else:
            st.dataframe(history, use_container_width=True, hide_index=True)
            st.download_button("Download round history", history.to_csv(index=False).encode("utf-8"),
                               f"{slug}_round_history.csv", "text/csv")


def render_sops(slug: str, config: dict[str, Any]) -> None:
    ui.hero(config, config["navigation"].get("sops", "SOP & Knowledge Portal"),
            "Search controlled procedures, operating guidance, lessons learned and unit training material.")
    uploaded = db.sops_frame(slug)
    seed = pd.DataFrame(config.get("sops", {}).get("seed", []))
    if not seed.empty:
        seed["id"] = None
        seed["timestamp"] = "Configured reference"
        seed["filename"] = ""
        seed["file_path"] = ""
        seed["username"] = "Configuration"
        seed = seed.rename(columns={"unit": "unit_name"})
    documents = pd.concat([uploaded, seed], ignore_index=True, sort=False) if not uploaded.empty or not seed.empty else pd.DataFrame()
    query = st.text_input("Search title, category, unit or version", placeholder="Example: startup, isolation, sampling")
    if not documents.empty and query:
        searchable = documents.fillna("").astype(str).agg(" ".join, axis=1)
        documents = documents[searchable.str.contains(query, case=False, regex=False)]
    if documents.empty:
        st.info("No knowledge records match this search. Administrators can upload controlled files on the Admin page.")
        return
    show = [column for column in ["title", "category", "unit_name", "version", "timestamp"] if column in documents.columns]
    st.dataframe(documents[show], use_container_width=True, hide_index=True)
    downloadable = documents[documents.get("file_path", pd.Series(dtype=str)).fillna("").astype(str) != ""] if "file_path" in documents.columns else pd.DataFrame()
    if not downloadable.empty:
        st.markdown("#### Download controlled file")
        choices = downloadable.index.tolist()
        selected = st.selectbox("Document", choices, format_func=lambda idx: str(downloadable.loc[idx, "title"]))
        path = Path(str(downloadable.loc[selected, "file_path"]))
        if path.exists():
            st.download_button("Download selected document", path.read_bytes(), str(downloadable.loc[selected, "filename"]))
        else:
            st.warning("The metadata exists, but the file is not present on this deployment instance.")
    st.caption("Configured references are metadata only until an administrator uploads the controlled document. Always verify approval status before use.")


def render_events(slug: str, config: dict[str, Any]) -> None:
    ui.hero(config, config["navigation"].get("events", "Events & Investigations"),
            "Preserve operational context, actions and lessons so future troubleshooting starts with evidence.")
    username, role, _ = _identity()
    create_tab, timeline_tab = st.tabs(["Record event", "Operational timeline"])
    with create_tab:
        with st.form(f"event_{slug}", clear_on_submit=True):
            c1, c2, c3 = st.columns(3)
            event_date = c1.date_input("Event date", value=date.today())
            category = c2.selectbox("Category", ["Process deviation", "Quality", "Equipment", "Instrumentation", "Safety", "Operating change", "Lesson learned"])
            severity = c3.selectbox("Priority", ["Low", "Moderate", "High", "Critical"])
            title = st.text_input("Event title")
            description = st.text_area("What happened / observation")
            actions = st.text_area("Actions taken / next step")
            status = st.selectbox("Status", ["Open", "Monitoring", "Closed"])
            submitted = st.form_submit_button("Save event", type="primary")
        if submitted:
            if not title.strip() or not description.strip():
                st.error("Enter an event title and description.")
            else:
                db.save_event(slug, username, str(event_date), title.strip(), category, severity, status, description.strip(), actions.strip())
                db.log_action(username, role, slug, "event_created", {"title": title, "severity": severity, "status": status})
                st.success("Event added to the operational timeline.")
    with timeline_tab:
        events = db.events_frame(slug)
        if events.empty:
            st.info("No events have been recorded for this business unit.")
        else:
            status_filter = st.multiselect("Status", sorted(events["status"].unique()), default=sorted(events["status"].unique()))
            view = events[events["status"].isin(status_filter)] if status_filter else events
            st.dataframe(view, use_container_width=True, hide_index=True)
            st.download_button("Download event timeline", view.to_csv(index=False).encode("utf-8"),
                               f"{slug}_events.csv", "text/csv")


def _read_upload(upload: Any) -> pd.DataFrame:
    payload = upload.getvalue()
    if upload.name.lower().endswith(".csv"):
        return pd.read_csv(io.BytesIO(payload))
    return pd.read_excel(io.BytesIO(payload), engine="openpyxl")


def render_admin(slug: str, config: dict[str, Any], units: dict[str, dict[str, Any]]) -> None:
    ui.hero(config, "Portal Administration", "Manage business units, operational data, knowledge files and audit records without changing Python code.")
    if st.session_state.get("role") != "admin":
        st.error("Administrator access is required.")
        return
    username, role, _ = _identity()
    bu_tab, data_tab, sop_tab, audit_tab, system_tab = st.tabs(
        ["Business units", "Data & KPIs", "SOP uploads", "Audit log", "System"]
    )
    with bu_tab:
        st.markdown("#### Create by cloning an existing framework")
        st.caption("Cloning copies navigation, KPI, round and knowledge structures. Edit the exported JSON and import it to change labels, columns and thresholds—no Python changes are required.")
        with st.form("clone_bu"):
            c1, c2 = st.columns(2)
            source = c1.selectbox("Template", list(units), format_func=lambda key: units[key]["name"])
            new_name = c2.text_input("New business-unit name")
            clone = st.form_submit_button("Create business unit")
        if clone:
            try:
                created = config_store.clone_business_unit(source, new_name, units)
                db.log_action(username, role, slug, "business_unit_created", {"new_slug": created, "template": source})
                st.success(f"Created {new_name}. Sign out and select it on the login page.")
            except config_store.ConfigError as exc:
                st.error(str(exc))
        c1, c2 = st.columns(2)
        c1.download_button("Download current BU configuration", config_store.config_as_json(slug, config),
                           f"{slug}_configuration.json", "application/json")
        import_file = c2.file_uploader("Import / replace BU configuration", type=["json"], key="import_bu")
        if import_file is not None and c2.button("Apply imported configuration", type="primary"):
            try:
                imported = config_store.import_business_unit(import_file.getvalue(), units)
                db.log_action(username, role, slug, "business_unit_config_imported", {"imported_slug": imported})
                st.success(f"Configuration saved for {imported}. Reloading…")
                st.rerun()
            except config_store.ConfigError as exc:
                st.error(str(exc))
        st.markdown("#### Configured business units")
        table = pd.DataFrame([
            {"Slug": key, "Business unit": value["name"], "Scope": " → ".join(value.get("hierarchy", [])),
             "Data source": value.get("data", {}).get("source_label", "")}
            for key, value in units.items()
        ])
        st.dataframe(table, use_container_width=True, hide_index=True)
        st.markdown("#### Master hierarchy")
        hierarchy_path = config_store.ROOT / "data" / "sample" / "master_hierarchy.csv"
        if hierarchy_path.exists():
            hierarchy_frame = pd.read_csv(hierarchy_path)
            st.download_button("Download master hierarchy", hierarchy_frame.to_csv(index=False).encode("utf-8"),
                               "master_hierarchy.csv", "text/csv")
        hierarchy_upload = st.file_uploader("Replace master hierarchy CSV", type=["csv"], key="hierarchy_upload")
        if hierarchy_upload is not None and st.button("Publish hierarchy"):
            try:
                hierarchy_frame = pd.read_csv(io.BytesIO(hierarchy_upload.getvalue()))
                required = {"business_unit", "block", "unit", "section", "equipment"}
                missing = required - set(hierarchy_frame.columns)
                if missing:
                    raise ValueError("Missing columns: " + ", ".join(sorted(missing)))
                hierarchy_path.parent.mkdir(parents=True, exist_ok=True)
                hierarchy_frame.to_csv(hierarchy_path, index=False)
                db.log_action(username, role, slug, "master_hierarchy_uploaded", {"rows": len(hierarchy_frame)})
                st.success("Master hierarchy published.")
            except Exception as exc:
                st.error(f"Could not publish hierarchy: {exc}")

    with data_tab:
        st.markdown("#### Upload operational dataset")
        upload = st.file_uploader("CSV or Excel", type=["csv", "xlsx", "xlsm"], key=f"data_upload_{slug}")
        if upload is not None:
            try:
                preview = _read_upload(upload)
                preview.columns = [str(column).strip() for column in preview.columns]
                st.dataframe(preview.head(25), use_container_width=True, hide_index=True)
                columns = preview.columns.tolist()
                date_hint = config.get("data", {}).get("date_column", "date")
                date_index = columns.index(date_hint) if date_hint in columns else 0
                date_column = st.selectbox("Date / period column", columns, index=date_index)
                numeric = [column for column in columns if pd.to_numeric(preview[column], errors="coerce").notna().mean() >= .7]
                selected_kpis = st.multiselect("KPI columns", numeric, default=numeric[:6])
                if st.button("Publish dataset and KPI layout", type="primary"):
                    refinery_required = {
                        "date", "feed_ic4_ratio", "product_ic4_ratio", "ic4_improvement",
                        "reactor_a_delta_t", "reactor_b_delta_t", "reactor_delta_t",
                        "reactor_delta_p", "Makeup Hydrogen Flow_feed",
                        "Stabiliser Pressure_feed", "Butane Drier Moisture Analyzer_feed",
                        "online_reactor", "reactor_inlet_temp", "reactor_outlet_temp",
                    }
                    missing = refinery_required - set(preview.columns) if slug == "refinery" else set()
                    if missing:
                        st.error("Refinery upload rejected. Missing columns: " + ", ".join(sorted(missing)))
                        st.stop()
                    config_store.save_uploaded_data(slug, preview, units)
                    units[slug]["data"]["date_column"] = date_column
                    units[slug]["kpis"] = [
                        {"column": column, "label": column.replace("_", " ").title(), "aggregate": "mean", "unit": "", "decimals": 1}
                        for column in selected_kpis
                    ]
                    config_store.save_business_units(units)
                    db.log_action(username, role, slug, "operational_data_uploaded", {"filename": upload.name, "rows": len(preview), "columns": len(preview.columns)})
                    st.success("Dataset and KPI layout published. Reloading…")
                    st.rerun()
            except Exception as exc:
                st.error(f"Could not process the upload: {exc}")
        st.markdown("#### Current KPI configuration")
        st.dataframe(pd.DataFrame(config.get("kpis", [])), use_container_width=True, hide_index=True)

    with sop_tab:
        st.markdown("#### Add controlled knowledge file")
        with st.form(f"sop_upload_{slug}", clear_on_submit=True):
            c1, c2 = st.columns(2)
            title = c1.text_input("Title")
            category = c2.selectbox("Category", ["SOP", "Operating guidance", "Training", "Checklist", "Lesson learned", "Other"])
            c3, c4 = st.columns(2)
            unit_name = c3.text_input("Unit / area", value=config.get("hierarchy", [""])[-1])
            version = c4.text_input("Version / revision")
            file = st.file_uploader("Document", type=["pdf", "docx", "xlsx", "pptx", "txt", "md"])
            save = st.form_submit_button("Upload document", type="primary")
        if save:
            if file is None or not title.strip():
                st.error("Enter a title and choose a document.")
            else:
                path = db.save_sop(slug, username, title.strip(), category, unit_name.strip(), version.strip(), file.name, file.getvalue())
                db.log_action(username, role, slug, "sop_uploaded", {"title": title, "filename": file.name})
                st.success(f"Uploaded {path.name}.")
        records = db.sops_frame(slug)
        if not records.empty:
            st.dataframe(records.drop(columns=["file_path"], errors="ignore"), use_container_width=True, hide_index=True)

    with audit_tab:
        audit = db.audit_frame()
        if audit.empty:
            st.info("No audit records yet.")
        else:
            chosen = st.multiselect("Business unit", sorted(audit["business_unit"].unique()), default=sorted(audit["business_unit"].unique()))
            view = audit[audit["business_unit"].isin(chosen)] if chosen else audit
            st.dataframe(view, use_container_width=True, hide_index=True)
            st.download_button("Export audit log", view.to_csv(index=False).encode("utf-8"), "portal_audit_log.csv", "text/csv")

    with system_tab:
        st.markdown("#### Security and deployment")
        st.info("Default credentials are for first-run demonstration only. Set PORTAL_OPERATOR_PASSWORD and PORTAL_ADMIN_PASSWORD, or add [auth] passwords in Streamlit secrets before production use.")
        st.markdown("#### Storage status")
        st.code(json.dumps({
            "configuration": str(config_store.CONFIG_PATH),
            "database": str(db.DB_PATH),
            "uploads": str(config_store.UPLOAD_DIR),
            "business_units": len(units),
        }, indent=2))
        st.warning("Streamlit Community Cloud local storage can reset when the app restarts. For production, mount persistent storage or replace the SQLite/file adapters with SharePoint, Dataverse, SQL or an approved API.")


def render_page(page: str, slug: str, config: dict[str, Any], units: dict[str, dict[str, Any]]) -> None:
    if page == "Admin":
        render_admin(slug, config, units)
        return
    if slug == "refinery":
        from portal import refinery_pages

        refinery_routes = {
            "Home": refinery_pages.render_overview,
            "Analytics": refinery_pages.render_analytics,
            "Digital rounds": refinery_pages.render_rounds,
            "SOP & knowledge": refinery_pages.render_knowledge,
        }
        if page in refinery_routes:
            refinery_routes[page](config)
            return
    routes = {
        "Home": render_home,
        "Analytics": render_analytics,
        "Digital rounds": render_rounds,
        "SOP & knowledge": render_sops,
        "Events": render_events,
    }
    routes.get(page, render_home)(slug, config)
