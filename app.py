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

C = {"bleu":"#378ADD","vert":"#1D9E75","orange":"#BA7517","rouge":"#D85A30","gris":"#888780"}

st.markdown("""
<style>
.main{background:#f8f9fa}
.sh{font-size:10px;font-weight:600;text-transform:uppercase;letter-spacing:.08em;
    color:#6c757d;margin:20px 0 10px;padding-bottom:5px;border-bottom:1px solid #e9ecef}
.al-r{background:#fff5f5;border-left:4px solid #D85A30;border-radius:6px;padding:10px 14px;margin-bottom:6px;font-size:13px;color:#c53030}
.al-a{background:#fffbeb;border-left:4px solid #BA7517;border-radius:6px;padding:10px 14px;margin-bottom:6px;font-size:13px;color:#b7791f}
.al-g{background:#f0fff4;border-left:4px solid #1D9E75;border-radius:6px;padding:10px 14px;margin-bottom:6px;font-size:13px;color:#276749}
.dp{color:#1D9E75;font-size:12px;font-weight:500}
.dn{color:#D85A30;font-size:12px;font-weight:500}
</style>
""", unsafe_allow_html=True)

@st.cache_data
def lire_balance(annee):
    p = DATA / f"balance_generale_{annee}.xlsx"
    if not p.exists():
        return {}
    df = pd.read_excel(p, header=None, dtype=str)
    comptes = {}
    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() not in ["","nan"]]
        if not vals: continue
        premier = vals[0].replace(" ","")
        if not premier or not premier[0].isdigit(): continue
        num = premier[:6]
        montants = []
        intitule = ""
        for v in vals[1:]:
            try:
                montants.append(float(v.replace(" ","").replace(",",".")))
            except:
                if not intitule and len(v) > 2: intitule = v
        if len(montants) >= 2:
            sd = montants[2] if len(montants) > 2 else 0
            sc = montants[3] if len(montants) > 3 else 0
            comptes[num] = {"intitule": intitule, "sd": sd, "sc": sc}
    return comptes

@st.cache_data
def lire_balance_agee(annee):
    p = DATA / f"balance_agee_clients_{annee}.xlsx"
    if not p.exists(): return {}
    df = pd.read_excel(p, header=None, dtype=str)
    clients = []
    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() not in ["","nan"]]
        if len(vals) < 3: continue
        if vals[0] in ["Totaux","Total","% Période"]: continue
        if not vals[0].isdigit() and len(vals[0]) > 2:
            nums = []
            for v in vals[2:]:
                try: nums.append(float(v.replace(" ","").replace(",",".")))
                except: pass
            if nums and nums[0] > 0:
                clients.append({
                    "nom": vals[1] if len(vals) > 1 else vals[0],
                    "total": nums[0] if len(nums) > 0 else 0,
                    "non_echu": nums[1] if len(nums) > 1 else 0,
                    "j1_30": nums[2] if len(nums) > 2 else 0,
                    "j31_45": nums[3] if len(nums) > 3 else 0,
                    "j46_60": nums[4] if len(nums) > 4 else 0,
                    "plus_61": nums[5] if len(nums) > 5 else 0,
                })
    return {
        "total": sum(c["total"] for c in clients),
        "non_echu": sum(c["non_echu"] for c in clients),
        "j1_30": sum(c["j1_30"] for c in clients),
        "plus_61": sum(c["plus_61"] for c in clients),
        "clients": clients
    }

