from __future__ import annotations
import json
from datetime import datetime
from zoneinfo import ZoneInfo
from .config import BASE

FILE = BASE / "data" / "state.json"


def _load() -> dict:
    try:
        return json.loads(FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"posts": []}


def posts_today(tz: str) -> int:
    today = datetime.now(ZoneInfo(tz)).date().isoformat()
    return sum(1 for p in _load()["posts"] if p.get("date") == today)


def recent_headlines(n: int = 10) -> list[str]:
    return [p.get("headline", "") for p in _load()["posts"][-n:]]


def record(tz: str, headline: str, results: dict) -> None:
    data = _load()
    now = datetime.now(ZoneInfo(tz))
    data["posts"].append({"date": now.date().isoformat(), "time": now.strftime("%H:%M"),
                          "headline": headline, "results": results})
    data["posts"] = data["posts"][-200:]
    FILE.parent.mkdir(parents=True, exist_ok=True)
    FILE.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
