import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path

st.set_page_config(page_title="ECCO BAT", page_icon="🏗️", layout="wide")

ROOT = Path(__file__).parent
DATA = ROOT / "data"

EXERCICES = {
    "2025": {"debut": "01/10/2024", "fin": "31/12/2025", "mois": 15},
    "2024": {"debut": "01/10/2023", "fin": "30/09/2024", "mois": 12},
    "2023": {"debut": "01/10/2022", "fin": "30/09/2023", "mois": 12},
}

C = {"bleu":"#378ADD","vert":"#1D9E75","orange":"#BA7517","rouge":"#D85A30","gris":"#888780","violet":"#7F77DD"}
CFG = {"displayModeBar": False}

st.markdown("""
<style>
.main { background: #f4f6f9; }
.block-container { padding-top: 1rem; }
.kpi-card {
    background: white; border-radius: 12px; padding: 18px 20px;
    border: 1px solid #e8ecf0; box-shadow: 0 1px 4px rgba(0,0,0,0.05);
    margin-bottom: 10px; height: 110px;
}
.kpi-label { font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: .06em; color: #8896a5; margin-bottom: 6px; }
.kpi-value { font-size: 26px; font-weight: 700; color: #1a2332; line-height: 1.1; }
.kpi-delta { font-size: 12px; margin-top: 4px; }
.dp { color: #1D9E75; font-weight: 600; }
.dn { color: #D85A30; font-weight: 600; }
.section-title { font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .1em; color: #8896a5; margin: 24px 0 12px;
    padding-bottom: 8px; border-bottom: 2px solid #e8ecf0; }
.alert-r { background:#fff5f5; border-left:4px solid #D85A30; border-radius:8px;
    padding:12px 16px; margin-bottom:8px; font-size:13px; color:#c53030; }
.alert-a { background:#fffbeb; border-left:4px solid #BA7517; border-radius:8px;
    padding:12px 16px; margin-bottom:8px; font-size:13px; color:#b7791f; }
.alert-g { background:#f0fff4; border-left:4px solid #1D9E75; border-radius:8px;
    padding:12px 16px; margin-bottom:8px; font-size:13px; color:#276749; }
.badge { display:inline-flex; padding:2px 8px; border-radius:20px; font-size:11px; font-weight:600; }
.badge-r { background:#FCEBEB; color:#A32D2D; }
.badge-a { background:#FAEEDA; color:#854F0B; }
.badge-g { background:#EAF3DE; color:#3B6D11; }
.badge-b { background:#E6F1FB; color:#185FA5; }
.badge-n { background:#F0F2F5; color:#4A5568; }
</style>
""", unsafe_allow_html=True)

def fmt(v, k=True):
    if k:
        n = v / 1000
        s = f"{abs(n):,.1f}".replace(",","X").replace(".",",").replace("X"," ")
        return ("-" if n < 0 else "") + s + " k€"
    s = f"{abs(v):,.0f}".replace(",", " ")
    return ("-" if v < 0 else "") + s + " €"

def fmt_pct(v):
    s = f"{abs(v):.1f}".replace(".", ",")
    return ("-" if v < 0 else "") + s + "%"

def annualiser(v, annee):
    m = EXERCICES.get(annee, {}).get("mois", 12)
    return v * 12 / m if m != 12 else v

def delta_html(vn, vc, inv=False):
    if not vc or vc == 0: return ""
    p = (vn - vc) / abs(vc) * 100
    bon = p > 0 if not inv else p < 0
    cls = "dp" if bon else "dn"
    arr = "▲" if p > 0 else "▼"
    return f'<span class="{cls}">{arr} {fmt_pct(abs(p))} vs N-1</span>'

def kpi_card(label, value, delta="", sub=""):
    return f"""
    <div class="kpi-card">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-delta">{delta}</div>
        {"<div style='font-size:11px;color:#adb5bd'>" + sub + "</div>" if sub else ""}
    </div>
    """

# ══════════════════════════════════════════════════════════
# LECTURE DES DONNÉES
# ══════════════════════════════════════════════════════════
@st.cache_data
def lire_balance(annee):
    p = DATA / f"balance_generale_{annee}.xlsx"
    if not p.exists(): return {}, {}
    df = pd.read_excel(p, header=None, dtype=str)
    comptes = {}
    totaux_classe = {}

    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.values
                if pd.notna(v) and str(v).strip() not in ["","nan"]]
        if not vals: continue
        premier = vals[0].replace(" ","")
        if not premier or not premier[0].isdigit(): continue
        num = premier

        montants = []
        intitule = ""
        for v in vals[1:]:
            try: montants.append(float(v.replace(" ","").replace(",",".")))
            except:
                if not intitule and len(v) > 2: intitule = v

        # Ligne de total de classe (ex: "70", "60", "64"...)
        if len(num) <= 2 and len(montants) >= 3:
            totaux_classe[num] = {
                "intitule": intitule,
                "debit_mvt": montants[0],
                "credit_mvt": montants[1],
                "solde_net": montants[-1]  # dernier = solde net
            }

        # Compte individuel (6 chiffres)
        elif len(num) == 6 and len(montants) >= 2:
            solde_net = montants[1] - montants[0]
            comptes[num] = {
                "intitule": intitule,
                "debit_mvt": montants[0],
                "credit_mvt": montants[1],
                "solde_net": solde_net,
                "sd": max(montants[2], 0) if len(montants) > 2 else max(-solde_net, 0),
                "sc": max(montants[3], 0) if len(montants) > 3 else max(solde_net, 0),
            }

    return comptes, totaux_classe