def calculer_kpi(comptes):
    def sc(p): return sum(c["sc"] for n,c in comptes.items() if n.startswith(p))
    def sd(p): return sum(c["sd"] for n,c in comptes.items() if n.startswith(p))
    ca = sc("70") if sc("70") > 0 else sd("70")
    achats = max(sd("60")-sc("60"),0)
    charges_pers = max(sd("64")-sc("64"),0)
    services = sd("61"); autres = sd("62")
    impots = sd("63"); dotations = sd("68"); is_ = max(sd("69")-sc("69"),0)
    charges_tot = achats+charges_pers+services+autres+impots+dotations+is_
    resultat = sc("120") if sc("120") > 0 else ca - charges_tot
    marge = ca - achats
    stocks = sum(c["sd"] for n,c in comptes.items() if n.startswith("31") and c["sd"]>0)
    creances = sum(c["sd"] for n,c in comptes.items() if n.startswith("411") and c["sd"]>0)
    dettes_f = sum(c["sc"] for n,c in comptes.items() if n.startswith("401") and c["sc"]>0)
    treso = sum(c["sd"]-c["sc"] for n,c in comptes.items() if n.startswith("512") or n.startswith("531"))
    treso = max(treso,0)
    bfr = stocks + creances - dettes_f
    return {
        "ca":ca,"marge":marge,"resultat":resultat,"charges_tot":charges_tot,
        "achats":achats,"charges_pers":charges_pers,"services":services,"dotations":dotations,"is_":is_,
        "stocks":stocks,"creances":creances,"dettes_f":dettes_f,"treso":treso,"bfr":bfr,
        "taux_marge":marge/ca*100 if ca>0 else 0,
        "taux_rent":resultat/ca*100 if ca>0 else 0,
        "bfr_jours":bfr/ca*365 if ca>0 else 0,
        "dso":creances/ca*365 if ca>0 else 0,
        "couverture":treso/(charges_tot/12) if charges_tot>0 else 0,
        "caf":resultat+dotations,
    }

def annualiser(v, annee):
    m = EXERCICES.get(annee,{}).get("mois",12)
    return v * 12 / m if m != 12 else v

def fmt(v, k=True):
    if k: return f"{v/1000:,.1f} k€"
    return f"{v:,.0f} €"

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

def sante(kpi):
    s = sum([kpi["taux_marge"]>45, kpi["taux_rent"]>5, kpi["treso"]>0, kpi["bfr_jours"]<60, kpi["dso"]<45]) * 2
    if s >= 8: return "😄","Excellente santé financière","#f0fff4","#38a169"
    if s >= 6: return "😊","Bonne santé — points à surveiller","#f0fff4","#38a169"
    if s >= 4: return "😐","Vigilance requise","#fffbeb","#d69e2e"
    return "😟","Points critiques à traiter","#fff5f5","#e53e3e"

def delta(vn, vc, inv=False):
    if not vc or vc == 0: return ""
    p = (vn-vc)/abs(vc)*100
    bon = p>0 if not inv else p<0
    cls = "dp" if bon else "dn"
    return f'<span class="{cls}">{"▲" if p>0 else "▼"} {abs(p):.1f}% vs N-1</span>'

# ── SIDEBAR ─────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏗️ ECCO BAT")
    st.markdown("---")
    annee = st.selectbox("Exercice", ["2025","2024","2023"],
        format_func=lambda x: f"Ex. {x} ({EXERCICES[x]['debut']} → {EXERCICES[x]['fin']})")
    annee_c = str(int(annee)-1)
    st.markdown("---")
    st.markdown("### 🎯 Objectifs")
    obj_ca    = st.number_input("CA cible (k€)",    value=5000, step=100)
    obj_marge = st.number_input("Marge cible (k€)", value=2800, step=100)
    obj_treso = st.number_input("Tréso mini (k€)",  value=800,  step=50)
    obj_bfr   = st.number_input("BFR max (k€)",     value=400,  step=50)
    st.markdown("---")
    seuil = st.slider("Seuil alerte fournisseurs", 1, 30, 5, format="%d%%")

# ── CHARGEMENT ───────────────────────────────────────────
comptes = lire_balance(annee)
comptes_c = lire_balance(annee_c) if annee_c in EXERCICES else {}
agee = lire_balance_agee(annee)
kpi = calculer_kpi(comptes) if comptes else {}
kpi_c = calculer_kpi(comptes_c) if comptes_c else {}

