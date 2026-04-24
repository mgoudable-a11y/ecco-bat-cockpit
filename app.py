import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from pathlib import Path

st.set_page_config(page_title="ECCO BAT", page_icon="🏗️", layout="wide")
ROOT = Path(__file__).parent
DATA = ROOT / "data"

EXERCICES = {
    "2025": {"debut":"01/10/2024","fin":"31/12/2025","mois":15},
    "2024": {"debut":"01/10/2023","fin":"30/09/2024","mois":12},
    "2023": {"debut":"01/10/2022","fin":"30/09/2023","mois":12},
}
C = {"bleu":"#378ADD","vert":"#1D9E75","orange":"#BA7517","rouge":"#D85A30","gris":"#888780","violet":"#7F77DD"}
CFG = {"displayModeBar":False}

st.markdown("""
<style>
.main{background:#f4f6f9}
.block-container{padding-top:1rem}
.kpi-card{
    background:white;border-radius:12px;padding:18px 20px;
    border:1px solid #e8ecf0;box-shadow:0 1px 4px rgba(0,0,0,0.05);
    margin-bottom:6px;cursor:pointer;transition:all 0.2s;
    height:140px;display:flex;flex-direction:column;justify-content:space-between;
}
.kpi-card:hover{box-shadow:0 4px 16px rgba(0,0,0,0.12);transform:translateY(-2px)}
.kpi-card.active{border:2px solid #378ADD;box-shadow:0 4px 16px rgba(55,138,221,0.2)}
.kpi-icon{font-size:20px;margin-bottom:2px}
.kpi-label{font-size:10px;font-weight:600;text-transform:uppercase;
    letter-spacing:.06em;color:#8896a5;margin-bottom:2px}
.kpi-value{font-size:22px;font-weight:700;color:#1a2332;line-height:1.1}
.kpi-delta{font-size:11px;margin-top:2px}
.kpi-sub{font-size:11px;color:#adb5bd}
.section-title{font-size:11px;font-weight:700;text-transform:uppercase;
    letter-spacing:.1em;color:#8896a5;margin:24px 0 12px;
    padding-bottom:8px;border-bottom:2px solid #e8ecf0}
.alert-r{background:#fff5f5;border-left:4px solid #D85A30;border-radius:8px;padding:12px 16px;margin-bottom:8px;font-size:13px;color:#c53030}
.alert-a{background:#fffbeb;border-left:4px solid #BA7517;border-radius:8px;padding:12px 16px;margin-bottom:8px;font-size:13px;color:#b7791f}
.dp{color:#1D9E75;font-weight:600}
.dn{color:#D85A30;font-weight:600}
.panel{background:white;border-radius:12px;padding:24px;border:2px solid #378ADD;
    box-shadow:0 8px 32px rgba(55,138,221,0.15);margin:12px 0 20px}
.panel-title{font-size:15px;font-weight:600;color:#1a2332;margin-bottom:16px;
    padding-bottom:8px;border-bottom:2px solid #e8ecf0}
/* Bouton invisible sous les KPI */
.kpi-btn-hidden {
    position: absolute;
    top: 0; left: 0; right: 0; bottom: 0;
    background: transparent;
    border: none;
    cursor: pointer;
    z-index: 10;
    width: 100%;
    height: 100%;
}
div[data-testid="stButton"] button {
    background: transparent !important;
    border: none !important;
    color: transparent !important;
    height: 2px !important;
    min-height: 2px !important;
    padding: 0 !important;
    margin: 0 !important;
    box-shadow: none !important;
    font-size: 1px !important;
}
.kpi-hint { display: none !important; }
</style>
""", unsafe_allow_html=True)

def fmt(v, k=True):
    if k:
        n=v/1000
        s=f"{abs(n):,.1f}".replace(",","X").replace(".",",").replace("X"," ")
        return ("-" if n<0 else "")+s+" k€"
    s=f"{abs(v):,.0f}".replace(",", " ")
    return ("-" if v<0 else "")+s+" €"

def fmt_pct(v):
    return ("-" if v<0 else "")+f"{abs(v):.1f}".replace(".",",")+"%"

def annualiser(v, annee):
    m=EXERCICES.get(annee,{}).get("mois",12)
    return v*12/m if m!=12 else v

def delta_html(vn, vc, inv=False):
    if not vc or vc==0: return ""
    p=(vn-vc)/abs(vc)*100
    bon=p>0 if not inv else p<0
    cls="dp" if bon else "dn"
    return f'<span class="{cls}">{"▲" if p>0 else "▼"} {fmt_pct(abs(p))} vs N-1</span>'

def norm_client(nom):
    nom_u=nom.upper()
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
    n=re.sub(r'\s+RG\s+\d+.*$','',nom).strip()
    return re.sub(r'\s+\d+[,.]?\d*%.*$','',n).strip()

def norm_fourn(nom):
    nom_u=nom.upper()
    if "FIMA" in nom_u: return "FIMA MENUISERIE"
    if "MALERBA" in nom_u: return "MALERBA"
    if "FARE MANA" in nom_u or "FAREMANA" in nom_u: return "FARE MANA"
    if "FRANCE FERMETURES" in nom_u: return "FRANCE FERMETURES"
    if "PROLIANS" in nom_u: return "PROLIANS QM"
    if "MONTGOLFIER" in nom_u: return "SCI MONTGOLFIER"
    if "SBTX" in nom_u: return "GROUPE SBTX"
    if "DEYA" in nom_u: return "DEYA"
    if "COULISS" in nom_u: return "COULISS"
    if "HORMANN" in nom_u: return "HORMANN"
    n=re.sub(r'\s+lcr.*$','',nom,flags=re.IGNORECASE)
    return re.sub(r'\s+-\s+\d+.*$','',n).strip()[:30]

