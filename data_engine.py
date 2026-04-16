"""
ECCO BAT — Moteur de données
Lit tous les fichiers Sage et calcule les KPI pour chaque exercice.
Gère les exercices fiscaux :
  - Avant 2026 : 01/10 → 30/09 (12 mois)
  - Transition 2025 : 01/10/2024 → 31/12/2025 (15 mois)
  - Depuis 2026 : 01/01 → 31/12 (12 mois)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import streamlit as st

# ─── Exercices fiscaux ────────────────────────────────────
EXERCICES = {
    "2023": {"debut": "2022-10-01", "fin": "2023-09-30", "mois": 12, "label": "Ex. 2023 (Oct 22 → Sep 23)"},
    "2024": {"debut": "2023-10-01", "fin": "2024-09-30", "mois": 12, "label": "Ex. 2024 (Oct 23 → Sep 24)"},
    "2025": {"debut": "2024-10-01", "fin": "2025-12-31", "mois": 15, "label": "Ex. 2025 (Oct 24 → Déc 25) — 15 mois"},
    "2026": {"debut": "2026-01-01", "fin": "2026-12-31", "mois": 12, "label": "Ex. 2026 (Jan → Déc 26)"},
}

def annualiser(valeur, annee):
    """Ramène une valeur sur 12 mois selon la durée de l'exercice."""
    mois = EXERCICES.get(str(annee), {}).get("mois", 12)
    return valeur * 12 / mois if mois != 12 else valeur


# ─── Lecture balance générale ─────────────────────────────
@st.cache_data
def lire_balance(fichier):
    """Extrait les soldes par compte depuis un export balance Sage."""
    try:
        df = pd.read_excel(fichier, header=None, dtype=str)
    except Exception:
        return {}

    comptes = {}
    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() not in ["", "nan"]]
        if not vals:
            continue
        premier = vals[0].replace(" ", "")
        if not premier or not premier[0].isdigit():
            continue
        num = premier[:6]
        intitule = ""
        montants = []
        for v in vals[1:]:
            try:
                m = float(str(v).replace(" ", "").replace(",", "."))
                montants.append(m)
            except:
                if not intitule and len(v) > 2:
                    intitule = v
        if len(montants) >= 2:
            sd = montants[2] if len(montants) > 2 else 0
            sc = montants[3] if len(montants) > 3 else 0
            comptes[num] = {
                "intitule": intitule,
                "debit": montants[0],
                "credit": montants[1],
                "solde_debiteur": sd,
                "solde_crediteur": sc,
            }
    return comptes


