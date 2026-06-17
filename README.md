# Databricks Streamlit Application Template

A commented starter template for building **Databricks-hosted Streamlit apps**.
It's designed for fast "vibe-coding": deploy the working Hello-World app first,
then wire up data and resources incrementally. Every file is annotated so you
(or an AI agent) can see exactly what each part does.

---

## What's in this repo

| File | Role | When you edit it |
| --- | --- | --- |
| `app.py` | Your Streamlit application (the entry point Databricks runs). | Constantly — this is your app. |
| `app.yaml` | **Runtime** config: the start command + environment variables. | When adding env vars or resources. |
| `manifest.yaml` | **Template** metadata + which resources to prompt for at setup. | When publishing as a reusable template. |
| `requirements.txt` | Python dependencies installed at build time. | When adding libraries. |
| `README.md` | This guide. | Whenever you want. |

### `app.yaml` vs `manifest.yaml` (the common confusion)

- **`manifest.yaml`** runs at *template/setup time*. It declares metadata and the
  resources a user is asked to connect (a SQL warehouse, a secret, etc.).
- **`app.yaml`** runs at *app start time*. It defines the launch `command` and the
  `env` variables your code reads — including `valueFrom:` references to the
  resources declared above.

---

## How a Databricks-hosted Streamlit app works

1. **You write `app.py`.** Standard Streamlit — no special imports required.
2. **Databricks builds it** by installing `requirements.txt`.
3. **Databricks starts it** with the `command:` from `app.yaml`. For Streamlit,
   the platform automatically binds to `0.0.0.0:$DATABRICKS_APP_PORT` and sets
   headless/CORS/XSRF flags, so the command stays minimal.
4. **The app runs as a service principal.** Databricks injects OAuth credentials
   as environment variables — you never put a token in code.

### Authentication (the important part)

Your app authenticates as a **service principal** using auto-injected env vars:

| Variable | Meaning |
| --- | --- |
| `DATABRICKS_HOST` | Workspace URL |
| `DATABRICKS_APP_PORT` | Port the app must listen on (Streamlit handles this) |
| `DATABRICKS_APP_NAME` | The deployed app's name |
| `DATABRICKS_WORKSPACE_ID` | Workspace ID |
| `DATABRICKS_CLIENT_ID` | Service principal client ID (OAuth) |
| `DATABRICKS_CLIENT_SECRET` | Service principal secret (OAuth) |

In `app.py`, the `databricks-sdk` `Config()` object reads these automatically:

```python
from databricks import sql
from databricks.sdk.core import Config

cfg = Config()  # discovers host + OAuth from the injected env vars
conn = sql.connect(
    server_hostname=cfg.host,
    http_path=f"/sql/1.0/warehouses/{os.getenv('DATABRICKS_WAREHOUSE_ID')}",
    credentials_provider=lambda: cfg.authenticate,
)
```

---

## Connecting data & resources (3 steps)

To let the app query a table you need a **SQL warehouse** the service principal
can use, plus access to the data. The flow is always:

**1. Declare / attach the resource.**
   - For a published template: uncomment a block under `resource_specs` in
     `manifest.yaml` (e.g. `sql_warehouse_spec` with `permission: CAN_USE`).
   - For an existing app: in the workspace, open the app → **Edit** →
     **Resources** → **Add resource** → pick the warehouse → **Can use**.

**2. Expose it as an env var in `app.yaml`** using `valueFrom` (the string must
   match the resource key):

```yaml
env:
  - name: "DATABRICKS_WAREHOUSE_ID"
    valueFrom: "sql-warehouse"
  - name: "APP_TABLE_NAME"
    value: "main.default.my_table"   # plain text is fine for non-secrets
```

`valueFrom` resolves to: `sql-warehouse` → warehouse ID, `secret` → the
decrypted secret value, `serving-endpoint` → endpoint name, `table` → full
table name.

> **Never** put a secret in a `value:` field or in code. Always use `valueFrom:`.

**3. Grant Unity Catalog access** to the app's service principal (in a SQL
   editor), then read the env vars in `app.py`:

```sql
GRANT USE CATALOG ON CATALOG main TO `<app-service-principal>`;
GRANT USE SCHEMA  ON SCHEMA  main.default TO `<app-service-principal>`;
GRANT SELECT      ON TABLE   main.default.my_table TO `<app-service-principal>`;
```

---

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

Locally there's no injected service principal, so for data queries either run
`databricks auth login` (the SDK reuses that session) or set `DATABRICKS_TOKEN`
and `DATABRICKS_HOST`. The Hello-World demo runs with no credentials at all.

## Deploy to Databricks

Using the Databricks CLI:

```bash
databricks apps deploy <app-name> --source-code-path .
```

Then open the app from the **Apps** section of your workspace. Check the app's
**Logs** tab if it crashes on startup.

---

## Common gotchas

- **App won't start:** the `command` in `app.yaml` is run without a shell — no
  `$VAR`, pipes, or `&&`. Keep it a plain list of arguments.
- **`Error during request to server` when querying:** the service principal
  can't reach the warehouse. Attach a SQL warehouse resource with **Can use**.
- **`PERMISSION_DENIED` on a table:** add the Unity Catalog `GRANT`s above.
- **Secret shows in plaintext:** you used `value:` instead of `valueFrom:`.
- **Module not found at runtime:** add the package to `requirements.txt` and
  redeploy.
