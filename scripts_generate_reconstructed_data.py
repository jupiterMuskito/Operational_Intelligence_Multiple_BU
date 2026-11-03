"""Generate deterministic reconstruction data when the original repository CSVs are unavailable.

These records are demonstrative. They preserve schemas and exercise the original calculations;
they must not be represented as real plant observations.
"""
from __future__ import annotations

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
rng = np.random.default_rng(42)
(ROOT / "data/processed/analysis").mkdir(parents=True, exist_ok=True)
(ROOT / "data/processed/dcs").mkdir(parents=True, exist_ok=True)
(ROOT / "data/sample").mkdir(parents=True, exist_ok=True)
(ROOT / "config").mkdir(parents=True, exist_ok=True)

dates = pd.date_range("2026-08-01", periods=76, freq="D")
feed = 39 + 3.5 * np.sin(np.arange(len(dates)) / 7) + rng.normal(0, 1.0, len(dates))
hydrogen = 1250 + rng.normal(0, 40, len(dates))
pressure = 7.5 + rng.normal(0, .18, len(dates))
moisture = np.clip(0.55 + rng.normal(0, .12, len(dates)), .15, 1.0)
reactor_dt = 9.8 + .012 * (hydrogen - 1250) - 1.1 * (moisture - .55) + rng.normal(0, .7, len(dates))
product = 84 + .18 * (feed - 39) + .48 * (reactor_dt - 9.8) - 1.6 * (moisture - .55) + rng.normal(0, .7, len(dates))
online = np.where(np.arange(len(dates)) % 20 < 10, "A", "B")
inlet = 145 + rng.normal(0, 1.2, len(dates))
outlet = inlet + reactor_dt
kpis = pd.DataFrame({
    "date": dates.date,
    "feed_ic4_ratio": np.round(feed, 2),
    "product_ic4_ratio": np.round(product, 2),
    "ic4_improvement": np.round(product - feed, 2),
    "reactor_a_delta_t": np.round(reactor_dt + rng.normal(0, .25, len(dates)), 2),
    "reactor_b_delta_t": np.round(reactor_dt + rng.normal(0, .25, len(dates)), 2),
    "reactor_delta_t": np.round(reactor_dt, 2),
    "reactor_delta_p": np.round(0.62 + rng.normal(0, .07, len(dates)), 3),
    "Makeup Hydrogen Flow_feed": np.round(hydrogen, 1),
    "Stabiliser Pressure_feed": np.round(pressure, 2),
    "Butane Drier Moisture Analyzer_feed": np.round(moisture, 3),
    "online_reactor": online,
    "reactor_inlet_temp": np.round(inlet, 2),
    "reactor_outlet_temp": np.round(outlet, 2),
})
kpis.to_csv(ROOT / "data/processed/analysis/butamer_kpi_dataset.csv", index=False)

modes = pd.DataFrame([
    {"start_date": "2026-09-10", "end_date": "2026-09-15", "mode": "Turnaround", "notes": "Reconstructed non-normal operating period", "source": "demonstration configuration"},
    {"start_date": "2026-10-03", "end_date": "2026-10-04", "mode": "Reduced Throughput", "notes": "Reconstructed low-rate period", "source": "demonstration configuration"},
])
modes.to_csv(ROOT / "config/operating_modes.csv", index=False)

pd.DataFrame([
    {"display_name": "Makeup Hydrogen Flow", "tag": "FI2520"},
    {"display_name": "Stabiliser Pressure", "tag": "PI2601"},
    {"display_name": "Butane Drier Moisture Analyzer", "tag": "AI2401"},
    {"display_name": "reactor_delta_p", "tag": "PDI2501"},
]).to_csv(ROOT / "config/parameter_mapping.csv", index=False)

