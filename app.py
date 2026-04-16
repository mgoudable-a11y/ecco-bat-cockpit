import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="ECCO BAT", page_icon="🏗️", layout="wide")

ROOT = Path(__file__).parent
DATA = ROOT / "data"

st.sidebar.title("🏗️ ECCO BAT")
annee = st.sidebar.selectbox("Exercice", ["2025", "2024", "2023"])

def lire(nom):
    p = DATA / nom
    if p.exists():
        return pd.read_excel(p, header=None, dtype=str)
    return None

df = lire(f"balance_generale_{annee}.xlsx")

if df is not None:
    st.success(f"✅ Balance {annee} chargée — {len(df)} lignes")
    st.write("Aperçu :")
    st.dataframe(df.head(20))
else:
    st.error(f"Fichier balance_generale_{annee}.xlsx non trouvé")
    st.write("Fichiers disponibles :")
    for f in DATA.glob("*.xlsx"):
        st.write(f"- {f.name}")
