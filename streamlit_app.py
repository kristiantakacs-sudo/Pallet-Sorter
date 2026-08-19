
import streamlit as st
import pandas as pd
import os
from itertools import combinations

# ==================================================
# NASTAVENIE APPKY
# ==================================================

st.set_page_config(
    page_title="Pallet Sorting Manager",
    page_icon="📦",
    layout="wide"
)

CSV_FILE = "rules.csv"
GEOSIZES = ["BPO", "SPO", "XPO", "XL", "VB"]


def keep_sscc_digits():
    st.session_state.sscc_input = "".join(
        character
        for character in st.session_state.sscc_input
        if character in "0123456789"
    )


def create_default_rules():
    rows = []
    rule_number = 1

    for geo_size in GEOSIZES:
        rows.append([
            rule_number,
            f"SKLC3-PRJ-TEST-{rule_number:02d}",
            geo_size,
            36 - rule_number + 1,
            1,
            1,
            True
        ])
        rule_number += 1

    for geo_size in GEOSIZES:
        rows.append([
            rule_number,
            f"SKLC3-PRJ-TEST-{rule_number:02d}",
            geo_size,
            36 - rule_number + 1,
            2,
            999,
            True
        ])
        rule_number += 1

    for combination_size in range(2, len(GEOSIZES) + 1):
        for geo_combination in combinations(GEOSIZES, combination_size):
            rows.append([
                rule_number,
                f"SKLC3-PRJ-TEST-{rule_number:02d}",
                ",".join(geo_combination),
                36 - rule_number + 1,
                2,
                999,
                True
            ])
            rule_number += 1

    return pd.DataFrame(rows, columns=[
        "Rule",
        "Location",
        "GeoSize",
        "Preferencia",
        "MinSKU",
        "MaxSKU",
        "Active"
    ])

# ==================================================
# VYTVORENIE CSV PRI PRVOM SPUSTENÍ
# ==================================================

if not os.path.exists(CSV_FILE):
    create_default_rules().to_csv(CSV_FILE, index=False)

# ==================================================
# NAČÍTANIE PRAVIDIEL
# ==================================================

rules_df = pd.read_csv(CSV_FILE)

if "Priority" in rules_df.columns:
    rules_df = rules_df.rename(columns={"Priority": "Preferencia"})
    rules_df["Preferencia"] = (
        37 - pd.to_numeric(rules_df["Rule"], errors="coerce")
    )
    rules_df.to_csv(CSV_FILE, index=False)

# ==================================================
# HLAVIČKA
# ==================================================

st.title("📦 Pallet Sorting Manager")

tab1, tab2 = st.tabs(
    [
        "⚙️ Správa pravidiel",
        "🧪 Test palety"
    ]
)

# ==================================================
# SPRÁVA PRAVIDIEL
# ==================================================

with tab1:

    st.subheader("Správa pravidiel")

    st.info(
        "Pridávaj, upravuj alebo maž pravidlá. Zmeny sa použijú okamžite pri testovaní."
    )

    if st.button("➕ Pridať nové pravidlo"):
        next_rule = int(pd.to_numeric(rules_df["Rule"]).max()) + 1
        new_rule = pd.DataFrame([{
            "Rule": next_rule,
            "Location": "",
            "GeoSize": "",
            "Preferencia": 1,
            "MinSKU": 1,
            "MaxSKU": 999,
            "Active": True
        }])
        pd.concat([rules_df, new_rule], ignore_index=True).to_csv(
            CSV_FILE,
            index=False
        )
        st.rerun()

    # Reset index so Streamlit editor won't show the technical dataframe index column
    rules_df = rules_df.reset_index(drop=True)

    edited_df = st.data_editor(
        rules_df,
        use_container_width=True,
        num_rows="fixed",
        hide_index=True,
        column_order=[
            "Active",
            "Rule",
            "Location",
            "GeoSize",
            "Preferencia",
            "MinSKU",
            "MaxSKU"
        ],
        column_config={
            "Active": st.column_config.CheckboxColumn(
                "Aktívna lokácia"
            )
        }
    )

    col1, col2 = st.columns(2)

    with col1:

        if st.button("💾 Uložiť pravidlá"):

            edited_df.to_csv(
                CSV_FILE,
                index=False
            )

            st.success("Pravidlá uložené.")

            st.rerun()

    with col2:

        st.download_button(
            "📥 Export CSV",
            edited_df.to_csv(index=False),
            file_name="rules.csv",
            mime="text/csv"
        )

# ==================================================
# TEST PALIET
# ==================================================

with tab2:

    st.subheader("Test smerovania palety")

    sscc = st.text_input(
        "SSCC (voliteľné, presne 18 číslic)",
        max_chars=100,
        key="sscc_input",
        on_change=keep_sscc_digits
    )

    sku_count = st.number_input(
        "Počet SKU",
        min_value=1,
        value=1
    )

    selected_geo = st.multiselect(
        "GeoSize na palete",
        [
            *GEOSIZES
        ]
    )

    col1, col2 = st.columns(2)

    with col1:
        test_btn = st.button("✅ Vyhodnoť")

    with col2:
        reset_btn = st.button("🔄 Reset")

    if reset_btn:
        st.rerun()

    if test_btn:

        if sscc and len(sscc) > 18:
            st.error("SSCC kód je príliš dlhý. Môže mať najviac 18 číslic.")
            st.stop()

        if sscc and len(sscc) < 18:
            st.error("SSCC musí obsahovať presne 18 číslic.")
            st.stop()

        if len(selected_geo) == 0:
            st.error("Vyber aspoň jeden GeoSize.")
            st.stop()

        rules_df = pd.read_csv(CSV_FILE)

        pallet_geo = set(selected_geo)

        matching_rules = []

        for _, row in rules_df.iterrows():

            if not row["Active"]:
                continue

            rule_geo = set(
                item.strip()
                for item in str(row["GeoSize"]).split(",")
            )

            geo_match = bool(rule_geo & pallet_geo)

            sku_match = (
                row["MinSKU"] <= sku_count <= row["MaxSKU"]
            )

            if geo_match and sku_match:
                matching_rule = row.copy()
                matching_rules.append(matching_rule)

        st.divider()

        pallet_type = (
            "MONO"
            if sku_count == 1
            else "MIX"
        )

        st.write(f"### Typ palety: {pallet_type}")

        st.write(f"Počet SKU: {sku_count}")

        st.write(
            f"GeoSize palety: {', '.join(sorted(pallet_geo))}"
        )

        if len(matching_rules) == 0:

            st.error(
                "❌ Nenašlo sa žiadne pravidlo."
            )

        else:

            result_df = pd.DataFrame(
                matching_rules
            )

            result_df = result_df.sort_values(
                by=["Preferencia", "Rule"],
                ascending=[False, True]
            ).reset_index(drop=True)

            result_df.insert(0, "Poradie", range(1, len(result_df) + 1))

            winner = result_df.iloc[0]

            st.success(
                f"Odporúčaná lokácia: {winner['Location']}"
            )

            st.write(
                f"Použité pravidlo: {int(winner['Rule'])}"
            )

            st.write(
                f"Preferencia: {winner['Preferencia']} (vyššie číslo = vyššia kompatibilita)"
            )

            st.subheader(
                "Lokácie podľa preferencie (najvyššia kompatibilita prvá)"
            )

            display_df = result_df.rename(
                columns={"Rule": "Číslo pravidla"}
            ).drop(columns=["Active"])

            st.dataframe(
                display_df,
                hide_index=True,
                use_container_width=True
            )