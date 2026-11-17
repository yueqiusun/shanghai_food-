#!/usr/bin/env python3
"""
Merge, validate, audit coordinates/landmarks, and generate:
  - data/restaurants.json
  - data/nagoya_food_map.csv (UTF-8 BOM)
  - nagoya_food_map.md
"""
import csv
import glob
import io
import json
import math
import os
import sys

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
ZONES_DIR = os.path.join(DATA_DIR, "zones")
LANDMARKS_PATH = os.path.join(DATA_DIR, "landmarks.json")
OUT_JSON = os.path.join(DATA_DIR, "restaurants.json")
OUT_CSV = os.path.join(DATA_DIR, "nagoya_food_map.csv")
OUT_MD = os.path.join(ROOT, "nagoya_food_map.md")

VALID_CATEGORIES = {
    "鳗鱼饭三吃 (ひつまぶし)",
    "味噌猪排与炸物 (味噌カツ)",
    "手羽先与交趾鸡 (手羽先・鶏料理)",
    "味噌乌冬与棊子面 (うどん・きしめん)",
    "台湾拉面与人气拉面 (ラーメン・担々麺)",
    "飞驒牛与和牛烧肉 (飛騨牛・焼肉)",
    "名古屋早餐与复古喫茶 (モーニング・純喫茶)",
    "甜品蛋糕与伴手礼 (スイーツ・カフェ)",
    "海鲜寿司与特大炸虾 (寿司・海鮮・エビフライ)",
    "居酒屋与烧鸟夜宵 (居酒屋・焼鳥)",
    "洋食披萨与精致料理 (洋食・ピッツァ・フレンチ)",
    "市井扫街小吃 (食べ歩き・屋台)",
}

