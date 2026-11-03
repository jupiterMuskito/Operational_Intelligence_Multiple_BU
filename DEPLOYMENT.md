# Streamlit deployment guide

## Streamlit Community Cloud

1. Extract this build and commit its contents to a GitHub repository.
2. In Streamlit Community Cloud, select **Create app**.
3. Choose the repository and branch.
4. Set **Main file path** to `app.py`.
5. Open **Advanced settings → Secrets** and add:

```toml
[auth]
operator_password = "replace-with-a-strong-password"
admin_password = "replace-with-a-different-strong-password"
```

6. Deploy.
7. Sign in as the administrator and upload authoritative data/configuration.
8. Confirm every Refinery page against the current production app before user acceptance.

## Important storage warning

Community Cloud has an ephemeral local filesystem. SQLite records, uploaded SOP files and in-app configuration changes can disappear after restart or redeploy. Use the packaged storage only for demonstration.

For a durable deployment, set these environment variables to mounted/persistent paths if your host supports them:

```text
PORTAL_CONFIG_PATH
PORTAL_DB_PATH
PORTAL_UPLOAD_DIR
PORTAL_SOP_DIR
```

For enterprise production, replace local storage with SharePoint/Dataverse or SQL and use organization identity.

## Data migration checklist

Replace the reconstructed CSV files with the authoritative files from the source repository. Preserve the same relative paths. For the Refinery KPI dataset, required columns are validated in Admin before publication.

After replacement, verify:

- operating-mode date boundaries and notes;
- parameter-to-tag mappings;
- Reactor A/B tag selection;
- operating-limit monitor/action thresholds;
- verification monitor/critical thresholds;
- hierarchy coverage and equipment spelling;
- schedule vs recorded-round completion logic;
- SOP document paths and approval status;
- KPI period, row counts and key values against the current live app.

## Health check

```bash
pip install -r requirements.txt
pytest -q
streamlit run app.py --server.headless true
```

Open `/_stcore/health` on the running service. It should return `ok`.
