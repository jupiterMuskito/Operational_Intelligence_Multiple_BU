from __future__ import annotations

import pandas as pd

from portal.config_store import load_business_units
from src.portal.data_store import (
    NORMAL_MODE,
    dcs_value,
    health_summary,
    limit_status,
    load_kpis,
    operating_mode,
    relationship_summary,
    tag_for,
    verify_reading,
)


def test_business_units_load():
    units = load_business_units()
    assert {"refinery", "cement", "fertilizer"}.issubset(units)
    assert units["refinery"]["hierarchy"] == ["Refinery", "Alkylation", "Butamer"]


def test_operating_mode_and_mapping():
    assert operating_mode("2026-09-12") == "Turnaround"
    assert operating_mode("2026-08-05") == NORMAL_MODE
    assert tag_for("Makeup Hydrogen Flow_feed") == "FI2520"


def test_limit_status_boundaries():
    limit = {"low_action": 5, "high_action": 15, "low_monitor": 8, "high_monitor": 12}
    assert limit_status(10, limit) == "Normal"
    assert limit_status(7, limit) == "Monitor"
    assert limit_status(4, limit) == "Action Required"
    assert limit_status(float("nan"), limit) == "No Data"


def test_health_and_dcs_lookup():
    frame = load_kpis()
    selected = frame.iloc[-1]
    assert dcs_value("FI2520", selected["date"]) is not None
    summary = health_summary(selected)
    assert not summary.empty
    assert {"Section", "Parameter", "Value", "Status", "Source"}.issubset(summary.columns)


def test_verification_thresholds():
    frame = load_kpis()
    day = frame.iloc[-1]["date"]
    reference = dcs_value("TI2504", day)
    normal = verify_reading("Reactor A", "Inlet temperature", day, reference + 0.5)
    monitor = verify_reading("Reactor A", "Inlet temperature", day, reference + 3.0)
    critical = verify_reading("Reactor A", "Inlet temperature", day, reference + 6.0)
    assert normal["status"] == "Normal"
    assert monitor["status"] == "Monitor"
    assert critical["status"] == "Critical"


def test_relationship_summary_strength_labels():
    frame = pd.DataFrame({"condition": [1, 2, 3, 4, 5], "product_ic4_ratio": [2, 4, 6, 8, 10]})
    summary = relationship_summary(frame, {"Condition": "condition"})
    assert summary.iloc[0]["Strength"] == "Strong"
    assert summary.iloc[0]["Correlation (r)"] == 1.0
