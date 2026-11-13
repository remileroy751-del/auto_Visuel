from __future__ import annotations
from pathlib import Path
from openpyxl import load_workbook

HEADERS = {"slogan", "slogans", "phrase", "phrases", "accroche", "accroches"}


def load_info(path) -> tuple[list[str], dict]:
    """Lit info.xlsx : feuille 'slogans' (colonne A) + feuille 'projet' (clé | valeur)."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f"Fichier introuvable : {path}. Lance 'python create_template.py' pour créer un modèle.")
    wb = load_workbook(path, data_only=True)
    ws = wb["slogans"] if "slogans" in wb.sheetnames else wb.worksheets[0]

    slogans: list[str] = []
    for (v,) in ws.iter_rows(min_row=1, max_col=1, values_only=True):
        if v is None:
            continue
        v = str(v).strip()
        if v and v.lower() not in HEADERS:
            slogans.append(v)
    if len(slogans) < 5:
        raise ValueError(f"Il faut au moins 5 slogans/phrases (colonne A), {len(slogans)} trouvé(s).")

    projet: dict[str, str] = {}
    if "projet" in wb.sheetnames:
        for k, v in wb["projet"].iter_rows(min_row=1, max_col=2, values_only=True):
            if k and v is not None and str(k).strip().lower() not in ("clé", "cle", "champ"):
                projet[str(k).strip().lower()] = str(v).strip()
    return slogans, projet
