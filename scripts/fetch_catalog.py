import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_client import BiliClient

UID = 452606628
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CATALOG_PATH = os.path.join(DATA_DIR, "catalog.json")
TZ_CN = timezone(timedelta(hours=8))


def fetch_series_videos(client: BiliClient) -> tuple[dict, dict]:
    """Return ({bvid: [series_name, ...]}, {bvid: archive_dict}) from user's seasons and series."""
    bvid_to_series = {}
    bvid_to_archive = {}
    resp = client.get_json(
        "https://api.bilibili.com/x/polymer/web-space/seasons_series_list",
        {"mid": UID, "page_num": 1, "page_size": 20},
    )
    if resp.get("code") != 0:
        print(f"[WARN] seasons_series_list returned {resp.get('code')}")
        return bvid_to_series, bvid_to_archive

    items = (resp.get("data") or {}).get("items_lists") or {}
    for season in items.get("seasons_list") or []:
        meta = season.get("meta") or {}
        sid = meta.get("season_id")
        sname = meta.get("name", "")
        if not sid:
            continue
        pn = 1
        while True:
            r = client.get_json(
                "https://api.bilibili.com/x/polymer/web-space/seasons_archives_list",
                {"mid": UID, "season_id": sid, "sort_reverse": "false", "page_num": pn, "page_size": 50},
            )
            archives = (r.get("data") or {}).get("archives") or []
            if not archives:
                break
            for a in archives:
                bvid = a.get("bvid")
                if bvid:
                    bvid_to_series.setdefault(bvid, [])
                    if sname not in bvid_to_series[bvid]:
                        bvid_to_series[bvid].append(sname)
                    bvid_to_archive[bvid] = a
            if len(archives) < 50:
                break
            pn += 1

    for series in items.get("series_list") or []:
        meta = series.get("meta") or {}
        sid = meta.get("series_id")
        sname = meta.get("name", "")
        if not sid:
            continue
        pn = 1
        while True:
            r = client.get_json(
                "https://api.bilibili.com/x/series/archives",
                {"mid": UID, "series_id": sid, "only_normal": "true", "sort": "desc", "pn": pn, "ps": 50},
            )
            archives = (r.get("data") or {}).get("archives") or []
            if not archives:
                break
            for a in archives:
                bvid = a.get("bvid")
                if bvid:
                    bvid_to_series.setdefault(bvid, [])
                    if sname not in bvid_to_series[bvid]:
                        bvid_to_series[bvid].append(sname)
                    bvid_to_archive[bvid] = a
            if len(archives) < 50:
                break
            pn += 1

    print(f"Mapped {len(bvid_to_series)} videos from seasons/series.")
    return bvid_to_series, bvid_to_archive


