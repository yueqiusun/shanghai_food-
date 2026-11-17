import csv
import glob
import json
import os
import urllib.parse

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
EXTRACTED_DIR = os.path.join(DATA_DIR, "extracted")
OUTPUT_JSON = os.path.join(DATA_DIR, "shanghai_restaurants_verified.json")
OUTPUT_CSV = os.path.join(DATA_DIR, "shanghai_food_map.csv")

REQUIRED_FIELDS = [
    "entry_id",
    "bvid",
    "video_title",
    "pubdate_str",
    "video_url",
    "series_name",
    "name",
    "branch_name",
    "aliases",
    "district",
    "commercial_area",
    "address",
    "lat",
    "lng",
    "cuisine_category",
    "price_per_person",
    "price_info",
    "verdict_tier",
    "recommended_dishes",
    "avoid_dishes",
    "wang_shifu_review",
    "xiao_maomao_review",
    "overall_review_summary",
    "amap_url",
    "gmaps_url",
    "dianping_url",
]

VALID_TIERS = {"强烈推荐", "值得一试", "中规中矩", "性价比低", "严重踩雷"}


def build_urls(name: str, address: str) -> tuple[str, str, str]:
    q_amap = urllib.parse.quote(f"上海 {name} {address}".strip())
    q_gmaps = urllib.parse.quote(f"{name} {address} Shanghai".strip())
    q_dp = urllib.parse.quote(name.strip())
    return (
        f"https://www.amap.com/search?query={q_amap}",
        f"https://www.google.com/maps/search/?api=1&query={q_gmaps}",
        f"https://www.dianping.com/search/keyword/1/0_{q_dp}",
    )


def main():
    files = sorted(glob.glob(os.path.join(EXTRACTED_DIR, "*.json")))
    if not files:
        raise RuntimeError(f"No extracted batch files found in {EXTRACTED_DIR}")

    all_records = []
    seen_ids = set()
    errors = []

    for fp in files:
        with open(fp, "r", encoding="utf-8") as f:
            batch = json.load(f)
        if not isinstance(batch, list):
            raise RuntimeError(f"{fp} must contain a JSON array")
        for rec in batch:
            eid = (rec.get("entry_id") or "").strip()
            name = (rec.get("name") or "").strip()
            if not eid:
                errors.append(f"Missing entry_id in {fp}: {name}")
                continue
            if eid in seen_ids:
                errors.append(f"Duplicate entry_id {eid} in {fp}")
                continue
            seen_ids.add(eid)

            if not name:
                errors.append(f"Empty name for {eid} in {fp}")
                continue

            lat = rec.get("lat")
            lng = rec.get("lng")
            if not isinstance(lat, (int, float)) or not (30.9 <= lat <= 31.45):
                errors.append(f"Invalid lat {lat} for {eid} ({name})")
                continue
            if not isinstance(lng, (int, float)) or not (121.1 <= lng <= 121.8):
                errors.append(f"Invalid lng {lng} for {eid} ({name})")
                continue

            tier = rec.get("verdict_tier", "")
            if tier not in VALID_TIERS:
                errors.append(f"Invalid verdict_tier '{tier}' for {eid} ({name})")
                continue

            amap, gmaps, dp = build_urls(name, rec.get("address") or "")
            clean = {
                "entry_id": eid,
                "bvid": rec.get("bvid", ""),
                "video_title": rec.get("video_title", ""),
                "pubdate_str": rec.get("pubdate_str", ""),
                "video_url": rec.get("video_url") or f"https://www.bilibili.com/video/{rec.get('bvid', '')}",
                "series_name": rec.get("series_name", "常规探店"),
                "name": name,
                "branch_name": rec.get("branch_name", ""),
                "aliases": rec.get("aliases") if isinstance(rec.get("aliases"), list) else [],
                "district": rec.get("district", ""),
                "commercial_area": rec.get("commercial_area", ""),
                "address": rec.get("address", ""),
                "lat": round(float(lat), 6),
                "lng": round(float(lng), 6),
                "cuisine_category": rec.get("cuisine_category", ""),
                "price_per_person": rec.get("price_per_person"),
                "price_info": rec.get("price_info", ""),
                "verdict_tier": tier,
                "recommended_dishes": rec.get("recommended_dishes") if isinstance(rec.get("recommended_dishes"), list) else [],
                "avoid_dishes": rec.get("avoid_dishes") if isinstance(rec.get("avoid_dishes"), list) else [],
                "wang_shifu_review": rec.get("wang_shifu_review", ""),
                "xiao_maomao_review": rec.get("xiao_maomao_review", ""),
                "overall_review_summary": rec.get("overall_review_summary", ""),
                "amap_url": rec.get("amap_url") or amap,
                "gmaps_url": rec.get("gmaps_url") or gmaps,
                "dianping_url": rec.get("dianping_url") or dp,
            }
            all_records.append(clean)

    if errors:
        print("VALIDATION ERRORS:")
        for e in errors[:30]:
            print("  -", e)
        raise RuntimeError(f"Validation failed with {len(errors)} errors")

    # Sort by pubdate_str descending, then entry_id
    all_records.sort(key=lambda r: (r["pubdate_str"], r["entry_id"]), reverse=True)

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)

    with open(OUTPUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=REQUIRED_FIELDS)
        writer.writeheader()
        for r in all_records:
            row = dict(r)
            for list_col in ("aliases", "recommended_dishes", "avoid_dishes"):
                row[list_col] = "、".join(str(x) for x in (row.get(list_col) or []))
            writer.writerow(row)

    tier_counts = {t: 0 for t in VALID_TIERS}
    for r in all_records:
        tier_counts[r["verdict_tier"]] += 1

    print(f"Merged & validated {len(all_records)} restaurants.")
    print(f"Tier distribution: {tier_counts}")
    print(f"Wrote: {OUTPUT_JSON}")
    print(f"Wrote: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
