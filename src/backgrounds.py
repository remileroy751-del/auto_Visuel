from __future__ import annotations
import base64
import io
import logging
import os
import random
import urllib.parse
import requests
from PIL import Image

log = logging.getLogger("autovisuel")


def _keys(name: str) -> list[str]:
    return [k.strip() for k in os.getenv(name, "").split(",") if k.strip()]


def _open(content: bytes) -> Image.Image:
    img = Image.open(io.BytesIO(content)).convert("RGB")
    if img.width < 500 or img.height < 500:
        raise ValueError("image trop petite")
    return img


def _pexels(query, prompt, size, cfg):
    """Vraies photos professionnelles (clé gratuite : pexels.com/api)."""
    keys = _keys("PEXELS_API_KEY")
    if not keys:
        return None
    r = requests.get("https://api.pexels.com/v1/search", headers={"Authorization": keys[0]},
                     params={"query": query, "orientation": "portrait", "size": "large", "per_page": 30}, timeout=30)
    r.raise_for_status()
    photos = r.json().get("photos", [])
    if not photos:
        raise ValueError(f"aucune photo Pexels pour « {query} »")
    src = random.choice(photos)["src"]
    img = requests.get(src.get("large2x") or src["large"], timeout=60)
    img.raise_for_status()
    return _open(img.content)


def _gemini_image(query, prompt, size, cfg):
    """Image générée par Gemini (même clé que le texte ; quota gratuit variable selon les pays)."""
    keys = _keys("GEMINI_API_KEY")
    if not keys:
        return None
    model = cfg["fond"]["gemini_image_model"]
    for key in keys:
        r = requests.post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                          headers={"x-goog-api-key": key, "Content-Type": "application/json"},
                          json={"contents": [{"parts": [{"text": prompt}]}],
                                "generationConfig": {"responseModalities": ["IMAGE"]}}, timeout=120)
        if not r.ok:
            log.warning("Gemini image : HTTP %s", r.status_code)
            continue
        for part in r.json()["candidates"][0]["content"]["parts"]:
            d = part.get("inlineData") or part.get("inline_data")
            if d:
                return _open(base64.b64decode(d["data"]))
    raise ValueError("Gemini n'a renvoyé aucune image")


def _pollinations(query, prompt, size, cfg):
    """Illustration IA via Pollinations (clé POLLINATIONS_API_KEY ; sans clé : accès anonyme limité)."""
    keys = _keys("POLLINATIONS_API_KEY")
    params = {"width": size[0], "height": size[1], "nologo": "true", "seed": random.randint(1, 10**6),
              "model": cfg["fond"].get("pollinations_model", "flux")}
    if keys:
        r = requests.get("https://gen.pollinations.ai/image/" + urllib.parse.quote(prompt), params=params,
                         headers={"Authorization": f"Bearer {keys[0]}"}, timeout=180)
    else:
        r = requests.get("https://image.pollinations.ai/prompt/" + urllib.parse.quote(prompt), params=params, timeout=120)
    r.raise_for_status()
    if "image" not in r.headers.get("content-type", ""):
        raise ValueError("réponse non image")
    return _open(r.content)


SOURCES = {"pexels": _pexels, "gemini_image": _gemini_image, "pollinations": _pollinations}


def fetch_background(cfg: dict, copy: dict, projet: dict, size) -> Image.Image | None:
    """Essaie chaque source dans l'ordre du config.yaml ; None => dégradé de secours."""
    query = copy.get("image_query") or projet.get("fond_mots_cles") or "business success entrepreneur"
    theme = copy.get("image_prompt") or f"professional cinematic illustration about {query}"
    prompt = (theme + ", vertical 9:16 composition, high quality, vivid colors, uncluttered center area left free "
              "for text overlay, no text, no letters, no words, no logo, no watermark")
    for name in cfg["fond"]["ordre"]:
        fn = SOURCES.get(name)
        if not fn:
            continue
        try:
            img = fn(query, prompt, size, cfg)
            if img:
                log.info("Fond obtenu via %s", name)
                return img
        except Exception as e:
            log.warning("Fond %s indisponible : %s", name, e)
    log.warning("Aucune photo de fond disponible : dégradé de secours.")
    return None
