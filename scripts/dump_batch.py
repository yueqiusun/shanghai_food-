import glob
import json
import os

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
DETAILS_DIR = os.path.join(DATA_DIR, "details")
BATCHES_DIR = os.path.join(DATA_DIR, "batches")


def main():
    os.makedirs(BATCHES_DIR, exist_ok=True)
    items = []
    for fp in glob.glob(os.path.join(DETAILS_DIR, "*.json")):
        with open(fp, "r", encoding="utf-8") as f:
            items.append(json.load(f))

    items.sort(key=lambda x: (x.get("pubdate_str", ""), x.get("bvid", "")), reverse=True)
    batch_size = 30
    total_batches = (len(items) + batch_size - 1) // batch_size

    for b in range(total_batches):
        start = b * batch_size
        chunk = items[start : start + batch_size]
        out_path = os.path.join(BATCHES_DIR, f"batch_{b}.txt")
        lines = [f"=== BATCH {b} ({start}..{start + len(chunk) - 1} of {len(items)}) ==="]
        for i, d in enumerate(chunk, start):
            lines.append(f"\n--- [{i}] {d['bvid']} | {d.get('pubdate_str')} | series={d.get('series_tags')} ---")
            lines.append(f"TITLE: {d.get('title')}")
            desc = (d.get("description") or "").strip()
            if desc and desc != "-":
                lines.append(f"DESC: {desc[:300]}")
            pc = d.get("pinned_comment")
            if pc and pc.get("message"):
                lines.append(f"PINNED({pc.get('uname')}): {pc['message'][:400]}")
            for hc in (d.get("hot_comments") or [])[:5]:
                msg = (hc.get("message") or "").replace("\n", " ")
                lines.append(f"COMMENT({hc.get('like', 0)}赞): {msg[:300]}")
        with open(out_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))

    print(f"Wrote {total_batches} batch files to {BATCHES_DIR}")


if __name__ == "__main__":
    main()
