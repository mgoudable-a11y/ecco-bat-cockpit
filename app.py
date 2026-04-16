import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
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
    margin-bottom: 10px; cursor: pointer;
}
.kpi-card:hover { box-shadow: 0 3px 12px rgba(0,0,0,0.1); }
.kpi-label { font-size: 11px; font-weight: 600; text-transform: uppercase;
    letter-spacing: .06em; color: #8896a5; margin-bottom: 6px; }
.kpi-value { font-size: 26px; font-weight: 700; color: #1a2332; line-height: 1.1; }
.kpi-delta { font-size: 12px; margin-top: 4px; }
.kpi-sub { font-size: 11px; color: #adb5bd; margin-top: 3px; }
.section-title { font-size: 11px; font-weight: 700; text-transform: uppercase;
    letter-spacing: .1em; color: #8896a5; margin: 24px 0 12px;
    padding-bottom: 8px; border-bottom: 2px solid #e8ecf0; }
.alert-r { background:#fff5f5; border-left:4px solid #D85A30; border-radius:8px;
    padding:12px 16px; margin-bottom:8px; font-size:13px; color:#c53030; }
.alert-a { background:#fffbeb; border-left:4px solid #BA7517; border-radius:8px;
    padding:12px 16px; margin-bottom:8px; font-size:13px; color:#b7791f; }
.alert-g { background:#f0fff4; border-left:4px solid #1D9E75; border-radius:8px;
    padding:12px 16px; margin-bottom:8px; font-size:13px; color:#276749; }
.dp { color: #1D9E75; font-weight: 600; }
.dn { color: #D85A30; font-weight: 600; }
.stDataFrame { font-size: 12px; }
</style>
""", unsafe_allow_html=True)

# ─── UTILITAIRES ─────────────────────────────────────────
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
    return f'<span class="{cls}">{"▲" if p>0 else "▼"} {fmt_pct(abs(p))} vs N-1</span>'

def kpi_card(label, value, delta="", sub="", couleur=None):
    border = f"border-top:4px solid {couleur};" if couleur else ""
    return f"""<div class="kpi-card" style="{border}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        {"<div class='kpi-delta'>" + delta + "</div>" if delta else ""}
        {"<div class='kpi-sub'>" + sub + "</div>" if sub else ""}
    </div>"""

def norm_client(nom):
    nom = nom.strip()
    nom_u = nom.upper()
    if "PLURALIS" in nom_u: return "PLURALIS"
    if "ADVIVO" in nom_u: return "ADVIVO"
    if "GRANDLYON" in nom_u or "GRAND LYON" in nom_u: return "GRANDLYON HABITAT"
    if "ALLIADE" in nom_u: return "ALLIADE HABITAT"
    if "SEMCODA" in nom_u: return "SEMCODA"
    if "METROPOLE HABITAT" in nom_u: return "LYON METROPOLE HABITAT"
    if "CDC HABITAT" in nom_u: return "CDC HABITAT"
    if "DAUPHINOISE" in nom_u: return "SDH"
    if "DYNACITE" in nom_u: return "DYNACITE"
    if "CLINIQUE" in nom_u: return "CLINIQUE TRENEL"
    if "CHAPONNAY" in nom_u: return "MAIRIE DE CHAPONNAY"
    if "SAINT QUENTIN" in nom_u: return "SAINT QUENTIN IMMOBILIER"
    if "ARMÉE DU SALUT" in nom_u or "ARMEE DU SALUT" in nom_u: return "FONDATION ARMÉE DU SALUT"
    return re.sub(r'\s+RG\s+\d+.*$', '', re.sub(r'\s+\d+[,.]?\d*%.*$', '', nom)).strip()

def norm_fourn(nom):
    nom_u = nom.upper()
    if "FIMA" in nom_u: return "FIMA MENUISERIE"
    if "MALERBA" in nom_u: return "MALERBA"
    if "FARE MANA" in nom_u or "FAREMANA" in nom_u: return "FARE MANA"
    if "FRANCE FERMETURES" in nom_u: return "FRANCE FERMETURES"
    if "PROLIANS" in nom_u: return "PROLIANS QM"
    if "CIBOX" in nom_u: return "CIBOX"
    if "MONTGOLFIER" in nom_u: return "SCI MONTGOLFIER"
    if "SOMFU" in nom_u or "SOMALY" in nom_u: return "SOMALU"
    if "GROUPE SBTX" in nom_u or "SBTX" in nom_u: return "GROUPE SBTX"
    if "DEYA" in nom_u: return "DEYA"
    if "COULISS" in nom_u: return "COULISS"
    if "HORMANN" in nom_u: return "HORMANN"
    n = re.sub(r'\s+lcr.*$', '', nom, flags=re.IGNORECASE)
    n = re.sub(r'\s+fact.*$', '', n, flags=re.IGNORECASE)
    n = re.sub(r'\s+-\s+\d+.*$', '', n)
    return n.strip()[:30]

def jauge(val, min_v, max_v, titre, unite="%", couleur=None, val_comp=None):
    if couleur is None:
        p = (val-min_v)/max(max_v-min_v,1)
        couleur = C["vert"] if p>0.6 else (C["orange"] if p>0.3 else C["rouge"])
    comp_txt = ""
    if val_comp is not None:
        comp_txt = f"<br><span style='font-size:10px;color:#aaa'>N-1 : {val_comp:.1f}{unite}</span>"
    fig = go.Figure(go.Indicator(
        mode="gauge+number", value=round(val,1),
        number={"suffix":unite,"font":{"size":20}},
        title={"text":titre+comp_txt,"font":{"size":11}},
        gauge={"axis":{"range":[min_v,max_v]},"bar":{"color":couleur,"thickness":0.25},
               "bgcolor":"white","borderwidth":0,
               "steps":[{"range":[min_v,min_v+(max_v-min_v)*.4],"color":"#ffecec"},
                        {"range":[min_v+(max_v-min_v)*.4,min_v+(max_v-min_v)*.7],"color":"#fff8e6"},
                        {"range":[min_v+(max_v-min_v)*.7,max_v],"color":"#edf7f0"}]}
    ))
    fig.update_layout(height=200,margin=dict(t=40,b=0,l=10,r=10),paper_bgcolor="rgba(0,0,0,0)")
    return fig

def sante(kpi):
    s = sum([kpi["taux_marge"]>45, kpi["taux_rent"]>5,
             kpi["treso"]>0, kpi["bfr_jours"]<60, kpi["dso"]<45]) * 2
    if s>=8: return "😄","Excellente santé financière","#f0fff4","#38a169"
    if s>=6: return "😊","Bonne santé — points à surveiller","#f0fff4","#38a169"
    if s>=4: return "😐","Vigilance requise","#fffbeb","#d69e2e"
    return "😟","Points critiques à traiter","#fff5f5","#e53e3e"

# ─── LECTURE DONNÉES ──────────────────────────────────────
@st.cache_data
def lire_balance(annee):
    p = DATA / f"balance_generale_{annee}.xlsx"
    if not p.exists(): return {}, {}
    df = pd.read_excel(p, header=None, dtype=str)
    comptes, totaux = {}, {}
    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() not in ["","nan"]]
        if not vals: continue
        num = vals[0].replace(" ","")
        if not num or not num[0].isdigit(): continue
        montants, intitule = [], ""
        for v in vals[1:]:
            try: montants.append(float(v.replace(" ","").replace(",",".")))
            except:
                if not intitule and len(v)>2: intitule = v
        if not montants: continue
        if len(num) <= 2:
            totaux[num] = {"intitule":intitule,"debit":montants[0],"credit":montants[1] if len(montants)>1 else 0,"solde":montants[-1]}
        elif len(num) == 6 and len(montants) >= 2:
            comptes[num] = {"intitule":intitule,"debit":montants[0],"credit":montants[1],
                            "sd":max(montants[2],0) if len(montants)>2 else 0,
                            "sc":max(montants[3],0) if len(montants)>3 else 0}
    return comptes, totaux

@st.cache_data
def lire_analytique(annee):
    p = DATA / f"balance_analytique_{annee}.xlsx"
    if not p.exists(): return {}
    df = pd.read_excel(p, header=None, dtype=str)
    result = {}
    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() not in ["","nan"]]
        if len(vals) < 4 or vals[0] != "Total": continue
        code, label = vals[1], vals[2] if len(vals)>2 else vals[1]
        if code not in ["1","2","3"]: continue
        nums = []
        for v in vals[3:]:
            try: nums.append(float(v.replace(" ","").replace(",",".")))
            except: pass
        if len(nums) >= 2:
            charges, produits = nums[0], nums[1]
            result[code] = {"label":label,"charges":charges,"ca":produits,"marge":produits-charges,
                            "taux_marge":(produits-charges)/produits*100 if produits>0 else 0}
    return result

@st.cache_data
def lire_balance_agee(annee):
    p = DATA / f"balance_agee_clients_{annee}.xlsx"
    if not p.exists(): return {}
    df = pd.read_excel(p, header=None, dtype=str)
    clients = []
    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() not in ["","nan"]]
        if len(vals)<3 or vals[0] in ["Totaux","Total","% Période"]: continue
        if not vals[0].isdigit() and len(vals[0])>2:
            nums = []
            for v in vals[2:]:
                try: nums.append(float(v.replace(" ","").replace(",",".")))
                except: pass
            if nums and abs(nums[0])>0:
                clients.append({"nom":vals[1] if len(vals)>1 else vals[0],
                    "total":abs(nums[0]),"non_echu":abs(nums[1]) if len(nums)>1 else 0,
                    "j1_30":abs(nums[2]) if len(nums)>2 else 0,"j31_45":abs(nums[3]) if len(nums)>3 else 0,
                    "j46_60":abs(nums[4]) if len(nums)>4 else 0,"plus_61":abs(nums[5]) if len(nums)>5 else 0})
    return {"total":sum(c["total"] for c in clients),"non_echu":sum(c["non_echu"] for c in clients),
            "j1_30":sum(c["j1_30"] for c in clients),"j31_45":sum(c["j31_45"] for c in clients),
            "j46_60":sum(c["j46_60"] for c in clients),"plus_61":sum(c["plus_61"] for c in clients),
            "clients":sorted(clients,key=lambda x:-x["plus_61"])}

@st.cache_data
def lire_clients(annee):
    """Top clients depuis grand livre 411 - débit = factures émises TTC"""
    p = DATA / f"grand_livre_clients_{annee}.xlsx"
    if not p.exists(): return {}, {}
    df = pd.read_excel(p, header=None, dtype=str)
    clients, mensuel = {}, {}
    for _, row in df.iterrows():
        date_raw = str(row[0]).strip() if pd.notna(row[0]) else ""
        journal  = str(row[1]).strip() if pd.notna(row[1]) else ""
        libelle  = str(row[5]).strip() if pd.notna(row[5]) else ""
        debit_r  = str(row[12]).strip() if pd.notna(row[12]) else ""
        if not any(yr in date_raw for yr in ["2022","2023","2024","2025"]): continue
        if journal not in ["AD","VT","VL"]: continue
        if not libelle or libelle=="nan": continue
        if any(x in libelle for x in ["VIR SEPA","Règlement","PRLV","Ajust","écart","RG 5%","EFFET"]): continue
        try:
            debit = float(debit_r.replace(" ","").replace(",","."))
            if debit <= 100: continue
            nom = norm_client(libelle)
            clients[nom] = clients.get(nom,0) + debit
            mois_key = date_raw[:7]
            mensuel[mois_key] = mensuel.get(mois_key,0) + debit
        except: pass
    return clients, mensuel

@st.cache_data
def lire_fournisseurs(annee):
    """Top fournisseurs depuis grand livre 401 - crédit = factures reçues"""
    p = DATA / f"grand_livre_fournisseurs_{annee}.xlsx"
    if not p.exists(): return {}
    df = pd.read_excel(p, header=None, dtype=str)
    fourn = {}
    for _, row in df.iterrows():
        date_raw = str(row[0]).strip() if pd.notna(row[0]) else ""
        libelle  = str(row[5]).strip() if pd.notna(row[5]) else ""
        credit_r = str(row[15]).strip() if pd.notna(row[15]) else ""
        if not any(yr in date_raw for yr in ["2022","2023","2024","2025"]): continue
        if not libelle or libelle=="nan": continue
        if any(x in libelle.upper() for x in ["VIR SEPA","PRLV","EFFET","PAIEMENT"]): continue
        try:
            credit = float(credit_r.replace(" ","").replace(",","."))
            if credit <= 200: continue
            nom = norm_fourn(libelle)
            fourn[nom] = fourn.get(nom,0) + credit
        except: pass
    return fourn

def calculer_kpi(comptes, totaux):
    def get_solde(code): return totaux[code]["solde"] if code in totaux else 0
    def sc(p): return sum(c["sc"] for n,c in comptes.items() if n.startswith(p))
    def sd(p): return sum(c["sd"] for n,c in comptes.items() if n.startswith(p))
    ca           = abs(get_solde("70"))
    achats       = abs(get_solde("60"))
    services     = abs(get_solde("61"))
    autres       = abs(get_solde("62"))
    impots       = abs(get_solde("63"))
    charges_pers = abs(get_solde("64"))
    charges_exc  = abs(get_solde("65")) + abs(get_solde("67"))
    charges_fin  = abs(get_solde("66"))
    dotations    = abs(get_solde("68"))
    is_          = abs(get_solde("69"))
    charges_tot  = achats+services+autres+impots+charges_pers+charges_exc+charges_fin+dotations+is_
    res_t = totaux.get("12",{}).get("solde",0)
    resultat = abs(res_t) if abs(res_t)>1000 else max(ca-charges_tot,0)
    marge    = ca - achats
    stocks   = sd("31")+sd("32")+sd("33")
    creances = sd("411")
    dettes_f = sc("401")
    treso    = max(sum(c["sd"]-c["sc"] for n,c in comptes.items() if n.startswith("512") or n.startswith("531")),0)
    bfr      = stocks+creances-dettes_f
    return {
        "ca":ca,"marge":marge,"resultat":resultat,"charges_tot":charges_tot,
        "achats":achats,"services":services,"autres":autres,"impots":impots,
        "charges_pers":charges_pers,"dotations":dotations,"is_":is_,"charges_fin":charges_fin,
        "stocks":stocks,"creances":creances,"dettes_f":dettes_f,"treso":treso,"bfr":bfr,
        "caf":resultat+dotations,
        "taux_marge":marge/ca*100 if ca>0 else 0,
        "taux_rent":resultat/ca*100 if ca>0 else 0,
        "bfr_jours":bfr/ca*365 if ca>0 else 0,
        "dso":creances/ca*365 if ca>0 else 0,
        "couverture":treso/(charges_tot/12) if charges_tot>0 else 0,
        "_c70":{n:c for n,c in comptes.items() if n.startswith("70") and c["credit"]>0},
        "_c60":{n:c for n,c in comptes.items() if n.startswith("60") and (c["debit"]+c["credit"])>0},
        "_c64":{n:c for n,c in comptes.items() if n.startswith("64") and (c["debit"]+c["credit"])>0},
        "_c61":{n:c for n,c in comptes.items() if n.startswith("61") and (c["debit"]+c["credit"])>0},
        "_c411":{n:c for n,c in comptes.items() if n.startswith("411") and (c["sd"]+c["sc"])>0},
        "_c512":{n:c for n,c in comptes.items() if n.startswith("512") and (c["sd"]+c["sc"])>0},
    }

def show_detail(comptes_dict, titre):
    """Affiche le détail des comptes dans un expander"""
    with st.expander(f"📋 Détail — {titre}"):
        rows = []
        for num, c in sorted(comptes_dict.items()):
            rows.append({"Compte":num,"Intitulé":c["intitule"][:40],
                         "Débit":fmt(c["debit"],k=False),"Crédit":fmt(c["credit"],k=False)})
        if rows: st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)

# ─── SIDEBAR ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏗️ ECCO BAT")
    st.markdown("---")
    st.markdown("**Exercice à afficher**")
    annee = st.selectbox("exo",["2025","2024","2023"],
        format_func=lambda x: f"Ex. {x}  ({EXERCICES[x]['debut']} → {EXERCICES[x]['fin']})",
        label_visibility="collapsed")
    st.markdown("**Exercice en comparaison**")
    autres = [a for a in ["2025","2024","2023"] if a!=annee]
    comp_choix = st.selectbox("comp",["N-1 automatique"]+autres,label_visibility="collapsed")
    annee_c = str(int(annee)-1) if comp_choix=="N-1 automatique" else comp_choix
    mois = EXERCICES[annee]["mois"]
    if mois!=12: st.info(f"⚠️ Ex. {annee} = {mois} mois\nDonnées annualisées ×12/{mois}")
    st.markdown("---")
    st.markdown("### 🎯 Objectifs")
    obj_ca    = st.number_input("CA cible (k€)",    value=5000, step=100)
    obj_marge = st.number_input("Marge cible (k€)", value=2800, step=100)
    obj_treso = st.number_input("Tréso mini (k€)",  value=800,  step=50)
    obj_bfr   = st.number_input("BFR max (k€)",     value=400,  step=50)
    st.markdown("---")
    seuil = st.slider("Seuil alerte charges (%)",1,30,10,format="%d%%")

# ─── CHARGEMENT ───────────────────────────────────────────
comptes,  totaux   = lire_balance(annee)
comptes_c,totaux_c = lire_balance(annee_c) if annee_c in EXERCICES else ({},{})
agee               = lire_balance_agee(annee)
agee_c             = lire_balance_agee(annee_c) if annee_c in EXERCICES else {}
analytique         = lire_analytique(annee)
ana_c              = lire_analytique(annee_c) if annee_c in EXERCICES else {}
clients_d, mensuel = lire_clients(annee)
clients_c, _       = lire_clients(annee_c) if annee_c in EXERCICES else ({},{})
fourn              = lire_fournisseurs(annee)
fourn_c            = lire_fournisseurs(annee_c) if annee_c in EXERCICES else {}
kpi                = calculer_kpi(comptes,totaux) if comptes else {}
kpi_c              = calculer_kpi(comptes_c,totaux_c) if comptes_c else {}

if not kpi:
    st.error(f"Impossible de charger la balance {annee}.")
    st.stop()

# ─── EN-TÊTE ──────────────────────────────────────────────
st.markdown("## 🏗️ ECCO BAT — Cockpit Dirigeant")
emoji, texte, bg, bord = sante(kpi)
ca_ann = annualiser(kpi["ca"], annee)
ann_label = f"Annualisé ×12/{mois}" if mois!=12 else "12 mois"
st.markdown(f"""
<div style="background:{bg};border-left:5px solid {bord};border-radius:12px;
    padding:16px 22px;margin-bottom:20px;display:flex;align-items:center;gap:16px;
    box-shadow:0 1px 4px rgba(0,0,0,0.05)">
    <span style="font-size:40px">{emoji}</span>
    <div>
        <b style="font-size:17px">{texte}</b><br>
        <span style="font-size:12px;color:#555">
            CA {fmt(kpi['ca'])} · Annualisé {fmt(ca_ann)} ·
            Marge {fmt_pct(kpi['taux_marge'])} ·
            Résultat {fmt(kpi['resultat'])} ({fmt_pct(kpi['taux_rent'])}) ·
            Tréso {fmt(kpi['treso'])} · Ex. {annee} vs Ex. {annee_c}
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ─── 5 ONGLETS ────────────────────────────────────────────
tabs = st.tabs(["🏠 Cockpit","📈 CA & Clients","🔬 Analytique","🔔 Charges & Fourn.","💰 BFR & Tréso"])

# ══════════ ONGLET 1 : COCKPIT ═══════════════════════════
with tabs[0]:
    st.markdown('<div class="section-title">Jauges de santé</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.plotly_chart(jauge(kpi["taux_marge"],0,100,"Taux de marge",val_comp=kpi_c.get("taux_marge") if kpi_c else None),use_container_width=True,config=CFG)
    with c2: st.plotly_chart(jauge(kpi["taux_rent"],0,30,"Rentabilité nette",val_comp=kpi_c.get("taux_rent") if kpi_c else None),use_container_width=True,config=CFG)
    with c3: st.plotly_chart(jauge(min(kpi["couverture"],12),0,12,"Tréso (mois charges)",unite=" mois",val_comp=min(kpi_c.get("couverture",12),12) if kpi_c else None),use_container_width=True,config=CFG)
    with c4:
        bfj = kpi["bfr_jours"]
        col = C["vert"] if bfj<60 else C["rouge"]
        st.plotly_chart(jauge(bfj,0,90,"BFR en jours",unite="j",couleur=col,val_comp=kpi_c.get("bfr_jours") if kpi_c else None),use_container_width=True,config=CFG)

    st.markdown('<div class="section-title">KPI essentiels — cliquer pour voir le détail des comptes</div>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5,c6 = st.columns(6)

    with c1:
        sub = f"Annualisé : {fmt(ca_ann)}" if mois!=12 else ""
        st.markdown(kpi_card("CA réel",fmt(kpi["ca"]),delta_html(ca_ann,kpi_c.get("ca") if kpi_c else None),sub,C["bleu"]),unsafe_allow_html=True)
        show_detail(kpi["_c70"],"Comptes de ventes (70)")
    with c2:
        st.markdown(kpi_card("Marge brute",fmt(kpi["marge"]),delta_html(annualiser(kpi["marge"],annee),kpi_c.get("marge") if kpi_c else None),fmt_pct(kpi["taux_marge"]),C["vert"]),unsafe_allow_html=True)
        show_detail(kpi["_c60"],"Achats (60)")
    with c3:
        st.markdown(kpi_card("Résultat net",fmt(kpi["resultat"]),delta_html(annualiser(kpi["resultat"],annee),kpi_c.get("resultat") if kpi_c else None),fmt_pct(kpi["taux_rent"]),C["violet"]),unsafe_allow_html=True)
    with c4:
        st.markdown(kpi_card("Trésorerie",fmt(kpi["treso"]),delta_html(kpi["treso"],kpi_c.get("treso") if kpi_c else None),"",C["vert"]),unsafe_allow_html=True)
        show_detail(kpi["_c512"],"Comptes bancaires (512)")
    with c5:
        st.markdown(kpi_card("Créances clients",fmt(kpi["creances"]),delta_html(kpi["creances"],kpi_c.get("creances") if kpi_c else None,inv=True),f"DSO : {kpi['dso']:.0f}j",C["orange"]),unsafe_allow_html=True)
        show_detail(kpi["_c411"],"Comptes clients (411)")
    with c6:
        st.markdown(kpi_card("BFR",fmt(kpi["bfr"]),delta_html(kpi["bfr"],kpi_c.get("bfr") if kpi_c else None,inv=True),f"{kpi['bfr_jours']:.0f} jours",C["rouge"]),unsafe_allow_html=True)

    st.markdown('<div class="section-title">Suivi des objectifs</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    for col,lbl,reel,cible,inv,couleur in [
        (c1,"CA",kpi["ca"],obj_ca*1000,False,C["bleu"]),
        (c2,"Marge brute",kpi["marge"],obj_marge*1000,False,C["vert"]),
        (c3,"Trésorerie",kpi["treso"],obj_treso*1000,False,C["vert"]),
        (c4,"BFR max",kpi["bfr"],obj_bfr*1000,True,C["orange"]),
    ]:
        with col:
            pct = min(max(reel/cible*100 if cible>0 else 0,0),150)
            ok = (pct>=80 if not inv else pct<=100)
            bar_col = C["vert"] if ok else C["rouge"]
            st.markdown(f"""<div class="kpi-card" style="border-top:4px solid {couleur}">
                <div class="kpi-label">{lbl}</div>
                <div class="kpi-value">{fmt(reel)}</div>
                <div class="kpi-delta" style="color:#8896a5">{pct:.0f}% de l'objectif ({fmt(cible)})</div>
                <div style="background:#e8ecf0;border-radius:6px;height:6px;margin-top:8px;overflow:hidden">
                    <div style="width:{min(pct,100):.0f}%;height:100%;background:{bar_col};border-radius:6px"></div>
                </div></div>""",unsafe_allow_html=True)

    if agee and agee.get("plus_61",0)>0:
        st.markdown('<div class="section-title">🚨 Impayés critiques +61 jours</div>', unsafe_allow_html=True)
        for c in [x for x in agee.get("clients",[]) if x.get("plus_61",0)>500][:5]:
            st.markdown(f'<div class="alert-r">⚠️ <b>{c["nom"]}</b> — {fmt(c["plus_61"],k=False)} en retard +61j · Total dû : {fmt(c["total"],k=False)}</div>',unsafe_allow_html=True)

# ══════════ ONGLET 2 : CA & CLIENTS ══════════════════════
with tabs[1]:
    # CA mensuel
    if mensuel:
        st.markdown('<div class="section-title">CA mensuel (TTC, depuis grand livre clients)</div>', unsafe_allow_html=True)
        ordre_mois = [f"{y}-{m:02d}" for y in range(2022,2026) for m in range(1,13)]
        mois_pres = [m for m in ordre_mois if m in mensuel]
        vals_m = [mensuel[m] for m in mois_pres]
        moy = sum(vals_m)/len(vals_m) if vals_m else 0

        labels_fr = {"01":"Jan","02":"Fév","03":"Mar","04":"Avr","05":"Mai","06":"Jun",
                     "07":"Jul","08":"Aoû","09":"Sep","10":"Oct","11":"Nov","12":"Déc"}
        x_labels = [labels_fr.get(m.split("-")[1],m)+"-"+m.split("-")[0][-2:] for m in mois_pres]

        fig = go.Figure()
        fig.add_trace(go.Bar(x=x_labels,y=vals_m,name="CA mensuel TTC",
            marker_color=[C["rouge"] if v<moy*0.5 else C["vert"] if v>moy*1.5 else C["bleu"] for v in vals_m]))
        fig.add_trace(go.Scatter(x=x_labels,y=[moy]*len(mois_pres),mode="lines",
            line=dict(color=C["orange"],dash="dash",width=1.5),name=f"Moyenne {fmt(moy,k=False)}"))
        fig.update_layout(height=280,margin=dict(t=10,b=0,l=0,r=0),
            legend=dict(orientation="h",y=1.1),
            plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(gridcolor="#f0f0f0"))
        st.plotly_chart(fig,use_container_width=True,config=CFG)

    # Top 10 clients
    if clients_d:
        st.markdown('<div class="section-title">Top 10 clients</div>', unsafe_allow_html=True)
        top10 = sorted(clients_d.items(),key=lambda x:-x[1])[:10]
        total_cli = sum(v for _,v in clients_d.items())
        total_c_cli = sum(v for _,v in clients_c.items()) if clients_c else 0

        c1, c2 = st.columns([1,1])
        with c1:
            # Tableau
            rows = []
            for nom, v in top10:
                pct = v/total_cli*100 if total_cli>0 else 0
                v_c = clients_c.get(nom,0) if clients_c else 0
                var = f"+{fmt_pct((v-v_c)/v_c*100)}" if v_c>0 else "Nouveau"
                rows.append({"Client":nom,"CA TTC":fmt(v,k=False),"%":f"{pct:.1f}%","vs N-1":var})
            df_cli = pd.DataFrame(rows)
            st.dataframe(df_cli,use_container_width=True,hide_index=True)

        with c2:
            # Graphique horizontal
            noms = [n[:20] for n,_ in top10]
            vals = [v/1000 for _,v in top10]
            fig = go.Figure(go.Bar(y=noms[::-1],x=vals[::-1],orientation="h",
                marker_color=C["bleu"],text=[fmt(v*1000) for v in vals[::-1]],textposition="outside"))
            fig.update_layout(height=320,margin=dict(t=10,b=0,l=0,r=80),
                plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title="k€ TTC",gridcolor="#f0f0f0"))
            st.plotly_chart(fig,use_container_width=True,config=CFG)

        # Alerte concentration
        if top10:
            top1_pct = top10[0][1]/total_cli*100
            top3_pct = sum(v for _,v in top10[:3])/total_cli*100
            if top1_pct>20:
                st.markdown(f'<div class="alert-r">🚨 <b>{top10[0][0]}</b> = {fmt_pct(top1_pct)} du CA — risque dépendance critique</div>',unsafe_allow_html=True)
            if top3_pct>50:
                st.markdown(f'<div class="alert-a">⚠️ Top 3 clients = {fmt_pct(top3_pct)} du CA — diversification recommandée</div>',unsafe_allow_html=True)

    # Balance âgée
    if agee and agee.get("total",0)>0:
        st.markdown('<div class="section-title">Balance âgée clients</div>', unsafe_allow_html=True)
        total = agee["total"]
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1: st.markdown(kpi_card("Total créances",fmt(total)),unsafe_allow_html=True)
        with c2: st.markdown(kpi_card("Non échu",fmt(agee["non_echu"]),f"{agee['non_echu']/total*100:.0f}%"),unsafe_allow_html=True)
        with c3: st.markdown(kpi_card("1-30 jours",fmt(agee["j1_30"])),unsafe_allow_html=True)
        with c4:
            p61=agee["plus_61"]
            p61_c=agee_c.get("plus_61",0) if agee_c else 0
            st.markdown(kpi_card("⚠️ +61 jours",fmt(p61),delta_html(p61,p61_c,inv=True) if p61_c else "",f"{p61/total*100:.0f}%"),unsafe_allow_html=True)
        with c5: st.markdown(kpi_card("DSO",f"{kpi['dso']:.0f} jours"),unsafe_allow_html=True)

        retards=[c for c in agee["clients"] if c.get("plus_61",0)>100]
        if retards:
            df_r=pd.DataFrame([{"Client":c["nom"],"Total dû":fmt(c["total"],k=False),"+61j":fmt(c["plus_61"],k=False)} for c in retards])
            st.dataframe(df_r,use_container_width=True,hide_index=True)

# ══════════ ONGLET 3 : ANALYTIQUE ════════════════════════
with tabs[2]:
    if not analytique:
        st.info("Balance analytique non disponible.")
    else:
        st.markdown('<div class="section-title">Performance par activité (totaux de sections)</div>', unsafe_allow_html=True)
        acts = [k for k in analytique if k!="FG"]
        cols = st.columns(len(acts))
        for col, code in zip(cols, acts):
            data = analytique[code]
            ca_c_a = ana_c.get(code,{}).get("ca",0)
            couleur = C["vert"] if data["marge"]>0 else C["rouge"]
            with col:
                st.markdown(f"""<div class="kpi-card" style="border-top:4px solid {couleur}">
                    <div class="kpi-label">{data['label']}</div>
                    <div class="kpi-value">{fmt(data['ca'])}</div>
                    <div style="color:{couleur};font-size:13px;font-weight:600;margin-top:4px">
                        Marge {fmt(data['marge'])} ({fmt_pct(data['taux_marge'])})
                    </div>
                    {"<div class='kpi-delta'>" + delta_html(annualiser(data['ca'],annee),ca_c_a) + "</div>" if ca_c_a else ""}
                </div>""",unsafe_allow_html=True)

        # Détails par activité
        for code in acts:
            data = analytique[code]
            ca_c_a = ana_c.get(code,{}).get("ca",0)
            mg_c_a = ana_c.get(code,{}).get("marge",0)
            with st.expander(f"📊 Détail — {data['label']}", expanded=False):
                c1,c2,c3,c4 = st.columns(4)
                with c1:
                    st.metric("CA",fmt(data["ca"]))
                    if ca_c_a: st.markdown(delta_html(annualiser(data["ca"],annee),ca_c_a),unsafe_allow_html=True)
                with c2: st.metric("Charges directes",fmt(data["charges"]))
                with c3:
                    st.metric("Marge",fmt(data["marge"]))
                    if mg_c_a: st.markdown(delta_html(annualiser(data["marge"],annee),mg_c_a),unsafe_allow_html=True)
                with c4: st.metric("Taux de marge",fmt_pct(data["taux_marge"]))

        if ana_c:
            st.markdown('<div class="section-title">Comparatif N vs N-1 annualisé</div>', unsafe_allow_html=True)
            fig = go.Figure()
            fig.add_trace(go.Bar(name=f"CA {annee} ann.",x=[analytique[a]["label"] for a in acts],
                y=[annualiser(analytique[a]["ca"],annee)/1000 for a in acts],marker_color=C["bleu"]))
            fig.add_trace(go.Bar(name=f"CA {annee_c}",x=[analytique[a]["label"] for a in acts],
                y=[ana_c.get(a,{}).get("ca",0)/1000 for a in acts],marker_color="#85B7EB"))
            fig.add_trace(go.Bar(name=f"Marge {annee} ann.",x=[analytique[a]["label"] for a in acts],
                y=[annualiser(analytique[a]["marge"],annee)/1000 for a in acts],marker_color=C["vert"]))
            fig.add_trace(go.Bar(name=f"Marge {annee_c}",x=[analytique[a]["label"] for a in acts],
                y=[ana_c.get(a,{}).get("marge",0)/1000 for a in acts],marker_color="#9FE1CB"))
            fig.update_layout(barmode="group",height=300,margin=dict(t=10,b=0,l=0,r=0),
                legend=dict(orientation="h",y=1.1),
                plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(title="k€",gridcolor="#f0f0f0"))
            st.plotly_chart(fig,use_container_width=True,config=CFG)

# ══════════ ONGLET 4 : CHARGES & FOURNISSEURS ════════════
with tabs[3]:
    # Structure charges
    st.markdown('<div class="section-title">Structure des charges</div>', unsafe_allow_html=True)
    postes = [
        ("Achats & matières (60)",kpi["achats"],kpi_c.get("achats",0) if kpi_c else 0,C["bleu"]),
        ("Personnel (64)",kpi["charges_pers"],kpi_c.get("charges_pers",0) if kpi_c else 0,C["vert"]),
        ("Services ext. (61)",kpi["services"],kpi_c.get("services",0) if kpi_c else 0,C["orange"]),
        ("Autres charges (62)",kpi["autres"],kpi_c.get("autres",0) if kpi_c else 0,C["gris"]),
        ("IS (69)",kpi["is_"],kpi_c.get("is_",0) if kpi_c else 0,C["rouge"]),
    ]
    cols = st.columns(len(postes))
    for col,(lbl,vn,vc,couleur) in zip(cols,postes):
        vn_ann = annualiser(vn,annee)
        d = delta_html(vn_ann,vc,inv=True) if vc else ""
        pct_ca = vn_ann/annualiser(kpi["ca"],annee)*100 if kpi["ca"]>0 else 0
        with col:
            st.markdown(f"""<div class="kpi-card" style="border-top:4px solid {couleur}">
                <div class="kpi-label">{lbl}</div>
                <div class="kpi-value">{fmt(vn)}</div>
                <div class="kpi-delta">{d}</div>
                <div class="kpi-sub">{fmt_pct(pct_ca)} du CA</div>
            </div>""",unsafe_allow_html=True)

    with st.expander("📋 Détail comptes de charges"):
        for pref, lab in [("60","Achats (60)"),("61","Services (61)"),("64","Personnel (64)")]:
            detail = {n:c for n,c in comptes.items() if n.startswith(pref) and (c["debit"]+c["credit"])>0}
            if detail:
                st.markdown(f"**{lab}**")
                st.dataframe(pd.DataFrame([{"Compte":n,"Intitulé":c["intitule"][:40],"Débit":fmt(c["debit"],k=False),"Crédit":fmt(c["credit"],k=False)} for n,c in sorted(detail.items(),key=lambda x:-x[1]["debit"])]),use_container_width=True,hide_index=True)

    # Alertes charges
    if kpi_c:
        st.markdown('<div class="section-title">Alertes variations charges N vs N-1</div>', unsafe_allow_html=True)
        for lbl,vn,vc,_ in postes:
            if vc>0:
                p = (annualiser(vn,annee)-vc)/vc*100
                if abs(p)>seuil:
                    cls = "alert-r" if p>seuil else "alert-g"
                    icn = "📈" if p>0 else "📉"
                    st.markdown(f'<div class="{cls}">{icn} <b>{lbl}</b> — {fmt(vc)} → {fmt(annualiser(vn,annee))} ann. ({"+" if p>0 else ""}{fmt_pct(p)})</div>',unsafe_allow_html=True)

    # Top 10 fournisseurs
    if fourn:
        st.markdown('<div class="section-title">Top 10 fournisseurs</div>', unsafe_allow_html=True)
        top10f = sorted(fourn.items(),key=lambda x:-x[1])[:10]
        total_f = sum(v for _,v in fourn.items())
        c1,c2 = st.columns([1,1])
        with c1:
            rows = []
            for nom,v in top10f:
                vc = fourn_c.get(nom,0)
                var = f"+{fmt_pct((annualiser(v,annee)-vc)/vc*100)}" if vc>0 else "Nouveau"
                rows.append({"Fournisseur":nom,"Facturé":fmt(v,k=False),"%":f"{v/total_f*100:.1f}%","vs N-1":var})
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True)
        with c2:
            noms_f = [n[:20] for n,_ in top10f]
            vals_f = [v/1000 for _,v in top10f]
            vals_c_f = [fourn_c.get(n,0)/1000 for n,_ in top10f]
            fig = go.Figure()
            fig.add_trace(go.Bar(name=annee,y=noms_f[::-1],x=vals_f[::-1],orientation="h",marker_color=C["bleu"]))
            if any(v>0 for v in vals_c_f):
                fig.add_trace(go.Bar(name=annee_c,y=noms_f[::-1],x=vals_c_f[::-1],orientation="h",marker_color="#85B7EB"))
            fig.update_layout(barmode="group",height=320,margin=dict(t=10,b=0,l=0,r=80),
                legend=dict(orientation="h",y=1.1),
                plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title="k€",gridcolor="#f0f0f0"))
            st.plotly_chart(fig,use_container_width=True,config=CFG)

# ══════════ ONGLET 5 : BFR & TRÉSO ═══════════════════════
with tabs[4]:
    st.markdown('<div class="section-title">Ratios financiers clés</div>', unsafe_allow_html=True)
    c1,c2,c3,c4,c5 = st.columns(5)
    with c1: st.markdown(kpi_card("Trésorerie",fmt(kpi["treso"]),delta_html(kpi["treso"],kpi_c.get("treso") if kpi_c else None),"",C["vert"]),unsafe_allow_html=True)
    with c2: st.markdown(kpi_card("BFR",fmt(kpi["bfr"]),delta_html(kpi["bfr"],kpi_c.get("bfr") if kpi_c else None,inv=True),f"{kpi['bfr_jours']:.0f} jours",C["orange"]),unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("CAF",fmt(kpi["caf"]),delta_html(annualiser(kpi["caf"],annee),kpi_c.get("caf") if kpi_c else None),"",C["bleu"]),unsafe_allow_html=True)
    with c4: st.markdown(kpi_card("FR disponible",fmt(kpi["treso"]-kpi["bfr"]),"","Tréso − BFR",C["violet"]),unsafe_allow_html=True)
    with c5: st.markdown(kpi_card("DSO",f"{kpi['dso']:.0f} jours",delta_html(kpi["dso"],kpi_c.get("dso") if kpi_c else None,inv=True),"",C["rouge"]),unsafe_allow_html=True)

    st.markdown('<div class="section-title">Décomposition du BFR</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.markdown(kpi_card("Stocks (31/32/33)",fmt(kpi["stocks"],k=False)),unsafe_allow_html=True)
    with c2: st.markdown(kpi_card("+ Créances (411)",fmt(kpi["creances"],k=False)),unsafe_allow_html=True)
    with c3: st.markdown(kpi_card("− Dettes fourn. (401)",f"−{fmt(kpi['dettes_f'],k=False)}"),unsafe_allow_html=True)
    with c4: st.markdown(kpi_card("= BFR",fmt(kpi["bfr"],k=False),delta_html(kpi["bfr"],kpi_c.get("bfr") if kpi_c else None,inv=True)),unsafe_allow_html=True)

    fig = go.Figure(go.Waterfall(
        orientation="v",measure=["absolute","relative","relative","total"],
        x=["Stocks","+ Créances","− Dettes fourn.","= BFR"],
        y=[kpi["stocks"],kpi["creances"],-kpi["dettes_f"],0],
        connector={"line":{"color":"#dee2e6"}},
        increasing={"marker":{"color":C["bleu"]}},
        decreasing={"marker":{"color":C["vert"]}},
        totals={"marker":{"color":C["orange"]}},
        texttemplate="%{y:,.0f} €",textposition="outside"
    ))
    fig.update_layout(height=260,margin=dict(t=10,b=0,l=0,r=0),
        plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#f0f0f0"))
    st.plotly_chart(fig,use_container_width=True,config=CFG)

    # Évolution pluriannuelle — UNIQUEMENT les exercices complets disponibles
    annees_dispo = [a for a in ["2023","2024","2025"] if (DATA/f"balance_generale_{a}.xlsx").exists()]
    if len(annees_dispo) >= 2:
        st.markdown('<div class="section-title">Évolution pluriannuelle (annualisé)</div>', unsafe_allow_html=True)

        kpis_g = {}
        for a in annees_dispo:
            cp, tt = lire_balance(a)
            if cp: kpis_g[a] = calculer_kpi(cp,tt)

        # Données par exercice (pas de demi-exercice)
        x_vals = list(kpis_g.keys())  # ["2023","2024","2025"]
        ca_g   = [annualiser(kpis_g[a]["ca"],a)/1000   for a in x_vals]
        mg_g   = [annualiser(kpis_g[a]["marge"],a)/1000 for a in x_vals]
        tr_g   = [kpis_g[a]["treso"]/1000              for a in x_vals]
        bfr_g  = [annualiser(kpis_g[a]["bfr"],a)/1000  for a in x_vals]
        res_g  = [annualiser(kpis_g[a]["resultat"],a)/1000 for a in x_vals]

        x_labels = [f"Ex. {a}" for a in x_vals]

        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=x_labels,y=ca_g,mode="lines+markers+text",name="CA ann.",
            line=dict(color=C["bleu"],width=2),
            text=[fmt(v*1000) for v in ca_g],textposition="top center",textfont=dict(size=10)))
        fig2.add_trace(go.Scatter(x=x_labels,y=mg_g,mode="lines+markers+text",name="Marge brute ann.",
            line=dict(color=C["vert"],width=2),
            text=[fmt(v*1000) for v in mg_g],textposition="top center",textfont=dict(size=10)))
        fig2.add_trace(go.Scatter(x=x_labels,y=tr_g,mode="lines+markers+text",name="Trésorerie",
            line=dict(color=C["violet"],width=2),
            text=[fmt(v*1000) for v in tr_g],textposition="bottom center",textfont=dict(size=10)))
        fig2.add_trace(go.Scatter(x=x_labels,y=res_g,mode="lines+markers+text",name="Résultat net ann.",
            line=dict(color=C["orange"],width=2,dash="dot"),
            text=[fmt(v*1000) for v in res_g],textposition="bottom center",textfont=dict(size=10)))

        fig2.update_layout(height=320,margin=dict(t=30,b=0,l=0,r=0),
            legend=dict(orientation="h",y=1.1),
            plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="k€",gridcolor="#f0f0f0"),
            xaxis=dict(categoryorder="array",categoryarray=x_labels))
        st.plotly_chart(fig2,use_container_width=True,config=CFG)

    st.markdown("""<div style="font-size:11px;color:#8896a5;font-style:italic;background:white;
        padding:10px 14px;border-radius:8px;border:1px solid #e8ecf0;margin-top:8px">
        BFR = Stocks + Créances clients − Dettes fournisseurs &nbsp;|&nbsp;
        BFR en jours = BFR × 365 / CA &nbsp;|&nbsp;
        CAF = Résultat net + Dotations &nbsp;|&nbsp;
        FR = Trésorerie − BFR &nbsp;|&nbsp;
        DSO = Créances × 365 / CA
    </div>""",unsafe_allow_html=True)
