"""Reduce dense MASTER runs after 25s without moving the remaining attacks."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
path = ROOT / "auto_charts.json"
entries = json.loads(path.read_text(encoding="utf-8"))
entry = entries["hatsune-miku-no-shoushitsu"]
revision = "20261004-lighter-runs-v2"
if entry.get("balance_revision") != revision:
    variant = entry["difficulty_charts"]["master"]
    notes = variant["notes"]
    seconds_per_beat = 60 / entry["bpm"]
    offset = entry.get("offset", 0)
    kept = []
    for index, note in enumerate(notes):
        seconds = offset + note["beat"] * seconds_per_beat
        slot = round(note["beat"] * 4)
        dense = (0 < index < len(notes) - 1
                 and (note["beat"] - notes[index - 1]["beat"]) * seconds_per_beat <= 0.08
                 and (notes[index + 1]["beat"] - note["beat"]) * seconds_per_beat <= 0.08)
        # Rest on selected weak sixteenths; keep beat accents and sparse phrases.
        if seconds >= 25 and note["type"] == "TAP" and dense and slot % 16 in (1, 3, 7, 9, 11, 15):
            continue
        kept.append(note)
    variant.update(notes=kept, selected_count=len(kept),
                   type_counts={kind: sum(n["type"] == kind for n in kept)
                                for kind in ("TAP", "HOLD", "SLIDE")})
    entry["balance_revision"] = revision
    path.write_text(json.dumps(entries, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Shoushitsu MASTER: {len(notes)} -> {len(kept)} ({len(notes)-len(kept)} removed)")
else:
    print("Balance revision already applied.")
