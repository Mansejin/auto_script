#!/bin/sh
# NAS SSH: remove example samples
#   cd /volume1/docker/saenggibu && sh scripts/nas-cleanup-example-samples.sh

set -e
SAMPLES_DIR="${NAS_SAMPLES_DIR:-/volume1/docker/saenggibu/data/saenggibu/samples}"
INDEX="$SAMPLES_DIR/index.json"

if [ ! -f "$INDEX" ]; then
  echo "ERROR: $INDEX not found"
  exit 1
fi

python3 << 'PY'
import json
import os
from pathlib import Path

samples_dir = Path(os.environ.get("NAS_SAMPLES_DIR", "/volume1/docker/saenggibu/data/saenggibu/samples"))
index_path = samples_dir / "index.json"
items = json.loads(index_path.read_text(encoding="utf-8"))
patterns = ("2025_2학년_샘플", "【예시】", "샘플A", "샘플B")

def is_example(item):
    label = str(item.get("label", ""))
    source = str(item.get("source_file", ""))
    if any(p in label for p in patterns):
        return True
    if "examples/sample_" in source or "saenggibu-samples.example" in source:
        return True
    return False

remove = [x for x in items if is_example(x)]
keep = [x for x in items if not is_example(x)]
if not remove:
    print("No example samples to remove.")
    raise SystemExit(0)

print(f"Removing {len(remove)} sample(s):")
for r in remove:
    print(f"  - {r.get('label')} ({r.get('id')})")
    p = samples_dir / f"{r.get('id')}.json"
    if p.exists():
        p.unlink()

index_path.write_text(json.dumps(keep, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"Done. {len(keep)} left.")
PY