@st.cache_data
def lire_balance_agee(annee):
    p = DATA / f"balance_agee_clients_{annee}.xlsx"
    if not p.exists(): return {}
    df = pd.read_excel(p, header=None, dtype=str)
    clients = []
    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.values
                if pd.notna(v) and str(v).strip() not in ["","nan"]]
        if len(vals) < 3: continue
        if vals[0] in ["Totaux","Total","% Période"]: continue
        if not vals[0].isdigit() and len(vals[0]) > 2:
            nums = []
            for v in vals[2:]:
                try: nums.append(float(v.replace(" ","").replace(",",".")))
                except: pass
            if nums and abs(nums[0]) > 0:
                clients.append({
                    "nom":     vals[1] if len(vals) > 1 else vals[0],
                    "total":   abs(nums[0]),
                    "non_echu":abs(nums[1]) if len(nums) > 1 else 0,
                    "j1_30":   abs(nums[2]) if len(nums) > 2 else 0,
                    "j31_45":  abs(nums[3]) if len(nums) > 3 else 0,
                    "j46_60":  abs(nums[4]) if len(nums) > 4 else 0,
                    "plus_61": abs(nums[5]) if len(nums) > 5 else 0,
                })
    return {
        "total":    sum(c["total"]    for c in clients),
        "non_echu": sum(c["non_echu"] for c in clients),
        "j1_30":    sum(c["j1_30"]    for c in clients),
        "plus_61":  sum(c["plus_61"]  for c in clients),
        "clients":  sorted(clients, key=lambda x: -x["plus_61"])
    }

@st.cache_data
def lire_analytique(annee):
    p = DATA / f"balance_analytique_{annee}.xlsx"
    if not p.exists(): return {}
    df = pd.read_excel(p, header=None, dtype=str)
    sections = {}
    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.values
                if pd.notna(v) and str(v).strip() not in ["","nan"]]
        if not vals: continue
        if vals[0] == "Total" and len(vals) >= 3:
            code = vals[1]
            label = vals[2] if len(vals) > 2 else code
            nums = []
            for v in vals[3:]:
                try: nums.append(float(v.replace(" ","").replace(",",".")))
                except: pass
            if len(nums) >= 2:
                sections[code] = {
                    "label": label,
                    "charges": nums[0],
                    "ca": nums[1] if nums[1] > nums[0] else 0,
                    "marge": nums[1] - nums[0]
                }
    groupes = {
        "Maintenance":            [k for k in sections if k.startswith("1")],
        "Rénovation énergétique": [k for k in sections if k.startswith("2")],
        "Maçonnerie":             [k for k in sections if k.startswith("3")],
        "Frais généraux":         [k for k in sections if k.startswith("9")],
    }
    result = {}
    for nom, codes in groupes.items():
        ca = sum(sections[c]["ca"] for c in codes if c in sections)
        ch = sum(sections[c]["charges"] for c in codes if c in sections)
        mg = ca - ch
        if ca > 0 or abs(mg) > 0:
            result[nom] = {
                "ca": ca, "charges": ch, "marge": mg,
                "taux_marge": mg / ca * 100 if ca > 0 else 0,
                "detail": {c: sections[c] for c in codes if c in sections}
            }
    return result

