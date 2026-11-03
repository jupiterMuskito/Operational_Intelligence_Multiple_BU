# Business-unit configuration guide

Business units are stored in `config/business_units.json`. Each unit is keyed by a URL-safe slug.

## Minimum structure

```json
{
  "name": "Example BU",
  "hierarchy": ["Example BU", "Division", "Unit"],
  "features": ["Home", "Analytics", "Digital rounds", "SOP & knowledge", "Events"],
  "navigation": {
    "overview": "Unit Overview",
    "analytics": "Operations Analytics",
    "rounds": "Digital Rounds",
    "sops": "Knowledge Portal",
    "events": "Events",
    "admin": "Portal Administration"
  },
  "data": {
    "process_file": "data/uploads/example-bu_process.csv",
    "date_column": "date",
    "mode_column": "operating_mode",
    "normal_mode": "Normal",
    "source_label": "Admin-supplied data",
    "is_demo": false
  },
  "kpis": [],
  "analytics": {},
  "rounds": {"shifts": [], "units": [], "fields": []},
  "sops": {"seed": []}
}
```

## KPI definition

```json
{
  "column": "output_tpd",
  "label": "Average output",
  "aggregate": "mean",
  "unit": "t/day",
  "decimals": 0,
  "target": 5000
}
```

Supported aggregates: `mean`, `latest`, `sum`, `min`, `max`, `count`.

## Round field definition

```json
{
  "tag": "PI-101",
  "label": "Feed pressure",
  "unit": "bar(g)",
  "dcs_column": "feed_pressure_barg",
  "tolerance": 0.3,
  "default": 18.0
}
```

Generic business units use the latest row in the uploaded dataset as the DCS reference. The preserved Refinery workspace instead uses `dcs_reference` and `verify_reading` from `src/portal/data_store.py`.

## Master hierarchy

`data/sample/master_hierarchy.csv` uses:

```text
business_unit,block,unit,section,equipment
```

The Refinery digital-round workflow uses this hierarchy directly. The administrator can download and replace the hierarchy in the app.

## Import safety

The Admin page validates required top-level keys before saving imported JSON. It does not validate engineering meaning. A competent owner must verify tags, thresholds, units, equipment mappings and controlled-document status before production use.
