import json
import os
from collections import Counter, defaultdict

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
OUT_MD = os.path.join(ROOT_DIR, "shanghai_food_map.md")

TIER_EMOJI = {
    "强烈推荐": "🏆 强烈推荐",
    "值得一试": "👍 值得一试",
    "中规中矩": "😐 中规中矩",
    "性价比低": "💸 性价比低",
    "严重踩雷": "💣 严重踩雷",
}


def fmt_price(r: dict) -> str:
    p = r.get("price_per_person")
    return f"¥{p}/人" if p else "时价"


def fmt_entry_block(r: dict) -> str:
    branch = f"（{r['branch_name']}）" if r.get("branch_name") else ""
    tier = TIER_EMOJI.get(r["verdict_tier"], r["verdict_tier"])
    rec = "、".join(r.get("recommended_dishes") or []) or "—"
    avoid = "、".join(r.get("avoid_dishes") or [])
    avoid_line = f"\n- **⚠️ 避雷菜品**：{avoid}" if avoid else ""
    return (
        f"#### {r['name']}{branch} ｜ {tier} ｜ {fmt_price(r)}\n"
        f"- **位置**：{r['district']} · {r['commercial_area']}（`{r['address']}`）\n"
        f"- **菜系 / 系列**：{r['cuisine_category']} ｜ `{r['series_name']}`\n"
        f"- **👍 推荐菜**：{rec}{avoid_line}\n"
        f"- **🧔 王师傅**：{r.get('wang_shifu_review') or '—'}\n"
        f"- **👩 小毛毛**：{r.get('xiao_maomao_review') or '—'}\n"
        f"- **📝 综合总结**：{r.get('overall_review_summary') or '—'}\n"
        f"- **📺 探店原视频**：[{r['video_title']}]({r['video_url']})（{r['pubdate_str']}）\n"
    )


