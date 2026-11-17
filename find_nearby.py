#!/usr/bin/env python3
"""
上海美食雷达 · 命令行周边餐厅查询工具
示例：
  python find_nearby.py "静安寺" --radius 1500 --red-only
  python find_nearby.py "人民广场" --radius 1000 --cuisine 火锅
  python find_nearby.py "31.2238,121.4459" --radius 800
  python find_nearby.py --list-landmarks
"""
import argparse
import json
import math
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
REST_PATH = os.path.join(BASE_DIR, "data", "shanghai_restaurants_verified.json")
LM_PATH = os.path.join(BASE_DIR, "data", "shanghai_landmarks.json")

DEG2RAD = math.pi / 180.0
DIRS_8 = ["↑北", "↗东北", "→东", "↘东南", "↓南", "↙西南", "←西", "↖西北"]


def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    dlat = (lat2 - lat1) * DEG2RAD
    dlng = (lng2 - lng1) * DEG2RAD
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(lat1 * DEG2RAD) * math.cos(lat2 * DEG2RAD) * math.sin(dlng / 2) ** 2
    )
    return 6371000.0 * 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def bearing_dir(lat1: float, lng1: float, lat2: float, lng2: float) -> str:
    dlng = (lng2 - lng1) * DEG2RAD
    y = math.sin(dlng) * math.cos(lat2 * DEG2RAD)
    x = math.cos(lat1 * DEG2RAD) * math.sin(lat2 * DEG2RAD) - (
        math.sin(lat1 * DEG2RAD) * math.cos(lat2 * DEG2RAD) * math.cos(dlng)
    )
    deg = (math.degrees(math.atan2(y, x)) + 360.0) % 360.0
    return DIRS_8[round(deg / 45.0) % 8]


def format_walk(meters: float, direction: str) -> str:
    mins = max(1, round(meters / 64.0))
    dist_s = f"{round(meters)}m" if meters < 1000 else f"{meters / 1000.0:.1f}km"
    return f"🚶 {mins}分 · {dist_s} {direction}"


def resolve_location(target: str, landmarks: list[dict], restaurants: list[dict]) -> tuple[float, float, str]:
    t = target.strip()
    if "," in t:
        parts = [p.strip() for p in t.split(",")]
        if len(parts) == 2:
            try:
                v1, v2 = float(parts[0]), float(parts[1])
                # Support both lat,lng and lng,lat
                if 28 <= v1 <= 35 and 118 <= v2 <= 124:
                    return v1, v2, f"自定义坐标({v1:.4f},{v2:.4f})"
                if 118 <= v1 <= 124 and 28 <= v2 <= 35:
                    return v2, v1, f"自定义坐标({v2:.4f},{v1:.4f})"
            except ValueError:
                pass

    tl = t.lower()
    # Exact match on landmark name / short_name / id / aliases
    for lm in landmarks:
        candidates = [lm["id"], lm["name"], lm.get("short_name", "")] + (lm.get("aliases") or [])
        if any(c.lower() == tl for c in candidates if c):
            return lm["lat"], lm["lng"], f"{lm['name']}（{lm['district']}）"

    # Substring match on landmarks
    for lm in landmarks:
        candidates = [lm["name"], lm.get("short_name", "")] + (lm.get("aliases") or [])
        if any(tl in c.lower() or c.lower() in tl for c in candidates if c):
            return lm["lat"], lm["lng"], f"{lm['name']}（{lm['district']}）"

    # Fallback: match a restaurant's commercial_area or name
    matched_pts = [
        (r["lat"], r["lng"])
        for r in restaurants
        if tl in (r.get("commercial_area") or "").lower() or tl in (r.get("address") or "").lower()
    ]
    if matched_pts:
        avg_lat = sum(p[0] for p in matched_pts) / len(matched_pts)
        avg_lng = sum(p[1] for p in matched_pts) / len(matched_pts)
        return avg_lat, avg_lng, f"{t}（商圈中心）"

    names_hint = "、".join(lm["short_name"] for lm in landmarks[:15])
    raise ValueError(f"无法识别位置“{target}”。试试：{names_hint} ... 或传入 '31.2238,121.4459'")