# ─── Calcul KPI depuis balance ────────────────────────────
def calculer_kpi(comptes, annee):
    def sc(prefix):
        return sum(c["solde_crediteur"] for n, c in comptes.items() if n.startswith(prefix) and c["solde_crediteur"] > 0)
    def sd(prefix):
        return sum(c["solde_debiteur"] for n, c in comptes.items() if n.startswith(prefix) and c["solde_debiteur"] > 0)
    def get_sc(num):
        return comptes.get(num, {}).get("solde_crediteur", 0)
    def get_sd(num):
        return comptes.get(num, {}).get("solde_debiteur", 0)

    ca              = sc("70")
    achats          = sd("60") - sc("60")
    services_ext    = sd("61")
    autres_services = sd("62")
    impots_taxes    = sd("63")
    charges_pers    = sd("64") - sc("64")
    autres_charges  = sd("65")
    charges_fin     = sd("66")
    charges_except  = sd("67")
    dotations       = sd("68")
    is_             = sd("69") - sc("69")

    marge_brute     = ca - max(achats, 0)
    charges_totales = max(achats,0) + services_ext + autres_services + impots_taxes + \
                      max(charges_pers,0) + autres_charges + charges_fin + \
                      charges_except + dotations + is_
    resultat_net    = get_sd("120") if get_sd("120") > 0 else sc("120") - sd("120")
    if resultat_net == 0:
        resultat_net = ca - charges_totales

    stocks          = get_sd("310") + get_sd("311") + get_sd("312") + get_sd("313")
    creances        = get_sd("411")
    dettes_fourn    = get_sc("401")

    tresorerie = sum(
        c["solde_debiteur"] - c["solde_crediteur"]
        for n, c in comptes.items()
        if n.startswith("512") or n.startswith("531")
    )
    tresorerie = max(tresorerie, 0)

    bfr             = stocks + creances - dettes_fourn
    bfr_jours       = bfr / ca * 365 if ca > 0 else 0
    caf             = resultat_net + dotations
    fonds_roulement = tresorerie - bfr
    dso             = creances / ca * 365 if ca > 0 else 0
    charges_mois    = charges_totales / 12
    couverture_mois = tresorerie / charges_mois if charges_mois > 0 else 0
    taux_marge      = marge_brute / ca * 100 if ca > 0 else 0
    taux_rent       = resultat_net / ca * 100 if ca > 0 else 0

    kpi = dict(
        annee=annee, ca=ca, marge_brute=marge_brute, taux_marge=taux_marge,
        resultat_net=resultat_net, taux_rent=taux_rent, charges_totales=charges_totales,
        achats=max(achats,0), services_ext=services_ext, autres_services=autres_services,
        impots_taxes=impots_taxes, charges_pers=max(charges_pers,0), dotations=dotations, is_=is_,
        stocks=stocks, creances=creances, dettes_fourn=dettes_fourn,
        tresorerie=tresorerie, bfr=bfr, bfr_jours=bfr_jours,
        caf=caf, fonds_roulement=fonds_roulement, dso=dso,
        couverture_mois=couverture_mois,
    )
    # Version annualisée pour comparatifs
    mois = EXERCICES.get(str(annee), {}).get("mois", 12)
    kpi["annualise"] = {k: v * 12 / mois if isinstance(v, (int, float)) and k not in ["taux_marge","taux_rent","bfr_jours","dso","couverture_mois","annee"] else v
                        for k, v in kpi.items()}
    return kpi


# ─── Lecture balance analytique ───────────────────────────
@st.cache_data
def lire_analytique(fichier):
    """Extrait CA et charges par section analytique."""
    try:
        df = pd.read_excel(fichier, header=None, dtype=str)
    except Exception:
        return {}

    sections = {}
    current = None

    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() not in ["", "nan"]]
        if not vals:
            continue

        # Ligne de section (4 chiffres + libellé)
        if len(vals) >= 2 and vals[0].isdigit() and len(vals[0]) == 4:
            current = vals[0]
            label = vals[1] if len(vals) > 1 else vals[0]
            if current not in sections:
                sections[current] = {"label": label, "ca": 0, "charges": 0}
            continue

        # Ligne Total section
        if vals[0] == "Total" and len(vals) >= 3:
            code = vals[1]
            if code in sections:
                nums = []
                for v in vals[3:]:
                    try:
                        nums.append(float(v.replace(" ", "").replace(",", ".")))
                    except:
                        pass
                if len(nums) >= 2:
                    debit, credit = nums[0], nums[1]
                    # Solde créditeur = CA (produits), solde débiteur = charges
                    solde = credit - debit
                    if solde > 0:
                        sections[code]["ca"] += solde
                    else:
                        sections[code]["charges"] += abs(solde)
            continue

        # Ligne de compte (6 chiffres)
        if current and vals[0].isdigit() and len(vals[0]) == 6:
            compte = vals[0]
            nums = []
            for v in vals[1:]:
                try:
                    n = float(v.replace(" ", "").replace(",", "."))
                    if n > 0.5:
                        nums.append(n)
                except:
                    pass

            if len(nums) >= 2:
                debit, credit = nums[0], nums[1]
                if compte.startswith("7"):
                    sections[current]["ca"] += credit
                elif compte.startswith("6"):
                    sections[current]["charges"] += debit

    # Regrouper par activité principale
    activites = {
        "Maintenance":            [k for k in sections if k.startswith("1") and k != "1"],
        "Rénovation énergétique": [k for k in sections if k.startswith("2") and k != "2"],
        "Maçonnerie":             [k for k in sections if k.startswith("3") and k != "3"],
        "Travaux":                [k for k in sections if k.startswith("4") and k != "4"],
        "Frais généraux":         [k for k in sections if k.startswith("9")],
    }

    result = {}
    for nom, codes in activites.items():
        ca = sum(sections[c]["ca"] for c in codes if c in sections)
        ch = sum(sections[c]["charges"] for c in codes if c in sections)
        if ca > 0 or ch > 0:
            result[nom] = {
                "ca": ca, "charges": ch,
                "marge": ca - ch,
                "taux_marge": (ca - ch) / ca * 100 if ca > 0 else 0,
                "sections": {c: sections[c] for c in codes if c in sections}
            }

    return result