VALID_TIERS = {"必吃封神", "强烈推荐", "顺路优选", "口味两极", "避坑提醒"}


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def main() -> None:
    zone_files = sorted(glob.glob(os.path.join(ZONES_DIR, "*.json")))
    if not zone_files:
        print("No zone JSON files found in", ZONES_DIR)
        sys.exit(1)

    all_rests = []
    seen_ids = set()
    errors = []

    for zf in zone_files:
        with open(zf, "r", encoding="utf-8") as f:
            items = json.load(f)
        print(f"Loaded {len(items)} records from {os.path.basename(zf)}")
        for item in items:
            rid = item.get("id", "")
            if rid in seen_ids:
                errors.append(f"Duplicate id: {rid}")
            seen_ids.add(rid)

            if item.get("category") not in VALID_CATEGORIES:
                errors.append(f"{rid} invalid category: {item.get('category')}")
            if item.get("tier") not in VALID_TIERS:
                errors.append(f"{rid} invalid tier: {item.get('tier')}")

            lat, lng = item.get("lat"), item.get("lng")
            if not isinstance(lat, (int, float)) or not (34.8 <= lat <= 35.45):
                errors.append(f"{rid} suspicious lat: {lat}")
            if not isinstance(lng, (int, float)) or not (136.7 <= lng <= 137.15):
                errors.append(f"{rid} suspicious lng: {lng}")

            for url_k in ("gmaps_url", "apple_maps_url", "tabelog_url", "xhs_url"):
                if not str(item.get(url_k, "")).startswith("https://"):
                    errors.append(f"{rid} missing/invalid {url_k}")

            all_rests.append(item)

    all_rests.sort(key=lambda r: (r["zone_id"], r["id"]))

    # Write merged restaurants.json
    with open(OUT_JSON, "w", encoding="utf-8") as f:
        json.dump(all_rests, f, ensure_ascii=False, indent=2)
    print(f"\nMerged {len(all_rests)} restaurants -> {OUT_JSON}")

    if errors:
        print(f"\n⚠️ Validation warnings/errors ({len(errors)}):")
        for e in errors[:30]:
            print("  -", e)
    else:
        print("✅ All restaurant records passed schema & coordinate validation!")

    # Audit landmarks coverage
    with open(LANDMARKS_PATH, "r", encoding="utf-8") as f:
        landmarks = json.load(f)
    print(f"\nAuditing {len(landmarks)} landmarks for 1km restaurant coverage:")
    uncovered = []
    for lm in landmarks:
        near = [
            (haversine_m(lm["lat"], lm["lng"], r["lat"], r["lng"]), r)
            for r in all_rests
        ]
        near.sort(key=lambda x: x[0])
        within_1km = [x for x in near if x[0] <= 1000]
        if not within_1km:
            uncovered.append((lm["name_zh"], near[0][0], near[0][1]["name_zh"]))
        else:
            print(f"  ✓ {lm['name_zh']}: {len(within_1km)} stores within 1km (nearest: {within_1km[0][1]['name_zh']} @ {int(within_1km[0][0])}m)")
    if uncovered:
        print("\n⚠️ Landmarks with 0 stores within 1km:")
        for name, dist, nearest in uncovered:
            print(f"  ✗ {name} (nearest: {nearest} @ {int(dist)}m)")

    # Write CSV (UTF-8 BOM)
    csv_cols = [
        "id", "zone_id", "zone", "district", "micro_hub", "name_zh", "name_ja", "branch",
        "category", "tier", "reservation_status", "tabelog_score", "hyakumeiten", "price_jpy", "price_display",
        "station_exit", "walk_min", "lat", "lng", "hours", "closed_days",
        "queue_strategy", "avoid_or_caution", "xhs_consensus", "local_tip",
        "address_ja", "address_zh", "gmaps_url", "apple_maps_url", "tabelog_url", "official_url", "xhs_url"
    ]
    with open(OUT_CSV, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=csv_cols)
        w.writeheader()
        for r in all_rests:
            row = {k: r.get(k, "") for k in csv_cols}
            w.writerow(row)
    print(f"\nGenerated CSV -> {OUT_CSV}")

    # Generate nagoya_food_map.md
    tier_counts = {}
    cat_counts = {}
    zone_counts = {}
    hyaku_count = 0
    for r in all_rests:
        tier_counts[r["tier"]] = tier_counts.get(r["tier"], 0) + 1
        cat_counts[r["category"]] = cat_counts.get(r["category"], 0) + 1
        zone_counts[(r["zone_id"], r["zone"])] = zone_counts.get((r["zone_id"], r["zone"]), 0) + 1
        if r.get("hyakumeiten"):
            hyaku_count += 1

    lines = [
        "# 名古屋全景美食地图（小红书共识 × Tabelog百名店）",
        "",
        f"> **收录规模**：共 **{len(all_rests)}** 家 2026 年实测营业餐厅 · 覆盖 **{len(zone_counts)}** 大核心商圈与景点 · **{len(landmarks)}** 个地铁/酒店/景点地标 · **{hyaku_count}** 家 Tabelog 百名店",
        "",
        "## 📊 数据总览",
        "",
        "### 口碑评级分布",
        "",
        "```mermaid",
        "pie title 名古屋美食评级分布",
    ]
    for t in ["必吃封神", "强烈推荐", "顺路优选", "口味两极", "避坑提醒"]:
        lines.append(f'    "{t}" : {tier_counts.get(t, 0)}')
    lines += [
        "```",
        "",
        "### 10 大地理分区动线图",
        "",
        "```mermaid",
        "flowchart LR",
        '    Z1["1.名站东口/双塔"] --> Z2["2.名站西/ESCA/则武"]',
        '    Z1 --> Z5["5.伏见/四间道/圆顿寺"]',
        '    Z5 --> Z3["3.荣·久屋·中日大厦"]',
        '    Z3 --> Z4["4.荣·松坂屋/LACHIC"]',
        '    Z4 --> Z6["6.大须观音/矢场町"]',
        '    Z6 --> Z7["7.热田神宫/金山"]',
        '    Z3 --> Z8["8.名古屋城/高岳/德川园"]',
        '    Z3 --> Z9["9.鹤舞/今池/觉王山百名店"]',
        '    Z1 --> Z10["10.机场/乐高/犬山/吉卜力"]',
        "```",
        "",
        "## 🌟 必吃封神红榜（精选）",
        "",
        "| 区域 | 餐厅 | 品类 | Tabelog | 人均 | 必点招牌 |",
        "|---|---|---|---|---|---|",
    ]
    for r in all_rests:
        if r["tier"] == "必吃封神":
            tb = f"{r['tabelog_score']}" if r.get("tabelog_score") else "-"
            if r.get("hyakumeiten"):
                tb += f" 🏆{r['hyakumeiten']}"
            must = "、".join(m["zh"] for m in r.get("must_order", [])[:2])
            lines.append(f"| {r['zone'].split('（')[0]} | [{r['name_zh']}]({r['gmaps_url']}) ({r['name_ja']}) | {r['category'].split(' (')[0]} | {tb} | {r['price_display']} | {must} |")

    lines += [
        "",
        "## ⚠️ 名古屋美食 6 大避坑 & 2026 必知情报",
        "",
        "1. **2026年2月28日名铁百货本店永久闭店**：原名铁百货店内的「まるや本店」「矢场猪排」「Konparu」等已停业或迁出，请改去名驿 MEICHIKA、ESCA 地下街、Sun Road 地下街或荣商圈分店。",
        "2. **山本屋总本家/本店「硬心味噌乌冬」**：面芯刻意偏硬，点单时可说 `麺やわらかめでお願いします`（煮软一点）。",
        "3. **世界的山ちゃん「幻之手羽先」**：黑胡椒与盐味极重，不吃辣可要求 `コショウ少なめでお願いします`（少胡椒），或改吃甜酱派「风来坊」。",
        "4. **味仙「台湾拉面」**：普通版即中大辣，怕辣必点 `アメリカン`（美式微辣）。",
        "5. **蓬莱轩排队破解术**：热田本店/神宫店常等 1–2 小时，可改去松坂屋南馆 10F 分流，或直接去松坂屋 B1 外带便当免排队。",
        "6. **HARBS 堂食低消**：堂食每人必须点 1 杯饮品，外带切片蛋糕免低消。",
        "",
        "## 🍱 Top 7 鳗鱼饭三吃横向对比",
        "",
        "| 品牌 | 烤制流派与口感 | 人均(JPY) | 排队/预约策略 |",
        "|---|---|---|---|",
        "| **蓬莱轩** | 备长炭直烤，皮脆肉嫩、酱汁偏甜厚 | ¥4,600 | 不可预约；松坂屋 B1 外带免等 |",
        "| **炭烧 うな富士** | 超厚切青鳗，外焦里糯油脂丰沛 | ¥5,200 | 本店排队狠，名站/白壁店可官网预约 |",
        "| **まるや本店** | 皮极脆、酱汁清爽带炭香，性价比高 | ¥4,300 | 名站 MEICHIKA / 中部机场店最顺路 |",
        "| **名古屋 备长** | 完全关西风地烤（不蒸），焦香脆皮 | ¥4,500 | LACHIC / ESCA / 金鯱横丁均有分店 |",
        "| **ひつまぶし 稻生** | 名站 ESCA 老字号，价格亲民出餐快 | ¥3,600 | ESCA 地下街排队相对温和 |",
        "| **うなぎ四代目菊川** | 招牌「整条一本鳗」，中日大厦新地标 | ¥5,000 | 中日大厦/名站店可在线预约 |",
        "| **うなぎのしろむら** | 三河一色活鳗+白烧吃法，环境雅致 | ¥4,800 | 名站店适合提前订位 |",
        "",
        "## 🗓️ 3 天不走回头路美食动线",
        "",
        "- **Day 1（名站核心 × 四间道 × 荣夜宵）**：Sun Road `Konparu 炸虾三明治` → ESCA `稻生鳗鱼饭` / `矢场猪排` → 则武之森 TSUTAYA + 四间道 `喫茶ゾウメシ` → 荣中日大厦/马喰一代飞驒牛 → 锦三 `世界的山ちゃん` / `味仙`。",
        "- **Day 2（名古屋城 × 大须扫街 × 热田神宫）**：高岳 `ボンボン` 复古喫茶 → 名古屋城金鯱横丁 → 大须商店街（`CESARI 世界冠军披萨` + `李桑炸鸡` + `KANNON COFFEE`）→ 热田神宫 `あつたnagAya` / `蓬莱轩`。",
        "- **Day 3（百名店巡礼 or 近郊一日游）**：市区线 `紫阳花拉面` / `人生饺子` + 觉王山 `吉芋` & `Chez Shibata`；近郊线 `犬山城下町` 或 `吉卜力公园`，返程于 `中部机场 T1 4F 提灯横丁` 收尾。",
        "",
        "## 🗺️ 分区完整收录清单",
        "",
    ]

    for zid, zname in sorted(zone_counts.keys()):
        lines.append(f"### {zid}. {zname}（{zone_counts[(zid, zname)]} 家）")
        lines.append("")
        for r in [x for x in all_rests if x["zone_id"] == zid]:
            tb = f"Tabelog {r['tabelog_score']}" if r.get("tabelog_score") else "Tabelog 暂无"
            hyaku = f" 🏆{r['hyakumeiten']}" if r.get("hyakumeiten") else ""
            res_tag = f" 📅{r['reservation_status']}" if r.get("reservation_status") else ""
            must = "、".join(f"{m['zh']}({m['ja']})" for m in r.get("must_order", []))
            lines.append(f"- **[{r['tier']}] {r['name_zh']}（{r['name_ja']}）** · {r['category']} · {tb}{hyaku}{res_tag} · {r['price_display']}")
            lines.append(f"  - 地址：{r['address_zh']}（{r['station_exit']}，步行约 {r['walk_min']} 分钟）")
            lines.append(f"  - 营业：{r['hours']}（休：{r['closed_days']}）")
            lines.append(f"  - 必点：{must}")
            lines.append(f"  - 小红书共识：{r['xhs_consensus']}")
            lines.append(f"  - 避坑/贴士：{r['avoid_or_caution']} | {r['local_tip']}")
            lines.append(f"  - 链接：[Google Maps]({r['gmaps_url']}) | [Apple Maps]({r['apple_maps_url']}) | [Tabelog]({r['tabelog_url']}) | [小红书]({r['xhs_url']})")
        lines.append("")

    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Generated Markdown -> {OUT_MD}")


if __name__ == "__main__":
    main()