def calculer_kpi(comptes, totaux):
    def get_total_solde(prefixe):
        t = totaux.get(prefixe)
        if t: return t["solde_net"]
        return sum(c["solde_net"] for n,c in comptes.items() if n.startswith(prefixe))

    def sc(p): return sum(c["sc"] for n,c in comptes.items() if n.startswith(p))
    def sd(p): return sum(c["sd"] for n,c in comptes.items() if n.startswith(p))

    # CA = solde net créditeur du total 70 (dernier montant)
    ca = abs(get_total_solde("70")) if get_total_solde("70") != 0 else sc("70")

    achats       = abs(get_total_solde("60")) if get_total_solde("60") < 0 else sd("60")
    charges_pers = abs(get_total_solde("64")) if get_total_solde("64") < 0 else sd("64")
    services     = abs(get_total_solde("61")) if get_total_solde("61") < 0 else sd("61")
    autres       = abs(get_total_solde("62")) if get_total_solde("62") < 0 else sd("62")
    impots       = abs(get_total_solde("63")) if get_total_solde("63") < 0 else sd("63")
    dotations    = abs(get_total_solde("68")) if get_total_solde("68") < 0 else sd("68")
    is_          = max(sd("69") - sc("69"), 0)
    charges_tot  = achats + charges_pers + services + autres + impots + dotations + is_

    resultat_t = get_total_solde("12")
    resultat = resultat_t if abs(resultat_t) > 1000 else ca - charges_tot

    marge    = ca - achats
    stocks   = sd("31") + sd("32") + sd("33")
    creances = sd("411")
    dettes_f = sc("401")
    treso    = max(sum(c["sd"]-c["sc"] for n,c in comptes.items()
                       if n.startswith("512") or n.startswith("531")), 0)
    bfr      = stocks + creances - dettes_f

    return {
        "ca": ca, "marge": marge, "resultat": resultat,
        "charges_tot": charges_tot, "achats": achats,
        "charges_pers": charges_pers, "services": services,
        "dotations": dotations, "is_": is_,
        "stocks": stocks, "creances": creances,
        "dettes_f": dettes_f, "treso": treso, "bfr": bfr,
        "taux_marge":  marge/ca*100    if ca>0 else 0,
        "taux_rent":   resultat/ca*100 if ca>0 else 0,
        "bfr_jours":   bfr/ca*365      if ca>0 else 0,
        "dso":         creances/ca*365 if ca>0 else 0,
        "couverture":  treso/(charges_tot/12) if charges_tot>0 else 0,
        "caf":         resultat + dotations,
        "detail_comptes": {
            "CA (70)": {n: c for n,c in comptes.items() if n.startswith("70") and c["credit_mvt"]>0},
            "Achats (60)": {n: c for n,c in comptes.items() if n.startswith("60") and (c["debit_mvt"]+c["credit_mvt"])>0},
            "Personnel (64)": {n: c for n,c in comptes.items() if n.startswith("64") and (c["debit_mvt"]+c["credit_mvt"])>0},
            "Services (61)": {n: c for n,c in comptes.items() if n.startswith("61") and (c["debit_mvt"]+c["credit_mvt"])>0},
            "Trésorerie (512)": {n: c for n,c in comptes.items() if n.startswith("512") and (c["sd"]+c["sc"])>0},
        }
    }

def sante(kpi):
    s = sum([kpi["taux_marge"]>45, kpi["taux_rent"]>5,
             kpi["treso"]>0, kpi["bfr_jours"]<60, kpi["dso"]<45]) * 2
    if s >= 8: return "😄","Excellente santé financière","#f0fff4","#38a169"
    if s >= 6: return "😊","Bonne santé — points à surveiller","#f0fff4","#38a169"
    if s >= 4: return "😐","Vigilance requise","#fffbeb","#d69e2e"
    return "😟","Points critiques à traiter","#fff5f5","#e53e3e"

def jauge(val, min_v, max_v, titre, unite="%", couleur=None):
    if couleur is None:
        p = (val-min_v)/max(max_v-min_v,1)
        couleur = C["vert"] if p>0.6 else (C["orange"] if p>0.3 else C["rouge"])
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(val,1),
        number={"suffix":unite,"font":{"size":18}},
        title={"text":titre,"font":{"size":11}},
        gauge={"axis":{"range":[min_v,max_v]},"bar":{"color":couleur,"thickness":0.25},
               "bgcolor":"white","borderwidth":0,
               "steps":[{"range":[min_v,min_v+(max_v-min_v)*.4],"color":"#ffecec"},
                        {"range":[min_v+(max_v-min_v)*.4,min_v+(max_v-min_v)*.7],"color":"#fff8e6"},
                        {"range":[min_v+(max_v-min_v)*.7,max_v],"color":"#edf7f0"}]}
    ))
    fig.update_layout(height=190,margin=dict(t=30,b=0,l=10,r=10),paper_bgcolor="rgba(0,0,0,0)")
    return fig

# ══════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## 🏗️ ECCO BAT")
    st.markdown("---")

    st.markdown("**Exercice à afficher**")
    annee = st.selectbox("", ["2025","2024","2023"],
        format_func=lambda x: f"Ex. {x}  ({EXERCICES[x]['debut']} → {EXERCICES[x]['fin']})",
        label_visibility="collapsed")

    st.markdown("**Exercice en comparaison**")
    options_comp = ["N-1 automatique"] + [a for a in ["2025","2024","2023"] if a != annee]
    comp_choix = st.selectbox("", options_comp, label_visibility="collapsed")
    annee_c = str(int(annee)-1) if comp_choix == "N-1 automatique" else comp_choix

    mois = EXERCICES[annee]["mois"]
    mois_c = EXERCICES.get(annee_c, {}).get("mois", 12)
    if mois != 12:
        st.info(f"⚠️ Ex. {annee} = {mois} mois → données annualisées ×12/{mois}")

    st.markdown("---")
    st.markdown("### 🎯 Objectifs")
    obj_ca    = st.number_input("CA cible (k€)",    value=5000, step=100)
    obj_marge = st.number_input("Marge cible (k€)", value=2800, step=100)
    obj_treso = st.number_input("Tréso mini (k€)",  value=800,  step=50)
    obj_bfr   = st.number_input("BFR max (k€)",     value=400,  step=50)
    st.markdown("---")
    seuil = st.slider("Seuil alerte charges (%)", 1, 30, 10, format="%d%%")

