import streamlit as st
from pathlib import Path

st.set_page_config(page_title="ECCO BAT", page_icon="🏗️", layout="wide")
st.title("🏗️ ECCO BAT — Cockpit Dirigeant")

DATA = Path(__file__).parent / "data"
fichiers = list(DATA.glob("*.xlsx")) if DATA.exists() else []

if fichiers:
    st.success(f"✅ {len(fichiers)} fichiers trouvés dans data/")
    for f in fichiers:
        st.write(f"- {f.name}")
else:
    st.error("Aucun fichier trouvé dans data/")
    st.write(f"Chemin cherché : {DATA}")
    st.write(f"Dossier existe : {DATA.exists()}")
    parent = Path(__file__).parent
    st.write("Fichiers à la racine :")
    for f in parent.glob("*.xlsx"):
        st.write(f"- {f.name}")
