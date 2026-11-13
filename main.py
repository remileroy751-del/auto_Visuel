#!/usr/bin/env python3
"""AutoVisuel - génère des visuels/vidéos de vente et les publie sur Facebook et TikTok."""
from __future__ import annotations
import argparse
import logging
import sys
from datetime import datetime
from pathlib import Path

from src.config import BASE, load_config
from src import ai_client, backgrounds, excel_loader, publishers, state, video, visual

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S")
log = logging.getLogger("autovisuel")


def info_path(cfg, arg):
    p = Path(arg or cfg["info_file"])
    return p if p.is_absolute() else BASE / p


def run_once(cfg: dict, info: Path, publish: bool = True, force: bool = False):
    tz = cfg["planning"]["fuseau_horaire"]
    if publish and not force and state.posts_today(tz) >= cfg["planning"]["max_par_jour"]:
        log.warning("Limite de %d publication(s)/jour atteinte : rien à faire.", cfg["planning"]["max_par_jour"])
        return None

    slogans, projet = excel_loader.load_info(info)
    log.info("%d slogans chargés, projet : %s", len(slogans), projet.get("nom", "(sans nom)"))
    copy = ai_client.generate_copy(cfg, projet, slogans, state.recent_headlines())
    log.info("Accroche : %s", copy["headline"])

    out = BASE / cfg["dossiers"]["sortie"] / datetime.now().strftime("%Y%m%d_%H%M%S")
    pal = visual.pick_palette(projet)
    vsize = (cfg["video"]["largeur"], cfg["video"]["hauteur"])
    photo = backgrounds.fetch_background(cfg, copy, projet, vsize)
    story = visual.build_visual(copy, projet, vsize, out, "story", pal, photo)
    post = visual.build_visual(copy, projet, (1080, 1350), out, "post", pal, photo)
    mp4 = video.make_video(cfg, story, out / "video.mp4")
    caption = ai_client.full_caption(copy, projet)
    (out / "caption.txt").write_text(caption, encoding="utf-8")
    log.info("Fichiers générés dans %s", out)

    if not publish:
        return out
    if cfg["mode_validation"] and sys.stdin.isatty():
        print(f"\nAperçu : {out}\n\n{caption}\n")
        if input("Publier ? [o/N] ").strip().lower() not in ("o", "oui", "y", "yes"):
            log.info("Publication annulée.")
            return out

    results = {}
    if cfg["facebook"]["actif"]:
        try:
            results["facebook"] = publishers.post_facebook(cfg, caption, mp4, post["flat"])
        except Exception as e:
            log.error("Facebook : %s", e)
            results["facebook"] = f"erreur: {e}"
    if cfg["tiktok"]["actif"]:
        try:
            results["tiktok"] = publishers.post_tiktok(cfg, caption, mp4)
        except Exception as e:
            log.error("TikTok : %s", e)
            results["tiktok"] = f"erreur: {e} | copie manuelle: {publishers.save_for_manual(cfg, mp4, caption)}"
    log.info("Résultats : %s", results)
    state.record(tz, copy["headline"], results)
    return out


def run_scheduler(cfg: dict, info: Path):
    from apscheduler.schedulers.blocking import BlockingScheduler
    from apscheduler.triggers.cron import CronTrigger
    tz = cfg["planning"]["fuseau_horaire"]
    sch = BlockingScheduler(timezone=tz)
    for hhmm in cfg["planning"]["publications"][: cfg["planning"]["max_par_jour"]]:
        h, m = hhmm.split(":")
        sch.add_job(lambda: _safe(cfg, info), CronTrigger(hour=int(h), minute=int(m), timezone=tz),
                    misfire_grace_time=3600, coalesce=True)
        log.info("Publication planifiée chaque jour à %s (%s)", hhmm, tz)
    log.info("Planificateur actif. Ctrl+C pour arrêter.")
    try:
        sch.start()
    except (KeyboardInterrupt, SystemExit):
        pass