def save_catalog(videos_by_bvid: dict, total_reported: int | None, completed_pages: list[int]):
    videos = sorted(videos_by_bvid.values(), key=lambda x: x.get("created", 0), reverse=True)
    payload = {
        "uid": UID,
        "fetched_at": datetime.now(tz=TZ_CN).isoformat(),
        "total_reported": total_reported,
        "total_fetched": len(videos),
        "completed_pages": completed_pages,
        "videos": videos,
    }
    with open(CATALOG_PATH, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def main():
    os.makedirs(DATA_DIR, exist_ok=True)
    videos_by_bvid = {}
    completed_pages = []
    total_count = None

    if os.path.exists(CATALOG_PATH):
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            existing = json.load(f)
        for v in existing.get("videos") or []:
            videos_by_bvid[v["bvid"]] = v
        completed_pages = existing.get("completed_pages") or []
        total_count = existing.get("total_reported")
        print(f"Resuming from existing catalog: {len(videos_by_bvid)} videos, pages={completed_pages}")

    client = BiliClient(delay_range=(0.5, 0.8))
    client.init_session()
    print("Session initialized.")

    bvid_to_series, bvid_to_archive = fetch_series_videos(client)
    for bvid, a in bvid_to_archive.items():
        if bvid not in videos_by_bvid:
            pub_ts = a.get("pubdate") or a.get("ctime") or 0
            pubdate_str = datetime.fromtimestamp(pub_ts, tz=TZ_CN).strftime("%Y-%m-%d")
            videos_by_bvid[bvid] = {
                "aid": a.get("aid"),
                "bvid": bvid,
                "title": a.get("title", ""),
                "description": "",
                "created": pub_ts,
                "pubdate_str": pubdate_str,
                "length": str(a.get("duration", "")),
                "play": (a.get("stat") or {}).get("view", 0),
                "comment": 0,
                "typeid": None,
                "pic": a.get("pic", ""),
                "video_url": f"https://www.bilibili.com/video/{bvid}",
                "is_union_video": 0,
                "series_tags": bvid_to_series.get(bvid, []),
            }
        else:
            videos_by_bvid[bvid]["series_tags"] = bvid_to_series.get(bvid, [])

    save_catalog(videos_by_bvid, total_count, completed_pages)

    # Now paginate arc/search gently
    client.delay_range = (4.0, 5.5)
    ps = 50
    max_pages = 12
    for pn in range(1, max_pages + 1):
        if pn in completed_pages:
            continue
        params = {"mid": UID, "ps": ps, "pn": pn, "tid": 0, "keyword": "", "order": "pubdate"}
        resp = None
        for attempt in range(5):
            try:
                r = client.get_json("https://api.bilibili.com/x/space/arc/search", params)
            except RuntimeError as e:
                if "HTTP 412" in str(e) and attempt < 4:
                    wait = 8.0 * (attempt + 1)
                    print(f"[WARN] HTTP 412 on page {pn}, sleeping {wait}s...")
                    time.sleep(wait)
                    continue
                raise
            code = r.get("code")
            if code == 0:
                resp = r
                break
            if code in (-799, -352, -412):
                wait = 8.0 * (attempt + 1)
                print(f"[WARN] arc/search code {code} on page {pn}, sleeping {wait}s...")
                time.sleep(wait)
                continue
            raise RuntimeError(f"arc/search error on page {pn}: {r}")

        if resp is None:
            print(f"[WARN] Stopping arc/search at page {pn} after retries; partial catalog saved.")
            break

        data = resp.get("data") or {}
        page_info = data.get("page") or {}
        if total_count is None:
            total_count = page_info.get("count", 0)
            print(f"Total videos reported by API: {total_count}")

        vlist = ((data.get("list") or {}).get("vlist")) or []
        if not vlist:
            completed_pages.append(pn)
            save_catalog(videos_by_bvid, total_count, completed_pages)
            break

        for v in vlist:
            bvid = v.get("bvid")
            if not bvid:
                continue
            created_ts = v.get("created") or 0
            pubdate_str = datetime.fromtimestamp(created_ts, tz=TZ_CN).strftime("%Y-%m-%d")
            videos_by_bvid[bvid] = {
                "aid": v.get("aid"),
                "bvid": bvid,
                "title": v.get("title", ""),
                "description": v.get("description", ""),
                "created": created_ts,
                "pubdate_str": pubdate_str,
                "length": v.get("length", ""),
                "play": v.get("play", 0),
                "comment": v.get("comment", 0),
                "typeid": v.get("typeid"),
                "pic": v.get("pic", ""),
                "video_url": f"https://www.bilibili.com/video/{bvid}",
                "is_union_video": v.get("is_union_video", 0),
                "series_tags": bvid_to_series.get(bvid, []),
            }

        completed_pages.append(pn)
        save_catalog(videos_by_bvid, total_count, completed_pages)
        print(f"Page {pn}: fetched {len(vlist)} items, total unique={len(videos_by_bvid)}/{total_count}")

        if len(vlist) < ps:
            break

    print(f"Catalog complete: {len(videos_by_bvid)} videos saved to {CATALOG_PATH}")


if __name__ == "__main__":
    main()
