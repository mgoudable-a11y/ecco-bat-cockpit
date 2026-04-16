import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(page_title="ECCO BAT", page_icon="🏗️", layout="wide")
st.title("🏗️ ECCO BAT — Cockpit Dirigeant")

ROOT = Path(__file__).parent
fichiers = list(ROOT.glob("*.xlsx"))

if fichiers:
    st.success(f"✅ {len(fichiers)} fichiers trouvés !")
    for f in fichiers:
        st.write(f"- {f.name}")
else:
    st.error("Aucun fichier Excel trouvé")
