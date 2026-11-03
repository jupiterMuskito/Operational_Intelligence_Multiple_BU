# Reconstruction notes

## Accessible source

- `app.py` from the user's OneDrive.
- `data_store.py` from the user's OneDrive.
- `2_Feed_Process_Product_Analytics.py` from the user's OneDrive.
- `3_Digital_Operator_Rounds.py` from the user's OneDrive.
- `4_SOP_Knowledge_Portal.py` from the user's OneDrive.
- The user's prior Operational Intelligence Streamlit build.
- The user's prior risk-assessment application and project context.

## Inaccessible source

The supplied GitHub repository returned an access-policy error in the container and the web retriever returned 404. The supplied live Streamlit URL also returned 404 to the web retriever. The original page 1 and repository CSV files therefore could not be copied.

## Reconstructed items

- Page 1 was reconstructed around the supplied `load_kpis`, `mode_note` and `health_summary` functions.
- Configuration CSVs were rebuilt to the schemas consumed by `data_store.py`.
- The Butamer KPI and DCS datasets were rebuilt as deterministic demonstration data.
- All `data/sample/*.csv` files were rebuilt to the schemas and columns consumed by pages 3 and 4.

## Preserved logic

The delivered `src/portal/data_store.py` is the supplied file. The authenticated UI calls its functions rather than replacing the engineering calculations.

## Acceptance boundary

The reconstructed datasets demonstrate function and layout only. They are not plant records. Before acceptance, replace them with the repository CSVs and compare values/page outputs against the current live app.
