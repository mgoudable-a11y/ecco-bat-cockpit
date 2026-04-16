"""
ECCO BAT — Cockpit Dirigeant v2
Les données sont chargées automatiquement depuis le dossier data/
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from data_engine import (
    EXERCICES, lire_balance, lire_analytique, lire_balance_agee,
    lire_fournisseurs, lire_journal_ventes, calculer_kpi,
    comparer_fournisseurs, annualiser
)

st.set_page_config(page_title="ECCO BAT — Cockpit", page_icon="🏗️",
                   layout="wide", initial_sidebar_state="expanded")

st.markdown("""
<style>
.main{background:#f8f9fa}
.section-hdr{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;
    color:#6c757d;margin:20px 0 10px;padding-bottom:5px;border-bottom:1px solid #e9ecef}
.alert-r{background:#fff5f5;border-left:4px solid #D85A30;border-radius:6px;padding:10px 14px;margin-bottom:6px;font-size:13px;color:#c53030}
.alert-a{background:#fffbeb;border-left:4px solid #BA7517;border-radius:6px;padding:10px 14px;margin-bottom:6px;font-size:13px;color:#b7791f}
.alert-g{background:#f0fff4;border-left:4px solid #1D9E75;border-radius:6px;padding:10px 14px;margin-bottom:6px;font-size:13px;color:#276749}
.alert-b{background:#e6f1fb;border-left:4px solid #378ADD;border-radius:6px;padding:10px 14px;margin-bottom:6px;font-size:13px;color:#185FA5}
.delta-pos{color:#1D9E75;font-size:12px;font-weight:500}
.delta-neg{color:#D85A30;font-size:12px;font-weight:500}
</style>
""", unsafe_allow_html=True)

C = {"bleu":"#378ADD","vert":"#1D9E75","orange":"#BA7517",
     "rouge":"#D85A30","gris":"#888780","violet":"#7F77DD"}

DATA = Path(__file__).parent/"data"

# ─── Chargement automatique depuis data/ ──────────────────
@st.cache_data
def charger_tout():
    """Charge tous les fichiers depuis data/ automatiquement."""
    donnees = {}
    mapping = {
        "2025": {
            "balance":    "balance_generale_2025.xlsx",
            "analytique": "balance_analytique_2025.xlsx",
            "agee":       "balance_agee_clients_2025.xlsx",
            "clients":    "grand_livre_clients_2025.xlsx",
            "fourn":      "grand_livre_fournisseurs_2025.xlsx",
            "journal":    "journal_ventes_2025.xlsx",
        },
        "2024": {
            "balance":    "balance_generale_2024.xlsx",
            "analytique": "balance_analytique_2024.xlsx",
            "agee":       "balance_agee_clients_2024.xlsx",
            "clients":    "grand_livre_clients_2024.xlsx",
            "fourn":      "grand_livre_fournisseurs_2024.xlsx",
        },
        "2023": {
            "balance":    "balance_generale_2023.xlsx",
            "analytique": "balance_analytique_2023.xlsx",
            "agee":       "balance_agee_clients_2023.xlsx",
            "clients":    "grand_livre_clients_2023.xlsx",
            "fourn":      "grand_livre_fournisseurs_2023.xlsx",
        },
    }
    for annee, fichiers in mapping.items():
        donnees[annee] = {}
        for type_f, nom_f in fichiers.items():
            path = DATA / nom_f
            if not path.exists():
                continue
            try:
                if type_f == "balance":
                    c = lire_balance(str(path))
                    donnees[annee]["comptes"] = c
                    donnees[annee]["kpi"] = calculer_kpi(c, annee)
                elif type_f == "analytique":
                    donnees[annee]["analytique"] = lire_analytique(str(path))
                elif type_f == "agee":
                    donnees[annee]["agee"] = lire_balance_agee(str(path))
                elif type_f == "fourn":
                    donnees[annee]["fourn"] = lire_fournisseurs(str(path))
                elif type_f == "journal":
                    donnees[annee]["journal"] = lire_journal_ventes(str(path))
            except Exception as e:
                st.warning(f"Erreur lecture {nom_f} : {e}")
    return donnees

donnees = charger_tout()

def fmt(v, k=True):
    if k: return f"{v/1000:,.1f} k€"
    return f"{v:,.0f} €"

def delta_html(v_n, v_n1, inverse=False):
    if not v_n1 or v_n1 == 0: return ""
    pct = (v_n - v_n1) / abs(v_n1) * 100
    bon = pct > 0 if not inverse else pct < 0
    cls = "delta-pos" if bon else "delta-neg"
    arr = "▲" if pct > 0 else "▼"
    return f'<span class="{cls}">{arr} {abs(pct):.1f}% vs N-1</span>'

def jauge(valeur, min_v, max_v, titre, unite="%", couleur=None):
    if couleur is None:
        pct = (valeur - min_v) / max(max_v - min_v, 1)
        couleur = C["vert"] if pct > 0.6 else (C["orange"] if pct > 0.3 else C["rouge"])
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(valeur, 1),
        number={"suffix": unite, "font": {"size": 18}},
        title={"text": titre, "font": {"size": 11}},
        gauge={"axis": {"range": [min_v, max_v]},
               "bar": {"color": couleur, "thickness": 0.25},
               "bgcolor": "white", "borderwidth": 0,
               "steps": [
                   {"range": [min_v, min_v+(max_v-min_v)*.4], "color": "#ffecec"},
                   {"range": [min_v+(max_v-min_v)*.4, min_v+(max_v-min_v)*.7], "color": "#fff8e6"},
                   {"range": [min_v+(max_v-min_v)*.7, max_v], "color": "#edf7f0"},
               ]}
    ))
    fig.update_layout(height=190, margin=dict(t=30,b=0,l=10,r=10),
                      paper_bgcolor="rgba(0,0,0,0)")
    return fig

def sante(kpi):
    s = 0
    if kpi.get("taux_marge",0) > 45: s += 2
    if kpi.get("taux_rent",0) > 5: s += 2
    if kpi.get("tresorerie",0) > 0: s += 2
    if kpi.get("bfr_jours",99) < 60: s += 1
    if kpi.get("dso",99) < 45: s += 1
    if s >= 7: return "😄","Excellente santé financière","#f0fff4","#38a169"
    if s >= 5: return "😊","Bonne santé — points à surveiller","#f0fff4","#38a169"
    if s >= 3: return "😐","Vigilance requise","#fffbeb","#d69e2e"
    return "😟","Points critiques à traiter","#fff5f5","#e53e3e"

# ══════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏗️ ECCO BAT")
    st.markdown("---")

    annees_dispo = [a for a in ["2025","2024","2023"] if donnees.get(a,{}).get("kpi")]
    if not annees_dispo:
        st.error("Aucun fichier trouvé dans data/")
        st.stop()

    annee_active = st.selectbox("Exercice principal", annees_dispo,
                                 format_func=lambda x: EXERCICES[x]["label"])
    annees_comp = [a for a in annees_dispo if a != annee_active]
    annee_comp = st.selectbox("Comparer avec",
                               ["N-1 automatique"] + annees_comp,
                               format_func=lambda x: EXERCICES.get(x,{}).get("label",x) if x != "N-1 automatique" else "N-1 automatique")
    if annee_comp == "N-1 automatique":
        annee_comp = str(int(annee_active) - 1)

    st.markdown("---")
    st.markdown("### 🎯 Objectifs")
    obj_ca    = st.number_input("CA cible (k€)",    value=5000, step=100)
    obj_marge = st.number_input("Marge cible (k€)", value=2800, step=100)
    obj_treso = st.number_input("Tréso mini (k€)",  value=800,  step=50)
    obj_bfr   = st.number_input("BFR max (k€)",     value=400,  step=50)

    st.markdown("---")
    seuil_fourn = st.slider("Seuil alerte fournisseurs", 1, 30, 5, format="%d%%")

    st.markdown("---")
    st.markdown("### 📁 Ajouter un fichier")
    annee_upload = st.selectbox("Exercice", ["2025","2024","2023","2026"])
    type_upload  = st.selectbox("Type", ["balance","analytique","agee","fourn","clients","journal"])
    f_upload = st.file_uploader("Fichier Excel", type=["xlsx","xls"])
    if f_upload and st.button("💾 Sauvegarder"):
        nom = f"{'balance_generale' if type_upload=='balance' else 'balance_analytique' if type_upload=='analytique' else 'balance_agee_clients' if type_upload=='agee' else 'grand_livre_fournisseurs' if type_upload=='fourn' else 'grand_livre_clients' if type_upload=='clients' else 'journal_ventes'}_{annee_upload}.xlsx"
        (DATA / nom).write_bytes(f_upload.read())
        st.success(f"✅ Sauvegardé : {nom}")
        st.cache_data.clear()
        st.rerun()

    st.markdown("---")
    if st.button("🔄 Recharger les données"):
        st.cache_data.clear()
        st.rerun()

# ══════════════════════════════════════════════
# DONNÉES ACTIVES
# ══════════════════════════════════════════════
d     = donnees.get(annee_active, {})
d_c   = donnees.get(annee_comp, {})
kpi   = d.get("kpi", {})
kpi_c = d_c.get("kpi", {})

if not kpi:
    st.error(f"Impossible de charger les données pour {annee_active}. Vérifiez le dossier data/")
    st.stop()

mois_ex = EXERCICES.get(annee_active, {}).get("mois", 12)
periode = EXERCICES.get(annee_active, {}).get("label", annee_active)

# ══════════════════════════════════════════════
# EN-TÊTE
# ══════════════════════════════════════════════
col_t, col_p = st.columns([4, 2])
with col_t:
    st.markdown("## 🏗️ ECCO BAT — Cockpit Dirigeant")
with col_p:
    st.markdown(f"<br><span style='color:#6c757d;font-size:13px'>{periode}</span>", unsafe_allow_html=True)

# Bannière santé
emoji, texte, bg, border = sante(kpi)
ann_note = f" · Données annualisées ×12/{mois_ex}" if mois_ex != 12 else ""
st.markdown(f"""
<div style="background:{bg};border-left:5px solid {border};border-radius:10px;
    padding:14px 20px;margin-bottom:20px;display:flex;align-items:center;gap:14px">
    <span style="font-size:36px">{emoji}</span>
    <div>
        <b style="font-size:16px">{texte}</b><br>
        <span style="font-size:12px;color:#555">
            Marge {kpi['taux_marge']:.1f}% · Rentabilité {kpi['taux_rent']:.1f}% ·
            Tréso {fmt(kpi['tresorerie'])} · BFR {kpi['bfr_jours']:.0f}j{ann_note}
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════
# 5 ONGLETS
# ══════════════════════════════════════════════
tabs = st.tabs(["🏠 Cockpit","📈 CA & Clients","🔬 Analytique","🔔 Fournisseurs","💰 BFR & Tréso"])

# ─── ONGLET 1 : COCKPIT ───────────────────────
with tabs[0]:
    st.markdown('<div class="section-hdr">Jauges de santé</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.plotly_chart(jauge(kpi["taux_marge"],0,100,"Taux de marge brute"), use_container_width=True)
    with c2: st.plotly_chart(jauge(kpi["taux_rent"],0,30,"Rentabilité nette"), use_container_width=True)
    with c3: st.plotly_chart(jauge(min(kpi["couverture_mois"],12),0,12,"Tréso (mois charges)",unite=" mois"), use_container_width=True)
    with c4:
        col = C["vert"] if kpi["bfr_jours"] < 60 else C["rouge"]
        st.plotly_chart(jauge(kpi["bfr_jours"],0,90,"BFR en jours",unite="j",couleur=col), use_container_width=True)

    st.markdown('<div class="section-hdr">KPI essentiels</div>', unsafe_allow_html=True)
    cols = st.columns(6)
    items = [
        ("CA", kpi["ca"], kpi_c.get("ca") if kpi_c else None, False),
        ("Marge brute", kpi["marge_brute"], kpi_c.get("marge_brute") if kpi_c else None, False),
        ("Résultat net", kpi["resultat_net"], kpi_c.get("resultat_net") if kpi_c else None, False),
        ("Trésorerie", kpi["tresorerie"], kpi_c.get("tresorerie") if kpi_c else None, False),
        ("Créances", kpi["creances"], kpi_c.get("creances") if kpi_c else None, True),
        ("BFR", kpi["bfr"], kpi_c.get("bfr") if kpi_c else None, True),
    ]
    for col, (lbl, v_n, v_c, inv) in zip(cols, items):
        with col:
            st.metric(lbl, fmt(v_n))
            if v_c:
                st.markdown(delta_html(annualiser(v_n, annee_active), v_c, inverse=inv), unsafe_allow_html=True)

    st.markdown('<div class="section-hdr">Suivi des objectifs</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    for col, lbl, reel, cible, inv in [
        (c1,"CA",kpi["ca"],obj_ca*1000,False),
        (c2,"Marge",kpi["marge_brute"],obj_marge*1000,False),
        (c3,"Trésorerie",kpi["tresorerie"],obj_treso*1000,False),
        (c4,"BFR max",kpi["bfr"],obj_bfr*1000,True),
    ]:
        with col:
            pct = min(reel/cible*100 if cible>0 else 0, 150)
            st.metric(lbl, fmt(reel), f"{pct:.0f}% objectif")
            st.progress(min(pct/100, 1.0))

    # Alertes impayés
    agee = d.get("agee", {})
    if agee and agee.get("plus_61",0) > 0:
        st.markdown('<div class="section-hdr">🚨 Impayés +61 jours</div>', unsafe_allow_html=True)
        for c in sorted([x for x in agee.get("clients",[]) if x.get("plus_61",0)>500], key=lambda x:-x["plus_61"])[:5]:
            st.markdown(f'<div class="alert-r">⚠️ <b>{c["nom"]}</b> — {fmt(c["plus_61"],k=False)} en retard</div>', unsafe_allow_html=True)

    # Alertes fournisseurs
    fourn   = d.get("fourn", {})
    fourn_c = d_c.get("fourn", {})
    if fourn and fourn_c:
        st.markdown('<div class="section-hdr">🔔 Alertes fournisseurs</div>', unsafe_allow_html=True)
        for a in [x for x in comparer_fournisseurs(fourn, fourn_c, annee_active, seuil_fourn) if x["statut"] in ["hausse","nouveau"]][:4]:
            if a["statut"] == "nouveau":
                st.markdown(f'<div class="alert-b">🆕 <b>{a["nom"]}</b> — Nouveau : {fmt(a["v_n"],k=False)}</div>', unsafe_allow_html=True)
            else:
                st.markdown(f'<div class="alert-a">📈 <b>{a["nom"]}</b> — +{a["variation"]:.0f}% ({fmt(a["v_n"],k=False)} ann.)</div>', unsafe_allow_html=True)

# ─── ONGLET 2 : CA & CLIENTS ──────────────────
with tabs[1]:
    journal = d.get("journal", {})

    if journal and journal.get("mensuel"):
        st.markdown('<div class="section-hdr">CA mensuel réel</div>', unsafe_allow_html=True)
        mois_ordre = ["Oct-22","Nov-22","Déc-22","Jan-23","Fév-23","Mar-23","Avr-23","Mai-23","Jun-23","Jul-23","Aoû-23","Sep-23",
                      "Oct-23","Nov-23","Déc-23","Jan-24","Fév-24","Mar-24","Avr-24","Mai-24","Jun-24","Jul-24","Aoû-24","Sep-24",
                      "Oct-24","Nov-24","Déc-24","Jan-25","Fév-25","Mar-25","Avr-25","Mai-25","Jun-25","Jul-25","Aoû-25","Sep-25","Oct-25","Nov-25","Déc-25"]
        mois_pres = [m for m in mois_ordre if m in journal["mensuel"]]
        vals = [journal["mensuel"][m] for m in mois_pres]
        moy = sum(vals)/len(vals) if vals else 0
        fig = go.Figure()
        fig.add_trace(go.Bar(x=mois_pres, y=vals, name="CA HT",
            marker_color=[C["rouge"] if v<moy*.5 else C["vert"] if v>moy*1.5 else C["bleu"] for v in vals]))
        fig.add_trace(go.Scatter(x=mois_pres, y=[moy]*len(mois_pres), mode="lines",
            line=dict(color=C["orange"],dash="dash",width=1.5), name=f"Moy. {fmt(moy,k=False)}"))
        fig.update_layout(height=300,margin=dict(t=10,b=0,l=0,r=0),
            legend=dict(orientation="h",y=1.1),
            plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig, use_container_width=True)

    if journal and journal.get("clients"):
        st.markdown('<div class="section-hdr">Répartition CA par client</div>', unsafe_allow_html=True)
        top = list(journal["clients"].items())[:10]
        total_ca = sum(v for _,v in top)
        c1,c2 = st.columns(2)
        with c1:
            fig = go.Figure(go.Pie(labels=[n[:20] for n,_ in top], values=[v for _,v in top], hole=0.55,
                marker_colors=[C["rouge"],C["bleu"],C["vert"],C["orange"],C["violet"],C["gris"],"#5DCAA5","#E24B4A","#639922","#FA8072"]))
            fig.update_layout(height=280,margin=dict(t=0,b=0,l=0,r=0),showlegend=False,paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            df_c = pd.DataFrame([(n, f"{v:,.0f} €", f"{v/total_ca*100:.1f}%") for n,v in top],
                                 columns=["Client","CA HT","% CA"])
            st.dataframe(df_c, use_container_width=True, hide_index=True)
        top1_pct = top[0][1]/total_ca*100 if top else 0
        if top1_pct > 20:
            st.markdown(f'<div class="alert-r">🚨 <b>{top[0][0]}</b> = {top1_pct:.1f}% du CA — risque dépendance</div>', unsafe_allow_html=True)

    agee = d.get("agee", {})
    agee_c = d_c.get("agee", {})
    if agee:
        st.markdown('<div class="section-hdr">Balance âgée clients</div>', unsafe_allow_html=True)
        total = agee.get("total",0)
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1: st.metric("Total", fmt(total))
        with c2: st.metric("Non échu", fmt(agee.get("non_echu",0)))
        with c3: st.metric("1-30j", fmt(agee.get("j1_30",0)))
        with c4: st.metric("31-60j", fmt(agee.get("j31_45",0)+agee.get("j46_60",0)))
        with c5:
            p61 = agee.get("plus_61",0)
            p61_c = agee_c.get("plus_61",0) if agee_c else None
            d_txt = delta_html(p61, p61_c, inverse=True) if p61_c else ""
            st.metric("⚠️ +61j", fmt(p61))
            if d_txt: st.markdown(d_txt, unsafe_allow_html=True)
        retards = sorted([c for c in agee.get("clients",[]) if c.get("plus_61",0)>200], key=lambda x:-x["plus_61"])
        if retards:
            df_r = pd.DataFrame([{"Client":c["nom"],"Total dû":f"{c['total']:,.0f} €","+61j":f"{c['plus_61']:,.0f} €"} for c in retards])
            st.dataframe(df_r, use_container_width=True, hide_index=True)

# ─── ONGLET 3 : ANALYTIQUE ────────────────────
with tabs[2]:
    analytique   = d.get("analytique", {})
    analytique_c = d_c.get("analytique", {})
    if not analytique:
        st.info("Balance analytique non disponible pour cet exercice.")
    else:
        for nom, data in analytique.items():
            if nom == "Frais généraux": continue
            ca_a = data["ca"]; mg_a = data["marge"]; tx_a = data["taux_marge"]
            ca_c_a = analytique_c.get(nom,{}).get("ca",0)
            mg_c_a = analytique_c.get(nom,{}).get("marge",0)
            with st.expander(f"**{nom}** — CA : {fmt(ca_a)} · Marge : {fmt(mg_a)} ({tx_a:.1f}%)", expanded=True):
                c1,c2,c3,c4 = st.columns(4)
                with c1:
                    st.metric("CA", fmt(ca_a))
                    if ca_c_a: st.markdown(delta_html(annualiser(ca_a,annee_active), ca_c_a), unsafe_allow_html=True)
                with c2: st.metric("Charges", fmt(data["charges"]))
                with c3:
                    st.metric("Marge", fmt(mg_a))
                    if mg_c_a: st.markdown(delta_html(annualiser(mg_a,annee_active), mg_c_a), unsafe_allow_html=True)
                with c4: st.metric("Taux marge", f"{tx_a:.1f}%")

        if analytique_c:
            st.markdown('<div class="section-hdr">Comparatif N vs N-1</div>', unsafe_allow_html=True)
            acts = [n for n in analytique if n != "Frais généraux"]
            fig = go.Figure()
            fig.add_trace(go.Bar(name=f"CA {annee_active} ann.", x=acts,
                y=[annualiser(analytique[a]["ca"],annee_active)/1000 for a in acts], marker_color=C["bleu"]))
            fig.add_trace(go.Bar(name=f"CA {annee_comp}", x=acts,
                y=[analytique_c.get(a,{}).get("ca",0)/1000 for a in acts], marker_color="#85B7EB"))
            fig.add_trace(go.Bar(name=f"Marge {annee_active} ann.", x=acts,
                y=[annualiser(analytique[a]["marge"],annee_active)/1000 for a in acts], marker_color=C["vert"]))
            fig.add_trace(go.Bar(name=f"Marge {annee_comp}", x=acts,
                y=[analytique_c.get(a,{}).get("marge",0)/1000 for a in acts], marker_color="#9FE1CB"))
            fig.update_layout(barmode="group",height=320,margin=dict(t=10,b=0,l=0,r=0),
                legend=dict(orientation="h",y=1.1),
                plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(title="k€",gridcolor="#f0f0f0"))
            st.plotly_chart(fig, use_container_width=True)

# ─── ONGLET 4 : FOURNISSEURS ──────────────────
with tabs[3]:
    fourn   = d.get("fourn", {})
    fourn_c = d_c.get("fourn", {})
    if not fourn:
        st.info("Grand livre fournisseurs non disponible.")
    else:
        alertes = comparer_fournisseurs(fourn, fourn_c, annee_active, seuil_fourn) if fourn_c else []
        for a in alertes[:10]:
            if a["statut"] == "hausse":
                st.markdown(f'<div class="alert-a">📈 <b>{a["nom"]}</b> — +{a["variation"]:.0f}% ({fmt(a["v_n1"],k=False)} → {fmt(a["v_n"],k=False)} ann.)</div>', unsafe_allow_html=True)
            elif a["statut"] == "nouveau":
                st.markdown(f'<div class="alert-b">🆕 <b>{a["nom"]}</b> — {fmt(a["v_n"],k=False)} ann.</div>', unsafe_allow_html=True)
            elif a["statut"] == "baisse":
                st.markdown(f'<div class="alert-g">📉 <b>{a["nom"]}</b> — {a["variation"]:.0f}% ({fmt(a["v_n"],k=False)} ann.)</div>', unsafe_allow_html=True)
            elif a["statut"] == "disparu":
                st.markdown(f'<div class="alert-g">✅ <b>{a["nom"]}</b> — Disparu (était {fmt(a["v_n1"],k=False)})</div>', unsafe_allow_html=True)

        coef = 12 / EXERCICES.get(annee_active,{}).get("mois",12)
        df_f = pd.DataFrame([{
            "Fournisseur": n,
            f"{annee_active} réel": f"{v:,.0f} €",
            f"{annee_active} ann.": f"{v*coef:,.0f} €",
            annee_comp: f"{fourn_c.get(n,0):,.0f} €" if fourn_c else "—",
        } for n,v in list(fourn.items())[:20]])
        st.dataframe(df_f, use_container_width=True, hide_index=True)

        top_f = list(fourn.items())[:10]
        fig = go.Figure()
        fig.add_trace(go.Bar(name=f"{annee_active} ann.", x=[n[:18] for n,_ in top_f],
            y=[v*coef/1000 for _,v in top_f], marker_color=C["bleu"]))
        if fourn_c:
            fig.add_trace(go.Bar(name=annee_comp, x=[n[:18] for n,_ in top_f],
                y=[fourn_c.get(n,0)/1000 for n,_ in top_f], marker_color="#85B7EB"))
        fig.update_layout(barmode="group",height=280,margin=dict(t=10,b=0,l=0,r=0),
            xaxis=dict(tickangle=-30),legend=dict(orientation="h",y=1.1),
            plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="k€",gridcolor="#f0f0f0"))
        st.plotly_chart(fig, use_container_width=True)

# ─── ONGLET 5 : BFR & TRÉSO ───────────────────
with tabs[4]:
    st.markdown('<div class="section-hdr">BFR — Besoin en Fonds de Roulement</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("Stocks", fmt(kpi["stocks"],k=False))
    with c2: st.metric("+ Créances", fmt(kpi["creances"],k=False))
    with c3: st.metric("− Dettes fourn.", f"−{fmt(kpi['dettes_fourn'],k=False)}")
    with c4:
        st.metric("= BFR", fmt(kpi["bfr"],k=False))
        if kpi_c: st.markdown(delta_html(kpi["bfr"], kpi_c["bfr"], inverse=True), unsafe_allow_html=True)

    fig = go.Figure(go.Waterfall(
        orientation="v", measure=["absolute","relative","relative","total"],
        x=["Stocks","+ Créances","− Dettes fourn.","= BFR"],
        y=[kpi["stocks"],kpi["creances"],-kpi["dettes_fourn"],0],
        connector={"line":{"color":"#dee2e6"}},
        increasing={"marker":{"color":C["bleu"]}},
        decreasing={"marker":{"color":C["vert"]}},
        totals={"marker":{"color":C["orange"]}},
        texttemplate="%{y:,.0f} €", textposition="outside"
    ))
    fig.update_layout(height=260,margin=dict(t=10,b=0,l=0,r=0),
        plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#f0f0f0"))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="section-hdr">Ratios financiers</div>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5 = st.columns(5)
    ratios = [
        (c1,"Trésorerie",kpi["tresorerie"],"tresorerie",False),
        (c2,"BFR jours",None,"bfr_jours",True),
        (c3,"CAF",kpi["caf"],"caf",False),
        (c4,"Fonds roulement",kpi["fonds_roulement"],"fonds_roulement",False),
        (c5,"DSO",None,"dso",True),
    ]
    for col, lbl, v, key, inv in ratios:
        with col:
            if key in ["bfr_jours","dso"]:
                st.metric(lbl, f"{kpi[key]:.0f} j")
            else:
                st.metric(lbl, fmt(v))
            if kpi_c and kpi_c.get(key):
                st.markdown(delta_html(kpi[key], kpi_c[key], inverse=inv), unsafe_allow_html=True)

    if kpi_c:
        st.markdown('<div class="section-hdr">Évolution 3 exercices</div>', unsafe_allow_html=True)
        annees_graph = sorted([a for a in donnees if donnees[a].get("kpi")])
        ca_g  = [annualiser(donnees[a]["kpi"]["ca"],a)/1000 for a in annees_graph]
        tr_g  = [donnees[a]["kpi"]["tresorerie"]/1000 for a in annees_graph]
        bfr_g = [annualiser(donnees[a]["kpi"]["bfr"],a)/1000 for a in annees_graph]
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=annees_graph,y=ca_g,mode="lines+markers",name="CA ann.",line=dict(color=C["bleu"],width=2)))
        fig.add_trace(go.Scatter(x=annees_graph,y=tr_g,mode="lines+markers",name="Trésorerie",line=dict(color=C["vert"],width=2)))
        fig.add_trace(go.Scatter(x=annees_graph,y=bfr_g,mode="lines+markers",name="BFR ann.",line=dict(color=C["orange"],width=2,dash="dot")))
        fig.update_layout(height=260,margin=dict(t=10,b=0,l=0,r=0),
            legend=dict(orientation="h",y=1.1),
            plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="k€",gridcolor="#f0f0f0"))
        st.plotly_chart(fig, use_container_width=True)
