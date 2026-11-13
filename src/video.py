from __future__ import annotations
import logging
import random
import shutil
import subprocess
from pathlib import Path
from .config import BASE

log = logging.getLogger("autovisuel")
AUDIO_EXT = {".mp3", ".wav", ".m4a", ".ogg", ".aac"}


def ffmpeg_exe() -> str:
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        exe = shutil.which("ffmpeg")
        if not exe:
            raise RuntimeError("FFmpeg introuvable (pip install imageio-ffmpeg ou installe ffmpeg).")
        return exe


def _pick_music(cfg: dict) -> Path | None:
    if not cfg["video"].get("musique", True):
        return None
    folder = BASE / cfg["dossiers"]["musique"]
    files = [f for f in folder.glob("*") if f.suffix.lower() in AUDIO_EXT] if folder.exists() else []
    return random.choice(files) if files else None


def make_video(cfg: dict, visual: dict, out_path: Path) -> Path:
    """Image -> MP4 vertical : zoom lent + apparition en fondu du titre, du sous-titre et du bouton."""
    v = cfg["video"]
    dur, fps, W, H = int(v["duree"]), int(v["fps"]), int(v["largeur"]), int(v["hauteur"])
    frames = dur * fps
    music = _pick_music(cfg)

    cmd = [ffmpeg_exe(), "-y", "-loglevel", "error",
           "-i", str(visual["bg"])]
    for p in visual["layers"]:
        cmd += ["-loop", "1", "-framerate", str(fps), "-t", str(dur), "-i", str(p)]
    if music:
        cmd += ["-stream_loop", "-1", "-i", str(music)]
    else:
        cmd += ["-f", "lavfi", "-t", str(dur), "-i", "anullsrc=r=44100:cl=stereo"]

    # apparition à 0.5 s, 3 s et 6 s
    starts = [0.5, 3.0, 6.0]
    fc = (f"[0:v]scale={int(W*1.5)}:{int(H*1.5)},"
          f"zoompan=z='1+0.18*on/{frames}':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)':d={frames}:s={W}x{H}:fps={fps}[base];")
    for i, s in enumerate(starts, 1):
        fc += f"[{i}:v]format=rgba,fade=t=in:st={s}:d=0.8:alpha=1[o{i}];"
    fc += "[base][o1]overlay=0:0[m1];[m1][o2]overlay=0:0[m2];[m2][o3]overlay=0:0,format=yuv420p[v];"
    fc += f"[4:a]atrim=0:{dur},afade=t=in:d=0.5,afade=t=out:st={dur-1}:d=1[a]"

    cmd += ["-filter_complex", fc, "-map", "[v]", "-map", "[a]",
            "-t", str(dur), "-r", str(fps),
            "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(out_path)]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError("FFmpeg a échoué :\n" + res.stderr[-1500:])
    log.info("Vidéo créée : %s (%.1f Mo)", out_path, out_path.stat().st_size / 1e6)
    return out_path