def _safe(cfg, info):
    try:
        run_once(cfg, info)
    except Exception:
        log.exception("Échec de la publication planifiée")


def check(cfg: dict, info: Path):
    slogans, projet = excel_loader.load_info(info)
    print(f"OK - {len(slogans)} slogans, {len(projet)} champs projet.")
    import os
    for k in ("GEMINI_API_KEY", "GROQ_API_KEY", "POLLINATIONS_API_KEY", "PEXELS_API_KEY", "FB_PAGE_ID", "FB_PAGE_TOKEN",
              "TIKTOK_CLIENT_KEY", "TIKTOK_ACCESS_TOKEN", "TIKTOK_REFRESH_TOKEN"):
        print(f"  {k:22} {'défini' if os.getenv(k) else 'ABSENT'}")


ENV_KEYS = [
    ("GEMINI_API_KEY", "Clé Gemini (texte IA)  -> aistudio.google.com/apikey"),
    ("GROQ_API_KEY", "Clé Groq (texte IA, secours)  -> console.groq.com/keys"),
    ("POLLINATIONS_API_KEY", "Clé Pollinations (illustrations IA de fond)  -> enter.pollinations.ai"),
    ("PEXELS_API_KEY", "Clé Pexels (belles photos de fond)  -> pexels.com/api"),
    ("FB_PAGE_ID", "Facebook : ID de la Page"),
    ("FB_PAGE_TOKEN", "Facebook : token de Page"),
    ("TIKTOK_CLIENT_KEY", "TikTok : client key"),
    ("TIKTOK_CLIENT_SECRET", "TikTok : client secret"),
    ("TIKTOK_ACCESS_TOKEN", "TikTok : access token"),
    ("TIKTOK_REFRESH_TOKEN", "TikTok : refresh token"),
]


def setup():
    """Assistant : saisie des clés API et création automatique du fichier .env."""
    from dotenv import dotenv_values, load_dotenv
    path = BASE / "cles.env" if (BASE / "cles.env").exists() else BASE / ".env"
    cur = dict(dotenv_values(path)) if path.exists() else {}
    print("\n=== Configuration des clés API ===")
    print("Colle chaque clé puis Entrée. Laisse vide + Entrée pour passer (ou garder la valeur actuelle).\n")
    for key, label in ENV_KEYS:
        v = input(f"{label}\n  {key} [{'déjà défini' if cur.get(key) else 'vide'}] : ").strip()
        if v:
            cur[key] = v
    path.write_text("\n".join(f"{k}={v}" for k, v in cur.items() if v) + "\n", encoding="utf-8")
    load_dotenv(path, override=True)
    print(f"\nClés enregistrées dans {path}\n")


def main():
    frozen = getattr(sys, "frozen", False)
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("commande", nargs="?", default="schedule" if frozen else "check",
                    choices=["check", "preview", "run", "schedule", "setup"],
                    help="check: vérifie le fichier et les clés | preview: génère sans publier | "
                         "run: génère et publie maintenant | schedule: publie aux heures du config.yaml | "
                         "setup: saisie guidée des clés API (crée le .env)")
    ap.add_argument("--info", help="chemin du fichier Excel (défaut : info.xlsx)")
    ap.add_argument("--config", help="chemin du config.yaml")
    ap.add_argument("--force", action="store_true", help="ignore la limite quotidienne")
    a = ap.parse_args()
    if a.commande == "setup" or (frozen and len(sys.argv) == 1 and not any((BASE / n).exists() for n in (".env", "cles.env"))):
        setup()
        if a.commande == "setup":
            return
    cfg = load_config(a.config)
    info = info_path(cfg, a.info)
    try:
        if a.commande == "check":
            check(cfg, info)
        elif a.commande == "preview":
            run_once(cfg, info, publish=False)
        elif a.commande == "run":
            run_once(cfg, info, force=a.force)
        else:
            run_scheduler(cfg, info)
    except (FileNotFoundError, ValueError) as e:
        log.error("%s", e)
        sys.exit(1)


if __name__ == "__main__":
    main()