def main():
    parser = argparse.ArgumentParser(description="上海美食雷达 · 周边探店命令行查询工具")
    parser.add_argument("location", nargs="?", default="静安寺", help="商圈/地铁站名称，或 'lat,lng' 坐标（默认：静安寺）")
    parser.add_argument("-r", "--radius", type=int, default=1500, help="搜索半径（米，0 表示全上海，默认：1500）")
    parser.add_argument("--red-only", action="store_true", help="仅显示红榜餐厅（强烈推荐 + 值得一试）")
    parser.add_argument("--top-only", action="store_true", help="仅显示【强烈推荐】餐厅")
    parser.add_argument("--black-only", action="store_true", help="仅显示黑榜【严重踩雷】餐厅")
    parser.add_argument("--cuisine", type=str, default="", help="按菜系关键词筛选（如：火锅、本帮、粤菜、牛排）")
    parser.add_argument("--max-price", type=int, default=0, help="最高人均价格限制（元）")
    parser.add_argument("-n", "--limit", type=int, default=20, help="最多返回条数（默认：20）")
    parser.add_argument("--list-landmarks", action="store_true", help="列出全部内置的 35 个上海热门地标/商圈")
    parser.add_argument("--json", action="store_true", help="以 JSON 格式输出结果")
    args = parser.parse_args()

    with open(REST_PATH, "r", encoding="utf-8") as f:
        restaurants = json.load(f)
    with open(LM_PATH, "r", encoding="utf-8") as f:
        landmarks = json.load(f)

    if args.list_landmarks:
        print(f"📍 内置上海热门商圈/地铁枢纽/景点（共 {len(landmarks)} 个）：")
        for lm in landmarks:
            aliases = " / ".join(lm.get("aliases") or [])
            print(f"  - {lm['name']} ({lm['district']} · {lm['type']}) [{lm['lat']}, {lm['lng']}] 别名: {aliases}")
        return

    try:
        lat, lng, label = resolve_location(args.location, landmarks, restaurants)
    except ValueError as e:
        print(f"[错误] {e}", file=sys.stderr)
        sys.exit(1)

    results = []
    for r in restaurants:
        dist = haversine_meters(lat, lng, r["lat"], r["lng"])
        if args.radius > 0 and dist > args.radius:
            continue
        tier = r.get("verdict_tier", "")
        if args.top_only and tier != "强烈推荐":
            continue
        if args.red_only and tier not in ("强烈推荐", "值得一试"):
            continue
        if args.black_only and tier != "严重踩雷":
            continue
        if args.cuisine:
            blob = f"{r.get('cuisine_category','')} {r.get('name','')} {' '.join(r.get('recommended_dishes') or [])}"
            if args.cuisine.lower() not in blob.lower():
                continue
        if args.max_price > 0 and (r.get("price_per_person") or 999999) > args.max_price:
            continue

        direction = bearing_dir(lat, lng, r["lat"], r["lng"])
        item = dict(r)
        item["distance_m"] = round(dist)
        item["direction"] = direction
        item["walk_info"] = format_walk(dist, direction)
        results.append(item)

    results.sort(key=lambda x: x["distance_m"])
    shown = results[: args.limit] if args.limit > 0 else results

    if args.json:
        print(json.dumps({"center": {"label": label, "lat": lat, "lng": lng}, "count": len(results), "items": shown}, ensure_ascii=False, indent=2))
        return

    rad_txt = f"{args.radius}m 内" if args.radius > 0 else "全城范围"
    mode_txt = " [仅红榜]" if args.red_only else (" [仅强烈推荐]" if args.top_only else (" [仅黑榜]" if args.black_only else ""))
    print("=" * 74)
    print(f"📍 中心点：{label} ({lat:.4f}, {lng:.4f}) ｜ 范围：{rad_txt}{mode_txt}")
    print(f"🍽️ 共匹配 {len(results)} 家餐厅（显示前 {len(shown)} 家）：")
    print("=" * 74)

    if not shown:
        print("暂无匹配餐厅，请尝试调大 --radius（如 --radius 3000）或去掉过滤条件。")
        return

    tier_ico = {"强烈推荐": "🏆", "值得一试": "👍", "中规中矩": "😐", "性价比低": "💸", "严重踩雷": "💣"}
    for idx, r in enumerate(shown, 1):
        ico = tier_ico.get(r["verdict_tier"], "•")
        price_s = f"¥{r['price_per_person']}/人" if r.get("price_per_person") else "时价"
        branch_s = f" ({r['branch_name']})" if r.get("branch_name") else ""
        rec_s = "、".join((r.get("recommended_dishes") or [])[:4])
        avd_s = "、".join((r.get("avoid_dishes") or [])[:3])
        print(f"\n[{idx}] {r['name']}{branch_s}  {ico} {r['verdict_tier']} ｜ {price_s} ｜ {r['walk_info']}")
        print(f"    📍 {r['district']}·{r['commercial_area']} ｜ {r['address']} ｜ {r['cuisine_category']}")
        if rec_s:
            print(f"    👍 推荐菜：{rec_s}")
        if avd_s:
            print(f"    ⚠️ 避雷菜：{avd_s}")
        print(f"    📝 总结：{r.get('overall_review_summary', '')}")
        print(f"    📺 视频：{r.get('video_url', '')}")


if __name__ == "__main__":
    main()