limits = [
    {"section": "Feed", "key": "feed_ic4_ratio", "label": "Feed iC4 ratio", "unit": "%", "data_source": "kpi", "low_action": 30, "high_action": 55, "low_monitor": 34, "high_monitor": 50},
    {"section": "Product", "key": "product_ic4_ratio", "label": "Product iC4 ratio", "unit": "%", "data_source": "kpi", "low_action": 78, "high_action": 95, "low_monitor": 81, "high_monitor": 90},
    {"section": "Reactor", "key": "reactor_inlet_temp", "label": "Online reactor inlet temperature", "unit": "°C", "data_source": "kpi", "low_action": 138, "high_action": 154, "low_monitor": 141, "high_monitor": 151},
    {"section": "Reactor", "key": "reactor_outlet_temp", "label": "Online reactor outlet temperature", "unit": "°C", "data_source": "kpi", "low_action": 147, "high_action": 166, "low_monitor": 150, "high_monitor": 163},
    {"section": "Reactor", "key": "reactor_delta_p", "label": "Reactor differential pressure", "unit": "bar", "data_source": "kpi", "low_action": 0.35, "high_action": 1.0, "low_monitor": 0.45, "high_monitor": 0.85},
    {"section": "Hydrogen", "key": "FI2520", "label": "Make-up hydrogen flow", "unit": "Nm³/h", "data_source": "dcs", "low_action": 1050, "high_action": 1450, "low_monitor": 1120, "high_monitor": 1380},
    {"section": "Treating", "key": "caustic_strength", "label": "Caustic strength", "unit": "%", "data_source": "lab", "low_action": 7, "high_action": 18, "low_monitor": 9, "high_monitor": 16},
]
pd.DataFrame(limits).to_csv(ROOT / "config/operating_limits.csv", index=False)

hierarchy = pd.DataFrame([
    ["Refinery", "Alkylation", "Butamer", "Feed", "Feed surge drum"],
    ["Refinery", "Alkylation", "Butamer", "Reaction", "Reactor A"],
    ["Refinery", "Alkylation", "Butamer", "Reaction", "Reactor B"],
    ["Refinery", "Alkylation", "Butamer", "Fractionation", "Stabilizer"],
    ["Refinery", "Alkylation", "Alkylation", "Reaction", "Alkylation reactor"],
    ["Cement", "Integrated Plant", "Pyroprocessing", "Kiln", "Rotary kiln"],
    ["Fertilizer", "Ammonia Plant", "Synthesis Loop", "Synthesis", "Ammonia converter"],
], columns=["business_unit", "block", "unit", "section", "equipment"])
hierarchy.to_csv(ROOT / "data/sample/master_hierarchy.csv", index=False)

# DCS values preserve the daily-average lookup in dcs_value.
dcs_rows = []
for i, row in kpis.iterrows():
    tag_values = {
        "TI2504": row["reactor_inlet_temp"], "TI2509": row["reactor_outlet_temp"],
        "TI2510": row["reactor_inlet_temp"] + .3, "TI2515": row["reactor_outlet_temp"] + .2,
        "FI2520": row["Makeup Hydrogen Flow_feed"], "PI2601": row["Stabiliser Pressure_feed"],
        "AI2401": row["Butane Drier Moisture Analyzer_feed"], "PDI2501": row["reactor_delta_p"],
    }
    for hour in (0, 8, 16):
        for tag, value in tag_values.items():
            dcs_rows.append({"timestamp": f"{row['date']} {hour:02d}:00:00", "instrument_tag": tag, "value": round(float(value + rng.normal(0, .02 if tag.startswith(('TI','PI','AI','PDI')) else 2)), 3)})
pd.DataFrame(dcs_rows).to_csv(ROOT / "data/processed/dcs/butamer_master_dataset.csv", index=False)

