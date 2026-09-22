
import streamlit as st
import pandas as pd
import os
from itertools import combinations

# ==================================================
# NASTAVENIE APPKY
# ==================================================

st.set_page_config(
    page_title="Pallet Sorting Manager",
    layout="wide"
)

CSV_FILE = "rules.csv"
DB_TABLE = "rules"
GEOSIZES = ["BPO", "SPO", "XPO", "XL", "VB"]
GEO_OPTIONS = [
    ",".join(combo)
    for size in range(1, len(GEOSIZES) + 1)
    for combo in combinations(GEOSIZES, size)
]


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


def get_database_url():
    if "DATABASE_URL" in os.environ:
        return os.environ["DATABASE_URL"]

    try:
        return st.secrets.get("DATABASE_URL")
    except Exception:
        return None


def normalize_rules(df):
    df = df.copy()

    if "Priority" in df.columns:
        df = df.rename(columns={"Priority": "Preferencia"})
        df["Preferencia"] = 37 - pd.to_numeric(df["Rule"], errors="coerce")

    for column in ["Rule", "Location", "GeoSize", "Preferencia", "MinSKU", "MaxSKU", "Active"]:
        if column not in df.columns:
            if column in ["Location", "GeoSize"]:
                df[column] = ""
            elif column == "Active":
                df[column] = True
            else:
                df[column] = 1

    df = df[["Rule", "Location", "GeoSize", "Preferencia", "MinSKU", "MaxSKU", "Active"]]
    df = df.fillna({
        "Location": "",
        "GeoSize": "",
        "Preferencia": 1,
        "MinSKU": 1,
        "MaxSKU": 999,
        "Active": True
    })

    for column in ["Rule", "Preferencia", "MinSKU", "MaxSKU"]:
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(1).astype(int)

    df["Location"] = df["Location"].astype(str)
    df["GeoSize"] = df["GeoSize"].astype(str)
    df["Active"] = df["Active"].astype(bool)

    return df


@st.cache_resource
def get_db_engine(database_url):
    from sqlalchemy import create_engine

    return create_engine(database_url, pool_pre_ping=True)


def load_rules_from_csv():
    if not os.path.exists(CSV_FILE):
        create_default_rules().to_csv(CSV_FILE, index=False)

    rules = normalize_rules(pd.read_csv(CSV_FILE))
    rules.to_csv(CSV_FILE, index=False)
    return rules


def save_rules_to_csv(df):
    normalize_rules(df).to_csv(CSV_FILE, index=False)


def load_rules():
    database_url = get_database_url()

    if not database_url:
        return load_rules_from_csv()

    engine = get_db_engine(database_url)

    try:
        rules = pd.read_sql_table(DB_TABLE, engine)
    except ValueError:
        rules = load_rules_from_csv()
        save_rules(rules)
        return rules

    if rules.empty:
        rules = load_rules_from_csv()
        save_rules(rules)
        return rules

    return normalize_rules(rules)


def save_rules(df):
    rules = normalize_rules(df)
    database_url = get_database_url()

    if not database_url:
        save_rules_to_csv(rules)
        return

    engine = get_db_engine(database_url)
    rules.to_sql(DB_TABLE, engine, if_exists="replace", index=False)


# ==================================================
# VYTVORENIE ULOZISKA PRI PRVOM SPUSTENI
# ==================================================

rules_df = load_rules()

# ==================================================
# NACITANIE PRAVIDIEL
# ==================================================

rules_df = normalize_rules(rules_df)

# ==================================================
# DIALOGY PRE PRIDANIE A UPRAVU PRAVIDLA
# ==================================================

@st.dialog("Pridať nové pravidlo")
def add_rule_dialog():
    with st.form("new_rule_form"):
        st.subheader("Nové pravidlo")

        location = st.text_input("Location", placeholder="napr. SKLC3-PRJ-TEST-99")
        geosizes = st.multiselect(
            "GeoSize",
            GEOSIZES,
            help="Zaškrtnite Geosize, ktoré majú byť v pravidle."
        )
        min_sku = st.number_input(
            "MinSKU",
            min_value=1,
            value=1,
            step=1
        )
        max_sku = st.number_input(
            "MaxSKU",
            min_value=1,
            value=999,
            step=1
        )
        active = st.checkbox("Aktívna lokácia", value=True)

        submitted = st.form_submit_button("Pridať pravidlo")

        if submitted:
            if not location.strip():
                st.warning("Vyplň Location.")
                return

            if not geosizes:
                st.warning("Vyber aspoň jeden GeoSize.")
                return

            next_rule = int(pd.to_numeric(rules_df["Rule"], errors="coerce").max()) + 1

            new_rule = pd.DataFrame([{
                "Rule": next_rule,
                "Location": location.strip(),
                "GeoSize": ",".join(geosizes),
                "Preferencia": max(1, 37 - next_rule),
                "MinSKU": int(min_sku),
                "MaxSKU": int(max_sku),
                "Active": bool(active)
            }])

            updated_rules = pd.concat([rules_df, new_rule], ignore_index=True)
            save_rules(updated_rules)
            st.success(f"Pravidlo {next_rule} pridané.")
            st.rerun()


