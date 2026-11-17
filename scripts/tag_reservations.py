import csv
import json
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT_DIR, "data", "shanghai_restaurants_verified.json")
CSV_PATH = os.path.join(ROOT_DIR, "data", "shanghai_food_map.csv")

# Mapping: entry_id -> reservation note (strict/recommended advance booking)
RESERVATION_MAP = {
    # 强预约 / 全预约制 / 工作室 / 怀石 / Omakase / 需提前定制备菜
    "BV1CoBrY8EQx_01": "全预约制中式Omakase，席位极少常需提前数周至数月预约",
    "BV1ey4ze8EnD_01": "全预约制私房火锅工作室，仅接受提前预订",
    "BV1WF41117sZ_01": "熟客全预约制天妇罗Omakase，需提前很久预约",
    "BV17o4y1j74i_01": "全预约制日法创意Omakase，需提前预订座位",
    "BV1MB4y1a7Ro_01": "顶级怀石料理需按当日空运食材备餐，需提前电话预约",
    "BV1kK4y1873h_01": "顶级怀石料理，席位有限需提前预约",
    "BV1X541187hQ_01": "完全预约制花园洋房私房菜，通常需提前数天预约",
    "BV1pf4y1B7sN_01": "预约制米其林私房川菜（注：该门店后续已歇业）",
    "BV1Jy4y167sW_01": "私房闽南菜及每日限量鸡汤需提前预订",
    "BV1wP4y1E7WA_01": "烤全羊需现烤数小时，到店前务必提前预约",
    "BV1dt4y137Rq_01": "佛跳墙及包厢需提前预约备制",
    "BV1fy4y187a7_01": "游艇俱乐部会所餐饮，需提前预约或会员携同",
    "BV1rA411s78W_01": "高端板前烧鸟和牛烤串，席位较少需提前预约",
    "BV1664y1d7ph_01": "老洋房全包厢/私房菜制，需提前预约",
    "BV1PZ4y157rW_01": "贝轩大公馆私房宴请（荣府宴），以包厢为主需提前预约",
    "BV1pa4y177A5_01": "米其林二星素食套餐制，需提前预约",
    "BV1MyHHzEEY1_01": "创意素食套餐制，建议提前预约",
    "BV1Xy4y1E7Zc_01": "太原别墅高端素食，需提前预约",

    # 米其林 / 黑珍珠 / 高空景观 / 顶级牛排与高端中餐（需或强烈建议提前预约）
    "BV1F64y1D7UB_01": "上海中心68楼米其林法餐，需提前预约座位",
    "BV1x5411b76p_01": "外滩18号米其林二星法餐，需提前预约",
    "BV1tX4y1P73B_01": "外滩BFC米其林二星意大利餐厅，需提前预约",
    "BV1oy4y1p7fV_01": "黑珍珠三钻新潮州菜，需提前预约",
    "BV1cv41177s5_01": "新天地朗廷酒店米其林粤菜，需提前预约",
    "BV12d4y1n7Sr_01": "锦江饭店黑珍珠三钻/米其林一星宁波菜，需提前预约",
    "BV1WV411v7x7_01": "浦东文华东方米其林一星江南菜，需提前预约",
    "BV1KK4y1K7rt_01": "外滩三号米其林粤菜，建议提前预约",
    "BV1jL411H7b4_01": "西郊黑珍珠顶级私房菜，需提前预约",
    "BV1Mi4y1L7YK_01": "西郊黑珍珠顶级私房菜，需提前预约",
    "BV1Vy4y1B7cP_01": "名厨主理高端融合中餐，需提前预约",
    "BV1f54y1x7xq_01": "龙柏饭店米其林指南徽菜，建议提前预约",
    "BV1eQ4y1w7CX_01": "米其林经典粤菜，晚市及招牌脆皮烧肉建议提前预约",
    "BV1m44y1r7b5_01": "虹桥米其林粤菜，建议提前预约",
    "BV1x64y11728_01": "新天地米其林指南高端鲁菜，建议提前预约",
    "BV19f4y1e7En_01": "外滩米其林蟹宴，蟹季晚市建议提前预约",
    "BV1jz4y1A7ST_01": "外滩18号米其林粤菜，建议提前预约",
    "BV1GP411s7qh_01": "上海中心120层世界最高餐厅，需提前预约（尤其靠窗位）",
    "BV19K4y1m7qB_01": "环球金融中心91层柏悦景观餐厅，需提前预约靠窗位",
    "BV1B84y1M7Eh_01": "浦东美术馆顶楼江景晚餐，需提前预约",
    "BV1xN411E7GG_01": "深坑酒店水下景观餐厅，席位紧俏需提前预约",
    "BV1nE411r7ND_01": "东方明珠267米旋转餐厅，需提前预订餐位及观光票",
    "BV1GJ411w7Xz_01": "外滩和平饭店正餐厅（华懋阁/龙凤厅），需提前预约",
    "BV1nhjB6WEkH_01": "创意融合川菜Fine Dining，建议提前预约",
    "BV1LvF3eUEJn_01": "外滩罗斯福公馆概念Fine Dining，需提前预约",
    "BV1hN4y1x7C5_01": "北外滩江景露台私宴/包厢，需提前预约",
    "BV19y4y1R7ry_01": "外滩五号高端蟹宴，需提前预约",
    "BV1co4y1D7bh_01": "东湖路高端干式熟成牛排馆，需提前预约",
    "BV13A411F7Lo_01": "国金中心高端美式牛排馆，晚市建议提前预约",
    "BV17K4y1e7pA_01": "干式熟成牛排馆，晚市及周末建议提前预约",
    "BV1ug411k7oR_01": "洋房干式熟成牛排馆，晚市建议提前预约",
    "BV1zf4y1v7Ta_01": "陆家嘴高端牛排馆，建议提前预约",
    "BV1Ps4y1S7rt_01": "现代印度Fine Dining，建议提前预约",
    "BV1UQ4y1Z78y_01": "人民公园斯里兰卡螃蟹专门店，大规格螃蟹及晚市建议提前预约",
    "BV1UE411o7my_01": "新天地黑珍珠高端港式火锅，需提前预约",
    "BV1154y1R7z5_01": "茂名南路老牌港式打边炉，花胶鸡汤底及晚市建议提前预约",
    "BV1Zd4y1x7MM_01": "高端海鲜自助火锅，需提前预约",
    "BV1CC41157yb_01": "新天地高端海鲜火锅，建议提前预约",
    "BV1ApK6zHExY_01": "顺德庭院私房菜人气极高，建议提前预约",
    "BV1ukiBYxE94_01": "热门新中式餐厅，周末及晚餐建议提前预约",
    "BV1GefGYLEEo_01": "热门意式约会餐厅，晚餐建议提前预约",
    "BV1kC4y1y7br_01": "新淮扬菜名店，周末及包厢建议提前预约",
    "BV12K4y1o7eh_01": "外滩BFC精致川菜，晚市建议提前预约",
    "BV14N411o7Po_01": "大型商务宴请公馆菜，包厢需提前预约",
    "BV1cK411P7DT_01": "高端烤鸭名店，烤鸭及晚市座位建议提前预约",
    "BV1xE411h74d_01": "巨鹿路吃蟹名店，晚市建议提前预约",
}


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        rests = json.load(f)

    req_count = 0
    for r in rests:
        eid = r["entry_id"]
        if eid in RESERVATION_MAP:
            r["reservation_required"] = True
            r["reservation_note"] = RESERVATION_MAP[eid]
            req_count += 1
        else:
            r["reservation_required"] = False
            r["reservation_note"] = ""

    with open(JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(rests, f, ensure_ascii=False, indent=2)

    fields = list(rests[0].keys())
    with open(CSV_PATH, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        for r in rests:
            row = dict(r)
            for col in ("aliases", "recommended_dishes", "avoid_dishes"):
                row[col] = "、".join(str(x) for x in (row.get(col) or []))
            writer.writerow(row)

    print(f"Tagged {req_count}/{len(rests)} restaurants with reservation_required=True and updated JSON + CSV.")


if __name__ == "__main__":
    main()
