"""Add ordinary flick accents to the existing MASTER cache without retiming it."""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from flick_chart import MASTER_FLICK_REVISION, add_master_flicks


def migrate_cache(cache):
    """Copy a cache and update only MASTER notes, counts, and revision metadata."""
    result = deepcopy(cache)
    for song_key, entry in result.items():
        master = entry.get("difficulty_charts", {}).get("master")
        if not master:
            continue
        notes = add_master_flicks(master["notes"], entry["bpm"], entry.get("offset", 0.0), song_key)
        master["notes"] = notes
        counts = Counter(note["type"] for note in notes)
        master["type_counts"] = {kind: counts[kind] for kind in ("TAP", "HOLD", "SLIDE", "FLICK")}
        master["flick_revision"] = MASTER_FLICK_REVISION
        entry["flick_revision"] = MASTER_FLICK_REVISION
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cache", type=Path, default=ROOT / "auto_charts.json")
    parser.add_argument("--apply", action="store_true", help="Write the updated cache")
    args = parser.parse_args()
    cache = json.loads(args.cache.read_text(encoding="utf-8"))
    result = migrate_cache(cache)
    for song_key, entry in result.items():
        master = entry.get("difficulty_charts", {}).get("master", {})
        counts = master.get("type_counts", {})
        print(f"{song_key}: {counts.get('FLICK', 0)} flicks / {len(master.get('notes', []))} MASTER notes")
    if args.apply:
        args.cache.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
