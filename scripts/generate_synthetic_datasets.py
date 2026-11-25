"""
Generate the six synthetic CSV files read by api_datasets/app.py.

The real CatBoost and business extracts are not versioned (*.csv is gitignored). These
files reproduce their columns and separators with fictional, deterministic values so the
recommendation API, the agent and the RL calibration can run locally. Renewal expiry dates
are placed shortly after today so the renewal routes always find a contract.

    python scripts/generate_synthetic_datasets.py [--out api_datasets] [--rag-out data/rag_docs] [--rows 40]
"""

import argparse
import csv
import random
from datetime import date, timedelta
from pathlib import Path

API_DIR = Path(__file__).resolve().parents[1] / "api_datasets"

SECTORS = [
    ("COMMERCE DE DETAIL", "COMMERCE DE DETAIL DE QUINCAILLERIE"),
    ("TRANSPORTS ET COMMUNICATIONS", "TRANSPORT ROUTIER DE MARCHANDISES"),
    ("INDUSTRIE MANUFACTURIERE", "FABRICATION DE MEUBLES"),
    ("INTERMEDIATION FINANCIERE", "CREDIT BAIL"),
    ("SANTE ET ACTION SOCIALE", "CLINIQUE PRIVEE"),
]
PROFESSIONS = [
    ("CADRES ET PROFESSIONS INTELLECTUELLES SUPERIEURES", "MEDECINS LIBERAUX GENERALISTES"),
    ("EMPLOYES", "EMPLOYE DE BANQUE"),
    ("OUVRIERS", "CONDUCTEURS DE VEHICULE ROUTIER"),
    ("ARTISANS COMMERCANTS", "COMMERCANT DETAILLANT"),
]
PRODUCTS = {
    "AUTOMOBILE": ("AUTOMOBILE", "AUTOMOBILE"),
    "MULTIRISQUES PROFESSIONNELLES": ("IARD", "MULTIRISQUES"),
    "SANTE ET PREVOYANCE": ("SANTE", "GROUPE"),
    "TEMPORAIRE DECES": ("VIE", "DECES"),
    "RESPONSABILITE CIVILE": ("IARD", "RESPONSABILITE CIVILE"),
    "INDIVIDUELLE ACCIDENTS": ("IARD", "ACCIDENTS"),
}
GUARANTEES = ["RC - RTI", "DEFENSE ET RECOURS", "INCENDIE", "VOL", "BRIS DE GLACES"]
CANDIDATE_GUARANTEES = [
    "CAR GLASS", "ASSISTANCE ACCIDENT AUTOMOBILE (3A)", "CATASTROPHE NATURELLE",
    "EMEUTE ET MOUVEMENT POPULAIRE", "DOMMAGES AU VEHICULE",
]
MARITAL = ["Marie", "Celibataire", "Divorce"]
PM_CATEGORIES = ["Entreprise", "Commerce & Services", "Industrie"]


def _write(path: Path, sep: str, rows: list) -> None:
    with open(path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]), delimiter=sep)
        writer.writeheader()
        writer.writerows(rows)
    print(f"{path.name}: {len(rows)} lignes")


def _contract(rng: random.Random, today: date, renewal: bool):
    product = rng.choice(list(PRODUCTS))
    branch, sub_branch = PRODUCTS[product]
    age = rng.randint(0, 12)
    if renewal:
        expiry = today + timedelta(days=rng.randint(5, 75))
    else:
        expiry = today + timedelta(days=rng.randint(90, 360))
    effect = expiry - timedelta(days=365)
    candidates = rng.sample([p for p in PRODUCTS if p != product], 2)
    return {
        "product": product, "branch": branch, "sub_branch": sub_branch, "age": age,
        "effect": effect.isoformat(), "expiry": expiry.isoformat(),
        "number": 2024300000000 + rng.randint(1, 999_999),
        "guarantees": ";".join(rng.sample(GUARANTEES, 3)),
        "candidate_guarantees": ";".join(rng.sample(CANDIDATE_GUARANTEES, 3)),
        "candidates": candidates,
    }