# ══════════════════════════════════════════════════════════
# CHARGEMENT
# ══════════════════════════════════════════════════════════
comptes, totaux       = lire_balance(annee)
comptes_c, totaux_c   = lire_balance(annee_c) if annee_c in EXERCICES else ({},{})
agee                  = lire_balance_agee(annee)
agee_c                = lire_balance_agee(annee_c) if annee_c in EXERCICES else {}
analytique            = lire_analytique(annee)
ana_c                 = lire_analytique(annee_c) if annee_c in EXERCICES else {}
kpi                   = calculer_kpi(comptes, totaux) if comptes else {}
kpi_c                 = calculer_kpi(comptes_c, totaux_c) if comptes_c else {}

if not kpi:
    st.error(f"Impossible de charger la balance {annee}. Vérifiez le dossier data/")
    st.stop()

# ══════════════════════════════════════════════════════════
# EN-TÊTE
# ══════════════════════════════════════════════════════════
col_t, col_p = st.columns([4, 2])
with col_t:
    st.markdown(f"## 🏗️ ECCO BAT — Cockpit Dirigeant")
with col_p:
    st.markdown(f"<br><span style='color:#8896a5;font-size:13px'>Ex. {annee} vs Ex. {annee_c}</span>",
                unsafe_allow_html=True)