def jauge(val, min_v, max_v, titre, unite="%", couleur=None, val_comp=None,
          seuils=None, mieux_si_haut=True, val_eur=None):
    if val_comp is not None:
        mieux = val > val_comp if mieux_si_haut else val < val_comp
        couleur_val = "#1D9E75" if mieux else "#D85A30"
        coul_comp = "#1D9E75" if mieux else "#D85A30"
        comp_str = f"N-1 : {val_comp:.1f}{unite}"
    else:
        mieux = True
        couleur_val = "#1D9E75"
        comp_str = ""
        coul_comp = "#888"
    if couleur is None:
        couleur = couleur_val
    if seuils is None: seuils = [0.4, 0.7]
    s0, s1 = seuils

    # Titre en noir fixe + valeur k€ + N-1 EN DESSOUS du k€
    sous_titre = ""
    if val_eur:
        sous_titre += f"<span style=\'font-size:12px;color:#333\'>{val_eur}</span>"
    if comp_str:
        sous_titre += f"<br><b><span style=\'font-size:11px;color:{coul_comp}\'>{comp_str}</span></b>"

    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=round(val, 1),
        number={
            "suffix": unite,
            "font": {"size": 28, "color": couleur_val},
            "valueformat": ".1f",
        },
        title={
            "text": f"<span style=\'color:#1a2332;font-weight:600\'>{titre}</span><br>{sous_titre}",
            "font": {"size": 11},
        },
        gauge={
            "axis": {"range": [min_v, max_v], "tickwidth": 1, "tickcolor": "#ddd",
                     "tickfont": {"size": 9}},
            "bar": {"color": couleur, "thickness": 0.35},
            "bgcolor": "white", "borderwidth": 0,
            "steps": [
                {"range": [min_v, min_v + (max_v - min_v) * s0], "color": "#FFEAEA"},
                {"range": [min_v + (max_v - min_v) * s0, min_v + (max_v - min_v) * s1], "color": "#FFF3CD"},
                {"range": [min_v + (max_v - min_v) * s1, max_v], "color": "#D4EDDA"},
            ],
            "threshold": {"line": {"color": couleur, "width": 4}, "thickness": 0.8, "value": val}
        }
    ))
    # Hauteur fixe + domain pour aligner les pieds des jauges
    fig.update_layout(
        height=240,
        margin=dict(t=10, b=10, l=10, r=10),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    fig.update_traces(domain={"x": [0, 1], "y": [0, 0.72]})
    return fig

def jauge_verticale(pct, label, valeur_str, valeur_keur):
    """Thermomètre vertical avec graduation % et valeur k€"""
    pct_c = min(pct, 100)
    if pct < 50:   couleur, bg = "#D85A30", "#FFF5F5"
    elif pct < 80: couleur, bg = "#BA7517", "#FFFBEB"
    else:           couleur, bg = "#1D9E75", "#F0FFF4"

    fig = go.Figure()

    # Fond gris (100%)
    fig.add_trace(go.Bar(
        x=[""], y=[100],
        marker_color="#E8ECF0", width=0.4,
        showlegend=False, hoverinfo="skip"
    ))
    # Remplissage coloré - sans texte dans la barre
    fig.add_trace(go.Bar(
        x=[""], y=[pct_c],
        marker_color=couleur, width=0.4,
        showlegend=False,
        hovertemplate=f"{label}: {pct:.0f}%<extra></extra>"
    ))
    # Ligne objectif 100%
    fig.add_hline(y=100, line_color="#555", line_dash="dot", line_width=1.5)

    # Annotation % EN DEHORS de la barre, tout en haut
    y_annot = pct_c + 6 if pct_c < 90 else pct_c - 10
    fig.add_annotation(
        x=0, y=y_annot,
        text=f"<b>{pct:.0f}%</b>",
        showarrow=False,
        font=dict(size=16, color=couleur),
        xanchor="center", yanchor="bottom"
    )

    fig.update_layout(
        height=230,
        margin=dict(t=55, b=5, l=35, r=10),
        plot_bgcolor=bg,
        paper_bgcolor="rgba(0,0,0,0)",
        barmode="overlay",
        yaxis=dict(
            range=[0, 115],
            tickvals=[0, 25, 50, 75, 100],
            ticktext=["0%", "25%", "50%", "75%", "100%"],
            tickfont=dict(size=9, color="#888"),
            gridcolor="#e8ecf0", gridwidth=1,
            showgrid=True, zeroline=False,
        ),
        xaxis=dict(showticklabels=False),
        title=dict(
            text=f"<b style='color:#1a2332'>{label}</b><br>"
                 f"<span style='font-size:13px;font-weight:700;color:{couleur}'>{valeur_keur}</span>",
            font=dict(size=12), x=0.5, xanchor="center",
            pad=dict(t=0)
        ),
    )
    return fig

def sante(kpi):
    s=sum([kpi["taux_marge"]>45,kpi["taux_rent"]>5,
           kpi["treso"]>0,kpi["bfr_jours"]<60,kpi["dso"]<45])*2
    if s>=8: return "😄","Excellente santé financière","#f0fff4","#38a169"
    if s>=6: return "😊","Bonne santé — points à surveiller","#f0fff4","#38a169"
    if s>=4: return "😐","Vigilance requise","#fffbeb","#d69e2e"
    return "😟","Points critiques à traiter","#fff5f5","#e53e3e"

@st.cache_data
def lire_balance(annee):
    p=DATA/f"balance_generale_{annee}.xlsx"
    if not p.exists(): return {},{}
    df=pd.read_excel(p,header=None,dtype=str)
    comptes,totaux={},{}
    for _,row in df.iterrows():
        vals=[str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() not in ["","nan"]]
        if not vals: continue
        num=vals[0].replace(" ","")
        if not num or not num[0].isdigit(): continue
        montants,intitule=[],""
        for v in vals[1:]:
            try: montants.append(float(v.replace(" ","").replace(",",".")))
            except:
                if not intitule and len(v)>2: intitule=v
        if not montants: continue
        if len(num)<=2:
            totaux[num]={"intitule":intitule,"debit":montants[0],
                         "credit":montants[1] if len(montants)>1 else 0,"solde":montants[-1]}
        elif len(num)==6 and len(montants)>=2:
            comptes[num]={"intitule":intitule,"debit":montants[0],"credit":montants[1],
                          "sd":max(montants[2],0) if len(montants)>2 else 0,
                          "sc":max(montants[3],0) if len(montants)>3 else 0}
    return comptes,totaux

@st.cache_data
def lire_analytique(annee):
    p=DATA/f"balance_analytique_{annee}.xlsx"
    if not p.exists(): return {}
    df=pd.read_excel(p,header=None,dtype=str)
    result={}
    for _,row in df.iterrows():
        vals=[str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() not in ["","nan"]]
        if len(vals)<4 or vals[0]!="Total": continue
        code=vals[1]
        if code not in ["1","2","3"]: continue
        label=vals[2]
        nums=[]
        for v in vals[3:]:
            try: nums.append(float(v.replace(" ","").replace(",",".")))
            except: pass
        if len(nums)>=2:
            charges,produits=nums[0],nums[1]
            result[code]={"label":label,"charges":charges,"ca":produits,
                          "marge":produits-charges,
                          "taux_marge":(produits-charges)/produits*100 if produits>0 else 0}
    return result

@st.cache_data
def lire_balance_agee(annee):
    p=DATA/f"balance_agee_clients_{annee}.xlsx"
    if not p.exists(): return {}
    df=pd.read_excel(p,header=None,dtype=str)
    clients=[]
    for _,row in df.iterrows():
        vals=[str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() not in ["","nan"]]
        if len(vals)<3 or vals[0] in ["Totaux","Total","% Période"]: continue
        if not vals[0].isdigit() and len(vals[0])>2:
            nums=[]
            for v in vals[2:]:
                try: nums.append(float(v.replace(" ","").replace(",",".")))
                except: pass
            if nums and abs(nums[0])>0:
                clients.append({"nom":vals[1] if len(vals)>1 else vals[0],
                    "total":abs(nums[0]),"non_echu":abs(nums[1]) if len(nums)>1 else 0,
                    "j1_30":abs(nums[2]) if len(nums)>2 else 0,
                    "j31_45":abs(nums[3]) if len(nums)>3 else 0,
                    "j46_60":abs(nums[4]) if len(nums)>4 else 0,
                    "plus_61":abs(nums[5]) if len(nums)>5 else 0})
    return {"total":sum(c["total"] for c in clients),
            "non_echu":sum(c["non_echu"] for c in clients),
            "j1_30":sum(c["j1_30"] for c in clients),
            "j31_45":sum(c["j31_45"] for c in clients),
            "j46_60":sum(c["j46_60"] for c in clients),
            "plus_61":sum(c["plus_61"] for c in clients),
            "clients":sorted(clients,key=lambda x:-x["plus_61"])}

@st.cache_data
def lire_clients(annee):
    p=DATA/f"grand_livre_clients_{annee}.xlsx"
    if not p.exists(): return {},{}
    df=pd.read_excel(p,header=None,dtype=str)
    clients_ttc,mensuel_ttc={},{}
    for _,row in df.iterrows():
        date_raw=str(row[0]).strip() if pd.notna(row[0]) else ""
        journal=str(row[1]).strip() if pd.notna(row[1]) else ""
        libelle=str(row[5]).strip() if pd.notna(row[5]) else ""
        debit_r=str(row[12]).strip() if pd.notna(row[12]) else ""
        if not any(yr in date_raw for yr in ["2022","2023","2024","2025"]): continue
        if journal not in ["AD","VT","VL"]: continue
        if not libelle or libelle=="nan": continue
        if any(x in libelle for x in ["VIR SEPA","Règlement","PRLV","Ajust","écart","RG 5%","EFFET"]): continue
        try:
            debit=float(debit_r.replace(" ","").replace(",","."))
            if debit<=100: continue
            nom=norm_client(libelle)
            clients_ttc[nom]=clients_ttc.get(nom,0)+debit
            mois_key=date_raw[:7]
            mensuel_ttc[mois_key]=mensuel_ttc.get(mois_key,0)+debit
        except: pass
    total_ttc=sum(clients_ttc.values())
    ca_ht=abs(lire_balance(annee)[1].get("70",{}).get("solde",total_ttc))
    coef=ca_ht/total_ttc if total_ttc>0 else 1.0
    return {k:v*coef for k,v in clients_ttc.items()},{k:v*coef for k,v in mensuel_ttc.items()}

@st.cache_data
def lire_fournisseurs(annee):
    p=DATA/f"grand_livre_fournisseurs_{annee}.xlsx"
    if not p.exists(): return {}
    df=pd.read_excel(p,header=None,dtype=str)
    fourn={}
    for _,row in df.iterrows():
        date_raw=str(row[0]).strip() if pd.notna(row[0]) else ""
        libelle=str(row[5]).strip() if pd.notna(row[5]) else ""
        credit_r=str(row[15]).strip() if pd.notna(row[15]) else ""
        if not any(yr in date_raw for yr in ["2022","2023","2024","2025"]): continue
        if not libelle or libelle=="nan": continue
        if any(x in libelle.upper() for x in ["VIR SEPA","PRLV","EFFET","PAIEMENT"]): continue
        try:
            credit=float(credit_r.replace(" ","").replace(",","."))
            if credit<=200: continue
            nom=norm_fourn(libelle)
            fourn[nom]=fourn.get(nom,0)+credit
        except: pass
    return fourn

def calculer_kpi(comptes,totaux):
    def gs(c): return totaux[c]["solde"] if c in totaux else 0
    def sc(p): return sum(c["sc"] for n,c in comptes.items() if n.startswith(p))
    def sd(p): return sum(c["sd"] for n,c in comptes.items() if n.startswith(p))
    ca=abs(gs("70")); achats=abs(gs("60")); services=abs(gs("61"))
    autres=abs(gs("62")); impots=abs(gs("63")); charges_pers=abs(gs("64"))
    dotations=abs(gs("68")); is_=abs(gs("69"))
    charges_fin=abs(gs("66"))+abs(gs("67"))
    charges_tot=achats+services+autres+impots+charges_pers+dotations+is_+charges_fin
    res_t=totaux.get("12",{}).get("solde",0)
    resultat=abs(res_t) if abs(res_t)>1000 else max(ca-charges_tot,0)
    ebe=ca-achats-charges_pers-services-autres-impots
    rex=ebe-dotations; marge=ca-achats
    stocks=sd("31")+sd("32")+sd("33"); creances=sd("411"); dettes_f=sc("401")
    treso=max(sum(c["sd"]-c["sc"] for n,c in comptes.items()
               if n.startswith("512") or n.startswith("531")),0)
    bfr=stocks+creances-dettes_f
    detail={}
    for pref in ["70","60","61","62","63","64","68","69","411","512","401"]:
        detail[pref]={n:c for n,c in comptes.items()
                      if n.startswith(pref) and (c["debit"]+c["credit"])>0}
    return {"ca":ca,"marge":marge,"resultat":resultat,"ebe":ebe,"rex":rex,
            "charges_tot":charges_tot,"achats":achats,"services":services,
            "autres":autres,"impots":impots,"charges_pers":charges_pers,
            "dotations":dotations,"is_":is_,"charges_fin":charges_fin,
            "stocks":stocks,"creances":creances,"dettes_f":dettes_f,
            "treso":treso,"bfr":bfr,"caf":resultat+dotations,
            "taux_marge":marge/ca*100 if ca>0 else 0,
            "taux_rent":resultat/ca*100 if ca>0 else 0,
            "taux_ebe":ebe/ca*100 if ca>0 else 0,
            "taux_rex":rex/ca*100 if ca>0 else 0,
            "bfr_jours":bfr/ca*365 if ca>0 else 0,
            "dso":creances/ca*365 if ca>0 else 0,
            "couverture":treso/(charges_tot/12) if charges_tot>0 else 0,
            "detail":detail}

def panel_detail(titre, comptes_dict, annee, comptes_c_dict=None, couleur=C["bleu"]):
    mois=EXERCICES.get(annee,{}).get("mois",12)
    st.markdown(f'<div class="panel"><div class="panel-title">📋 {titre}</div>',
                unsafe_allow_html=True)
    rows=[]
    for num,c in sorted(comptes_dict.items(),
        key=lambda x:-max(x[1]["debit"],x[1]["credit"],x[1].get("sd",0),x[1].get("sc",0))):
        val_n=max(c["debit"],c["credit"],c.get("sd",0),c.get("sc",0))
        val_n_ann=annualiser(val_n,annee)
        val_c=0
        if comptes_c_dict and num in comptes_c_dict:
            cc=comptes_c_dict[num]
            val_c=max(cc["debit"],cc["credit"],cc.get("sd",0),cc.get("sc",0))
        row={"Compte":num,"Intitulé":c["intitule"][:50],"Montant N":fmt(val_n,k=False)}
        if mois!=12: row["Annualisé"]=fmt(val_n_ann,k=False)
        if val_c>0:
            p=(val_n_ann-val_c)/val_c*100
            row["N-1"]=fmt(val_c,k=False)
            row["Variation"]=("🔴 +" if p>5 else "🟢 " if p<-5 else "⚪ ")+fmt_pct(p)
        rows.append(row)
    if rows:
        df_d=pd.DataFrame(rows)
        st.dataframe(df_d,use_container_width=True,hide_index=True,
                    height=min(len(rows)*38+50,500))
    st.markdown('</div>',unsafe_allow_html=True)
    if st.button("✕ Fermer le détail",key=f"close_{titre[:15]}"):
        st.session_state["panel_ouvert"]=None
        st.rerun()

def panel_variations(titre, annee, annee_c, prefixe, couleur=C["bleu"]):
    cp,_=lire_balance(annee)
    cp_c,_=lire_balance(annee_c) if annee_c in EXERCICES else ({},)
    mois=EXERCICES.get(annee,{}).get("mois",12)
    tous=set(list(cp.keys())+list(cp_c.keys()))
    variations=[]
    for num in tous:
        if not num.startswith(prefixe): continue
        vn=max(cp.get(num,{}).get("debit",0),cp.get(num,{}).get("credit",0))*12/mois
        vc=max(cp_c.get(num,{}).get("debit",0),cp_c.get(num,{}).get("credit",0))
        intitule=cp.get(num,cp_c.get(num,{})).get("intitule","")
        if vc>500:
            p=(vn-vc)/vc*100
            variations.append({"num":num,"intitule":intitule,"vn":vn,"vc":vc,"p":p})
    st.markdown(f'<div class="panel"><div class="panel-title">📊 {titre} — Top variations N vs N-1</div>',
                unsafe_allow_html=True)
    hausses=sorted(variations,key=lambda x:-x["p"])[:10]
    baisses=sorted(variations,key=lambda x:x["p"])[:10]
    c1,c2=st.columns(2)
    with c1:
        st.markdown("#### 📈 Hausses")
        if hausses:
            st.dataframe(pd.DataFrame([{"Compte":v["num"],"Intitulé":v["intitule"][:45],
                f"Ex.{annee} ann.":fmt(v["vn"],k=False),f"Ex.{annee_c}":fmt(v["vc"],k=False),
                "Variation":f"+{fmt_pct(v['p'])}"} for v in hausses]),
                use_container_width=True,hide_index=True,height=380)
    with c2:
        st.markdown("#### 📉 Baisses")
        if baisses:
            st.dataframe(pd.DataFrame([{"Compte":v["num"],"Intitulé":v["intitule"][:45],
                f"Ex.{annee} ann.":fmt(v["vn"],k=False),f"Ex.{annee_c}":fmt(v["vc"],k=False),
                "Variation":fmt_pct(v["p"])} for v in baisses]),
                use_container_width=True,hide_index=True,height=380)
    st.markdown('</div>',unsafe_allow_html=True)
    if st.button("✕ Fermer",key=f"close_var_{prefixe}"):
        st.session_state["panel_ouvert"]=None
        st.rerun()

if "panel_ouvert" not in st.session_state:
    st.session_state["panel_ouvert"]=None

# ── SIDEBAR ───────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🏗️ ECCO BAT")
    st.markdown("---")
    st.markdown("**Exercice à afficher**")
    annee=st.selectbox("exo",["2025","2024","2023"],
        format_func=lambda x:f"Ex. {x}  ({EXERCICES[x]['debut']} → {EXERCICES[x]['fin']})",
        label_visibility="collapsed")
    st.markdown("**Exercice en comparaison**")
    autres=[a for a in ["2025","2024","2023"] if a!=annee]
    comp_choix=st.selectbox("comp",["N-1 automatique"]+autres,label_visibility="collapsed")
    annee_c=str(int(annee)-1) if comp_choix=="N-1 automatique" else comp_choix
    mois=EXERCICES[annee]["mois"]
    if mois!=12: st.info(f"⚠️ Ex. {annee} = {mois} mois\nAnnualisé ×12/{mois}")
    st.markdown("---")
    st.markdown("### 🎯 Objectifs")
    obj_ca    = st.number_input("CA cible (k€)",    value=5000, step=100)
    obj_marge = st.number_input("Marge cible (k€)", value=2800, step=100)
    obj_treso = st.number_input("Tréso mini (k€)",  value=800,  step=50)
    obj_bfr   = st.number_input("BFR max (k€)",     value=400,  step=50)
    st.markdown("---")
    st.markdown("### ⚙️ Seuils jauges")
    s_mg  = [st.slider("Marge bas (%)",   0,100,40)/100, st.slider("Marge haut (%)",  0,100,60)/100]
    s_rt  = [st.slider("Rent. bas (%)",   0,30,5)/30,    st.slider("Rent. haut (%)",  0,30,12)/30]
    s_ebe = [st.slider("EBE bas (%)",     0,40,10)/40,   st.slider("EBE haut (%)",    0,40,20)/40]
    seuil_charges=st.slider("Alerte charges (%)",1,30,10,format="%d%%")

# ── CHARGEMENT ────────────────────────────────────────────
comptes,totaux     = lire_balance(annee)
comptes_c,totaux_c = lire_balance(annee_c) if annee_c in EXERCICES else ({},{})
agee               = lire_balance_agee(annee)
agee_c             = lire_balance_agee(annee_c) if annee_c in EXERCICES else {}
analytique         = lire_analytique(annee)
ana_c              = lire_analytique(annee_c) if annee_c in EXERCICES else {}
clients_d,mensuel  = lire_clients(annee)
clients_c,_        = lire_clients(annee_c) if annee_c in EXERCICES else ({},{})
fourn              = lire_fournisseurs(annee)
fourn_c            = lire_fournisseurs(annee_c) if annee_c in EXERCICES else {}
kpi                = calculer_kpi(comptes,totaux) if comptes else {}
kpi_c              = calculer_kpi(comptes_c,totaux_c) if comptes_c else {}

if not kpi:
    st.error(f"Impossible de charger la balance {annee}.")
    st.stop()

ca_ann=annualiser(kpi["ca"],annee)

# ── EN-TÊTE ───────────────────────────────────────────────
st.markdown("## 🏗️ ECCO BAT — Cockpit Dirigeant")
emoji,texte,bg,bord=sante(kpi)
st.markdown(f"""
<div style="background:{bg};border-left:5px solid {bord};border-radius:12px;
    padding:16px 22px;margin-bottom:20px;display:flex;align-items:center;gap:16px;
    box-shadow:0 1px 4px rgba(0,0,0,0.05)">
    <span style="font-size:40px">{emoji}</span>
    <div>
        <b style="font-size:17px">{texte}</b><br>
        <span style="font-size:12px;color:#555">
            CA {fmt(kpi['ca'])} ({fmt(ca_ann)} ann.) ·
            Marge {fmt_pct(kpi['taux_marge'])} · EBE {fmt_pct(kpi['taux_ebe'])} ·
            Résultat {fmt(kpi['resultat'])} ({fmt_pct(kpi['taux_rent'])}) ·
            Tréso {fmt(kpi['treso'])} · Ex. {annee} vs Ex. {annee_c}
        </span>
    </div>
</div>
""",unsafe_allow_html=True)

tabs=st.tabs(["🏠 Cockpit","📈 CA & Clients","🔬 Analytique","🔔 Charges & Fourn.","💰 BFR & Tréso"])

# ══ ONGLET 1 : COCKPIT ════════════════════════════════════
with tabs[0]:

    # ── Jauges ──────────────────────────────────────────
    st.markdown('<div class="section-title">Jauges de santé</div>',unsafe_allow_html=True)
    c1,c2,c3,c4,c5=st.columns(5)
    with c1: st.plotly_chart(jauge(kpi["taux_marge"],0,100,"Taux de marge",seuils=s_mg,
        val_comp=kpi_c.get("taux_marge") if kpi_c else None,mieux_si_haut=True,
        val_eur=fmt(kpi["marge"])),
        use_container_width=True,config=CFG)
    with c2: st.plotly_chart(jauge(kpi["taux_rent"],0,30,"Rentabilité nette",seuils=s_rt,
        val_comp=kpi_c.get("taux_rent") if kpi_c else None,mieux_si_haut=True,
        val_eur=fmt(kpi["resultat"])),
        use_container_width=True,config=CFG)
    with c3: st.plotly_chart(jauge(kpi["taux_ebe"],0,40,"EBE / CA",seuils=s_ebe,
        val_comp=kpi_c.get("taux_ebe") if kpi_c else None,mieux_si_haut=True,
        val_eur=fmt(kpi["ebe"])),
        use_container_width=True,config=CFG)
    with c4: st.plotly_chart(jauge(min(kpi["couverture"],12),0,12,"Tréso (mois charges)",
        unite=" mois",seuils=[0.25,0.5],mieux_si_haut=True,
        val_comp=min(kpi_c.get("couverture",12),12) if kpi_c else None,
        val_eur=fmt(kpi["treso"])),
        use_container_width=True,config=CFG)
    with c5:
        bfj=kpi["bfr_jours"]
        st.plotly_chart(jauge(bfj,0,90,"BFR en jours",unite="j",
            couleur=C["vert"] if bfj<60 else C["rouge"],seuils=[0.67,0.33],mieux_si_haut=False,
            val_comp=kpi_c.get("bfr_jours") if kpi_c else None,
            val_eur=fmt(kpi["bfr"])),
            use_container_width=True,config=CFG)



    # ── KPI essentiels ──────────────────────────────────
    st.markdown('<div class="section-title">KPI essentiels — cliquer pour le détail des comptes</div>',
                unsafe_allow_html=True)

    # Définition des 7 KPI avec icône, label, valeur, couleur, prefixe detail
    kpi_defs = [
        ("ca",    "💰", "CA réel",          kpi["ca"],       kpi_c.get("ca")       if kpi_c else None, False, C["bleu"],   f"Ann. : {fmt(ca_ann)}" if mois!=12 else "", "70"),
        ("marge", "📊", "Marge brute",       kpi["marge"],    kpi_c.get("marge")    if kpi_c else None, False, C["vert"],   fmt_pct(kpi["taux_marge"]),                  "60"),
        ("ebe",   "⚙️", "EBE",               kpi["ebe"],      kpi_c.get("ebe")      if kpi_c else None, False, C["orange"], fmt_pct(kpi["taux_ebe"]),                    None),
        ("res",   "📈", "Résultat net",       kpi["resultat"], kpi_c.get("resultat") if kpi_c else None, False, C["violet"], fmt_pct(kpi["taux_rent"]),                   None),
        ("treso", "🏦", "Trésorerie",         kpi["treso"],    kpi_c.get("treso")    if kpi_c else None, False, C["vert"],   "",                                          "512"),
        ("crean", "🧾", "Créances clients",   kpi["creances"], kpi_c.get("creances") if kpi_c else None, True,  C["orange"], f"DSO : {kpi['dso']:.0f}j",                  "411"),
        ("bfr",   "⚖️", "BFR",               kpi["bfr"],      kpi_c.get("bfr")      if kpi_c else None, True,  C["rouge"],  f"{kpi['bfr_jours']:.0f} jours",             None),
    ]

    cols=st.columns(7)
    for col,(key,icone,lbl,vn,vc,inv,couleur,sub,pref) in zip(cols,kpi_defs):
        with col:
            vn_ann=annualiser(vn,annee)
            d=delta_html(vn_ann,vc,inv) if vc else ""
            actif = st.session_state.get("panel_ouvert")==key
            border_style = f"border:2px solid {couleur};box-shadow:0 4px 16px rgba(0,0,0,0.15);" if actif else f"border-top:4px solid {couleur};"
            st.markdown(f"""
            <div class="kpi-card" style="{border_style}">
                <div class="kpi-icon">{icone}</div>
                <div class="kpi-label">{lbl}</div>
                <div class="kpi-value">{fmt(vn)}</div>
                <div class="kpi-delta">{d}</div>
                <div class="kpi-sub">{sub}</div>
            </div>
            """,unsafe_allow_html=True)
            if st.button(" ",key=f"btn_{key}",use_container_width=True):
                st.session_state["panel_ouvert"] = None if actif else key
                st.rerun()

    # Panneau pleine largeur
    panel=st.session_state.get("panel_ouvert")
    pref_map={"ca":"70","marge":"60","treso":"512","crean":"411"}
    titre_map={
        "ca":"Comptes de ventes (70) — Détail du CA",
        "marge":"Achats & matières (60) — Détail des charges",
        "treso":"Comptes bancaires (512) — Détail trésorerie",
        "crean":"Comptes clients (411) — Détail des créances",
    }
    if panel in pref_map:
        panel_detail(titre_map[panel],kpi["detail"].get(pref_map[panel],{}),annee,
                     kpi_c["detail"].get(pref_map[panel],{}) if kpi_c else None,
                     couleur=dict(ca=C["bleu"],marge=C["vert"],treso=C["vert"],crean=C["orange"])[panel])
    elif panel in ["res","ebe","bfr"]:
        noms={"res":"Résultat net","ebe":"EBE","bfr":"BFR"}
        st.info(f"ℹ️ {noms[panel]} est un agrégat calculé — voir **Analytique** et **BFR & Tréso** pour le détail.")
        if st.button("✕ Fermer",key="close_agg"): st.session_state["panel_ouvert"]=None; st.rerun()

    # ── Objectifs — jauges verticales ───────────────────
    st.markdown('<div class="section-title">Suivi des objectifs</div>',unsafe_allow_html=True)
    c1,c2,c3,c4=st.columns(4)
    objectifs=[
        (c1,"CA",         kpi["ca"],     obj_ca*1000,    False),
        (c2,"Marge brute",kpi["marge"],  obj_marge*1000, False),
        (c3,"Trésorerie", kpi["treso"],  obj_treso*1000, False),
        (c4,"BFR max",    kpi["bfr"],    obj_bfr*1000,   True),
    ]
    for col,lbl,reel,cible,inv in objectifs:
        with col:
            pct=reel/cible*100 if cible>0 else 0
            if inv:
                # BFR : mieux si en dessous de l'objectif
                pct = max(0, 200 - pct) if pct > 100 else 100
            pct=max(0,min(pct,150))
            valeur_keur = fmt(reel)
            valeur_str = f"{fmt(reel)} / obj. {fmt(cible)}"
            fig=jauge_verticale(pct, lbl, valeur_str, valeur_keur)
            st.plotly_chart(fig,use_container_width=True,config=CFG)

    # ── Alertes impayés ──────────────────────────────────
    if agee and agee.get("plus_61",0)>0:
        st.markdown('<div class="section-title">🚨 Impayés critiques +61 jours</div>',
                    unsafe_allow_html=True)
        for c in [x for x in agee.get("clients",[]) if x.get("plus_61",0)>500][:5]:
            st.markdown(f'<div class="alert-r">⚠️ <b>{c["nom"]}</b> — '
                        f'{fmt(c["plus_61"],k=False)} en retard +61j · '
                        f'Total dû : {fmt(c["total"],k=False)}</div>',unsafe_allow_html=True)

# ══ ONGLET 2 : CA & CLIENTS ══════════════════════════════
with tabs[1]:
    if mensuel:
        st.markdown('<div class="section-title">CA mensuel HT</div>',unsafe_allow_html=True)
        ordre_mois=[f"{y}-{m:02d}" for y in range(2022,2026) for m in range(1,13)]
        mois_pres=[m for m in ordre_mois if m in mensuel]
        vals_m=[mensuel[m] for m in mois_pres]
        moy=sum(vals_m)/len(vals_m) if vals_m else 0
        labels_fr={"01":"Jan","02":"Fév","03":"Mar","04":"Avr","05":"Mai","06":"Jun",
                   "07":"Jul","08":"Aoû","09":"Sep","10":"Oct","11":"Nov","12":"Déc"}
        x_labels=[labels_fr.get(m.split("-")[1],m)+"-"+m.split("-")[0][-2:] for m in mois_pres]
        fig=go.Figure()
        fig.add_trace(go.Bar(x=x_labels,y=vals_m,
            marker_color=[C["rouge"] if v<moy*0.5 else C["vert"] if v>moy*1.5 else C["bleu"] for v in vals_m],
            text=[fmt(v,k=False) for v in vals_m],textposition="outside",textfont=dict(size=9)))
        fig.add_trace(go.Scatter(x=x_labels,y=[moy]*len(mois_pres),mode="lines",
            line=dict(color=C["orange"],dash="dash",width=1.5),name=f"Moy. {fmt(moy,k=False)}"))
        fig.update_layout(height=300,margin=dict(t=30,b=0,l=0,r=0),showlegend=False,
            plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="€ HT",gridcolor="#f0f0f0"))
        st.plotly_chart(fig,use_container_width=True,config=CFG)

    if clients_d:
        st.markdown('<div class="section-title">Top 10 clients</div>',unsafe_allow_html=True)
        top10=sorted(clients_d.items(),key=lambda x:-x[1])[:10]
        total_cli=sum(v for _,v in clients_d.items())
        c1,c2=st.columns([1,1])
        with c1:
            rows=[]
            for nom,v in top10:
                pct=v/total_cli*100 if total_cli>0 else 0
                vc_cli=clients_c.get(nom,0)
                if vc_cli>0:
                    p=(annualiser(v,annee)-vc_cli)/vc_cli*100
                    var=f"{'+'if p>0 else ''}{fmt_pct(p)} ({fmt(vc_cli)})"
                else: var="Nouveau"
                rows.append({"Client":nom,"CA HT":fmt(v,k=False),"% CA":f"{pct:.1f}%","vs N-1":var})
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True,
                column_config={"Client":st.column_config.TextColumn("Client",width="medium")})
        with c2:
            noms=[n[:22] for n,_ in top10]; vals_cli=[v/1000 for _,v in top10]
            fig=go.Figure(go.Bar(y=noms[::-1],x=vals_cli[::-1],orientation="h",
                marker_color=C["bleu"],text=[fmt(v*1000) for v in vals_cli[::-1]],textposition="outside"))
            fig.update_layout(height=320,margin=dict(t=10,b=0,l=0,r=100),
                plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title="k€ HT",gridcolor="#f0f0f0"))
            st.plotly_chart(fig,use_container_width=True,config=CFG)
        if top10:
            top1_pct=top10[0][1]/total_cli*100
            if top1_pct>20:
                st.markdown(f'<div class="alert-r">🚨 <b>{top10[0][0]}</b> = {fmt_pct(top1_pct)} du CA</div>',unsafe_allow_html=True)

    if agee and agee.get("total",0)>0:
        st.markdown('<div class="section-title">Balance âgée clients</div>',unsafe_allow_html=True)
        total=agee["total"]
        c1,c2,c3,c4,c5=st.columns(5)
        kpi_agee=[
            (c1,"Total créances",fmt(total),"",""),
            (c2,"Non échu",fmt(agee["non_echu"]),f"{agee['non_echu']/total*100:.0f}%",""),
            (c3,"1-30 jours",fmt(agee["j1_30"]),"",""),
            (c4,"⚠️ +61 jours",fmt(agee["plus_61"]),f"{agee['plus_61']/total*100:.0f}%",C["rouge"]),
            (c5,"DSO",f"{kpi['dso']:.0f} j","",""),
        ]
        for col,lbl,val,sub,coul in kpi_agee:
            border=f"border-top:4px solid {coul};" if coul else ""
            with col:
                st.markdown(f'<div class="kpi-card" style="{border}cursor:default"><div class="kpi-label">{lbl}</div><div class="kpi-value">{val}</div><div class="kpi-sub">{sub}</div></div>',unsafe_allow_html=True)
        retards=[c for c in agee["clients"] if c.get("plus_61",0)>100]
        if retards:
            st.dataframe(pd.DataFrame([{"Client":c["nom"],"Total dû":fmt(c["total"],k=False),
                "+61j":fmt(c["plus_61"],k=False)} for c in retards]),
                use_container_width=True,hide_index=True)