def generate(out: Path, rows: int, seed: int, today: date) -> None:
    rng = random.Random(seed)
    out.mkdir(parents=True, exist_ok=True)

    def pm_base(i, renewal=False):
        sector, activity = rng.choice(SECTORS)
        c = _contract(rng, today, renewal)
        return c, {
            "REF_pm": f"REF_pm_SYN_{i:04d}",
            "Lib_Secteur_Activite": sector, "Lib_Activite": activity,
            "LIB_PRODUIT": c["product"], "Branche": c["branch"], "Lib_Sous_Branche": c["sub_branch"],
            "Age_Contrat": c["age"], "Category": rng.choice(PM_CATEGORIES),
        }

    def pp_base(i, renewal=False):
        sector, profession = rng.choice(PROFESSIONS)
        c = _contract(rng, today, renewal)
        return c, {
            "REF_pp": f"REF_pp_SYN_{i:04d}",
            "Num_Piece_Identite": 10_000_000 + i,
            "Situation_Familiale": rng.choice(MARITAL),
            "Lib_Secteur_Activite": sector, "Lib_Profession": profession,
            "Age_Contrat": c["age"], "LIB_PRODUIT": c["product"], "Category": "Particulier",
            "Age": rng.randint(22, 70),
        }

    # catboost_pm.csv — product recommendation, companies (sep ",")
    data = []
    for i in range(rows):
        c, row = pm_base(i)
        score = rng.random()
        row.update({
            "Candidate_Produit": c["candidates"][0], "nb_produits": rng.randint(1, 8),
            "score": round(score, 6), "goodBuyer_score_pourcent": round(score * 100, 1),
            "Lib_Garantie": c["guarantees"], "Candidate_Garanties": c["candidate_guarantees"],
        })
        data.append(row)
    _write(out / "catboost_pm.csv", ",", data)

    # catboost_pp_updated.csv — product recommendation, individuals
    data = []
    for i in range(rows):
        c, row = pp_base(i)
        row.update({
            "recommended_product": c["candidates"][0],
            "recommended_score": round(rng.uniform(20, 99), 2), "status": "OK",
            "LIB_BRANCHE": c["branch"], "LIB_SOUS_BRANCHE": c["sub_branch"],
            "bought": rng.randint(0, 1), "nb_produits": rng.randint(1, 5),
            "good_buyer_pct": round(rng.uniform(10, 100), 1),
        })
        data.append(row)
    _write(out / "catboost_pp_updated.csv", ";", data)

    # facture_pm.csv — unpaid invoices, companies
    data = []
    for i in range(rows):
        c, row = pm_base(i)
        row.update({
            "statut_paiement": "NON PAYE", "NB_SINISTRE": rng.randint(0, 3),
            "candidate_product": ";".join(c["candidates"]),
            "Decision": "rappel pour regler facture du contrat",
            "EFFET_CONTRAT_DATE": c["effect"], "Num_Contrat": c["number"],
            "Lib_Garantie": c["guarantees"], "Candidate_Garanties": c["candidate_guarantees"],
            "nb_sinistres_2025": rng.randint(0, 5),
        })
        data.append(row)
    _write(out / "facture_pm.csv", ";", data)

    # reglement_facture_pp.csv — unpaid invoices, individuals
    data = []
    for i in range(rows):
        c, row = pp_base(i)
        row.update({
            "Candidate_Produit": ";".join(c["candidates"]), "Decision": "Reglement facture",
            "statut_paiement": "Non paye", "Effet_Contrat": c["effect"],
            "Date_Expiration": c["expiry"], "Num_Contrat": c["number"],
            "Lib_Garantie": c["guarantees"], "Candidate_Garanties": c["candidate_guarantees"],
        })
        data.append(row)
    _write(out / "reglement_facture_pp.csv", ";", data)

    # renouvellement_pm.csv — contracts expiring soon, companies
    data = []
    for i in range(rows):
        c, row = pm_base(i, renewal=True)
        row.update({
            "STATUT_PAIEMENT": rng.choice(["PAYE", "PAYE", "NON PAYE"]),
            "NB_SINISTRE": rng.randint(0, 3), "candidate_product": ";".join(c["candidates"]),
            "Decision": "renouvellement contrat", "EFFET_CONTRAT_DATE": c["effect"],
            "DATE_EXPIRATION_CONTRAT": c["expiry"], "NUM_CONTRAT": c["number"],
            "Lib_Garantie": c["guarantees"], "Candidate_Garanties": c["candidate_guarantees"],
            "nb_sinistres_2025": rng.randint(0, 5),
        })
        data.append(row)
    _write(out / "renouvellement_pm.csv", ";", data)

    # renouvellement_contrat_pp.csv — contracts expiring soon, individuals
    data = []
    for i in range(rows):
        c, row = pp_base(i, renewal=True)
        row.update({
            "Candidate_Produit": ";".join(c["candidates"]), "Decision": "renouvellement contrat",
            "statut_paiement": rng.choice(["Paye", "Paye", "Non paye"]),
            "Effet_Contrat": c["effect"], "Date_Expiration": c["expiry"],
            "Num_Contrat": c["number"], "Lib_Garantie": c["guarantees"],
            "LIB_BRANCHE": c["branch"], "LIB_SOUS_BRANCHE": c["sub_branch"],
            "nb_sinistres_2025": rng.randint(0, 5),
            "Candidate_Garanties": c["candidate_guarantees"],
        })
        data.append(row)
    _write(out / "renouvellement_contrat_pp.csv", ";", data)


