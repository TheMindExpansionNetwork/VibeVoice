"""Modal wrapper for Microsoft VibeVoice-Realtime-0.5B.

Jimsky/Mind Expansion use case: fast voice proof for digital entities, workshop narration,
voice-pilot demos, and podcast/dialogue prototypes without downloading models locally.

Safety:
- CPU prefetch caches the HF model in a Modal volume.
- GPU synthesis is a separate bounded function that scales to zero.
- Outputs are stored in a Modal volume and can be pulled locally.
"""
from __future__ import annotations

import json
from pathlib import Path

import modal

APP_NAME = "hermes-vibevoice-realtime"
MODEL_ID = "microsoft/VibeVoice-Realtime-0.5B"
CACHE_DIR = "/cache/huggingface"
REPO_DIR = "/opt/VibeVoice"
OUTPUT_ROOT = "/outputs/vibevoice-realtime"

app = modal.App(APP_NAME)
cache_vol = modal.Volume.from_name("vibevoice-cache", create_if_missing=True)
out_vol = modal.Volume.from_name("vibevoice-outputs", create_if_missing=True)

base_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git", "ffmpeg", "libsndfile1", "curl", "ca-certificates")
    .pip_install(
        "huggingface_hub>=0.25.0",
        "hf_transfer>=0.1.8",
        "soundfile>=0.12.1",
    )
    # Install VibeVoice from upstream code. Keep this intentionally in the image so
    # the local wrapper can stay tiny and repo-independent.
    .run_commands(
        "git clone --depth 1 https://github.com/microsoft/VibeVoice.git /opt/VibeVoice",
        "cd /opt/VibeVoice && pip install -e '.[streamingtts]'",
    )
    .env(
        {
            "HF_HOME": CACHE_DIR,
            "HF_HUB_CACHE": f"{CACHE_DIR}/hub",
            "HF_HUB_ENABLE_HF_TRANSFER": "1",
            "PYTHONUNBUFFERED": "1",
        }
    )
)


def _du(path: str) -> int:
    total = 0
    p = Path(path)
    if p.exists():
        for f in p.rglob("*"):
            if f.is_file():
                try:
                    total += f.stat().st_size
                except FileNotFoundError:
                    pass
    return total


@app.function(
    image=base_image,
    cpu=2.0,
    memory=8192,
    timeout=1800,
    volumes={"/cache": cache_vol, "/outputs": out_vol},
)
def prefetch_model() -> str:
    """CPU-only model cache warmup; no GPU spend."""
    from huggingface_hub import snapshot_download

    path = snapshot_download(repo_id=MODEL_ID, cache_dir=CACHE_DIR)
    cache_vol.commit()
    payload = {
        "ok": True,
        "model": MODEL_ID,
        "snapshot_path": path,
        "cache_bytes": _du(CACHE_DIR),
        "cache_gb": round(_du(CACHE_DIR) / 1e9, 3),
    }
    return json.dumps(payload)


@app.function(
    image=base_image,
    gpu="L4",
    cpu=4.0,
    memory=24576,
    timeout=1800,
    volumes={"/cache": cache_vol, "/outputs": out_vol},
    scaledown_window=60,
)
def synthesize_jimsky_voice(
    text: str,
    speaker: str = "Carter",
    run_name: str = "jimsky_vibevoice_demo",
    cfg_scale: float = 1.5,
) -> str:
    """Generate a short voice clip with VibeVoice-Realtime-0.5B."""
    import os
    import platform
    import shutil
    import subprocess
    import time

    import torch

    safe_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in run_name)[:80]
    out_dir = Path(OUTPUT_ROOT) / safe_name
    out_dir.mkdir(parents=True, exist_ok=True)
    text_path = out_dir / "script.txt"
    text_path.write_text(text.strip() + "\n", encoding="utf-8")

    cmd = [
        "python",
        "demo/realtime_model_inference_from_file.py",
        "--model_path",
        MODEL_ID,
        "--txt_path",
        str(text_path),
        "--speaker_name",
        speaker,
        "--output_dir",
        str(out_dir),
        "--device",
        "cuda",
        "--cfg_scale",
        str(cfg_scale),
    ]
    started = time.time()
    proc = subprocess.run(
        cmd,
        cwd=REPO_DIR,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=1700,
    )
    elapsed = time.time() - started
    log_path = out_dir / "run.log"
    log_path.write_text(proc.stdout, encoding="utf-8", errors="replace")

    wavs = sorted(str(p) for p in out_dir.glob("*.wav"))
    mp3s = []
    for wav in wavs:
        mp3 = str(Path(wav).with_suffix(".mp3"))
        subprocess.run(["ffmpeg", "-y", "-i", wav, "-codec:a", "libmp3lame", "-q:a", "3", mp3], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if Path(mp3).exists():
            mp3s.append(mp3)

    payload = {
        "ok": proc.returncode == 0 and bool(wavs),
        "model": MODEL_ID,
        "speaker": speaker,
        "run_name": safe_name,
        "output_dir": str(out_dir),
        "wavs": wavs,
        "mp3s": mp3s,
        "log_path": str(log_path),
        "elapsed_seconds": round(elapsed, 3),
        "returncode": proc.returncode,
        "torch": torch.__version__,
        "cuda": torch.cuda.is_available(),
        "device": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
        "python": platform.python_version(),
        "cache_gb": round(_du(CACHE_DIR) / 1e9, 3),
    }
    (out_dir / "result.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    out_vol.commit()
    return json.dumps(payload)


@app.local_entrypoint()
def main(mode: str = "demo"):
    if mode == "prefetch":
        print(json.dumps(json.loads(prefetch_model.remote()), indent=2))
    elif mode == "demo":
        script = (
            "Jimsky voice pilot online. Tonight we turn digital entities into teammates: "
            "humans pilot, train, and verify them until they can help build worlds, music, films, "
            "and local business tools. This is not replacement. This is a new workshop economy."
        )
        print(json.dumps(json.loads(synthesize_jimsky_voice.remote(script, speaker="Carter", run_name="jimsky_history_voice_pilot")), indent=2))
    else:
        raise SystemExit(f"Unknown mode: {mode}")
