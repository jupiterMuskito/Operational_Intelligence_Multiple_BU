# Digital Operations & Knowledge Portal

A deployment-ready Streamlit application for multiple business units. The selected business unit controls the hierarchy, labels, KPI layout, round form, analytics and knowledge workspace shown after login.

## What changed

- Added a login experience with username, password and business-unit selection before entry.
- Added role-based navigation and an administrator-only page.
- Rebuilt the visual layer as a professional web application: branded login, persistent workspace navigation, hero panels, cards, KPI tiles, responsive charts and explicit data-source badges.
- Preserved the Refinery / Alkylation / Butamer calculation logic from `src/portal/data_store.py`:
  - `operating_mode` and `mode_note`;
  - `tag_for` and daily-average `dcs_value`;
  - `limit_status` and `health_summary`, including Reactor A/B tag selection;
  - `dcs_reference`, `verify_reading` and `verification_table` with monitor/critical differences;
  - `relationship_summary` correlation ranking and strength labels.
- Reimplemented the supplied Refinery pages inside the authenticated shell:
  - Butamer Unit Overview;
  - Feed → Process → Product Analytics;
  - Digital Operator Rounds & Verification;
  - SOP & Knowledge Portal;
  - Events & Investigations.
- Reused the `business_unit → block → unit → section → equipment` master hierarchy as the reusable model.
- Added configurable Cement and Fertilizer workspaces to demonstrate replication without new Python pages.
- Added admin workflows for cloning/importing business-unit configuration, replacing the master hierarchy, uploading operational data, publishing SOP files, and exporting the audit log.

## Source status

The supplied GitHub repository and live Streamlit URL were inaccessible from the build environment. The supplied `data_store.py` and pages 2–4 were used directly as the logic/source reference. Page 1 and the CSV assets were reconstructed to the schemas required by the supplied code. Reconstructed CSVs are deterministic demonstration data and are labelled as such in the UI.

Replace these files with the authoritative repository versions before operational use:

```text
config/parameter_mapping.csv
config/operating_modes.csv
config/operating_limits.csv
config/verification_limits.csv
data/processed/analysis/butamer_kpi_dataset.csv
data/processed/dcs/butamer_master_dataset.csv
data/sample/*.csv
```

No business claim should be made from the packaged reconstruction.

## Default first-run credentials

| Role | Username | Password |
|---|---|---|
| Operator | `operator` | `Operator@123` |
| Administrator | `admin` | `Admin@123` |

These defaults are only for demonstration. Override them before deployment with environment variables:

```bash
export PORTAL_OPERATOR_PASSWORD='strong-value'
export PORTAL_ADMIN_PASSWORD='different-strong-value'
```

Or add the equivalent values to Streamlit secrets using `.streamlit/secrets.example.toml` as the template.

## Run locally

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux:
source .venv/bin/activate
pip install -r requirements.txt
streamlit run app.py
```

## Add another business unit without Python code

1. Sign in as `admin`.
2. Open **Portal Administration → Business units**.
3. Clone an existing business unit.
4. Download its JSON configuration.
5. Edit hierarchy labels, navigation labels, KPI definitions, round fields and knowledge seeds.
6. Import the JSON configuration.
7. Upload the business unit's operational CSV/Excel dataset under **Data & KPIs**.
8. Upload controlled knowledge files under **SOP uploads**.
9. Sign out and select the new business unit on the login page.

The configuration contract is in `CONFIGURATION_GUIDE.md`.

## Storage and production limitations

The packaged build uses local JSON/CSV files plus SQLite. This is suitable for a proof of concept and a controlled single-instance deployment. Streamlit Community Cloud local storage can reset on instance restart and is not a system of record.

For production, keep the page/config model but replace the storage adapters with SharePoint/Dataverse, SQL or an approved service. Use Entra ID or another enterprise identity provider instead of shared default credentials.

## Test

```bash
pytest -q
```

The tests cover the preserved Refinery calculations, configuration load, login rendering and an authenticated Refinery smoke path.