tag_reference = pd.DataFrame([
    ["Feed surge drum", "Pressure", "PI-2101", "Feed surge drum local pressure", "PI2601", "Mapped", "bar(g)"],
    ["Reactor A", "Inlet temperature", "TI-2201", "Reactor A local inlet temperature", "TI2504", "Mapped", "°C"],
    ["Reactor A", "Outlet temperature", "TI-2202", "Reactor A local outlet temperature", "TI2509", "Mapped", "°C"],
    ["Reactor B", "Inlet temperature", "TI-2211", "Reactor B local inlet temperature", "TI2510", "Mapped", "°C"],
    ["Reactor B", "Outlet temperature", "TI-2212", "Reactor B local outlet temperature", "TI2515", "Mapped", "°C"],
    ["Stabilizer", "Pressure", "PI-2301", "Stabilizer local pressure", "PI2601", "Mapped", "bar(g)"],
], columns=["equipment", "parameter", "tag", "description", "dcs_tag", "tag_status", "unit_of_measure"])
tag_reference.to_csv(ROOT / "data/sample/tag_reference.csv", index=False)

pd.DataFrame([
    ["Feed surge drum", "Pressure", .3, .7],
    ["Reactor A", "Inlet temperature", 2, 5],
    ["Reactor A", "Outlet temperature", 2, 5],
    ["Reactor B", "Inlet temperature", 2, 5],
    ["Reactor B", "Outlet temperature", 2, 5],
    ["Stabilizer", "Pressure", .2, .5],
], columns=["equipment", "parameter", "monitor_difference", "critical_difference"]).to_csv(ROOT / "config/verification_limits.csv", index=False)

round_dates = [dates[-3].date(), dates[-2].date(), dates[-1].date()]
schedule_rows, round_rows = [], []
for day in round_dates:
    for equipment, parameter, criticality in [
        ("Feed surge drum", "Pressure", "High"), ("Reactor A", "Inlet temperature", "High"),
        ("Reactor A", "Outlet temperature", "High"), ("Stabilizer", "Pressure", "Medium")]:
        schedule_rows.append({"date": day, "business_unit": "Refinery", "block": "Alkylation", "unit": "Butamer", "equipment": equipment, "parameter": parameter, "expected_entries": 1, "criticality": criticality})
    source = kpis[kpis["date"].astype(str) == str(day)].iloc[0]
    for equipment, parameter, value, uom in [
        ("Feed surge drum", "Pressure", source["Stabiliser Pressure_feed"] + .05, "bar(g)"),
        ("Reactor A", "Inlet temperature", source["reactor_inlet_temp"] + .6, "°C"),
        ("Reactor A", "Outlet temperature", source["reactor_outlet_temp"] + 2.4, "°C"),
    ]:
        round_rows.append({"date": day, "business_unit": "Refinery", "block": "Alkylation", "unit": "Butamer", "section": "Reaction" if "Reactor" in equipment else "Feed", "equipment": equipment, "parameter": parameter, "field_value": round(float(value), 2), "unit_of_measure": uom, "status": "Normal", "remarks": "Reconstructed demonstration entry", "recorded_by": "Demo Operator", "recorded_at": f"{day} 08:00"})
pd.DataFrame(schedule_rows).to_csv(ROOT / "data/sample/measurement_schedule.csv", index=False)
pd.DataFrame(round_rows).to_csv(ROOT / "data/sample/operator_rounds.csv", index=False)

checklist_rows = []
for equipment in tag_reference["equipment"].unique():
    for item in ["No visible leakage", "Local indication legible", "Area housekeeping satisfactory"]:
        checklist_rows.append({"equipment": equipment, "check_item": item})
pd.DataFrame(checklist_rows).to_csv(ROOT / "data/sample/equipment_checklists.csv", index=False)
pd.DataFrame(columns=["date", "equipment", "check_item", "checked", "recorded_by", "recorded_at"]).to_csv(ROOT / "data/sample/checklist_records.csv", index=False)

sim_rows = []
for day in round_dates:
    sim_rows.append({"date": day, "equipment": "Feed surge drum", "parameter": "Level", "dcs_value": 55.0})
pd.DataFrame(sim_rows).to_csv(ROOT / "data/sample/dcs_simulated_values.csv", index=False)

