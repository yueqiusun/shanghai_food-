#!/usr/bin/env python3
"""
Interactive CLI to find the nearest verified Nagoya restaurants from any landmark,
station, hotel, attraction, or lat/lng coordinate.

Usage:
  py scripts/find_nearby.py "荣松坂屋"
  py scripts/find_nearby.py "希尔顿" --radius 1200 --limit 10
  py scripts/find_nearby.py "35.1709,136.8815" --category "鳗鱼饭"
  py scripts/find_nearby.py --list-landmarks
"""
import argparse
import io
import json
import math
import os
import re
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
RESTAURANTS_PATH = os.path.join(DATA_DIR, "restaurants.json")
LANDMARKS_PATH = os.path.join(DATA_DIR, "landmarks.json")


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def compass_dir(lat1: float, lng1: float, lat2: float, lng2: float) -> str:
    dl = math.radians(lng2 - lng1)
    p1, p2 = math.radians(lat1), math.radians(lat2)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    deg = (math.degrees(math.atan2(y, x)) + 360) % 360
    dirs = ["↑正北", "↗东北", "→正东", "↘东南", "↓正南", "↙西南", "←正西", "↖西北"]
    return dirs[int((deg + 22.5) // 45) % 8]


def load_json(path: str):
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def resolve_location(query: str, landmarks: list[dict], restaurants: list[dict]):
    q = query.strip()
    m = re.match(r"^\s*(-?\d+(?:\.\d+)?)\s*[,，\s]\s*(-?\d+(?:\.\d+)?)\s*$", q)
    if m:
        return float(m.group(1)), float(m.group(2)), f"坐标 ({m.group(1)}, {m.group(2)})"

    ql = q.lower()
    best_lm = None
    best_score = 0
    for lm in landmarks:
        candidates = [lm["name_zh"], lm["name_ja"], *lm.get("aliases", [])]
        for c in candidates:
            cl = c.lower()
            if ql == cl:
                return lm["lat"], lm["lng"], lm["name_zh"]
            if ql in cl or cl in ql:
                score = min(len(ql), len(cl)) / max(len(ql), len(cl))
                if score > best_score:
                    best_score = score
                    best_lm = lm
    if best_lm:
        return best_lm["lat"], best_lm["lng"], best_lm["name_zh"]

    # Fallback: match restaurant name or micro_hub
    for r in restaurants:
        hay = f"{r['name_zh']} {r['name_ja']} {r['micro_hub']} {r['address_zh']}".lower()
        if ql in hay:
            return r["lat"], r["lng"], f"{r['name_zh']} 附近"

    return None


def main() -> None:
    parser = argparse.ArgumentParser(description="Find nearby verified Nagoya restaurants.")
    parser.add_argument("query", nargs="?", help="Landmark/station/hotel name or 'lat,lng'")
    parser.add_argument("--radius", type=int, default=1000, help="Search radius in meters (default: 1000)")
    parser.add_argument("--limit", type=int, default=12, help="Max results to display (default: 12)")
    parser.add_argument("--category", type=str, default="", help="Filter by category substring")
    parser.add_argument("--tier", type=str, default="", help="Filter by tier substring")
    parser.add_argument("--list-landmarks", action="store_true", help="List all supported landmarks")
    args = parser.parse_args()

    landmarks = load_json(LANDMARKS_PATH)
    restaurants = load_json(RESTAURANTS_PATH)

    if args.list_landmarks:
        for lm in landmarks:
            print(f"[{lm['type']}] {lm['name_zh']} ({lm['lat']:.5f}, {lm['lng']:.5f}) — 别名: {', '.join(lm.get('aliases', []))}")
        return

    if not args.query:
        parser.print_help()
        sys.exit(1)

    resolved = resolve_location(args.query, landmarks, restaurants)
    if not resolved:
        print(f"未找到与「{args.query}」匹配的地标或坐标。可用 --list-landmarks 查看支持的地标。")
        sys.exit(1)

    lat0, lng0, label = resolved
    results = []
    for r in restaurants:
        if args.category and args.category.lower() not in r["category"].lower():
            continue
        if args.tier and args.tier.lower() not in r["tier"].lower():
            continue
        dist = haversine_m(lat0, lng0, r["lat"], r["lng"])
        results.append((dist, r))

    results.sort(key=lambda x: x[0])
    within = [item for item in results if item[0] <= args.radius]
    shown = within[: args.limit] if within else results[: min(5, args.limit)]

    print(f"📍 当前位置: {label} ({lat0:.5f}, {lng0:.5f})")
    if within:
        print(f"✅ 半径 {args.radius}m 内共找到 {len(within)} 家认证餐厅（展示前 {len(shown)} 家）：\n")
    else:
        print(f"⚠️ 半径 {args.radius}m 内暂无餐厅，为您展示最近的 {len(shown)} 家：\n")

    for i, (dist, r) in enumerate(shown, 1):
        walk_min = max(1, round(dist / 75))
        direction = compass_dir(lat0, lng0, r["lat"], r["lng"])
        tb = f"Tabelog {r['tabelog_score']}" if r.get("tabelog_score") else "Tabelog 暂无"
        hyaku = f" 🏆{r['hyakumeiten']}" if r.get("hyakumeiten") else ""
        res_tag = f" [📅 {r['reservation_status']}]" if r.get("reservation_status") else ""
        print(f"{i}. [{r['tier']}]{res_tag} {r['name_zh']}（{r['name_ja']}）")
        print(f"   📏 直线 {int(round(dist))}m ({direction}) | 🚶 约步行 {walk_min} 分钟 | {r['category']} | {tb}{hyaku} | {r['price_display']}")
        print(f"   🏠 {r['address_zh']}（{r['station_exit']}）")
        print(f"   🕒 营业: {r['hours']} | 休: {r['closed_days']}")
        must = "、".join(f"{m['zh']}({m['ja']})" for m in r.get("must_order", []))
        print(f"   🍽️ 必点: {must}")
        print(f"   💬 小红书共识: {r['xhs_consensus']}")
        print(f"   ⚠️ 避坑/排队: {r['avoid_or_caution']} | {r['queue_strategy']}")
        print(f"   🔗 Google地图: {r['gmaps_url']}")
        print(f"   🍎 Apple地图: {r['apple_maps_url']}")
        print(f"   📊 Tabelog: {r['tabelog_url']}\n")


if __name__ == "__main__":
    main()
