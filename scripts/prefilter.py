import json
import os
import re

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
CATALOG_PATH = os.path.join(DATA_DIR, "catalog.json")
PREFILTER_PATH = os.path.join(DATA_DIR, "prefilter.json")

OUT_OF_TOWN_KEYWORDS = [
    # Domestic cities / provinces / regions
    "北京", "广州", "深圳", "成都", "重庆", "杭州", "南京", "苏州", "西安", "长沙",
    "武汉", "厦门", "青岛", "哈尔滨", "沈阳", "大连", "天津", "郑州", "济南", "福州",
    "昆明", "贵阳", "南宁", "海口", "三亚", "拉萨", "乌鲁木齐", "香港", "澳门", "台北",
    "台湾", "顺德", "潮汕", "汕头", "潮州", "延吉", "宁波", "温州", "无锡", "扬州",
    "常州", "绍兴", "嘉兴", "湖州", "台州", "金华", "珠海", "东莞", "佛山", "惠州",
    "中山", "江门", "泉州", "漳州", "桂林", "柳州", "北海", "大理", "丽江", "西双版纳",
    "香格里拉", "乐山", "自贡", "宜宾", "绵阳", "遵义", "银川", "西宁", "兰州", "太原",
    "大同", "呼和浩特", "长春", "吉林", "石家庄", "保定", "唐山", "烟台", "威海", "淄博",
    "徐州", "连云港", "淮安", "盐城", "镇江", "泰州", "南通", "合肥", "芜湖", "黄山",
    "南昌", "景德镇", "九江", "宜昌", "襄阳", "岳阳", "张家界", "凤凰", "新疆", "西藏",
    "云南", "四川", "广东", "福建", "广西", "东北", "海南", "内蒙古", "青海", "甘肃",
    "宁夏", "陕西", "山西", "河北", "河南", "山东", "江苏", "浙江", "安徽", "江西",
    "湖北", "湖南", "贵州", "黑龙江", "辽宁",
    # Foreign countries / cities
    "日本", "东京", "大阪", "京都", "北海道", "札幌", "福冈", "冲绳", "名古屋", "神户",
    "奈良", "横滨", "韩国", "首尔", "釜山", "济州", "泰国", "曼谷", "清迈", "普吉",
    "新加坡", "马来西亚", "吉隆坡", "槟城", "越南", "胡志明", "河内", "印尼", "巴厘岛",
    "菲律宾", "马尼拉", "柬埔寨", "美国", "纽约", "洛杉矶", "旧金山", "拉斯维加斯",
    "芝加哥", "西雅图", "波士顿", "夏威夷", "加州", "加拿大", "温哥华", "多伦多",
    "英国", "伦敦", "爱丁堡", "法国", "巴黎", "里昂", "马赛", "意大利", "罗马", "米兰",
    "威尼斯", "佛罗伦萨", "那不勒斯", "德国", "柏林", "慕尼黑", "法兰克福", "瑞士",
    "苏黎世", "日内瓦", "西班牙", "马德里", "巴塞罗那", "葡萄牙", "里斯本", "荷兰",
    "阿姆斯特丹", "比利时", "奥地利", "维也纳", "捷克", "布拉格", "希腊", "雅典",
    "土耳其", "伊斯坦布尔", "俄罗斯", "莫斯科", "澳洲", "澳大利亚", "悉尼", "墨尔本",
    "新西兰", "奥克兰", "迪拜", "阿联酋", "埃及", "摩洛哥", "墨西哥", "巴西", "秘鲁",
]

# Phrases where a city name is actually a cuisine/dish in Shanghai, not a location
CUISINE_FALSE_POSITIVES = [
    "北京烤鸭", "成都火锅", "重庆火锅", "重庆小面", "成都串串", "长沙臭豆腐",
    "广州早茶", "顺德菜", "潮汕牛肉", "潮汕火锅", "潮汕砂锅粥", "潮汕生腌",
    "香港茶餐厅", "台湾牛肉面", "台湾卤肉饭", "延吉冷面", "东北菜", "东北烧烤",
    "东北铁锅炖", "云南菜", "云南米线", "云南火锅", "四川火锅", "川菜", "粤菜",
    "湘菜", "鲁菜", "苏菜", "浙菜", "徽菜", "闽菜", "西北菜", "新疆菜", "新疆大盘鸡",
    "新疆烧烤", "南京大牌档", "南京盐水鸭", "苏州面", "苏帮菜", "杭州菜", "杭帮菜",
    "宁波菜", "温州菜", "台州菜", "福建菜", "江西菜", "湖北菜", "武汉热干面",
    "西安肉夹馍", "陕西面", "兰州拉面", "日本料理", "日料", "韩国烤肉", "韩餐",
    "泰国菜", "泰餐", "越南河粉", "新加坡菜", "马来西亚菜", "美国汉堡", "法餐",
    "意大利菜", "意餐", "西班牙菜", "墨西哥菜", "土耳其烤肉", "印度菜",
]