emoji, texte, bg, bord = sante(kpi)
ann_note = f" · Annualisé ×12/{mois}" if mois != 12 else ""
st.markdown(f"""
<div style="background:{bg};border-left:5px solid {bord};border-radius:12px;
    padding:16px 22px;margin-bottom:20px;display:flex;align-items:center;gap:16px;
    box-shadow:0 1px 4px rgba(0,0,0,0.06)">
    <span style="font-size:40px">{emoji}</span>
    <div>
        <b style="font-size:17px">{texte}</b><br>
        <span style="font-size:12px;color:#555">
            Marge {fmt_pct(kpi['taux_marge'])} · Rentabilité {fmt_pct(kpi['taux_rent'])} ·
            Tréso {fmt(kpi['treso'])} · BFR {kpi['bfr_jours']:.0f}j{ann_note}
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════
# 5 ONGLETS
# ══════════════════════════════════════════════════════════
tabs = st.tabs(["🏠 Cockpit","📈 CA & Clients","🔬 Analytique","🔔 Charges & Fourn.","💰 BFR & Tréso"])

# ─── ONGLET 1 : COCKPIT ───────────────────────────────────
with tabs[0]:
    # Jauges
    st.markdown('<div class="section-title">Jauges de santé</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.plotly_chart(jauge(kpi["taux_marge"],0,100,"Taux de marge"), use_container_width=True, config=CFG)
    with c2: st.plotly_chart(jauge(kpi["taux_rent"],0,30,"Rentabilité nette"), use_container_width=True, config=CFG)
    with c3: st.plotly_chart(jauge(min(kpi["couverture"],12),0,12,"Tréso (mois charges)",unite=" mois"), use_container_width=True, config=CFG)
    with c4:
        col = C["vert"] if kpi["bfr_jours"]<60 else C["rouge"]
        st.plotly_chart(jauge(kpi["bfr_jours"],0,90,"BFR en jours",unite="j",couleur=col), use_container_width=True, config=CFG)

    # KPI rectangles
    st.markdown('<div class="section-title">KPI essentiels — cliquez pour voir le détail des comptes</div>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5,c6 = st.columns(6)
    items_kpi = [
        (c1,"CA",kpi["ca"],kpi_c.get("ca"),False,"CA (70)"),
        (c2,"Marge brute",kpi["marge"],kpi_c.get("marge"),False,"Achats (60)"),
        (c3,"Résultat net",kpi["resultat"],kpi_c.get("resultat"),False,None),
        (c4,"Trésorerie",kpi["treso"],kpi_c.get("treso"),False,"Trésorerie (512)"),
        (c5,"Créances clients",kpi["creances"],kpi_c.get("creances"),True,None),
        (c6,"BFR",kpi["bfr"],kpi_c.get("bfr"),True,None),
    ]
    for col,(c,lbl,vn,vc,inv,detail_key) in zip([c1,c2,c3,c4,c5,c6], items_kpi):
        with c:
            vn_ann = annualiser(vn, annee)
            d = delta_html(vn_ann, vc, inv) if vc else ""
            sub = f"Annualisé : {fmt(vn_ann)}" if mois != 12 else ""
            st.markdown(kpi_card(lbl, fmt(vn), d, sub), unsafe_allow_html=True)
            if detail_key and kpi.get("detail_comptes", {}).get(detail_key):
                with st.expander("📋 Détail"):
                    detail = kpi["detail_comptes"][detail_key]
                    rows = []
                    for num, c_data in detail.items():
                        rows.append({
                            "Compte": num,
                            "Intitulé": c_data["intitule"][:35],
                            "Débit": fmt(c_data["debit_mvt"], k=False),
                            "Crédit": fmt(c_data["credit_mvt"], k=False),
                        })
                    if rows:
                        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)

    # Objectifs
    st.markdown('<div class="section-title">Suivi des objectifs</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    for col,lbl,reel,cible,inv,couleur in [
        (c1,"CA",kpi["ca"],obj_ca*1000,False,C["bleu"]),
        (c2,"Marge brute",kpi["marge"],obj_marge*1000,False,C["vert"]),
        (c3,"Trésorerie",kpi["treso"],obj_treso*1000,False,C["vert"]),
        (c4,"BFR max",kpi["bfr"],obj_bfr*1000,True,C["orange"]),
    ]:
        with col:
            pct = min(max(reel/cible*100 if cible>0 else 0, 0), 150)
            ok = pct >= 80 if not inv else pct <= 100
            bar_col = C["vert"] if ok else C["rouge"]
            st.markdown(f"""
            <div class="kpi-card">
                <div class="kpi-label">{lbl}</div>
                <div class="kpi-value">{fmt(reel)}</div>
                <div class="kpi-delta" style="color:#8896a5">{pct:.0f}% de l'objectif ({fmt(cible)})</div>
                <div style="background:#e8ecf0;border-radius:6px;height:6px;margin-top:8px;overflow:hidden">
                    <div style="width:{min(pct,100):.0f}%;height:100%;background:{bar_col};border-radius:6px"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Alertes impayés
    if agee and agee.get("plus_61",0) > 0:
        st.markdown('<div class="section-title">🚨 Impayés critiques +61 jours</div>', unsafe_allow_html=True)
        for c in [x for x in agee.get("clients",[]) if x.get("plus_61",0)>500][:5]:
            st.markdown(f'<div class="alert-r">⚠️ <b>{c["nom"]}</b> — {fmt(c["plus_61"],k=False)} en retard +61j &nbsp;|&nbsp; Total dû : {fmt(c["total"],k=False)}</div>', unsafe_allow_html=True)

# ─── ONGLET 2 : CA & CLIENTS ───────────────────────────────
with tabs[1]:
    # KPI clients
    st.markdown('<div class="section-title">Vue d\'ensemble clients</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    ca_ann = annualiser(kpi["ca"], annee)
    ca_c_val = kpi_c.get("ca", 0)
    with c1: st.markdown(kpi_card("CA réel", fmt(kpi["ca"]), "", f"Ex. {annee} ({mois} mois)"), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card("CA annualisé", fmt(ca_ann), delta_html(ca_ann, ca_c_val), f"Base 12 mois"), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card(f"CA Ex. {annee_c}", fmt(ca_c_val) if ca_c_val else "—", ""), unsafe_allow_html=True)
    with c4: st.markdown(kpi_card("Créances clients", fmt(kpi["creances"]), delta_html(kpi["creances"], kpi_c.get("creances"), inv=True), f"DSO : {kpi['dso']:.0f}j"), unsafe_allow_html=True)

    # Balance âgée
    if agee and agee.get("total",0) > 0:
        st.markdown('<div class="section-title">Balance âgée clients</div>', unsafe_allow_html=True)
        total = agee["total"]
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1: st.markdown(kpi_card("Total créances", fmt(total)), unsafe_allow_html=True)
        with c2: st.markdown(kpi_card("Non échu", fmt(agee["non_echu"]), f"{agee['non_echu']/total*100:.0f}% du total"), unsafe_allow_html=True)
        with c3: st.markdown(kpi_card("1 à 30 jours", fmt(agee["j1_30"])), unsafe_allow_html=True)
        with c4:
            p61 = agee["plus_61"]
            p61_c = agee_c.get("plus_61",0) if agee_c else 0
            st.markdown(kpi_card("⚠️ +61 jours", fmt(p61),
                delta_html(p61, p61_c, inv=True) if p61_c else "",
                f"{p61/total*100:.0f}% du total"), unsafe_allow_html=True)
        with c5: st.markdown(kpi_card("DSO", f"{kpi['dso']:.0f} jours"), unsafe_allow_html=True)

        # Graphique balance âgée
        j31 = sum(c["j31_45"] for c in agee["clients"])
        j46 = sum(c["j46_60"] for c in agee["clients"])
        fig = go.Figure(go.Bar(
            x=["Non échu","1-30j","31-45j","46-60j","+61j"],
            y=[agee["non_echu"]/1000, agee["j1_30"]/1000, j31/1000, j46/1000, agee["plus_61"]/1000],
            marker_color=[C["vert"],C["bleu"],C["orange"],C["orange"],C["rouge"]],
            text=[fmt(v*1000) for v in [agee["non_echu"]/1000, agee["j1_30"]/1000, j31/1000, j46/1000, agee["plus_61"]/1000]],
            textposition="outside"
        ))
        fig.update_layout(height=260,margin=dict(t=20,b=0,l=0,r=0),
            plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="k€",gridcolor="#f0f0f0"))
        st.plotly_chart(fig, use_container_width=True, config=CFG)

        # Tableau clients en retard
        retards = [c for c in agee["clients"] if c.get("plus_61",0)>100]
        if retards:
            st.markdown('<div class="section-title">Clients avec retard +61 jours</div>', unsafe_allow_html=True)
            df_r = pd.DataFrame([{
                "Client": c["nom"],
                "Total dû": fmt(c["total"],k=False),
                "Non échu": fmt(c["non_echu"],k=False),
                "+61 jours": fmt(c["plus_61"],k=False),
                "% du total": f"{c['plus_61']/c['total']*100:.0f}%" if c["total"]>0 else "—"
            } for c in retards])
            st.dataframe(df_r, use_container_width=True, hide_index=True)

# ─── ONGLET 3 : ANALYTIQUE ────────────────────────────────
with tabs[2]:
    if not analytique:
        st.info("Balance analytique non disponible pour cet exercice.")
    else:
        st.markdown('<div class="section-title">Performance par activité</div>', unsafe_allow_html=True)

        # KPI par activité
        acts = [n for n in analytique if n != "Frais généraux"]
        cols = st.columns(len(acts))
        for col, nom in zip(cols, acts):
            data = analytique[nom]
            ca_a = data["ca"]
            mg_a = data["marge"]
            tx_a = data["taux_marge"]
            ca_c_a = ana_c.get(nom,{}).get("ca",0)
            with col:
                couleur = C["vert"] if mg_a > 0 else C["rouge"]
                st.markdown(f"""
                <div class="kpi-card" style="height:auto;border-top:4px solid {couleur}">
                    <div class="kpi-label">{nom}</div>
                    <div class="kpi-value">{fmt(ca_a)}</div>
                    <div style="font-size:13px;color:{couleur};font-weight:600;margin-top:4px">
                        Marge {fmt(mg_a)} ({fmt_pct(tx_a)})
                    </div>
                    {('<div class="kpi-delta">' + delta_html(annualiser(ca_a,annee), ca_c_a) + '</div>') if ca_c_a else ''}
                </div>
                """, unsafe_allow_html=True)

        # Détail par activité
        for nom in acts:
            data = analytique[nom]
            ca_c_a = ana_c.get(nom,{}).get("ca",0)
            mg_c_a = ana_c.get(nom,{}).get("marge",0)
            with st.expander(f"📊 Détail — {nom}", expanded=False):
                c1,c2,c3,c4 = st.columns(4)
                with c1:
                    st.metric("CA", fmt(data["ca"]))
                    if ca_c_a: st.markdown(delta_html(annualiser(data["ca"],annee), ca_c_a), unsafe_allow_html=True)
                with c2: st.metric("Charges directes", fmt(data["charges"]))
                with c3:
                    st.metric("Marge", fmt(data["marge"]))
                    if mg_c_a: st.markdown(delta_html(annualiser(data["marge"],annee), mg_c_a), unsafe_allow_html=True)
                with c4: st.metric("Taux de marge", fmt_pct(data["taux_marge"]))

                # Détail sections
                if data.get("detail"):
                    df_d = pd.DataFrame([{
                        "Section": k,
                        "Libellé": v["label"][:40],
                        "CA": fmt(v["ca"],k=False),
                        "Charges": fmt(v["charges"],k=False),
                        "Marge": fmt(v["marge"],k=False),
                    } for k,v in data["detail"].items()])
                    st.dataframe(df_d, use_container_width=True, hide_index=True)

        # Graphique comparatif
        if ana_c:
            st.markdown('<div class="section-title">Comparatif N vs N-1 (annualisé)</div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(name=f"CA {annee} ann.", x=acts,
                y=[annualiser(analytique[a]["ca"],annee)/1000 for a in acts], marker_color=C["bleu"]))
            fig.add_trace(go.Bar(name=f"CA {annee_c}", x=acts,
                y=[ana_c.get(a,{}).get("ca",0)/1000 for a in acts], marker_color="#85B7EB"))
            fig.add_trace(go.Bar(name=f"Marge {annee} ann.", x=acts,
                y=[annualiser(analytique[a]["marge"],annee)/1000 for a in acts], marker_color=C["vert"]))
            fig.add_trace(go.Bar(name=f"Marge {annee_c}", x=acts,
                y=[ana_c.get(a,{}).get("marge",0)/1000 for a in acts], marker_color="#9FE1CB"))
            fig.update_layout(barmode="group",height=320,margin=dict(t=10,b=0,l=0,r=0),
                legend=dict(orientation="h",y=1.1),
                plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(title="k€",gridcolor="#f0f0f0"))
            st.plotly_chart(fig, use_container_width=True, config=CFG)

