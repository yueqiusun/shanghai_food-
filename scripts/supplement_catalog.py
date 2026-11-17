import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_client import BiliClient

UID = 452606628
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CATALOG_PATH = os.path.join(DATA_DIR, "catalog.json")
TZ_CN = timezone(timedelta(hours=8))

KEYWORDS = [
    "王师傅和小毛毛",
    "王师傅和小毛毛 上海",
    "王师傅和小毛毛 探店",
    "王师傅和小毛毛 餐厅",
    "王师傅和小毛毛 吃",
    "王师傅和小毛毛 美食",
]


def strip_em(s: str) -> str:
    return re.sub(r"</?em[^>]*>", "", s or "")


def save_cat(cat: dict, videos_by_bvid: dict):
    videos = sorted(videos_by_bvid.values(), key=lambda x: x.get("created", 0), reverse=True)
    cat["videos"] = videos
    cat["total_fetched"] = len(videos)
    cat["fetched_at"] = datetime.now(tz=TZ_CN).isoformat()
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(cat, f, ensure_ascii=False, indent=2)


def main():
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        cat = json.load(f)

    videos_by_bvid = {v["bvid"]: v for v in cat.get("videos") or []}
    before = len(videos_by_bvid)

    client = BiliClient(delay_range=(1.2, 1.8))
    client.init_session()

    for kw in KEYWORDS:
        added_kw = 0
        for pg in range(1, 11):
            try:
                r = client.get_json(
                    "https://api.bilibili.com/x/web-interface/search/type",
                    {"search_type": "video", "keyword": kw, "page": pg, "page_size": 50},
                )
            except RuntimeError as e:
                print(f"[WARN] Stopping search on '{kw}' p{pg}: {e}")
                save_cat(cat, videos_by_bvid)
                print(f"Saved partial catalog: {before} -> {len(videos_by_bvid)} (+{len(videos_by_bvid) - before})")
                return

            if r.get("code") != 0:
                print(f"[WARN] search {kw} p{pg} code={r.get('code')}")
                break
            res = (r.get("data") or {}).get("result") or []
            if not res:
                break
            for item in res:
                if item.get("mid") != UID:
                    continue
                bvid = item.get("bvid")
                if not bvid or bvid in videos_by_bvid:
                    continue
                pub_ts = item.get("pubdate") or 0
                pubdate_str = datetime.fromtimestamp(pub_ts, tz=TZ_CN).strftime("%Y-%m-%d")
                videos_by_bvid[bvid] = {
                    "aid": item.get("aid"),
                    "bvid": bvid,
                    "title": strip_em(item.get("title", "")),
                    "description": strip_em(item.get("description", "")),
                    "created": pub_ts,
                    "pubdate_str": pubdate_str,
                    "length": item.get("duration", ""),
                    "play": item.get("play", 0),
                    "comment": item.get("review", 0),
                    "typeid": item.get("typeid"),
                    "pic": item.get("pic", ""),
                    "video_url": f"https://www.bilibili.com/video/{bvid}",
                    "is_union_video": 0,
                    "series_tags": [],
                }
                added_kw += 1
            if len(res) < 50:
                break
        save_cat(cat, videos_by_bvid)
        print(f"Keyword '{kw}': +{added_kw} new (total={len(videos_by_bvid)})")

    print(f"Catalog updated: {before} -> {len(videos_by_bvid)} videos (+{len(videos_by_bvid) - before})")


if __name__ == "__main__":
    main()