# ══ ONGLET 3 : ANALYTIQUE ═════════════════════════════════
with tabs[2]:
    if not analytique:
        st.info("Balance analytique non disponible.")
    else:
        st.markdown('<div class="section-title">Performance par activité</div>',unsafe_allow_html=True)
        st.caption("ℹ️ Crédit = CA · Débit = charges directes · Écart possible avec CA total (refacturations internes)")
        acts=list(analytique.keys())
        cols=st.columns(len(acts))
        for col,code in zip(cols,acts):
            data=analytique[code]; ca_c_a=ana_c.get(code,{}).get("ca",0)
            couleur=C["vert"] if data["marge"]>0 else C["rouge"]
            with col:
                st.markdown(f"""<div class="kpi-card" style="border-top:4px solid {couleur};cursor:default;height:auto">
                    <div class="kpi-label">{data['label']}</div>
                    <div class="kpi-value">{fmt(data['ca'])}</div>
                    <div style="color:{couleur};font-size:13px;font-weight:600;margin-top:4px">
                        Marge {fmt(data['marge'])} ({fmt_pct(data['taux_marge'])})
                    </div>
                    {('<div class="kpi-delta">'+delta_html(annualiser(data['ca'],annee),ca_c_a)+'</div>') if ca_c_a else ''}
                </div>""",unsafe_allow_html=True)
        for code in acts:
            data=analytique[code]; ca_c_a=ana_c.get(code,{}).get("ca",0); mg_c_a=ana_c.get(code,{}).get("marge",0)
            with st.expander(f"📊 {data['label']} — CA : {fmt(data['ca'])} · Marge : {fmt(data['marge'])} ({fmt_pct(data['taux_marge'])})",expanded=False):
                c1,c2,c3,c4=st.columns(4)
                with c1:
                    st.metric("CA (crédit)",fmt(data["ca"]))
                    if ca_c_a: st.markdown(delta_html(annualiser(data["ca"],annee),ca_c_a),unsafe_allow_html=True)
                with c2: st.metric("Charges (débit)",fmt(data["charges"]))
                with c3:
                    st.metric("Marge",fmt(data["marge"]))
                    if mg_c_a: st.markdown(delta_html(annualiser(data["marge"],annee),mg_c_a),unsafe_allow_html=True)
                with c4: st.metric("Taux de marge",fmt_pct(data["taux_marge"]))
        if ana_c:
            st.markdown('<div class="section-title">Comparatif N vs N-1</div>',unsafe_allow_html=True)
            labels_act=[analytique[a]["label"][:20] for a in acts]
            fig=go.Figure()
            fig.add_trace(go.Bar(name=f"CA {annee} ann.",x=labels_act,y=[annualiser(analytique[a]["ca"],annee)/1000 for a in acts],marker_color=C["bleu"]))
            fig.add_trace(go.Bar(name=f"CA {annee_c}",x=labels_act,y=[ana_c.get(a,{}).get("ca",0)/1000 for a in acts],marker_color="#85B7EB"))
            fig.add_trace(go.Bar(name=f"Marge {annee} ann.",x=labels_act,y=[annualiser(analytique[a]["marge"],annee)/1000 for a in acts],marker_color=C["vert"]))
            fig.add_trace(go.Bar(name=f"Marge {annee_c}",x=labels_act,y=[ana_c.get(a,{}).get("marge",0)/1000 for a in acts],marker_color="#9FE1CB"))
            fig.update_layout(barmode="group",height=300,margin=dict(t=10,b=0,l=0,r=0),
                legend=dict(orientation="h",y=1.1),plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                yaxis=dict(title="k€",gridcolor="#f0f0f0"))
            st.plotly_chart(fig,use_container_width=True,config=CFG)