# ─── Lecture balance âgée clients ────────────────────────
@st.cache_data
def lire_balance_agee(fichier):
    """Extrait les impayés clients par tranche d'ancienneté."""
    try:
        df = pd.read_excel(fichier, header=None, dtype=str)
    except Exception:
        return {"total": 0, "non_echu": 0, "j1_30": 0, "j31_45": 0, "j46_60": 0, "plus_61": 0, "clients": []}

    clients = []
    totaux = {"total": 0, "non_echu": 0, "j1_30": 0, "j31_45": 0, "j46_60": 0, "plus_61": 0}

    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() not in ["", "nan"]]
        if len(vals) < 4:
            continue
        if vals[0] in ["Totaux", "Total", "% Période"]:
            continue
        # Ligne client : code tiers + libellé + montants
        if not vals[0].isdigit() and len(vals[0]) > 2 and len(vals) >= 4:
            nums = []
            libelle = vals[1] if len(vals) > 1 else vals[0]
            for v in vals[2:]:
                try:
                    nums.append(float(v.replace(" ", "").replace(",", ".")))
                except:
                    pass
            if nums and nums[0] != 0:
                client = {
                    "code": vals[0],
                    "nom": libelle,
                    "total": nums[0] if len(nums) > 0 else 0,
                    "non_echu": nums[1] if len(nums) > 1 else 0,
                    "j1_30": nums[2] if len(nums) > 2 else 0,
                    "j31_45": nums[3] if len(nums) > 3 else 0,
                    "j46_60": nums[4] if len(nums) > 4 else 0,
                    "plus_61": nums[5] if len(nums) > 5 else 0,
                }
                if client["total"] > 0:
                    clients.append(client)

        # Totaux généraux
        if "Totaux" in vals[0] or (len(vals) > 2 and vals[0] == ""):
            nums = []
            for v in vals:
                try:
                    nums.append(float(v.replace(" ", "").replace(",", ".")))
                except:
                    pass
            if len(nums) >= 5:
                totaux = {
                    "total": nums[0], "non_echu": nums[1],
                    "j1_30": nums[2], "j31_45": nums[3],
                    "j46_60": nums[4], "plus_61": nums[5] if len(nums) > 5 else 0,
                    "clients": clients
                }

    if totaux["total"] == 0 and clients:
        totaux["total"] = sum(c["total"] for c in clients)
        totaux["non_echu"] = sum(c["non_echu"] for c in clients)
        totaux["j1_30"] = sum(c["j1_30"] for c in clients)
        totaux["j31_45"] = sum(c["j31_45"] for c in clients)
        totaux["j46_60"] = sum(c["j46_60"] for c in clients)
        totaux["plus_61"] = sum(c["plus_61"] for c in clients)
        totaux["clients"] = clients

    return totaux


# ─── Lecture grand livre fournisseurs ────────────────────
@st.cache_data
def lire_fournisseurs(fichier):
    """Extrait les achats par fournisseur depuis le grand livre 401."""
    try:
        df = pd.read_excel(fichier, header=None, dtype=str)
    except Exception:
        return {}

    fournisseurs = {}
    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() not in ["", "nan"]]
        if not vals:
            continue
        first = vals[0]
        if first.isdigit() and len(first) == 5:
            libelle = ""
            nums = []
            for v in vals[1:]:
                try:
                    n = float(v.replace(",", ".").replace(" ", ""))
                    if n > 1 and n not in [44835, 45199, 45200, 45565, 45566, 46022]:
                        nums.append(n)
                except:
                    if len(v) > 3 and v not in ["*"] and not any(x in v for x in ["Sage", "Ecco", "VIR SEPA", "PRLV", "EFFET", "PAIEMENT", "Règlement"]):
                        libelle = v[:35]
            if libelle and len(nums) >= 2:
                credit = nums[1]
                if credit > 100:
                    nom = libelle.split(" fact")[0].split(" lcr")[0].split(" Lcr")[0].strip()[:30]
                    fournisseurs[nom] = fournisseurs.get(nom, 0) + credit

    return dict(sorted(fournisseurs.items(), key=lambda x: -x[1]))


