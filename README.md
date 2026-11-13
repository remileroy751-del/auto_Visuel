# AutoVisuel

Génère automatiquement des visuels et des vidéos de 10 s percutants pour vendre des produits digitaux
(formations, logiciels), puis les publie sur **Facebook (Page)** et **TikTok**, 2 fois par jour.

## Fonctionnement
1. Lit `info.xlsx` : feuille **slogans** (min. 5 phrases, colonne A) + feuille **projet** (description du produit).
2. L'IA (Gemini, puis Groq en secours) combine les slogans en accroche, sous-titre, appel à l'action, légende et hashtags.
   Sans clé API, le logiciel combine simplement tes phrases (mode hors-ligne).
3. Pillow compose le visuel (1080x1920 et 1080x1350), FFmpeg en fait une vidéo de 10 s (zoom lent + apparition du texte + musique optionnelle).
4. Publication sur Facebook et TikTok, 2 fois par jour maximum (08:00 et 19:30 par défaut).

## Installation (Python 3.10+)
```bash
pip install -r requirements.txt
python create_template.py        # crée info.xlsx (modèle à remplir)
# (ou laisse l assistant le faire : python main.py setup)
python main.py setup           # assistant : saisie guidée des clés (crée .env automatiquement)
python main.py check             # vérifie le fichier Excel et les clés
python main.py preview           # génère un visuel + une vidéo dans output/, sans publier
python main.py run               # génère ET publie maintenant
python main.py schedule          # publie chaque jour aux heures de config.yaml (laisser tourner)
```
FFmpeg est embarqué via `imageio-ffmpeg`. Rien d'autre à installer.

## Obtenir les clés
- **Gemini** : https://aistudio.google.com/apikey (niveau gratuit). **Groq** : https://console.groq.com/keys (niveau gratuit).
  Tu peux mettre plusieurs clés séparées par des virgules : rotation automatique si un quota est atteint.
- **Pollinations** (illustrations IA liées au texte) : clé `sk_...` sur https://enter.pollinations.ai (endpoint `gen.pollinations.ai`).
  C'est la 1re source de fond par défaut. Ne mets jamais cette clé dans un dépôt Git public.
- **Pexels** (belles photos de fond, recommandé) : https://www.pexels.com/api/ (clé gratuite). Le logiciel cherche une photo
  liée au produit grâce aux mots-clés écrits par l'IA, puis applique un voile coloré pour garder le texte lisible.
  Ordre des sources de fond réglable dans `config.yaml` (`fond.ordre`) ; dégradé de couleur si aucune n'est disponible.
- **Facebook** : crée une app sur https://developers.facebook.com, ajoute les permissions `pages_manage_posts`
  et `pages_read_engagement`, puis génère un **token de Page longue durée** et copie l'ID de la Page.
  (Publication sur une Page uniquement, pas sur un profil personnel.)
- **TikTok** : crée une app sur https://developers.tiktok.com avec le produit **Content Posting API**, autorise ton compte
  (OAuth) pour obtenir `access_token` et `refresh_token`. Tant que l'app n'est pas auditée par TikTok, les posts API
  restent **privés** (`privacy_level: SELF_ONLY`). En cas d'échec, la vidéo et sa légende sont rangées dans
  `output/tiktok_a_poster/` pour publication manuelle.

## Fichier de clés
Le logiciel lit `.env` ou `cles.env`, placé **à côté de `AutoVisuel.exe`** (ou à la racine du projet).
Ces fichiers sont exclus de Git (`.gitignore`) : ne les envoie jamais sur GitHub.

## Personnalisation
- Horaires, fuseau, limite quotidienne, modèles d'IA, durée vidéo : `config.yaml`.
- Musique : dépose des fichiers libres de droits (mp3, wav...) dans `music/`.
- Police : dépose un `.ttf` dans `fonts/` (sinon une police système est utilisée).
- Couleur de marque : champ `couleur` (hex) dans la feuille **projet**.
- Aperçu avant publication : `mode_validation: true` (en lancement manuel dans un terminal).

## GitHub
- **Exécutable Windows** : onglet *Actions* > « Compiler l'exécutable Windows » > *Run workflow*.
  Récupère l'artefact `AutoVisuel-windows`, remplis `.env` et `info.xlsx` à côté du `.exe`, puis double-clique (mode planificateur).
- **Publication sans PC allumé** : le workflow « Publication automatique » tourne à 08:00 et 19:30 UTC.
  1. Utilise un dépôt **privé** et commite ton `info.xlsx`.
  2. *Settings > Secrets and variables > Actions* : ajoute `GEMINI_API_KEY`, `GROQ_API_KEY`, `FB_PAGE_ID`, `FB_PAGE_TOKEN`,
     `TIKTOK_CLIENT_KEY`, `TIKTOK_CLIENT_SECRET`, `TIKTOK_ACCESS_TOKEN`, `TIKTOK_REFRESH_TOKEN`.
  3. Si TikTok renouvelle le refresh token, mets à jour le secret correspondant.
  Adapte les heures du `cron` (en UTC) si ton fuseau change.

## Bonnes pratiques
Ne publie jamais `.env`. Garde un rythme raisonnable (2 posts/jour) et varie les slogans : les plateformes
peuvent signaler un contenu répétitif comme du spam.