# ══ ONGLET 4 : CHARGES & FOURNISSEURS ═════════════════════
with tabs[3]:
    postes=[
        ("Achats & matières (60)",kpi["achats"],kpi_c.get("achats",0) if kpi_c else 0,C["bleu"],"60"),
        ("Personnel (64)",kpi["charges_pers"],kpi_c.get("charges_pers",0) if kpi_c else 0,C["vert"],"64"),
        ("Services ext. (61)",kpi["services"],kpi_c.get("services",0) if kpi_c else 0,C["orange"],"61"),
        ("Autres charges (62)",kpi["autres"],kpi_c.get("autres",0) if kpi_c else 0,C["gris"],"62"),
        ("IS (69)",kpi["is_"],kpi_c.get("is_",0) if kpi_c else 0,C["rouge"],"69"),
    ]
    st.markdown('<div class="section-title">Structure des charges</div>',unsafe_allow_html=True)
    c1,c2,c3,c4,c5=st.columns(5)
    for col,(lbl,vn,vc,couleur,pref) in zip([c1,c2,c3,c4,c5],postes):
        vn_ann=annualiser(vn,annee); d=delta_html(vn_ann,vc,inv=True) if vc else ""
        pct_ca=vn_ann/annualiser(kpi["ca"],annee)*100 if kpi["ca"]>0 else 0
        with col:
            st.markdown(f"""<div class="kpi-card" style="border-top:4px solid {couleur};height:auto">
                <div class="kpi-label">{lbl}</div><div class="kpi-value">{fmt(vn)}</div>
                <div class="kpi-delta">{d}</div><div class="kpi-sub">{fmt_pct(pct_ca)} du CA</div>
                <div class="kpi-hint">🔍 Cliquer pour variations</div>
            </div>""",unsafe_allow_html=True)
            if st.button("📊",key=f"btn_var_{pref}",use_container_width=True):
                st.session_state["panel_ouvert"]=None if st.session_state.get("panel_ouvert")==f"var_{pref}" else f"var_{pref}"
                st.rerun()
    for lbl,vn,vc,couleur,pref in postes:
        if st.session_state.get("panel_ouvert")==f"var_{pref}" and annee_c in EXERCICES:
            panel_variations(lbl,annee,annee_c,pref,couleur); break
    if kpi_c:
        st.markdown('<div class="section-title">Alertes</div>',unsafe_allow_html=True)
        for lbl,vn,vc,_,__ in postes:
            if vc>0:
                p=(annualiser(vn,annee)-vc)/vc*100
                if abs(p)>seuil_charges:
                    cls="alert-r" if p>seuil_charges else "alert-g"
                    st.markdown(f'<div class="{cls}">{"📈" if p>0 else "📉"} <b>{lbl}</b> — {fmt(vc)} → {fmt(annualiser(vn,annee))} ann. ({"+" if p>0 else ""}{fmt_pct(p)})</div>',unsafe_allow_html=True)
    if fourn:
        st.markdown('<div class="section-title">Top 10 fournisseurs</div>',unsafe_allow_html=True)
        top10f=sorted(fourn.items(),key=lambda x:-x[1])[:10]; total_f=sum(v for _,v in fourn.items())
        c1,c2=st.columns([1,1])
        with c1:
            rows=[]
            for nom,v in top10f:
                vc_f=fourn_c.get(nom,0)
                var=(f"{'+'if (p:=(annualiser(v,annee)-vc_f)/vc_f*100)>0 else ''}{fmt_pct(p)}" if vc_f>0 else "Nouveau")
                rows.append({"Fournisseur":nom,"Facturé":fmt(v,k=False),"%":f"{v/total_f*100:.1f}%","vs N-1":var})
            st.dataframe(pd.DataFrame(rows),use_container_width=True,hide_index=True,
                column_config={"Fournisseur":st.column_config.TextColumn("Fournisseur",width="medium")})
        with c2:
            noms_f=[n[:22] for n,_ in top10f]; vals_f=[v/1000 for _,v in top10f]
            vals_c_f=[fourn_c.get(n,0)/1000 for n,_ in top10f]
            fig=go.Figure()
            fig.add_trace(go.Bar(name=annee,y=noms_f[::-1],x=vals_f[::-1],orientation="h",marker_color=C["bleu"]))
            if any(v>0 for v in vals_c_f):
                fig.add_trace(go.Bar(name=annee_c,y=noms_f[::-1],x=vals_c_f[::-1],orientation="h",marker_color="#85B7EB"))
            fig.update_layout(barmode="group",height=320,margin=dict(t=10,b=0,l=0,r=100),
                legend=dict(orientation="h",y=1.1),plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
                xaxis=dict(title="k€",gridcolor="#f0f0f0"))
            st.plotly_chart(fig,use_container_width=True,config=CFG)

