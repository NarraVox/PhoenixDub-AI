import json
from pathlib import Path

path = Path("uploads/video_COMPUTER_VILLAGE_3__Full_Movie__The_a2e7ad/transcription_cache.json")
if path.exists():
    data = json.load(open(path, "r", encoding="utf-8"))
    target_ids = ["seg_2", "seg_3", "seg_4", "seg_5", "seg_6", "seg_7", "seg_8", "seg_10", "seg_11", "seg_13", "seg_14", "seg_15", "seg_18", "seg_19"]
    for s in data:
        if s["id"] in target_ids:
            print(f"{s['id']}: {s.get('text', '')}")
else:
    print("transcription_cache.json not found")