NON_RESTAURANT_KEYWORDS = [
    "开箱", "网购", "淘宝", "拼多多", "外卖测评", "零食测评", "便利店", "超市测评",
    "山姆", "Costco", "开市客", "盒马", "奥乐齐", "ALDI", "在家做", "自己做",
    "教程", "食谱", "厨房", "做饭", "Vlog", "vlog", "VLOG", "搬家", "装修",
    "婚礼", "结婚", "猫咪", "小猫", "狗狗", "问答", "Q&A", "直播", "年度总结",
    "月饼", "粽子", "年货", "礼盒", "速食", "自热", "预制菜", "螺蛳粉测评",
    "泡面", "方便面", "奶茶测评", "雪糕", "冰淇淋测评", "试吃",
]


def classify_video(video: dict) -> tuple[str, str]:
    title = video.get("title", "")
    desc = video.get("description", "")
    series_tags = video.get("series_tags") or []
    text = f"{title} {desc}"

    # If explicitly mentions 上海 or known Shanghai districts/landmarks, keep
    shanghai_markers = ["上海", "魔都", "静安", "徐汇", "黄浦", "长宁", "浦东", "杨浦", "虹口", "普陀", "闵行", "宝山", "嘉定", "松江", "青浦", "奉贤", "金山", "崇明", "外滩", "陆家嘴", "武康路", "安福路", "巨鹿路", "富民路", "长乐路", "愚园路", "定西路", "五角场", "新天地", "人民广场", "南京西路", "南京东路", "淮海路", "徐家汇", "打浦桥", "七宝", "前滩"]
    has_shanghai = any(m in text for m in shanghai_markers)

    # Series "体验猩生活" or "王师傅好为人师系列" or "Food chat" might be non-restaurant
    if any(s in series_tags for s in ["王师傅好为人师系列"]):
        return "exclude_non_restaurant", "series:王师傅好为人师系列"

    # Strip known cuisine false positives before checking out-of-town location
    cleaned_title = title
    for fp in CUISINE_FALSE_POSITIVES:
        cleaned_title = cleaned_title.replace(fp, "")

    matched_cities = [kw for kw in OUT_OF_TOWN_KEYWORDS if kw in cleaned_title]
    if matched_cities and not has_shanghai:
        return "exclude_out_of_town", f"title_city:{','.join(matched_cities)}"

    # Check description for strong out-of-town travel markers if title doesn't mention Shanghai
    if not has_shanghai:
        cleaned_desc = desc
        for fp in CUISINE_FALSE_POSITIVES:
            cleaned_desc = cleaned_desc.replace(fp, "")
        # Look for patterns like "来北京", "在成都", "东京之旅", "广州探店"
        for kw in OUT_OF_TOWN_KEYWORDS:
            if re.search(rf"(来|去|在|飞|逛|吃遍){re.escape(kw)}|{re.escape(kw)}(探店|旅游|旅行|美食|第一|第二|Vlog)", cleaned_desc):
                return "exclude_out_of_town", f"desc_city:{kw}"

    # Check non-restaurant keywords in title
    matched_non_rest = [kw for kw in NON_RESTAURANT_KEYWORDS if kw in title]
    if matched_non_rest:
        # Exceptions: some "还愿挑战" or "凭啥这么贵" might have "外卖" etc., check carefully
        return "exclude_non_restaurant", f"title_non_rest:{','.join(matched_non_rest)}"

    return "candidate", "shanghai_or_uncertain"


def main():
    with open(CATALOG_PATH, "r", encoding="utf-8") as f:
        catalog = json.load(f)

    videos = catalog.get("videos", [])
    counts = {"candidate": 0, "exclude_out_of_town": 0, "exclude_non_restaurant": 0}
    results = []
    for v in videos:
        status, reason = classify_video(v)
        counts[status] += 1
        item = dict(v)
        item["prefilter_status"] = status
        item["prefilter_reason"] = reason
        results.append(item)

    out = {
        "total": len(videos),
        "counts": counts,
        "videos": results,
    }
    with open(PREFILTER_PATH, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Prefilter complete: {counts}")


if __name__ == "__main__":
    main()