@st.dialog("Upraviť pravidlo")
def edit_rule_dialog():
    rule_number = st.selectbox(
        "Vyber pravidlo",
        options=rules_df["Rule"].tolist(),
        format_func=lambda value: f"{int(value)} - {rules_df.loc[rules_df['Rule'] == value, 'Location'].iloc[0]}"
    )

    rule_row = rules_df.loc[rules_df["Rule"] == int(rule_number)].iloc[0]
    location_value = "" if pd.isna(rule_row["Location"]) else str(rule_row["Location"])
    geo_value = "" if pd.isna(rule_row["GeoSize"]) else str(rule_row["GeoSize"])
    selected_default = [
        item.strip()
        for item in geo_value.split(",")
        if item.strip() and item.strip() in GEOSIZES
    ]

    with st.form(f"edit_rule_form_{rule_number}"):
        st.subheader(f"Pravidlo {int(rule_number)}")

        location = st.text_input("Location", value=location_value)
        selected_geos = st.multiselect(
            "GeoSize",
            GEOSIZES,
            default=selected_default,
            help="Zaškrtnite Geosize, ktoré majú byť v pravidle."
        )
        min_sku = st.number_input(
            "MinSKU",
            min_value=1,
            value=int(rule_row["MinSKU"]),
            step=1
        )
        max_sku = st.number_input(
            "MaxSKU",
            min_value=1,
            value=int(rule_row["MaxSKU"]),
            step=1
        )
        active = st.checkbox("Aktívna lokácia", value=bool(rule_row["Active"]))

        submitted = st.form_submit_button("Uložiť zmeny")

        if submitted:
            if not location.strip():
                st.warning("Vyplň Location.")
                return

            if not selected_geos:
                st.warning("Vyber aspoň jeden GeoSize.")
                return

            rules_df.loc[rules_df["Rule"] == int(rule_number), "Location"] = location.strip()
            rules_df.loc[rules_df["Rule"] == int(rule_number), "GeoSize"] = ",".join(selected_geos)
            rules_df.loc[rules_df["Rule"] == int(rule_number), "MinSKU"] = int(min_sku)
            rules_df.loc[rules_df["Rule"] == int(rule_number), "MaxSKU"] = int(max_sku)
            rules_df.loc[rules_df["Rule"] == int(rule_number), "Active"] = bool(active)
            save_rules(rules_df)
            st.success(f"Pravidlo {int(rule_number)} upravené.")
            st.rerun()


@st.dialog("Zmazať pravidlo")
def delete_rule_dialog():
    global rules_df
    rule_number = st.selectbox(
        "Vyber pravidlo",
        options=rules_df["Rule"].tolist(),
        format_func=lambda value: f"{int(value)} - {rules_df.loc[rules_df['Rule'] == value, 'Location'].iloc[0]}"
    )

    with st.form(f"delete_rule_confirm_{rule_number}"):
        st.warning(f"Naozaj chceš zmazať pravidlo {int(rule_number)}?")
        confirm = st.form_submit_button("Áno, zmazať")

        if confirm:
            rules_df = rules_df[rules_df["Rule"] != int(rule_number)].copy()
            rules_df = rules_df.reset_index(drop=True)
            save_rules(rules_df)
            st.success(f"Pravidlo {int(rule_number)} zmazané.")
            st.rerun()

# ==================================================
# HLAVICKA
# ==================================================

st.title("Pallet Sorting Manager")

tab1, tab2 = st.tabs(
    [
        "Správa pravidiel",
        "Test palety"
    ]
)

# ==================================================
# SPRAVA PRAVIDIEL
# ==================================================

with tab1:

    st.subheader("Správa pravidiel")

    if st.button("Upraviť"):
        edit_rule_dialog()

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

    if st.button("Pridať pravidlo"):
        add_rule_dialog()

    if st.button("Zmazať"):
        delete_rule_dialog()

    if st.button("Uložiť pravidlá"):

        save_rules(edited_df)

        st.success("Pravidlá uložené.")

        st.rerun()

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
        test_btn = st.button("Vyhodnoť")

    with col2:
        reset_btn = st.button("Reset")

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

        rules_df = load_rules()

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
                "Nenašlo sa žiadne pravidlo."
            )

        else:

            result_df = pd.DataFrame(
                matching_rules
            )

            # Správne triedenie: najprv presná zhoda množiny GeoSize,
            # potom počet zhodných GeoSize a až potom Preferencia.
            # Tým sa zabezpečí, že napr. paleta BPO,SPO pôjde na TEST-11,
            # nie na Rule 6/7 alebo na iné širšie pravidlo.
            result_df["rule_geo_set"] = result_df["GeoSize"].apply(
                lambda x: set(item.strip() for item in str(x).split(",") if item.strip())
            )

            result_df["exact_geo_match"] = result_df["rule_geo_set"].apply(
                lambda geo_set: geo_set == pallet_geo
            )
            result_df["matching_count"] = result_df["rule_geo_set"].apply(
                lambda geo_set: len(geo_set & pallet_geo)
            )

            result_df = result_df.sort_values(
                by=["exact_geo_match", "matching_count", "Preferencia", "Rule"],
                ascending=[False, False, False, True]
            ).reset_index(drop=True)

            result_df = result_df.drop(columns=["rule_geo_set", "exact_geo_match", "matching_count"])

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