RAG_DIR = Path(__file__).resolve().parents[1] / "data" / "rag_docs"

# Fictional general conditions, one folder per branch in the layout read by mlops/data_rag
RAG_DOCS = {
    "1-CG-Automobile": [
        ("Objet du contrat", "Les conditions générales de l'assurance automobile définissent les "
         "garanties accordées au conducteur et au véhicule désigné aux conditions particulières."),
        ("Garanties de l'assurance automobile", "Le contrat automobile comprend la responsabilité "
         "civile obligatoire, la défense et recours, et en option l'incendie, le vol, le bris de "
         "glaces, les dommages collision et l'assistance accident automobile."),
        ("Bris de glaces", "La garantie bris de glaces prend en charge le remplacement du pare-brise, "
         "des vitres latérales et de la lunette arrière, sans franchise en cas de réparation."),
    ],
    "2-CG-Vie": [
        ("Objet du contrat", "L'assurance vie garantit le versement d'un capital ou d'une rente aux "
         "bénéficiaires désignés selon l'option choisie."),
        ("Garantie décès", "En cas de décès de l'assuré pendant la durée du contrat, l'assureur verse "
         "le capital décès aux bénéficiaires désignés, dans un délai d'un mois après réception des "
         "pièces justificatives."),
        ("Exclusions de la garantie décès", "Le suicide au cours de la première année et les décès "
         "résultant de la participation volontaire à une rixe ne sont pas couverts."),
    ],
    "3-CG-Santé": [
        ("Objet du contrat", "L'assurance santé rembourse les frais médicaux engagés par l'assuré et "
         "ses ayants droit, en complément du régime obligatoire."),
        ("Frais médicaux remboursés", "Sont remboursés les consultations, les médicaments prescrits, "
         "les analyses, l'hospitalisation, les soins dentaires et l'optique, dans la limite des "
         "plafonds annuels."),
        ("Délai de carence", "Les soins dentaires et l'optique sont couverts après un délai de "
         "carence de trois mois à compter de la date d'effet."),
    ],
    "4-CG-Transport": [
        ("Objet du contrat", "L'assurance transport couvre les marchandises transportées par voie "
         "terrestre, maritime ou aérienne entre le lieu de départ et le lieu de destination."),
        ("Marchandises couvertes", "Sont couvertes les marchandises désignées au contrat contre la "
         "perte, le vol et les dommages matériels survenus pendant le transport et la manutention."),
        ("Marchandises exclues", "Les espèces, les bijoux et les animaux vivants sont exclus sauf "
         "convention contraire aux conditions particulières."),
    ],
    "5-CG-IARD": [
        ("Objet du contrat", "L'assurance incendie et risques divers protège les biens immobiliers et "
         "mobiliers de l'assuré."),
        ("Garantie incendie", "La garantie incendie couvre les dommages causés par l'incendie, "
         "l'explosion et la foudre aux bâtiments et à leur contenu."),
        ("Exclusions de la garantie incendie", "Sont exclus de la garantie incendie les dommages "
         "intentionnels, les brûlures causées par les fumeurs et les dommages dus à un défaut "
         "d'entretien connu de l'assuré."),
    ],
    "6-CG-Engineering": [
        ("Objet du contrat", "L'assurance engineering tous risques chantier couvre les ouvrages en "
         "cours de construction et le matériel de chantier."),
        ("Couverture du chantier", "Le chantier est couvert contre les dommages matériels accidentels "
         "survenus pendant les travaux, y compris l'effondrement et les intempéries."),
        ("Responsabilité civile du maître d'ouvrage", "La responsabilité civile couvre les dommages "
         "causés aux tiers par l'exécution des travaux sur le chantier."),
    ],
}


def generate_rag_docs(out: Path) -> None:
    for folder, sections in RAG_DOCS.items():
        directory = out / folder
        directory.mkdir(parents=True, exist_ok=True)
        title = folder.split("-", 1)[1]
        body = "\n\n".join(f"## {heading}\n\n{text}" for heading, text in sections)
        (directory / "conditions_generales.md").write_text(
            f"# Conditions générales {title} (document synthétique)\n\n{body}\n", encoding="utf-8")
        (directory / "conditions_generales.md.meta.yaml").write_text(
            "date_effet: 2026-01-01\nversion: synthetic-1\n", encoding="utf-8")
    print(f"documents RAG synthétiques : {len(RAG_DOCS)} dans {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, default=API_DIR)
    parser.add_argument("--rag-out", type=Path, default=RAG_DIR)
    parser.add_argument("--rows", type=int, default=40)
    parser.add_argument("--seed", type=int, default=7)
    args = parser.parse_args()
    generate(args.out, args.rows, args.seed, date.today())
    generate_rag_docs(args.rag_out)