lab_rows, drager_rows = [], []
for day in round_dates:
    lab_rows.append({"date": day, "equipment": "Stabilizer", "sample_point": "Caustic system", "parameter": "Caustic Strength", "value": 12.3, "unit": "%"})
    for location, value in [("Reactor area", 1.0), ("Stabilizer area", 0.4)]:
        drager_rows.append({"date": day, "equipment": "Reactor A", "test_location": location, "hcl_ppm": value})
pd.DataFrame(lab_rows).to_csv(ROOT / "data/sample/laboratory_results.csv", index=False)
pd.DataFrame(drager_rows).to_csv(ROOT / "data/sample/drager_tests.csv", index=False)

investigations = pd.DataFrame([
    {"date": round_dates[-1], "equipment": "Reactor A", "area": "Reaction", "observation": "Field and DCS outlet temperatures require review", "priority": "Medium", "status": "Open", "possible_cause": "Local indicator bias or daily-average timing difference", "recommended_action": "Repeat simultaneous field/DCS check and raise instrument work request if outside limits", "related_sop": "SOP-BUT-002", "related_issue": "Field and DCS temperature mismatch"},
])
investigations.to_csv(ROOT / "data/sample/investigation_history.csv", index=False)

pd.DataFrame([
    {"section": "Feed", "equipment": "Feed surge drum", "tag": "PI-2101", "purpose": "Feed buffer and pressure indication", "key_checks": "Pressure, level, leakage"},
    {"section": "Reaction", "equipment": "Reactor A", "tag": "TI2504/TI2509", "purpose": "Isomerization reaction", "key_checks": "Temperature profile, differential pressure, leakage"},
    {"section": "Fractionation", "equipment": "Stabilizer", "tag": "PI2601", "purpose": "Product stabilization", "key_checks": "Pressure, temperature, reboiler condition"},
]).to_csv(ROOT / "data/sample/equipment_reference.csv", index=False)

pd.DataFrame([
    {"sop_id": "SOP-BUT-001", "title": "Butamer unit startup – sample metadata", "category": "Operations", "status": "Illustrative", "document_path": ""},
    {"sop_id": "SOP-BUT-002", "title": "Reactor temperature verification – sample metadata", "category": "Instrumentation", "status": "Illustrative", "document_path": ""},
    {"sop_id": "SOP-BUT-003", "title": "Feed and product sampling – sample metadata", "category": "Laboratory", "status": "Illustrative", "document_path": ""},
]).to_csv(ROOT / "data/sample/sop_library.csv", index=False)

pd.DataFrame([
    {"issue": "Field and DCS temperature mismatch", "symptoms": "Local and DCS values differ beyond the configured threshold", "possible_causes": "Indicator bias; transmitter drift; timing mismatch; impulse or sensing issue", "recommended_actions": "Repeat simultaneous check; validate calibration; inspect sensing element; raise work request"},
    {"issue": "Low product iC4 ratio", "symptoms": "Product quality below expected range", "possible_causes": "Feed quality change; reactor temperature; hydrogen availability; analyzer or lab issue", "recommended_actions": "Confirm sample; review feed, reactor ΔT, hydrogen and operating mode before adjustment"},
]).to_csv(ROOT / "data/sample/troubleshooting_guide.csv", index=False)

pd.DataFrame([
    {"area": "Reaction", "title": "Verify timestamps before comparing field and DCS readings", "observation": "Daily averages can differ from a point-in-time local reading", "resolution": "Use simultaneous readings for confirmation", "recommendation": "Record comparison time and source in the round"},
    {"area": "Quality", "title": "Separate non-normal periods from performance baselines", "observation": "Turnaround and reduced-rate data distort averages", "resolution": "Apply operating-mode labels", "recommendation": "Use Normal Operation for baseline comparisons"},
]).to_csv(ROOT / "data/sample/lessons_learned.csv", index=False)

print("Reconstructed schemas and demonstration datasets created.")
