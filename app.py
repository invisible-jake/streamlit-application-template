"""
================================================================================
 Databricks-hosted Streamlit app — main entry point
================================================================================

This is the file Databricks Apps runs (see the `command:` in app.yaml).
Everything a Streamlit script can do works here; the only Databricks-specific
parts are (1) how the app authenticates and (2) how it reads configuration from
environment variables.

VIBE-CODING NOTES
-----------------
* Edit freely and redeploy — the structure below is just a starting point.
* The "Hello world" demo at the bottom runs out of the box with NO Databricks
  resources attached, so you can deploy first and wire up data later.
* The `get_connection()` / `run_query()` helpers show the recommended way to
  query a SQL warehouse using the app's service principal (no tokens in code).
* Anything marked `# OPTIONAL` can be deleted if you don't need it.
================================================================================
"""

import os

import pandas as pd
import streamlit as st

# ------------------------------------------------------------------------------
# 1. Page configuration — must be the first Streamlit call.
# ------------------------------------------------------------------------------
st.set_page_config(
    page_title="Databricks Streamlit Template",
    page_icon="🧱",
    layout="wide",
)

# ------------------------------------------------------------------------------
# 2. Environment variables
# ------------------------------------------------------------------------------
# Databricks AUTO-INJECTS these when the app is deployed (do not set them
# yourself). They are the foundation of service-principal auth:
#
#   DATABRICKS_HOST            -> workspace URL, e.g. https://<id>.cloud.databricks.com
#   DATABRICKS_APP_PORT        -> port the server must bind to (handled by Streamlit)
#   DATABRICKS_APP_NAME        -> the deployed app's name
#   DATABRICKS_WORKSPACE_ID    -> workspace ID
#   DATABRICKS_CLIENT_ID       -> service principal client ID  (OAuth)
#   DATABRICKS_CLIENT_SECRET   -> service principal secret     (OAuth)
#
# CUSTOM variables come from the `env:` block in app.yaml. Define resources in
# manifest.yaml, bind them with `valueFrom:` in app.yaml, then read them here.
DATABRICKS_HOST = os.getenv("DATABRICKS_HOST")
APP_NAME = os.getenv("DATABRICKS_APP_NAME", "local-dev")

# Provided by a SQL warehouse resource (app.yaml: valueFrom: sql-warehouse).
WAREHOUSE_ID = os.getenv("DATABRICKS_WAREHOUSE_ID")

# Plain-text config you set in app.yaml via `value:` (safe, non-secret).
# Format: catalog.schema.table  (e.g. "main.default.my_table")
TABLE_NAME = os.getenv("APP_TABLE_NAME", "<catalog>.<schema>.<table>")


# ------------------------------------------------------------------------------
# 3. Databricks connection helpers  (# OPTIONAL — delete if your app has no data)
# ------------------------------------------------------------------------------
# Auth model: the app runs as a SERVICE PRINCIPAL. The databricks-sdk `Config`
# object discovers credentials automatically from the injected env vars, so you
# never put a token in code. Locally, it falls back to your `databricks auth
# login` session or a DATABRICKS_TOKEN env var.
@st.cache_resource(show_spinner=False)
def get_connection():
    """Open and cache a Databricks SQL warehouse connection."""
    from databricks import sql
    from databricks.sdk.core import Config

    if not WAREHOUSE_ID:
        raise RuntimeError(
            "No SQL warehouse attached. Add a 'sql-warehouse' resource to the "
            "app and expose it via app.yaml (valueFrom: sql-warehouse)."
        )

    cfg = Config()  # reads DATABRICKS_HOST + OAuth client id/secret from env
    return sql.connect(
        server_hostname=cfg.host,
        http_path=f"/sql/1.0/warehouses/{WAREHOUSE_ID}",
        credentials_provider=lambda: cfg.authenticate,
    )


@st.cache_data(ttl=600, show_spinner="Querying Databricks...")
def run_query(query: str) -> pd.DataFrame:
    """Run a SQL query and return a DataFrame. Cached for 10 minutes."""
    with get_connection().cursor() as cursor:
        cursor.execute(query)
        rows = cursor.fetchall()
        columns = [c[0] for c in cursor.description]
    return pd.DataFrame(rows, columns=columns)


# ------------------------------------------------------------------------------
# 4. Sidebar — handy environment diagnostics while vibe-coding.
# ------------------------------------------------------------------------------
with st.sidebar:
    st.subheader("🔌 Environment")
    st.write(f"**App:** `{APP_NAME}`")
    st.write(f"**Host:** `{DATABRICKS_HOST or 'not set (running locally?)'}`")
    st.write(f"**Warehouse:** `{WAREHOUSE_ID or 'none attached'}`")

# ------------------------------------------------------------------------------
# 5. Main content.
# ------------------------------------------------------------------------------
st.title("🧱 Databricks Streamlit Template")
st.caption("Edit `app.py` to build your app. Delete the demo below when ready.")

# --- Demo A: works with zero Databricks resources -----------------------------
st.header("Hello world!")
apps = st.slider("Number of apps", max_value=60, value=10)
chart_data = pd.DataFrame({"y": [2**x for x in range(apps)]})
st.bar_chart(
    chart_data,
    height=500,
    width=min(100 + 50 * apps, 1000),
    use_container_width=False,
    x_label="Apps",
    y_label="Fun with data",
)

# --- Demo B: query a Unity Catalog table  (# OPTIONAL) ------------------------
# Uncomment after you attach a SQL warehouse resource and set APP_TABLE_NAME.
#
# st.header("Data from Databricks")
# if st.button("Load data"):
#     try:
#         df = run_query(f"SELECT * FROM {TABLE_NAME} LIMIT 1000")
#         st.dataframe(df, use_container_width=True)
#     except Exception as exc:  # noqa: BLE001
#         st.error(f"Query failed: {exc}")
