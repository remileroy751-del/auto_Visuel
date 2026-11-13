from __future__ import annotations
import json
import logging
import os
import shutil
import time
from pathlib import Path
import requests
from .config import BASE

log = logging.getLogger("autovisuel")
FB_VERSION = "v21.0"
TOKENS = BASE / "data" / "tiktok_tokens.json"


class PublishError(Exception):
    pass


def _check(r: requests.Response, what: str):
    if not r.ok:
        raise PublishError(f"{what} : HTTP {r.status_code} - {r.text[:400]}")
    return r


# ------------------------------------------------------------------ Facebook (Page)
def post_facebook(cfg: dict, caption: str, video: Path, photo: Path) -> str:
    page_id, token = os.getenv("FB_PAGE_ID"), os.getenv("FB_PAGE_TOKEN")
    if not page_id or not token:
        raise PublishError("FB_PAGE_ID / FB_PAGE_TOKEN manquants dans .env")
    if cfg["facebook"]["type"] == "photo":
        with open(photo, "rb") as f:
            r = requests.post(f"https://graph.facebook.com/{FB_VERSION}/{page_id}/photos",
                              data={"caption": caption, "access_token": token}, files={"source": f}, timeout=300)
    else:
        with open(video, "rb") as f:
            r = requests.post(f"https://graph-video.facebook.com/{FB_VERSION}/{page_id}/videos",
                              data={"description": caption, "access_token": token}, files={"source": f}, timeout=900)
    _check(r, "Facebook")
    return "ok:" + str(r.json().get("id", ""))


# ------------------------------------------------------------------ TikTok
def _tiktok_access_token() -> str:
    key, secret = os.getenv("TIKTOK_CLIENT_KEY"), os.getenv("TIKTOK_CLIENT_SECRET")
    saved = json.loads(TOKENS.read_text()) if TOKENS.exists() else {}
    refresh = saved.get("refresh_token") or os.getenv("TIKTOK_REFRESH_TOKEN")
    if key and secret and refresh:      # le token d'accès dure 24 h : on le renouvelle à chaque publication
        r = requests.post("https://open.tiktokapis.com/v2/oauth/token/",
                          data={"client_key": key, "client_secret": secret,
                                "grant_type": "refresh_token", "refresh_token": refresh}, timeout=30)
        _check(r, "TikTok refresh")
        data = r.json()
        if data.get("access_token"):
            TOKENS.parent.mkdir(parents=True, exist_ok=True)
            TOKENS.write_text(json.dumps({"refresh_token": data.get("refresh_token", refresh)}))
            return data["access_token"]
    token = os.getenv("TIKTOK_ACCESS_TOKEN")
    if not token:
        raise PublishError("Aucun token TikTok (TIKTOK_ACCESS_TOKEN ou TIKTOK_REFRESH_TOKEN + clés)")
    return token


def post_tiktok(cfg: dict, caption: str, video: Path) -> str:
    token = _tiktok_access_token()
    size = video.stat().st_size
    body = {"post_info": {"title": caption[:2000], "privacy_level": cfg["tiktok"]["privacy_level"],
                          "disable_duet": False, "disable_comment": False, "disable_stitch": False},
            "source_info": {"source": "FILE_UPLOAD", "video_size": size, "chunk_size": size, "total_chunk_count": 1}}
    hdr = {"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8"}
    r = _check(requests.post("https://open.tiktokapis.com/v2/post/publish/video/init/", headers=hdr, json=body, timeout=60),
               "TikTok init")
    data = r.json().get("data") or {}
    if not data.get("upload_url"):
        raise PublishError(f"TikTok init sans upload_url : {r.text[:300]}")
    with open(video, "rb") as f:
        up = requests.put(data["upload_url"], data=f.read(), timeout=600,
                          headers={"Content-Type": "video/mp4", "Content-Length": str(size),
                                   "Content-Range": f"bytes 0-{size - 1}/{size}"})
    _check(up, "TikTok upload")
    status = "envoyé"
    for _ in range(6):                  # suivi rapide du traitement
        time.sleep(5)
        s = requests.post("https://open.tiktokapis.com/v2/post/publish/status/fetch/", headers=hdr,
                          json={"publish_id": data["publish_id"]}, timeout=30)
        status = (s.json().get("data") or {}).get("status", status) if s.ok else status
        if status in ("PUBLISH_COMPLETE", "FAILED"):
            break
    if status == "FAILED":
        raise PublishError("TikTok a refusé la vidéo (FAILED)")
    return f"ok:{data['publish_id']}:{status}"


def save_for_manual(cfg: dict, video: Path, caption: str) -> str:
    """Secours : la vidéo + la légende sont rangées pour une publication manuelle."""
    folder = BASE / cfg["dossiers"]["sortie"] / "tiktok_a_poster"
    folder.mkdir(parents=True, exist_ok=True)
    dest = folder / f"{video.parent.name}.mp4"
    shutil.copy(video, dest)
    dest.with_suffix(".txt").write_text(caption, encoding="utf-8")
    return str(dest)
