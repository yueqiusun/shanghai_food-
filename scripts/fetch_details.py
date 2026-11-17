import json
import os
import sys
import time
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from bili_client import BiliClient

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
PREFILTER_PATH = os.path.join(DATA_DIR, "prefilter.json")
DETAILS_DIR = os.path.join(DATA_DIR, "details")
TZ_CN = timezone(timedelta(hours=8))


def extract_comment_obj(r: dict) -> dict | None:
    if not r:
        return None
    member = r.get("member") or {}
    content = r.get("content") or {}
    sub_replies = []
    for sr in (r.get("replies") or [])[:5]:
        sm = sr.get("member") or {}
        sc = sr.get("content") or {}
        sub_replies.append({
            "uname": sm.get("uname", ""),
            "message": sc.get("message", ""),
            "like": sr.get("like", 0),
        })
    return {
        "rpid": r.get("rpid"),
        "uname": member.get("uname", ""),
        "mid": member.get("mid"),
        "message": content.get("message", ""),
        "like": r.get("like", 0),
        "ctime": r.get("ctime", 0),
        "sub_replies": sub_replies,
    }


def fetch_video_detail(client: BiliClient, video: dict) -> dict:
    bvid = video["bvid"]
    aid = video["aid"]

    # 1. Video view info
    view_resp = client.get_json(
        "https://api.bilibili.com/x/web-interface/view", {"bvid": bvid}
    )
    if view_resp.get("code") != 0:
        raise RuntimeError(f"view error for {bvid}: {view_resp}")
    vdata = view_resp.get("data") or {}
    cid = vdata.get("cid")
    aid = vdata.get("aid") or aid

    pages = [
        {"page": p.get("page"), "part": p.get("part", ""), "duration": p.get("duration", 0)}
        for p in (vdata.get("pages") or [])
    ]
    ugc_season = None
    if vdata.get("ugc_season"):
        us = vdata["ugc_season"]
        ugc_season = {"id": us.get("id"), "title": us.get("title", "")}

    # 2. Pinned + top 20 hot comments
    pinned_comment = None
    hot_comments = []
    try:
        reply_resp = client.get_json(
            "https://api.bilibili.com/x/v2/reply/main",
            {"type": 1, "oid": aid, "mode": 3, "ps": 20},
        )
        if reply_resp.get("code") == 0:
            rdata = reply_resp.get("data") or {}
            top = rdata.get("top") or {}
            if top.get("upper"):
                pinned_comment = extract_comment_obj(top["upper"])
            for r in (rdata.get("replies") or [])[:20]:
                c = extract_comment_obj(r)
                if c:
                    hot_comments.append(c)
    except Exception as e:
        print(f"  [WARN] comments failed for {bvid}: {e}")

    # 3. Subtitles if available (already listed in view response)
    subtitles = []
    sub_list = ((vdata.get("subtitle") or {}).get("list")) or []
    for s in sub_list[:1]:
        s_url = s.get("subtitle_url", "")
        if s_url:
            if s_url.startswith("//"):
                s_url = "https:" + s_url
            try:
                sub_json = client.get_json(s_url)
                body = sub_json.get("body") or []
                subtitles = [line.get("content", "") for line in body if line.get("content")]
            except Exception:
                pass

    pub_ts = vdata.get("pubdate") or video.get("created") or 0
    pubdate_str = datetime.fromtimestamp(pub_ts, tz=TZ_CN).strftime("%Y-%m-%d")

    return {
        "bvid": bvid,
        "aid": aid,
        "cid": cid,
        "title": vdata.get("title") or video.get("title", ""),
        "description": vdata.get("desc") or video.get("description", ""),
        "pubdate": pub_ts,
        "pubdate_str": pubdate_str,
        "tname": vdata.get("tname", ""),
        "duration": vdata.get("duration", 0),
        "video_url": f"https://www.bilibili.com/video/{bvid}",
        "series_tags": video.get("series_tags") or [],
        "ugc_season": ugc_season,
        "pages": pages,
        "pinned_comment": pinned_comment,
        "hot_comments": hot_comments,
        "subtitle_lines": subtitles,
    }


def main():
    os.makedirs(DETAILS_DIR, exist_ok=True)
    with open(PREFILTER_PATH, "r", encoding="utf-8") as f:
        pf = json.load(f)

    candidates = [v for v in pf["videos"] if v.get("prefilter_status") == "candidate"]
    print(f"Total candidates to fetch details for: {len(candidates)}")

    client = BiliClient(delay_range=(0.45, 0.70))
    client.init_session()

    fetched = 0
    skipped = 0
    errors = 0
    for idx, v in enumerate(candidates, 1):
        bvid = v["bvid"]
        out_path = os.path.join(DETAILS_DIR, f"{bvid}.json")
        if os.path.exists(out_path):
            skipped += 1
            continue

        try:
            detail = fetch_video_detail(client, v)
            with open(out_path, "w", encoding="utf-8") as f:
                json.dump(detail, f, ensure_ascii=False, indent=2)
            fetched += 1
            if fetched % 10 == 0 or idx == len(candidates):
                print(
                    f"[{idx}/{len(candidates)}] fetched={fetched}, skipped={skipped}, errors={errors} (last: {bvid})"
                )
        except Exception as e:
            errors += 1
            print(f"[{idx}/{len(candidates)}] [ERROR] {bvid}: {e}")
            time.sleep(2.0)

    print(f"Done! fetched={fetched}, skipped={skipped}, errors={errors}")


if __name__ == "__main__":
    main()
