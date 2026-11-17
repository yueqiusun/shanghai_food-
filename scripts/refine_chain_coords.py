import csv
import json
import os

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
JSON_PATH = os.path.join(ROOT_DIR, "data", "shanghai_restaurants_verified.json")
CSV_PATH = os.path.join(ROOT_DIR, "data", "shanghai_food_map.csv")

# Real flagship Shanghai branch coordinates & street addresses for chain entries
REFINEMENTS = {
    "BV1NP411B7MQ_01": ("镇宁路店", "上海市静安区愚园路470弄/镇宁路附近", 31.2212, 121.4368),
    "BV1GL411A7b8_01": ("万航渡路店", "上海市静安区万航渡路218号", 31.2261, 121.4418),
    "BV1oa41117bs_01": ("胶州路店", "上海市静安区胶州路273弄12号", 31.2281, 121.4452),
    "BV14g411A7pa_01": ("长寿路/常德路店", "上海市静安区常德路888号", 31.2348, 121.4436),
    "BV1vy4y1V7VS_01": ("巨鹿路店", "上海市静安区巨鹿路758号", 31.2206, 121.4541),
    "BV1rA411s78W_01": ("富民路店", "上海市静安区富民路183号", 31.2195, 121.4502),
    "BV1gC4y1R7qo_01": ("南京东路宏伊广场店", "上海市黄浦区南京东路299号宏伊国际广场B1层", 31.2374, 121.4859),
    "BV1514y1K7tw_01": ("南京东路悦荟店", "上海市黄浦区南京东路353号悦荟广场5层", 31.2376, 121.4836),
    "BV1iL411b7xV_01": ("世茂广场店", "上海市黄浦区南京东路829号世茂广场L6层", 31.2351, 121.4759),
    "BV1Sf4y1s7S9_01": ("新世界城店", "上海市黄浦区南京西路2-68号新世界城8层", 31.2352, 121.4735),
    "BV1ak4y1q77J_01": ("人广高腾大厦店", "上海市黄浦区西藏中路180号高腾大厦3层", 31.2308, 121.4768),
    "BV1wL411S7Tp_01": ("来福士广场店", "上海市黄浦区西藏中路268号来福士广场B1层", 31.2322, 121.4765),
    "BV1hz411e7cE_01": ("美罗城店", "上海市徐汇区肇嘉浜路1111号美罗城2层", 31.1942, 121.4392),
    "BV1RB4y1q7KZ_01": ("北京西路店", "上海市静安区北京西路1068号食博汇3层", 31.2298, 121.4558),
    "BV1C3411573n_01": ("亚龙国际广场店", "上海市黄浦区金陵东路500号亚龙国际广场2层", 31.2289, 121.4812),
    "BV1d34y1d7MP_01": ("百联ZX/新世界店", "上海市黄浦区南京西路2-68号新世界城7层", 31.2354, 121.4731),
    "BV1Eg411P7eZ_01": ("云南南路店", "上海市黄浦区云南南路180号", 31.2272, 121.4796),
    "BV1Yg411F79N_01": ("人广福州路店", "上海市黄浦区福州路556号", 31.2339, 121.4789),
    "BV1Sb4y1y74Q_01": ("黄河路店", "上海市黄浦区黄河路72号", 31.2358, 121.4716),
    "BV1Yg411L7Xf_01": ("金陵东路店", "上海市黄浦区金陵东路569号汇都国际广场3层", 31.2283, 121.4782),
    "BV19K4y1T7kw_01": ("徐家汇腾飞大厦店", "上海市徐汇区天钥桥路333号腾飞大厦4层", 31.1895, 121.4416),
    "BV1Wp4y1W7tx_01": ("和平影都店", "上海市黄浦区西藏中路290号", 31.2336, 121.4758),
    "BV12v411W798_01": ("福州路总店", "上海市黄浦区福州路530号", 31.2337, 121.4795),
    "BV133411u7Zg_01": ("南京东路恒基名人店", "上海市黄浦区南京东路300号恒基名人购物中心4层", 31.2371, 121.4851),
}


def main():
    with open(JSON_PATH, "r", encoding="utf-8") as f:
        rests = json.load(f)

    updated = 0
    for r in rests:
        eid = r["entry_id"]
        if eid in REFINEMENTS:
            branch, addr, lat, lng = REFINEMENTS[eid]
            r["branch_name"] = branch
            r["address"] = addr
            r["lat"] = lat
            r["lng"] = lng
            updated += 1

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

    print(f"Refined {updated} flagship branch coordinates & synced JSON + CSV.")


if __name__ == "__main__":
    main()
