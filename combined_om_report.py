import os
import glob
import re
from datetime import datetime

import pandas as pd
import plotly.express as px
import streamlit as st

# ── Streamlit page config ──────────────────────────────────────────────────────
st.set_page_config(
    page_title="Combined OM City-Wise Loss Report",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ── Constants ──────────────────────────────────────────────────────────────────
FOLDER       = r"C:\Users\Mohitmo1\Documents\ACTUAL DEsgin - combo"
FILE_PATTERN = "combined_om_C_*.csv"
N_TOP        = 10  # top negative-OM SKUs per city

# ── Load latest combined file ───────────────────────────────────────────────────
files = glob.glob(os.path.join(FOLDER, FILE_PATTERN))
if not files:
    st.error(f"No files matching '{FILE_PATTERN}' in {FOLDER}")
    st.stop()

# pick the file with the most recent date in its name
rx = re.compile(r"combined_om_C_(\d{2}-\d{2}-\d{4})\.csv")
dated = []
for f in files:
    m = rx.search(os.path.basename(f))
    if m:
        dt = datetime.strptime(m.group(1), "%d-%m-%Y")
        dated.append((f, dt))
if not dated:
    st.error("No dated combined files found.")
    st.stop()

latest_file = max(dated, key=lambda x: x[1])[0]
df = pd.read_csv(latest_file)

# ── Normalize percentages and ensure OMValue ────────────────────────────────────
for c in df.columns:
    if c.strip().endswith('%'):
        df[c] = pd.to_numeric(df[c], errors="coerce") / 100

if "OMValue" not in df:
    df["OMValue"] = df["Revenue"] * df["OM%"]

# ── App title ───────────────────────────────────────────────────────────────────
st.title("🚨 Combined OM City-Wise Loss Report")

# ── One tab per city (warehouse) ────────────────────────────────────────────────
cities = sorted(df["Warehouse"].dropna().unique())
tabs   = st.tabs(cities)

for city, tab in zip(cities, tabs):
    with tab:
        city_df = df[df["Warehouse"] == city]
        losses = city_df[city_df["OMValue"] < 0]
        if losses.empty:
            st.info(f"No negative-OM SKUs in **{city}**.")
            continue

        # Top negative OM SKUs
        top = (
            losses
            .groupby("SKU Name", as_index=False)
            .agg(LostMargin=("OMValue", "sum"))
            .assign(LostMargin=lambda d: -d["LostMargin"])
            .nlargest(N_TOP, "LostMargin")
        )
        top["Label"] = top["LostMargin"].apply(lambda x: f"₹{x:,.0f}")

        st.subheader(f"Top {N_TOP} Negative-OM SKUs in {city}")
        fig = px.bar(
            top,
            x="LostMargin",
            y="SKU Name",
            orientation="h",
            text="Label",
            labels={"LostMargin": "₹ Lost Margin", "SKU Name": "SKU"}
        )
        fig.update_layout(
            yaxis={"categoryorder": "total descending"},
            margin=dict(l=200)
        )
        st.plotly_chart(fig, use_container_width=True)

        # Drill-down selection
        selection = st.multiselect(
            f"Drill down SKUs in {city}",
            options=top["SKU Name"].tolist(),
            key=f"drill_{city}"
        )
        if selection:
            detail = losses[losses["SKU Name"].isin(selection)]
            display_cols = [
                "Report Date", "Warehouse", "Customer Name", "SKU Name",
                "FG Qty Sold", "Revenue", "PM%", "Ops Cost %", "OM%", "OMValue"
            ]
            st.dataframe(
                detail[display_cols].rename(columns={"OMValue": "LostMargin"}),
                height=300
            )

# ── Sidebar info ───────────────────────────────────────────────────────────────
st.sidebar.markdown("**Data Source:**")
st.sidebar.write(os.path.basename(latest_file))