# ══ ONGLET 5 : BFR & TRÉSO ════════════════════════════════
with tabs[4]:
    st.markdown('<div class="section-title">Ratios financiers clés</div>',unsafe_allow_html=True)
    c1,c2,c3,c4,c5=st.columns(5)
    for col,lbl,icone,val,d,sub,couleur in [
        (c1,"Trésorerie","🏦",fmt(kpi["treso"]),delta_html(kpi["treso"],kpi_c.get("treso") if kpi_c else None),"",C["vert"]),
        (c2,"BFR","⚖️",fmt(kpi["bfr"]),delta_html(kpi["bfr"],kpi_c.get("bfr") if kpi_c else None,inv=True),f"{kpi['bfr_jours']:.0f}j",C["orange"]),
        (c3,"CAF","💫",fmt(kpi["caf"]),delta_html(annualiser(kpi["caf"],annee),kpi_c.get("caf") if kpi_c else None),"",C["bleu"]),
        (c4,"FR disponible","🔄",fmt(kpi["treso"]-kpi["bfr"]),"","Tréso−BFR",C["violet"]),
        (c5,"DSO","📅",f"{kpi['dso']:.0f}j",delta_html(kpi["dso"],kpi_c.get("dso") if kpi_c else None,inv=True),"",C["rouge"]),
    ]:
        with col:
            st.markdown(f'<div class="kpi-card" style="border-top:4px solid {couleur};cursor:default"><div class="kpi-icon">{icone}</div><div class="kpi-label">{lbl}</div><div class="kpi-value">{val}</div><div class="kpi-delta">{d}</div><div class="kpi-sub">{sub}</div></div>',unsafe_allow_html=True)

    st.markdown('<div class="section-title">Décomposition du BFR</div>',unsafe_allow_html=True)
    c1,c2,c3,c4,c5=st.columns([3,1,3,1,3])
    couleur_bfr=C["vert"] if kpi["bfr"]<obj_bfr*1000 else C["rouge"]
    d_bfr=delta_html(kpi["bfr"],kpi_c.get("bfr") if kpi_c else None,inv=True)
    for col,contenu in [
        (c1,f'<div style="background:white;border-radius:12px;padding:20px;text-align:center;border-top:4px solid {C["bleu"]};border:1px solid #e8ecf0"><div style="font-size:36px">📦</div><div style="font-size:22px;font-weight:700">{fmt(kpi["stocks"],k=False)}</div><div style="font-size:11px;color:#8896a5;text-transform:uppercase;margin-top:4px">Stocks</div></div>'),
        (c2,f'<div style="display:flex;align-items:center;justify-content:center;height:140px;font-size:32px;font-weight:700;color:{C["bleu"]}">+</div>'),
        (c3,f'<div style="background:white;border-radius:12px;padding:20px;text-align:center;border-top:4px solid {C["orange"]};border:1px solid #e8ecf0"><div style="font-size:36px">🧾</div><div style="font-size:22px;font-weight:700">{fmt(kpi["creances"],k=False)}</div><div style="font-size:11px;color:#8896a5;text-transform:uppercase;margin-top:4px">Créances · DSO {kpi["dso"]:.0f}j</div><div style="font-size:11px;color:#aaa;margin-top:4px">Dettes fourn. déduites : −{fmt(kpi["dettes_f"],k=False)}</div></div>'),
        (c4,f'<div style="display:flex;align-items:center;justify-content:center;height:140px;font-size:32px;font-weight:700;color:{couleur_bfr}">=</div>'),
        (c5,f'<div style="background:white;border-radius:12px;padding:20px;text-align:center;border-top:4px solid {couleur_bfr};border:1px solid #e8ecf0"><div style="font-size:36px">{"✅" if kpi["bfr"]<obj_bfr*1000 else "⚠️"}</div><div style="font-size:22px;font-weight:700;color:{couleur_bfr}">{fmt(kpi["bfr"],k=False)}</div><div style="font-size:11px;color:#8896a5;text-transform:uppercase;margin-top:4px">BFR · {kpi["bfr_jours"]:.0f}j</div><div style="font-size:12px;margin-top:4px">{d_bfr}</div></div>'),
    ]:
        with col: st.markdown(contenu,unsafe_allow_html=True)

    annees_dispo=[a for a in ["2023","2024","2025"] if (DATA/f"balance_generale_{a}.xlsx").exists()]
    if len(annees_dispo)>=2:
        st.markdown('<div class="section-title">Évolution pluriannuelle</div>',unsafe_allow_html=True)
        kpis_g={}
        for a in annees_dispo:
            cp,tt=lire_balance(a)
            if cp: kpis_g[a]=calculer_kpi(cp,tt)
        x_labels=[f"Ex. {a}" for a in annees_dispo]
        fig2=go.Figure()
        for nom,vals,couleur in [
            ("CA ann.",[annualiser(kpis_g[a]["ca"],a)/1000 for a in annees_dispo],C["bleu"]),
            ("Marge ann.",[annualiser(kpis_g[a]["marge"],a)/1000 for a in annees_dispo],C["vert"]),
            ("EBE ann.",[annualiser(kpis_g[a]["ebe"],a)/1000 for a in annees_dispo],C["orange"]),
            ("Résultat ann.",[annualiser(kpis_g[a]["resultat"],a)/1000 for a in annees_dispo],C["violet"]),
            ("Trésorerie",[kpis_g[a]["treso"]/1000 for a in annees_dispo],C["gris"]),
        ]:
            fig2.add_trace(go.Bar(name=nom,x=x_labels,y=vals,marker_color=couleur,
                text=[fmt(v*1000) for v in vals],textposition="outside",textfont=dict(size=10)))
        fig2.update_layout(barmode="group",height=360,margin=dict(t=30,b=0,l=0,r=0),
            legend=dict(orientation="h",y=1.12),plot_bgcolor="rgba(0,0,0,0)",paper_bgcolor="rgba(0,0,0,0)",
            yaxis=dict(title="k€",gridcolor="#f0f0f0"),
            xaxis=dict(categoryorder="array",categoryarray=x_labels))
        st.plotly_chart(fig2,use_container_width=True,config=CFG)

    st.markdown("""<div style="font-size:11px;color:#8896a5;background:white;padding:10px 14px;
        border-radius:8px;border:1px solid #e8ecf0;margin-top:8px">
        EBE = CA − Achats − Personnel − Services − Autres − Impôts&taxes &nbsp;|&nbsp;
        CAF = Résultat + Dotations &nbsp;|&nbsp;
        BFR = Stocks + Créances − Dettes fourn. &nbsp;|&nbsp;
        DSO = Créances × 365 / CA
    </div>""",unsafe_allow_html=True)