if not kpi:
    st.error(f"Impossible de charger la balance {annee}. Vérifiez le dossier data/")
    st.stop()

mois = EXERCICES[annee]["mois"]

# ── EN-TÊTE ───────────────────────────────────────────────
st.markdown("## 🏗️ ECCO BAT — Cockpit Dirigeant")
emoji, texte, bg, bord = sante(kpi)
note = f" · Données annualisées ×12/{mois}" if mois != 12 else ""
st.markdown(f"""
<div style="background:{bg};border-left:5px solid {bord};border-radius:10px;
    padding:14px 20px;margin-bottom:20px;display:flex;align-items:center;gap:14px">
    <span style="font-size:36px">{emoji}</span>
    <div>
        <b style="font-size:16px">{texte}</b><br>
        <span style="font-size:12px;color:#555">
            Marge {kpi['taux_marge']:.1f}% · Rentabilité {kpi['taux_rent']:.1f}% ·
            Tréso {fmt(kpi['treso'])} · BFR {kpi['bfr_jours']:.0f}j{note}
        </span>
    </div>
</div>
""", unsafe_allow_html=True)

# ── 5 ONGLETS ────────────────────────────────────────────
tabs = st.tabs(["🏠 Cockpit","📈 CA & Clients","🔬 Analytique","🔔 Fournisseurs","💰 BFR & Tréso"])

