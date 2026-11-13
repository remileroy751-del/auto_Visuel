from __future__ import annotations
import sys
from pathlib import Path
import yaml
from dotenv import load_dotenv


def _base_dir() -> Path:
    if getattr(sys, "frozen", False):          # exécutable PyInstaller
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE = _base_dir()
for _n in (".env", "cles.env"):
    load_dotenv(BASE / _n)

DEFAULTS = {
    "langue": "français",
    "info_file": "info.xlsx",
    "mode_validation": False,
    "planning": {"publications": ["08:00", "19:30"], "fuseau_horaire": "Africa/Lome", "max_par_jour": 2},
    "ia": {"ordre": ["gemini", "groq"], "gemini_model": "gemini-2.5-flash", "groq_model": "llama-3.3-70b-versatile"},
    "video": {"duree": 10, "fps": 30, "largeur": 1080, "hauteur": 1920, "musique": True},
    "facebook": {"actif": True, "type": "video"},
    "tiktok": {"actif": True, "privacy_level": "SELF_ONLY"},
    "dossiers": {"sortie": "output", "musique": "music"},
    "fond": {"ordre": ["pollinations", "gemini_image", "pexels"], "gemini_image_model": "gemini-2.5-flash-image",
             "pollinations_model": "flux"},
}


def _merge(a: dict, b: dict) -> dict:
    out = dict(a)
    for k, v in (b or {}).items():
        out[k] = _merge(out[k], v) if isinstance(v, dict) and isinstance(out.get(k), dict) else v
    return out


def load_config(path: str | None = None) -> dict:
    p = Path(path) if path else BASE / "config.yaml"
    user = yaml.safe_load(p.read_text(encoding="utf-8")) if p.exists() else {}
    return _merge(DEFAULTS, user or {})
