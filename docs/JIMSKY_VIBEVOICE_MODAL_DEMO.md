# Jimsky VibeVoice Realtime Modal Demo

This fork branch packages Microsoft VibeVoice-Realtime-0.5B as a bounded Modal workflow for digital-entity voice demos.

## Why this branch exists

Jimsky / Mindbotz needs a reusable way to give digital entities safe, disclosed, fictional voices for:

- workshop narration,
- agent proof-of-work reports,
- live demo booth hosts,
- podcast/story pilots,
- Matrix-Game / Mindverse trailer narration,
- local-business explainer assets.

## Files

- `modal/vibevoice_realtime_modal_app.py` — Modal wrapper with CPU prefetch and L4 synthesis.

## Commands

```bash
set -a; . /opt/data/.env >/dev/null 2>&1; set +a
/opt/data/hermes-agent/venv/bin/modal run modal/vibevoice_realtime_modal_app.py --mode prefetch
/opt/data/hermes-agent/venv/bin/modal run modal/vibevoice_realtime_modal_app.py --mode demo
```

## Verified proof run

- Model: `microsoft/VibeVoice-Realtime-0.5B`
- Modal app: `hermes-vibevoice-realtime`
- Cache volume: `vibevoice-cache`
- Output volume: `vibevoice-outputs`
- GPU: `NVIDIA L4`
- Output: `script_generated.mp3` / `script_generated.wav`
- Audio duration: `14.856s`
- Model generation time from log: `10.03s`
- RTF from log: `0.68x`
- Modal cost for VibeVoice work that day: `$0.02205088`
- Modal status after run: `Tasks: 0`

## Public proof page

https://themindexpansionnetwork.github.io/jimsky-realm-shards-datasets-pages/vibevoice-realtime.html

## Responsible use

This branch is intended for research, prototyping, and disclosed fictional/digital-entity audio. Do not use it to impersonate real people or create misleading speech. Public clips should include an AI-generated speech disclosure and proof metadata.