# ─── ONGLET 1 : COCKPIT ───────────────────────────────────
with tabs[0]:
    st.markdown('<div class="sh">Jauges de santé</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.plotly_chart(jauge(kpi["taux_marge"],0,100,"Taux de marge"), use_container_width=True),config={"displayModeBar": False}
    with c2: st.plotly_chart(jauge(kpi["taux_rent"],0,30,"Rentabilité nette"), use_container_width=True),config={"displayModeBar": False}
    with c3: st.plotly_chart(jauge(min(kpi["couverture"],12),0,12,"Tréso (mois)",unite=" mois"), use_container_width=True),config={"displayModeBar": False}
    with c4:
        col = C["vert"] if kpi["bfr_jours"]<60 else C["rouge"]
        st.plotly_chart(jauge(kpi["bfr_jours"],0,90,"BFR en jours",unite="j",couleur=col), use_container_width=True),config={"displayModeBar": False}

    st.markdown('<div class="sh">KPI essentiels</div>', unsafe_allow_html=True)
    cols = st.columns(6)
    items = [
        ("CA", kpi["ca"], kpi_c.get("ca"), False),
        ("Marge brute", kpi["marge"], kpi_c.get("marge"), False),
        ("Résultat net", kpi["resultat"], kpi_c.get("resultat"), False),
        ("Trésorerie", kpi["treso"], kpi_c.get("treso"), False),
        ("Créances", kpi["creances"], kpi_c.get("creances"), True),
        ("BFR", kpi["bfr"], kpi_c.get("bfr"), True),
    ]
    for col,(lbl,vn,vc,inv) in zip(cols,items):
        with col:
            st.metric(lbl, fmt(vn))
            if vc: st.markdown(delta(annualiser(vn,annee), vc, inv), unsafe_allow_html=True)

    st.markdown('<div class="sh">Objectifs</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    for col,lbl,reel,cible,inv in [
        (c1,"CA",kpi["ca"],obj_ca*1000,False),
        (c2,"Marge",kpi["marge"],obj_marge*1000,False),
        (c3,"Trésorerie",kpi["treso"],obj_treso*1000,False),
        (c4,"BFR max",kpi["bfr"],obj_bfr*1000,True),
    ]:
        with col:
            pct = min(reel/cible*100 if cible>0 else 0,150)
            st.metric(lbl, fmt(reel), f"{pct:.0f}% objectif")
            st.progress(max(0.0, min(pct/100, 1.0)))

    if agee and agee.get("plus_61",0) > 0:
        st.markdown('<div class="sh">🚨 Impayés +61 jours</div>', unsafe_allow_html=True)
        for c in sorted([x for x in agee.get("clients",[]) if x.get("plus_61",0)>500], key=lambda x:-x["plus_61"])[:5]:
            st.markdown(f'<div class="al-r">⚠️ <b>{c["nom"]}</b> — {fmt(c["plus_61"],k=False)} en retard +61j</div>', unsafe_allow_html=True)

# ─── ONGLET 2 : CA & CLIENTS ───────────────────────────────
with tabs[1]:
    if agee:
        st.markdown('<div class="sh">Balance âgée clients</div>', unsafe_allow_html=True)
        total = agee.get("total",0)
        c1,c2,c3,c4,c5 = st.columns(5)
        with c1: st.metric("Total créances", fmt(total))
        with c2: st.metric("Non échu", fmt(agee.get("non_echu",0)), f"{agee.get('non_echu',0)/total*100:.0f}%" if total else "")
        with c3: st.metric("1-30 jours", fmt(agee.get("j1_30",0)))
        with c4: st.metric("+61 jours ⚠️", fmt(agee.get("plus_61",0)),
                           f"{agee.get('plus_61',0)/total*100:.0f}%" if total else "", delta_color="inverse")
        with c5: st.metric("DSO estimé", f"{kpi['dso']:.0f} jours")

        retards = sorted([c for c in agee.get("clients",[]) if c.get("plus_61",0)>200], key=lambda x:-x["plus_61"])
        if retards:
            st.markdown('<div class="sh">Clients en retard +61j</div>', unsafe_allow_html=True)
            df_r = pd.DataFrame([{"Client":c["nom"],"Total dû":f"{c['total']:,.0f} €","+61j":f"{c['plus_61']:,.0f} €"} for c in retards])
            st.dataframe(df_r, use_container_width=True, hide_index=True)
    else:
        st.info("Chargez la balance âgée clients pour voir les impayés.")

# ─── ONGLET 3 : ANALYTIQUE ────────────────────────────────
with tabs[2]:
    st.info("Balance analytique — à venir dans la prochaine version.")

# ─── ONGLET 4 : FOURNISSEURS ───────────────────────────────
with tabs[3]:
    st.markdown('<div class="sh">Principaux postes d\'achat</div>', unsafe_allow_html=True)
    postes = {
        "Achats matières (60)": kpi["achats"],
        "Personnel (64)": kpi["charges_pers"],
        "Services ext. (61)": kpi["services"],
        "Dotations (68)": kpi["dotations"],
        "IS (69)": kpi["is_"],
    }
    fig = go.Figure(go.Bar(
        x=list(postes.keys()),
        y=[v/1000 for v in postes.values()],
        marker_color=[C["bleu"],C["vert"],C["orange"],C["gris"],C["rouge"]],
        text=[fmt(v) for v in postes.values()],
        textposition="outside"
    ))
    fig.update_layout(height=320, margin=dict(t=10,b=0,l=0,r=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(title="k€", gridcolor="#f0f0f0"))
    st.plotly_chart(fig, use_container_width=True)

    if kpi_c:
        st.markdown('<div class="sh">Comparatif N vs N-1</div>', unsafe_allow_html=True)
        postes_c = {"Achats":kpi_c.get("achats",0),"Personnel":kpi_c.get("charges_pers",0),"Services":kpi_c.get("services",0)}
        postes_n = {"Achats":kpi["achats"],"Personnel":kpi["charges_pers"],"Services":kpi["services"]}
        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name=annee, x=list(postes_n.keys()), y=[v/1000 for v in postes_n.values()], marker_color=C["bleu"]))
        fig2.add_trace(go.Bar(name=annee_c, x=list(postes_c.keys()), y=[v/1000 for v in postes_c.values()], marker_color="#85B7EB"))
        fig2.update_layout(barmode="group", height=280, margin=dict(t=10,b=0,l=0,r=0),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="k€", gridcolor="#f0f0f0"))
        st.plotly_chart(fig2, use_container_width=True)