# ─── ONGLET 4 : CHARGES & FOURNISSEURS ─────────────────────
with tabs[3]:
    st.markdown('<div class="section-title">Structure des charges (annualisé)</div>', unsafe_allow_html=True)

    postes = [
        ("Achats & matières (60)", kpi["achats"], kpi_c.get("achats",0), C["bleu"]),
        ("Personnel (64)",         kpi["charges_pers"], kpi_c.get("charges_pers",0), C["vert"]),
        ("Services ext. (61)",     kpi["services"], kpi_c.get("services",0), C["orange"]),
        ("Dotations (68)",         kpi["dotations"], kpi_c.get("dotations",0), C["gris"]),
        ("Impôt société (69)",     kpi["is_"], kpi_c.get("is_",0), C["rouge"]),
    ]

    cols = st.columns(len(postes))
    for col,(lbl,vn,vc,couleur) in zip(cols, postes):
        with col:
            vn_ann = annualiser(vn, annee)
            d = delta_html(vn_ann, vc, inv=True) if vc else ""
            pct_ca = vn_ann/annualiser(kpi["ca"],annee)*100 if kpi["ca"]>0 else 0
            st.markdown(f"""
            <div class="kpi-card" style="height:auto;border-top:4px solid {couleur}">
                <div class="kpi-label">{lbl}</div>
                <div class="kpi-value">{fmt(vn)}</div>
                <div class="kpi-delta">{d}</div>
                <div style="font-size:11px;color:#8896a5;margin-top:4px">{fmt_pct(pct_ca)} du CA</div>
            </div>
            """, unsafe_allow_html=True)

    # Alertes charges
    if kpi_c:
        st.markdown('<div class="section-title">Alertes variations charges N vs N-1</div>', unsafe_allow_html=True)
        for lbl,vn,vc,_ in postes:
            if vc > 0:
                vn_ann = annualiser(vn, annee)
                p = (vn_ann - vc) / vc * 100
                if abs(p) > seuil:
                    cls = "alert-r" if p > seuil else "alert-g"
                    icn = "📈" if p > 0 else "📉"
                    st.markdown(
                        f'<div class="{cls}">{icn} <b>{lbl}</b> — '
                        f'{fmt(vc)} → {fmt(vn_ann)} ann. '
                        f'({"+" if p>0 else ""}{fmt_pct(p)})</div>',
                        unsafe_allow_html=True
                    )

    # Graphique charges
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name=f"Ex. {annee} ann.", x=[p[0][:20] for p in postes],
        y=[annualiser(p[1],annee)/1000 for p in postes],
        marker_color=[p[3] for p in postes],
        text=[fmt(annualiser(p[1],annee)) for p in postes], textposition="outside"
    ))
    if kpi_c:
        fig.add_trace(go.Bar(
            name=f"Ex. {annee_c}", x=[p[0][:20] for p in postes],
            y=[p[2]/1000 for p in postes],
            marker_color=["rgba(55,138,221,0.4)","rgba(29,158,117,0.4)",
                          "rgba(186,117,23,0.4)","rgba(136,135,128,0.4)","rgba(216,90,48,0.4)"],
        ))
    fig.update_layout(barmode="group",height=300,margin=dict(t=20,b=0,l=0,r=0),
        legend=dict(orientation="h",y=1.1),
        plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(title="k€",gridcolor="#f0f0f0"))
    st.plotly_chart(fig, use_container_width=True, config=CFG)

    # Détail comptes charges
    with st.expander("📋 Détail des comptes de charges", expanded=False):
        for prefixe, label in [("60","Achats (60)"),("61","Services ext. (61)"),("64","Personnel (64)")]:
            detail = {n:c for n,c in comptes.items()
                      if n.startswith(prefixe) and (c["debit_mvt"]+c["credit_mvt"])>0}
            if detail:
                st.markdown(f"**{label}**")
                df_d = pd.DataFrame([{
                    "Compte": n,
                    "Intitulé": c["intitule"][:40],
                    "Débit": fmt(c["debit_mvt"],k=False),
                    "Crédit": fmt(c["credit_mvt"],k=False),
                    "Solde net": fmt(abs(c["solde_net"]),k=False),
                } for n,c in sorted(detail.items(), key=lambda x: -abs(x[1]["debit_mvt"]))])
                st.dataframe(df_d, use_container_width=True, hide_index=True)