# ─── Lecture journal des ventes ───────────────────────────
@st.cache_data
def lire_journal_ventes(fichier):
    """Extrait CA HT par client et par mois depuis le journal des ventes."""
    try:
        df = pd.read_excel(fichier, header=None, dtype=str)
    except Exception:
        return {"clients": {}, "mensuel": {}}

    # Déterminer la date de début de l'exercice
    date_debut = None
    for _, row in df.iterrows():
        for v in row.values:
            try:
                n = int(float(str(v)))
                if 44000 < n < 47000:
                    date_debut = n
                    break
            except:
                pass
        if date_debut:
            break

    clients = {}
    mensuel = {}

    mois_labels = {
        0: "Oct-24", 1: "Nov-24", 2: "Déc-24",
        3: "Jan-25", 4: "Fév-25", 5: "Mar-25",
        6: "Avr-25", 7: "Mai-25", 8: "Jun-25",
        9: "Jul-25", 10: "Aoû-25", 11: "Sep-25",
        12: "Oct-25", 13: "Nov-25", 14: "Déc-25",
        # Ex 2024
        -12: "Oct-23", -11: "Nov-23", -10: "Déc-23",
        -9: "Jan-24", -8: "Fév-24", -7: "Mar-24",
        -6: "Avr-24", -5: "Mai-24", -4: "Jun-24",
        -3: "Jul-24", -2: "Aoû-24", -1: "Sep-24",
    }

    for _, row in df.iterrows():
        vals = [str(v).strip() for v in row.values if pd.notna(v) and str(v).strip() not in ["", "nan"]]
        if not vals:
            continue
        first = vals[0]
        if not (first.isdigit() and len(first) == 5):
            continue

        jour = int(first)
        compte = ""
        libelle = ""
        credit = 0.0

        for v in vals[1:]:
            if v.startswith("706") and len(v) == 6:
                compte = v
            else:
                try:
                    n = float(v.replace(",", ".").replace(" ", ""))
                    if n > 1 and n not in [44835, 45199, 45200, 45565, 45566, 46022]:
                        credit = n
                except:
                    if len(v) > 3 and v not in ["*", "VT"] and not any(x in v for x in ["Sage", "Ecco"]):
                        libelle = v[:35]

        if compte.startswith("706") and libelle and credit > 0:
            clients[libelle] = clients.get(libelle, 0) + credit
            if date_debut:
                offset = (jour - date_debut) // 30
                mois = mois_labels.get(offset, f"M{offset}")
                mensuel[mois] = mensuel.get(mois, 0) + credit

    return {"clients": dict(sorted(clients.items(), key=lambda x: -x[1])), "mensuel": mensuel}


# ─── Comparer fournisseurs N vs N-1 ──────────────────────
def comparer_fournisseurs(fourn_n, fourn_n1, annee_n, seuil=5.0):
    """Compare deux périodes et retourne les variations."""
    mois_n = EXERCICES.get(str(annee_n), {}).get("mois", 12)
    coef = 12 / mois_n  # annualisation

    resultats = []
    tous = set(list(fourn_n.keys()) + list(fourn_n1.keys()))

    for nom in tous:
        v_n = fourn_n.get(nom, 0) * coef
        v_n1 = fourn_n1.get(nom, 0)

        if v_n1 > 0 and v_n > 0:
            variation = (v_n - v_n1) / v_n1 * 100
            statut = "hausse" if variation > seuil else "baisse" if variation < -seuil else "stable"
        elif v_n > 0 and v_n1 == 0:
            variation = 999
            statut = "nouveau"
        elif v_n == 0 and v_n1 > 0:
            variation = -100
            statut = "disparu"
        else:
            continue

        if max(v_n, v_n1) > 2000:
            resultats.append({
                "nom": nom, "v_n": v_n, "v_n1": v_n1,
                "variation": variation, "statut": statut
            })

    return sorted(resultats, key=lambda x: abs(x["variation"]) if x["variation"] != 999 else 900, reverse=True)