# ─── ONGLET 5 : BFR & TRÉSO ────────────────────────────────
with tabs[4]:
    st.markdown('<div class="sh">BFR — Besoin en Fonds de Roulement</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1: st.metric("Stocks", fmt(kpi["stocks"],k=False))
    with c2: st.metric("+ Créances", fmt(kpi["creances"],k=False))
    with c3: st.metric("− Dettes fourn.", f"−{fmt(kpi['dettes_f'],k=False)}")
    with c4:
        st.metric("= BFR", fmt(kpi["bfr"],k=False))
        if kpi_c: st.markdown(delta(kpi["bfr"], kpi_c.get("bfr"), inv=True), unsafe_allow_html=True)

    fig = go.Figure(go.Waterfall(
        orientation="v", measure=["absolute","relative","relative","total"],
        x=["Stocks","+ Créances","− Dettes","= BFR"],
        y=[kpi["stocks"],kpi["creances"],-kpi["dettes_f"],0],
        connector={"line":{"color":"#dee2e6"}},
        increasing={"marker":{"color":C["bleu"]}},
        decreasing={"marker":{"color":C["vert"]}},
        totals={"marker":{"color":C["orange"]}},
        texttemplate="%{y:,.0f} €", textposition="outside"
    ))
    fig.update_layout(height=260, margin=dict(t=10,b=0,l=0,r=0),
        plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
        yaxis=dict(gridcolor="#f0f0f0"))
    st.plotly_chart(fig, use_container_width=True)

    st.markdown('<div class="sh">Ratios financiers</div>', unsafe_allow_html=True)
    c1,c2,c3,c4 = st.columns(4)
    with c1:
        st.metric("Trésorerie", fmt(kpi["treso"]))
        if kpi_c: st.markdown(delta(kpi["treso"], kpi_c.get("treso")), unsafe_allow_html=True)
    with c2:
        st.metric("BFR en jours", f"{kpi['bfr_jours']:.0f} j")
        if kpi_c: st.markdown(delta(kpi["bfr_jours"], kpi_c.get("bfr_jours"), inv=True), unsafe_allow_html=True)
    with c3:
        st.metric("CAF", fmt(kpi["caf"]))
        if kpi_c: st.markdown(delta(kpi["caf"], kpi_c.get("caf")), unsafe_allow_html=True)
    with c4:
        st.metric("DSO", f"{kpi['dso']:.0f} jours")
        if kpi_c: st.markdown(delta(kpi["dso"], kpi_c.get("dso"), inv=True), unsafe_allow_html=True)

    if kpi_c:
        st.markdown('<div class="sh">Évolution sur 3 exercices</div>', unsafe_allow_html=True)
        annees_g = [a for a in ["2023","2024","2025"] if lire_balance(a)]
        ca_g = [annualiser(calculer_kpi(lire_balance(a))["ca"],a)/1000 for a in annees_g]
        tr_g = [calculer_kpi(lire_balance(a))["treso"]/1000 for a in annees_g]
        bfr_g = [annualiser(calculer_kpi(lire_balance(a))["bfr"],a)/1000 for a in annees_g]
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(x=annees_g, y=ca_g, mode="lines+markers", name="CA ann.", line=dict(color=C["bleu"],width=2)))
        fig2.add_trace(go.Scatter(x=annees_g, y=tr_g, mode="lines+markers", name="Trésorerie", line=dict(color=C["vert"],width=2)))
        fig2.add_trace(go.Scatter(x=annees_g, y=bfr_g, mode="lines+markers", name="BFR ann.", line=dict(color=C["orange"],width=2,dash="dot")))
        fig2.update_layout(height=260, margin=dict(t=10,b=0,l=0,r=0),
            legend=dict(orientation="h",y=1.1),
            plot_bgcolor="rgba(0,0,0,0)", paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="k€", gridcolor="#f0f0f0"))
        st.plotly_chart(fig2, use_container_width=True)
