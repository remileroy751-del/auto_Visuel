"""Crée un modèle info.xlsx (slogans + description du projet)."""
from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

F = Font(name="Arial", size=11)
H = Font(name="Arial", size=11, bold=True, color="FFFFFF")
FILL = PatternFill("solid", fgColor="302B63")
NOTE = Font(name="Arial", size=10, italic=True, color="666666")

wb = Workbook()
ws = wb.active
ws.title = "slogans"
ws.append(["slogan"])
for s in [
    "Arrête de rêver, commence à encaisser.",
    "Une seule formation. Zéro excuse.",
    "Ils ont commencé comme toi. Regarde où ils en sont.",
    "Ton futur revenu t'attend de l'autre côté de cette page.",
    "Maîtrise le marketing digital en 30 jours, pas en 3 ans.",
    "Offre limitée : les places partent vite.",
]:
    ws.append([s])
ws["C1"] = "MODE D'EMPLOI"
ws["C2"] = "Colonne A : une phrase / un slogan par ligne (minimum 5)."
ws["C3"] = "Les 6 lignes ci-contre sont des exemples : remplace-les par les tiens."
ws["C1"].font = Font(name="Arial", size=11, bold=True)
ws["C2"].font = ws["C3"].font = NOTE
ws["A1"].font, ws["A1"].fill = H, FILL
for r in range(2, ws.max_row + 1):
    ws.cell(r, 1).font = F
ws.column_dimensions["A"].width = 70
ws.column_dimensions["C"].width = 65

p = wb.create_sheet("projet")
p.append(["clé", "valeur"])
rows = [
    ("nom", "Formation Marketing Pro"),
    ("type", "Formation en ligne"),
    ("description", "Programme vidéo de 30 jours pour apprendre à vendre en ligne, pas à pas."),
    ("fonctionnement", "Accès immédiat, 40 vidéos, exercices pratiques, communauté privée, support 7j/7."),
    ("cible", "Débutants et entrepreneurs africains francophones qui veulent un revenu en ligne."),
    ("benefices", "Résultats en 30 jours; Accès à vie; Sans diplôme ni expérience; Garantie 14 jours"),
    ("prix", "49 000 FCFA"),
    ("cta", "Je rejoins maintenant"),
    ("lien", "https://exemple.com/formation"),
    ("couleur", "#FFD400"),
]
for r in rows:
    p.append(list(r))
p["D1"] = "MODE D'EMPLOI"
p["D2"] = "Colonne B : remplace les valeurs. 'couleur' (code hex) et 'lien' sont optionnels."
p["D1"].font = Font(name="Arial", size=11, bold=True)
p["D2"].font = NOTE
p["A1"].font = p["B1"].font = H
p["A1"].fill = p["B1"].fill = FILL
for row in p.iter_rows(min_row=2, max_col=2):
    for c in row:
        c.font = F
        c.alignment = Alignment(wrap_text=True, vertical="top")
p.column_dimensions["A"].width = 18
p.column_dimensions["B"].width = 80
p.column_dimensions["D"].width = 70

wb.save("info.xlsx")
print("info.xlsx créé.")