# ─── ONGLET 5 : BFR & TRÉSO ────────────────────────────────
with tabs[4]:
    st.markdown('<div class="section-title">Ratios financiers clés</div>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5 = st.columns(5)
    ratios = [
        (c1,"Trésorerie",fmt(kpi["treso"]),delta_html(kpi["treso"],kpi_c.get("treso")),C["vert"]),
        (c2,"BFR",fmt(kpi["bfr"]),delta_html(kpi["bfr"],kpi_c.get("bfr"),inv=True),C["orange"]),
        (c3,"CAF",fmt(kpi["caf"]),delta_html(kpi["caf"],kpi_c.get("caf")),C["bleu"]),
        (c4,"BFR en jours",f"{kpi['bfr_jours']:.0f} j",delta_html(kpi["bfr_jours"],kpi_c.get("bfr_jours"),inv=True),C["orange"]),
        (c5,"DSO",f"{kpi['dso']:.0f} jours",delta_html(kpi["dso"],kpi_c.get("dso"),inv=True),C["rouge"]),
    ]
    for col,lbl,val,d,couleur in ratios:
        with col:
            st.markdown(f"""
            <div class="kpi-card" style="border-top:4px solid {couleur}">
                <div class="kpi-label">{lbl}</div>
                <div class="kpi-value">{val}</div>
                <div class="kpi-delta">{d}</div>
            </div>
            """, unsafe_allow_html=True)

    # Waterfall BFR
    st.markdown('<div class="section-title">Décomposition du BFR</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(kpi_card("Stocks (31/32/33)", fmt(kpi["stocks"],k=False)), unsafe_allow_html=True)
    with c2: st.markdown(kpi_card("+ Créances clients (411)", fmt(kpi["creances"],k=False)), unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("− Dettes fourn. (401)", f"−{fmt(kpi['dettes_f'],k=False)}"), unsafe_allow_html=True)
    with c4: st.markdown(kpi_card("= BFR", fmt(kpi["bfr"],k=False), delta_html(kpi["bfr"],kpi_c.get("bfr"),inv=True)), unsafe_allow_html=True)

    fig = go.Figure(go.Waterfall(
        orientation="v", measure=["absolute","relative","relative","total"],
        x=["Stocks","+ Créances","− Dettes fourn.","= BFR"],
        y=[kpi["stocks"],kpi["creances"],-kpi["dettes_f"],0],
        connector={"line":{"color":"#dee2e6"}},
        increasing={"marker":{"color":C["bleu"]}},
        decreasing={"marker":{"color":C["vert"]}},
        totals={"marker":{"color":C["orange"]}},
        texttemplate="%{y:,.0f} €", textposition="outside"
    ))
    fig.update_layout(height=260,margin=dict(t=10,b=0,l=0,r=0),
        plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#f0f0f0"))
    st.plotly_chart(fig, use_container_width=True, config=CFG)

    st.markdown("""
    <div style="font-size:11px;color:#8896a5;font-style:italic;background:white;
        padding:10px 14px;border-radius:8px;border:1px solid #e8ecf0;margin-top:8px">
    BFR = Stocks + Créances clients − Dettes fournisseurs &nbsp;|&nbsp;
    BFR en jours = BFR × 365 / CA HT &nbsp;|&nbsp;
    CAF = Résultat net + Dotations amortissements &nbsp;|&nbsp;
    FR disponible = Trésorerie − BFR
    </div>
    """, unsafe_allow_html=True)

    # Évolution 3 exercices
    annees_dispo = [a for a in ["2023","2024","2025"] if (DATA/f"balance_generale_{a}.xlsx").exists()]
    if len(annees_dispo) > 1:
        st.markdown('<div class="section-title">Évolution pluriannuelle (annualisé)</div>', unsafe_allow_html=True)
        kpis_g = {}
        for a in annees_dispo:
            cp, tt = lire_balance(a)
            if cp: kpis_g[a] = calculer_kpi(cp, tt)

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=annees_dispo,
            y=[annualiser(kpis_g[a]["ca"],a)/1000 for a in annees_dispo],
            mode="lines+markers+text",name="CA ann.",
            line=dict(color=C["bleu"],width=2),
            text=[fmt(annualiser(kpis_g[a]["ca"],a)) for a in annees_dispo],
            textposition="top center"))
        fig2.add_trace(go.Scatter(x=annees_dispo,
            y=[kpis_g[a]["treso"]/1000 for a in annees_dispo],
            mode="lines+markers+text",name="Trésorerie",
            line=dict(color=C["vert"],width=2),
            text=[fmt(kpis_g[a]["treso"]) for a in annees_dispo],
            textposition="top center"))
        fig2.add_trace(go.Scatter(x=annees_dispo,
            y=[annualiser(kpis_g[a]["bfr"],a)/1000 for a in annees_dispo],
            mode="lines+markers+text",name="BFR ann.",
            line=dict(color=C["orange"],width=2,dash="dot"),
            text=[fmt(annualiser(kpis_g[a]["bfr"],a)) for a in annees_dispo],
            textposition="bottom center"))
        fig2.update_layout(height=300,margin=dict(t=30,b=0,l=0,r=0),
            legend=dict(orientation="h",y=1.1),
            plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="k€",gridcolor="#f0f0f0"))
        st.plotly_chart(fig2, use_container_width=True, config=CFG)