def main():
    with open(os.path.join(DATA_DIR, "shanghai_restaurants_verified.json"), "r", encoding="utf-8") as f:
        rests = json.load(f)

    tier_counts = Counter(r["verdict_tier"] for r in rests)
    dist_counts = Counter(r["district"] for r in rests)

    lines = [
        "# 🍽️ 上海美食雷达 · 王师傅和小毛毛探店完整红黑榜攻略",
        "",
        f"> 收录 **164 家**上海实体探店记录 ｜ 覆盖 **{len(dist_counts)} 个行政区** ｜ 数据可直接配合在线 PWA 地图与 `find_nearby.py` 周边命令行工具使用。",
        "",
        "## 📊 评级总览与目录",
        "",
        "| 综合评级 | 家数 | 说明 |",
        "| :--- | :---: | :--- |",
        f"| 🏆 **强烈推荐** | **{tier_counts['强烈推荐']}** | [跳转红榜封神名录](#一红榜强烈推荐闭眼冲-38-家) |",
        f"| 👍 **值得一试** | **{tier_counts['值得一试']}** | 口碑稳定、顺路或符合预算可冲 |",
        f"| 😐 **中规中矩** | **{tier_counts['中规中矩']}** | 景观/主题/常规连锁，无功无过 |",
        f"| 💸 **性价比低** | **{tier_counts['性价比低']}** | [跳转低性价比提醒](#三低性价比高溢价提醒-21-家) |",
        f"| 💣 **严重踩雷** | **{tier_counts['严重踩雷']}** | [跳转黑榜避坑预警](#二黑榜严重踩雷避坑预警-13-家) |",
        "",
        "---",
        "",
        f"## 一、红榜：🏆 强烈推荐（闭眼冲 {tier_counts['强烈推荐']} 家）",
        "",
    ]

    red_top = [r for r in rests if r["verdict_tier"] == "强烈推荐"]
    budget = sorted([r for r in red_top if (r.get("price_per_person") or 0) <= 80], key=lambda x: x.get("price_per_person") or 0)
    mid = sorted([r for r in red_top if 80 < (r.get("price_per_person") or 0) <= 300], key=lambda x: x.get("price_per_person") or 0)
    lux = sorted([r for r in red_top if (r.get("price_per_person") or 0) > 300], key=lambda x: x.get("price_per_person") or 0)

    lines.append(f"### 1.1 平价封神榜（人均 ≤ ¥80 · 共 {len(budget)} 家）\n")
    for r in budget:
        lines.append(fmt_entry_block(r))

    lines.append(f"### 1.2 聚餐必冲榜（人均 ¥81–¥300 · 共 {len(mid)} 家）\n")
    for r in mid:
        lines.append(fmt_entry_block(r))

    lines.append(f"### 1.3 高奢不踩雷（人均 > ¥300 · 共 {len(lux)} 家）\n")
    for r in lux:
        lines.append(fmt_entry_block(r))

    lines.append("---\n")
    lines.append(f"## 二、黑榜：💣 严重踩雷避坑预警（{tier_counts['严重踩雷']} 家）\n")
    black = sorted([r for r in rests if r["verdict_tier"] == "严重踩雷"], key=lambda x: x.get("price_per_person") or 0, reverse=True)
    for r in black:
        lines.append(fmt_entry_block(r))

    lines.append("---\n")
    lines.append(f"## 三、低性价比/高溢价提醒（💸 性价比低 · {tier_counts['性价比低']} 家）\n")
    lines.append("| 店名 | 区域/商圈 | 菜系 | 人均 | 一句话总结 | 原视频 |")
    lines.append("| :--- | :--- | :--- | :---: | :--- | :---: |")
    low_val = sorted([r for r in rests if r["verdict_tier"] == "性价比低"], key=lambda x: x.get("price_per_person") or 0, reverse=True)
    for r in low_val:
        lines.append(
            f"| **{r['name']}** | {r['district']}·{r['commercial_area']} | {r['cuisine_category']} | {fmt_price(r)} | {r['overall_review_summary']} | [B站]({r['video_url']}) |"
        )
    lines.append("")

    lines.append("---\n")
    lines.append("## 四、按行政区与商圈全量速查（164 家全收录）\n")

    by_district = defaultdict(list)
    for r in rests:
        by_district[r["district"]].append(r)

    tier_order = {"强烈推荐": 0, "值得一试": 1, "中规中矩": 2, "性价比低": 3, "严重踩雷": 4}
    for dist, _cnt in dist_counts.most_common():
        d_list = sorted(
            by_district[dist],
            key=lambda x: (tier_order.get(x["verdict_tier"], 9), x.get("commercial_area", ""), x.get("price_per_person") or 0),
        )
        lines.append(f"### 📍 {dist}（共 {len(d_list)} 家）\n")
        by_area = defaultdict(list)
        for item in d_list:
            by_area[item.get("commercial_area") or "其他商圈"].append(item)

        for area, a_items in sorted(by_area.items(), key=lambda kv: -len(kv[1])):
            lines.append(f"#### 🏙️ {dist} · {area}（{len(a_items)} 家）\n")
            lines.append("| 店名 | 评级 | 人均 | 菜系 | 推荐菜 / 避雷提示 | 地址 | 视频 |")
            lines.append("| :--- | :---: | :---: | :--- | :--- | :--- | :---: |")
            for r in a_items:
                rec_s = "、".join((r.get("recommended_dishes") or [])[:3])
                avd_s = "、".join((r.get("avoid_dishes") or [])[:2])
                dish_note = ""
                if rec_s:
                    dish_note += f"👍 {rec_s}"
                if avd_s:
                    dish_note += (" ｜ " if dish_note else "") + f"⚠️ 避雷:{avd_s}"
                if not dish_note:
                    dish_note = r["overall_review_summary"][:28]
                lines.append(
                    f"| **{r['name']}** | {TIER_EMOJI.get(r['verdict_tier'], r['verdict_tier'])} | {fmt_price(r)} | {r['cuisine_category']} | {dish_note} | {r['address']} | [观看]({r['video_url']}) |"
                )
            lines.append("")

    md_text = "\n".join(lines)
    with open(OUT_MD, "w", encoding="utf-8") as f:
        f.write(md_text)

    print(f"Generated {OUT_MD} ({len(md_text):,} chars)")


if __name__ == "__main__":
    main()
