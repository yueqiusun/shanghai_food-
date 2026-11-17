import glob
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_client import BiliClient
from fetch_details import extract_comment_obj

DETAILS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "details"
)


def main():
    files = sorted(glob.glob(os.path.join(DETAILS_DIR, "*.json")))
    targets = []
    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            d = json.load(f)
        if not d.get("hot_comments") and not d.get("pinned_comment"):
            targets.append((fp, d))

    print(f"Targets missing comments: {len(targets)}")
    if not targets:
        return

    client = BiliClient(delay_range=(1.0, 1.5))
    client.init_session()

    updated = 0
    for idx, (fp, d) in enumerate(targets, 1):
        aid = d.get("aid")
        if not aid:
            continue
        pinned = None
        hot = []
        # Try x/v2/reply?sort=2 first (fewer 412s)
        try:
            r = client.get_json(
                "https://api.bilibili.com/x/v2/reply",
                {"type": 1, "oid": aid, "sort": 2, "ps": 20, "pn": 1},
            )
            if r.get("code") == 0:
                rdata = r.get("data") or {}
                upper_top = (rdata.get("upper") or {}).get("top")
                if upper_top:
                    pinned = extract_comment_obj(upper_top)
                for rep in (rdata.get("replies") or [])[:20]:
                    c = extract_comment_obj(rep)
                    if c:
                        hot.append(c)
        except Exception as e:
            print(f"[{idx}/{len(targets)}] {d['bvid']} reply failed: {e}")
            time.sleep(2.0)

        if pinned or hot:
            d["pinned_comment"] = pinned
            d["hot_comments"] = hot
            with open(fp, "w", encoding="utf-8") as f:
                json.dump(d, f, ensure_ascii=False, indent=2)
            updated += 1

        if idx % 20 == 0 or idx == len(targets):
            print(f"[{idx}/{len(targets)}] updated={updated}")

    print(f"Backfill complete: updated {updated}/{len(targets)} files.")


if __name__ == "__main__":
    main()
