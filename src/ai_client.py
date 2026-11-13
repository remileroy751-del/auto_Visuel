from __future__ import annotations
import json
import logging
import os
import random
import re
import requests

log = logging.getLogger("autovisuel")

SYSTEM = ("Tu es un copywriter expert en marketing direct et en vente de produits digitaux "
          "(formations, logiciels). Tu écris des textes courts, percutants, qui déclenchent l'achat. "
          "Tu réponds UNIQUEMENT avec un objet JSON valide, sans texte autour.")


def _keys(env_name: str) -> list[str]:
    return [k.strip() for k in os.getenv(env_name, "").split(",") if k.strip()]


def _prompt(projet: dict, slogans: list[str], langue: str, history: list[str]) -> str:
    sample = random.sample(slogans, min(len(slogans), 4))
    infos = "\n".join(f"- {k} : {v}" for k, v in projet.items()) or "- (aucune information)"
    avoid = "\n".join(f"- {h}" for h in history if h) or "- (aucun)"
    return f"""Langue : {langue}.
Produit à vendre :
{infos}

Slogans / phrases déclencheurs existants (source d'inspiration) :
{chr(10).join('- ' + s for s in sample)}

Mission : COMBINE et reformule ces idées en UNE publicité visuelle inédite, pour réseaux sociaux.
Évite de répéter ces accroches déjà utilisées :
{avoid}

Réponds avec ce JSON exact :
{{"headline": "accroche choc, 8 mots maximum",
 "subline": "bénéfice concret ou preuve, 14 mots maximum",
 "cta": "appel à l'action, 4 mots maximum",
 "caption": "légende du post, 2 à 4 phrases persuasives avec un appel à l'action",
 "hashtags": ["5 à 8 hashtags pertinents"],
 "image_query": "3 à 4 mots-clés EN ANGLAIS pour trouver une photo de fond professionnelle (ex: young entrepreneur laptop office)",
 "image_prompt": "UNE phrase EN ANGLAIS décrivant une photo de fond cinématographique réaliste liée au produit, sans texte ni lettres"}}"""


def _gemini(prompt: str, key: str, model: str) -> str:
    r = requests.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
        headers={"x-goog-api-key": key, "Content-Type": "application/json"},
        json={"systemInstruction": {"parts": [{"text": SYSTEM}]},
              "contents": [{"parts": [{"text": prompt}]}],
              "generationConfig": {"temperature": 1.0, "responseMimeType": "application/json"}},
        timeout=60)
    r.raise_for_status()
    return r.json()["candidates"][0]["content"]["parts"][0]["text"]


def _groq(prompt: str, key: str, model: str) -> str:
    r = requests.post(
        "https://api.groq.com/openai/v1/chat/completions",
        headers={"Authorization": f"Bearer {key}"},
        json={"model": model, "temperature": 1.0, "response_format": {"type": "json_object"},
              "messages": [{"role": "system", "content": SYSTEM}, {"role": "user", "content": prompt}]},
        timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def _parse(text: str) -> dict:
    m = re.search(r"\{.*\}", text, re.S)
    data = json.loads(m.group(0) if m else text)
    for k in ("headline", "subline", "cta", "caption"):
        if not str(data.get(k, "")).strip():
            raise ValueError(f"champ manquant : {k}")
    tags = data.get("hashtags") or []
    if isinstance(tags, str):
        tags = tags.split()
    data["hashtags"] = [("#" + t.lstrip("#")) for t in tags if t]
    return data


def _offline(projet: dict, slogans: list[str]) -> dict:
    """Secours sans IA : combine simplement les phrases du fichier Excel."""
    a, b = random.sample(slogans, 2)
    benefits = [x.strip() for x in re.split(r"[;\n|]", projet.get("benefices", "")) if x.strip()]
    return {"headline": a, "subline": random.choice(benefits) if benefits else b,
            "cta": projet.get("cta", "Je me lance maintenant"),
            "caption": f"{a}. {b}", "hashtags": [], "source": "hors-ligne",
            "image_query": projet.get("fond_mots_cles", "business success entrepreneur laptop")}


def generate_copy(cfg: dict, projet: dict, slogans: list[str], history: list[str]) -> dict:
    prompt = _prompt(projet, slogans, cfg["langue"], history)
    providers = {"gemini": (_gemini, "GEMINI_API_KEY", cfg["ia"]["gemini_model"]),
                 "groq": (_groq, "GROQ_API_KEY", cfg["ia"]["groq_model"])}
    for name in cfg["ia"]["ordre"]:
        if name not in providers:
            continue
        fn, env, model = providers[name]
        for i, key in enumerate(_keys(env), 1):
            try:
                data = _parse(fn(prompt, key, model))
                data["source"] = f"{name}#{i}"
                log.info("Texte généré par %s (clé %d)", name, i)
                return data
            except Exception as e:  # quota, réseau, JSON invalide... on passe au suivant
                log.warning("%s (clé %d) a échoué : %s", name, i, e)
    log.warning("Aucune IA disponible : mode hors-ligne (combinaison simple des slogans).")
    return _offline(projet, slogans)


def full_caption(copy: dict, projet: dict) -> str:
    parts = [copy["caption"].strip()]
    if projet.get("lien"):
        parts.append(f"👉 {projet['lien']}")
    if copy.get("hashtags"):
        parts.append(" ".join(copy["hashtags"]))
    return "\n\n".join(parts)
