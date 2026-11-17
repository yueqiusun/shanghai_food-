import html
import json
import os
import urllib.parse
from collections import Counter

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT_DIR, "data")
DOCS_DIR = os.path.join(ROOT_DIR, "docs")


def classify_cuisine_group(cat: str) -> str:
    c = cat or ""
    if any(k in c for k in ("火锅", "涮", "斑鱼", "椰子鸡", "打边炉", "烧鸡公", "大锅台", "美蛙", "粥底")):
        return "火锅涮肉"
    if any(k in c for k in ("本帮", "淮扬", "宁波", "台州", "徽菜", "南京", "江浙", "蟹宴")):
        return "本帮江浙"
    if any(k in c for k in ("粤菜", "顺德", "潮州", "港式", "茶餐厅", "煲仔", "啫啫", "烧腊")):
        return "粤菜顺德"
    if any(k in c for k in ("川", "湘")):
        return "川湘江湖"
    if any(k in c for k in ("日料", "日式", "寿喜", "烧鸟", "怀石", "天妇罗", "海胆", "烧肉", "韩式", "韩料")):
        return "日韩料理"
    if any(k in c for k in ("西餐", "牛排", "法餐", "意大利", "意面", "意式", "披萨", "西班牙", "美式", "德州")):
        return "西餐牛排"
    if any(k in c for k in ("烧烤", "羊肉串", "烤羊", "烤全羊", "小龙虾", "夜宵", "宵夜", "东北")):
        return "烧烤夜宵"
    if any(k in c for k in ("面", "生煎", "馄饨", "小吃", "炸鸡", "快餐", "蛋挞", "素", "咖啡")):
        return "小吃面点"
    return "异域自助"


def build_apple_maps_url(name: str, address: str, lat: float, lng: float) -> str:
    q = urllib.parse.quote(f"{name} {address}".strip())
    return f"https://maps.apple.com/?q={q}&ll={lat},{lng}"


def build_amap_uri(name: str, lat: float, lng: float) -> str:
    q = urllib.parse.quote(name.strip())
    return f"https://uri.amap.com/search?keyword={q}&center={lng},{lat}&city=310000&src=shanghai_food_radar"


def render_prerendered_card(r: dict, is_black: bool = False) -> str:
    eid = html.escape(r["entry_id"])
    name = html.escape(r["name"])
    branch = html.escape(r.get("branch_name") or "")
    district = html.escape(r.get("district") or "")
    area = html.escape(r.get("commercial_area") or "")
    cuisine = html.escape(r.get("cuisine_category") or "")
    series = html.escape(r.get("series_name") or "")
    price = r.get("price_per_person")
    price_str = f"¥{price}/人" if price else "时价"
    summary = html.escape(r.get("overall_review_summary") or "")
    rec_dishes = [html.escape(d) for d in (r.get("recommended_dishes") or [])]
    avoid_dishes = [html.escape(d) for d in (r.get("avoid_dishes") or [])]
    apple_url = html.escape(build_apple_maps_url(r["name"], r.get("address", ""), r["lat"], r["lng"]))
    amap_url = html.escape(build_amap_uri(r["name"], r["lat"], r["lng"]))
    video_url = html.escape(r.get("video_url") or "")
    dp_url = html.escape(r.get("dianping_url") or "")

    badge_cls = "tier-black" if is_black else "tier-top"
    badge_txt = "💣 严重踩雷" if is_black else "🏆 强烈推荐"

    dishes_html = ""
    if rec_dishes and not is_black:
        pills = "".join(f'<span class="dish-tag good">👍 {d}</span>' for d in rec_dishes[:4])
        dishes_html = f'<div class="dish-row">{pills}</div>'
    elif avoid_dishes:
        pills = "".join(f'<span class="dish-tag bad">⚠️ 避雷：{d}</span>' for d in avoid_dishes[:4])
        dishes_html = f'<div class="dish-row">{pills}</div>'

    branch_html = f' <span class="card-branch">({branch})</span>' if branch else ""
    res_badge_html = '<span class="res-badge">📅 需预约</span>' if r.get("reservation_required") else ""

    return f"""<article class="rest-card {'is-black-card' if is_black else 'is-red-card'}" data-eid="{eid}">
  <div class="card-head">
    <div class="card-title-wrap">
      <h4 class="card-title">{name}{branch_html}</h4>
      <div class="card-meta">
        <span class="tier-badge {badge_cls}">{badge_txt}</span>
        {res_badge_html}
        <span class="price-pill">{price_str}</span>
        <span class="meta-dot">{district} · {area}</span>
        <span class="meta-dot">{cuisine}</span>
        <span class="series-pill">{series}</span>
      </div>
    </div>
    <button type="button" class="fav-btn" data-fav-toggle="{eid}" aria-label="收藏 {name}">☆</button>
  </div>
  <p class="card-summary">{summary}</p>
  {dishes_html}
  <div class="card-actions">
    <button type="button" class="act-btn primary" data-open-modal="{eid}">🗣️ 点单/打车卡</button>
    <a class="act-btn" href="{apple_url}" target="_blank" rel="noopener">🍎 Apple地图</a>
    <a class="act-btn" href="{amap_url}" target="_blank" rel="noopener">🧭 高德</a>
    <a class="act-btn" href="{video_url}" target="_blank" rel="noopener">📺 B站</a>
    <a class="act-btn" href="{dp_url}" target="_blank" rel="noopener">🍜 点评</a>
  </div>
</article>"""


def build_red_black_html(restaurants: list[dict]) -> str:
    red_top = [r for r in restaurants if r["verdict_tier"] == "强烈推荐"]
    black_list = [r for r in restaurants if r["verdict_tier"] == "严重踩雷"]

    budget = [r for r in red_top if (r.get("price_per_person") or 0) <= 80]
    mid = [r for r in red_top if 80 < (r.get("price_per_person") or 0) <= 300]
    luxury = [r for r in red_top if (r.get("price_per_person") or 0) > 300]

    budget.sort(key=lambda x: x.get("price_per_person") or 0)
    mid.sort(key=lambda x: x.get("price_per_person") or 0)
    luxury.sort(key=lambda x: x.get("price_per_person") or 0)
    black_list.sort(key=lambda x: x.get("price_per_person") or 0, reverse=True)

    sec_budget = "\n".join(render_prerendered_card(r, False) for r in budget)
    sec_mid = "\n".join(render_prerendered_card(r, False) for r in mid)
    sec_lux = "\n".join(render_prerendered_card(r, False) for r in luxury)
    sec_black = "\n".join(render_prerendered_card(r, True) for r in black_list)

    return f"""
<div class="rb-hero">
  <div class="rb-stat-grid">
    <a href="#rb-budget" class="rb-stat-card red">
      <div class="rb-stat-num">{len(budget)}</div>
      <div class="rb-stat-lbl">🥢 平价封神 (≤¥80)</div>
    </a>
    <a href="#rb-mid" class="rb-stat-card orange">
      <div class="rb-stat-num">{len(mid)}</div>
      <div class="rb-stat-lbl">🍲 聚餐必冲 (¥81-300)</div>
    </a>
    <a href="#rb-lux" class="rb-stat-card gold">
      <div class="rb-stat-num">{len(luxury)}</div>
      <div class="rb-stat-lbl">🥂 高奢不踩雷 (&gt;¥300)</div>
    </a>
    <a href="#rb-black" class="rb-stat-card dark">
      <div class="rb-stat-num">{len(black_list)}</div>
      <div class="rb-stat-lbl">💣 严重踩雷预警</div>
    </a>
  </div>
  <div class="rb-jump-row">
    <a href="#ios-pwa-guide" class="pwa-banner-link">📱 在 iPhone Safari 添加到主屏幕 · 享全屏 120Hz 与断网离线秒开 →</a>
  </div>
</div>

<section id="rb-budget" class="rb-section">
  <div class="rb-sec-header">
    <h3>🥢 红榜 · 平价封神（人均 ≤ ¥80 · 共 {len(budget)} 家）</h3>
    <p>小吃、面馆、生煎、盖码饭与平价自助，闭眼冲不心疼钱包</p>
  </div>
  <div class="card-stack">{sec_budget}</div>
</section>

<section id="rb-mid" class="rb-section">
  <div class="rb-sec-header">
    <h3>🍲 红榜 · 聚餐闭眼冲（人均 ¥81–¥300 · 共 {len(mid)} 家）</h3>
    <p>烧烤、火锅、烟熏烤肉、地方菜驻沪办，朋友聚会高性价比首选</p>
  </div>
  <div class="card-stack">{sec_mid}</div>
</section>

<section id="rb-lux" class="rb-section">
  <div class="rb-sec-header">
    <h3>🥂 红榜 · 高奢不踩雷（人均 &gt; ¥300 · 共 {len(luxury)} 家）</h3>
    <p>纪念日与重磅宴请，贵但物有所值的米其林/黑珍珠封神店</p>
  </div>
  <div class="card-stack">{sec_lux}</div>
</section>

<section id="rb-black" class="rb-section black-zone">
  <div class="rb-sec-header">
    <h3>💣 黑榜预警 · 严重踩雷（共 {len(black_list)} 家）</h3>
    <p>高溢价噱头、图文不符、口味翻车或曾被提示食安隐患，出行前必看避坑</p>
  </div>
  <div class="card-stack">{sec_black}</div>
</section>

<section id="ios-pwa-guide" class="rb-section pwa-guide-box">
  <div class="rb-sec-header">
    <h3>📱 如何在 iPhone 上添加到主屏幕离线使用</h3>
    <p>无需下载 App Store 安装包，3 步把上海美食雷达变成原生级全屏离线应用</p>
  </div>
  <div class="pwa-steps">
    <div class="pwa-step">
      <div class="pwa-step-badge">STEP 1</div>
      <div class="pwa-svg-box">
        <svg viewBox="0 0 120 80" width="96" height="64" aria-hidden="true">
          <rect x="14" y="8" width="92" height="64" rx="12" fill="none" stroke="currentColor" stroke-width="2.5" opacity="0.45"/>
          <rect x="44" y="26" width="32" height="32" rx="7" fill="none" stroke="#ff5722" stroke-width="2.8"/>
          <path d="M60 15 V42 M51 24 L60 15 L69 24" fill="none" stroke="#ff5722" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <h4>1. 点击底部「分享」</h4>
      <p>用 iPhone 自带 <strong>Safari 浏览器</strong>打开本网址，轻点屏幕正下方的分享图标 <code>[↑]</code>。</p>
    </div>
    <div class="pwa-step">
      <div class="pwa-step-badge">STEP 2</div>
      <div class="pwa-svg-box">
        <svg viewBox="0 0 120 80" width="96" height="64" aria-hidden="true">
          <rect x="14" y="12" width="92" height="56" rx="12" fill="none" stroke="currentColor" stroke-width="2.5" opacity="0.45"/>
          <rect x="26" y="24" width="32" height="32" rx="8" fill="none" stroke="#ff5722" stroke-width="2.8"/>
          <path d="M42 32 V48 M34 40 H50" stroke="#ff5722" stroke-width="3" stroke-linecap="round"/>
          <line x1="66" y1="36" x2="94" y2="36" stroke="currentColor" stroke-width="3" stroke-linecap="round"/>
          <line x1="66" y1="46" x2="86" y2="46" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" opacity="0.6"/>
        </svg>
      </div>
      <h4>2. 选择「添加到主屏幕」</h4>
      <p>在弹出的系统菜单中向上滑动，找到并点击 <strong>「添加到主屏幕」</strong> 选项。</p>
    </div>
    <div class="pwa-step">
      <div class="pwa-step-badge">STEP 3</div>
      <div class="pwa-svg-box">
        <svg viewBox="0 0 120 80" width="96" height="64" aria-hidden="true">
          <rect x="20" y="10" width="80" height="60" rx="14" fill="none" stroke="currentColor" stroke-width="2.5" opacity="0.45"/>
          <circle cx="48" cy="40" r="14" fill="#ff5722" opacity="0.2"/>
          <circle cx="48" cy="40" r="7" fill="#ff5722"/>
          <path d="M68 41 L76 49 L92 31" fill="none" stroke="#10b981" stroke-width="3.5" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
      </div>
      <h4>3. 点击右上角「添加」</h4>
      <p>从桌面图标启动即可隐藏地址栏全屏浏览，地下商场/地铁无信号也能离线查店点菜！</p>
    </div>
  </div>
</section>
"""


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="zh-CN" data-theme="oled">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=5, viewport-fit=cover">
  <title>上海美食雷达 · 王师傅和小毛毛探店地图 (164店)</title>
  <meta name="description" content="王师傅和小毛毛164家上海实体餐厅探店红黑榜、35大商圈周边步行距离导航、纯矢量触控地图与离线到店点单大字卡">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
  <meta name="apple-mobile-web-app-title" content="上海美食雷达">
  <meta name="mobile-web-app-capable" content="yes">
  <meta name="format-detection" content="telephone=no">
  <meta name="theme-color" id="metaThemeColor" content="#000000">
  <link rel="manifest" href="./manifest.webmanifest">
  <link rel="apple-touch-icon" href="./apple-touch-icon.png">
  <link rel="icon" type="image/png" sizes="180x180" href="./apple-touch-icon.png">
  <link rel="icon" type="image/svg+xml" href="./icon.svg">
  <style>
    :root, [data-theme="light"] {
      --bg-app: #f5f5f7;
      --bg-surface: #ffffff;
      --bg-elevated: #f0f1f5;
      --bg-pill: #ebedf2;
      --text-main: #141519;
      --text-sub: #525665;
      --text-muted: #7b8091;
      --border-subtle: rgba(20, 21, 25, 0.09);
      --border-strong: rgba(20, 21, 25, 0.18);
      --accent: #e64a19;
      --accent-soft: rgba(230, 74, 25, 0.12);
      --accent-text: #ffffff;
      --tier-top-bg: #ffe9e2;
      --tier-top-fg: #c62828;
      --tier-good-bg: #e0f5ec;
      --tier-good-fg: #0d7a52;
      --tier-mid-bg: #eef0f5;
      --tier-mid-fg: #4a5060;
      --tier-low-bg: #fff4db;
      --tier-low-fg: #a66300;
      --tier-black-bg: #fee2e2;
      --tier-black-fg: #991b1b;
      --map-bg: #eef3f8;
      --map-water: #b9dcf7;
      --map-water-stroke: #8cc2ec;
      --map-metro: #10b981;
      --map-ring: rgba(20, 21, 25, 0.12);
      --shadow-card: 0 2px 10px rgba(0, 0, 0, 0.05);
      --theme-meta: #ffffff;
    }

    [data-theme="oled"] {
      --bg-app: #000000;
      --bg-surface: #111216;
      --bg-elevated: #1b1d24;
      --bg-pill: #20232c;
      --text-main: #f4f5f8;
      --text-sub: #b0b5c4;
      --text-muted: #7c8294;
      --border-subtle: rgba(255, 255, 255, 0.10);
      --border-strong: rgba(255, 255, 255, 0.20);
      --accent: #ff5e36;
      --accent-soft: rgba(255, 94, 54, 0.18);
      --accent-text: #ffffff;
      --tier-top-bg: rgba(255, 87, 51, 0.22);
      --tier-top-fg: #ff8a65;
      --tier-good-bg: rgba(16, 185, 129, 0.20);
      --tier-good-fg: #4ade80;
      --tier-mid-bg: rgba(148, 163, 184, 0.18);
      --tier-mid-fg: #cbd5e1;
      --tier-low-bg: rgba(245, 158, 11, 0.20);
      --tier-low-fg: #fbbf24;
      --tier-black-bg: rgba(239, 68, 68, 0.25);
      --tier-black-fg: #fca5a5;
      --map-bg: #07090e;
      --map-water: #0e2439;
      --map-water-stroke: #183d5e;
      --map-metro: #10b981;
      --map-ring: rgba(255, 255, 255, 0.10);
      --shadow-card: 0 4px 16px rgba(0, 0, 0, 0.45);
      --theme-meta: #000000;
    }

    [data-theme="sunlight"] {
      --bg-app: #ffffff;
      --bg-surface: #ffffff;
      --bg-elevated: #f3f4f6;
      --bg-pill: #e5e7eb;
      --text-main: #000000;
      --text-sub: #111827;
      --text-muted: #374151;
      --border-subtle: #111827;
      --border-strong: #000000;
      --accent: #c81e1e;
      --accent-soft: #fde8e8;
      --accent-text: #ffffff;
      --tier-top-bg: #991b1b;
      --tier-top-fg: #ffffff;
      --tier-good-bg: #065f46;
      --tier-good-fg: #ffffff;
      --tier-mid-bg: #374151;
      --tier-mid-fg: #ffffff;
      --tier-low-bg: #92400e;
      --tier-low-fg: #ffffff;
      --tier-black-bg: #000000;
      --tier-black-fg: #fef08a;
      --map-bg: #ffffff;
      --map-water: #93c5fd;
      --map-water-stroke: #1d4ed8;
      --map-metro: #047857;
      --map-ring: rgba(0, 0, 0, 0.35);
      --shadow-card: none;
      --theme-meta: #ffffff;
    }

    * {
      box-sizing: border-box;
      -webkit-tap-highlight-color: transparent;
    }

    html, body {
      margin: 0;
      padding: 0;
      width: 100%;
      height: 100%;
      background: var(--bg-app);
      color: var(--text-main);
      font-family: -apple-system, BlinkMacSystemFont, "SF Pro Text", "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", system-ui, sans-serif;
      line-height: 1.45;
      overflow: hidden;
      -webkit-text-size-adjust: 100%;
    }

    /* Prevent iOS Safari auto-zoom on focus: all form controls >= 16px */
    input, select, textarea {
      font-size: 16px !important;
      font-family: inherit;
      color: var(--text-main);
    }

    button {
      font-family: inherit;
      cursor: pointer;
    }

    /* Strict 3-part viewport flex shell */
    .app-shell {
      position: fixed;
      inset: 0;
      height: 100vh;
      height: 100dvh;
      display: flex;
      flex-direction: column;
      overflow: hidden;
      background: var(--bg-app);
    }

    /* 1. Top Fixed Header Bar */
    .top-bar {
      flex: 0 0 auto;
      padding: calc(env(safe-area-inset-top, 0px) + 8px) calc(env(safe-area-inset-right, 0px) + 12px) 8px calc(env(safe-area-inset-left, 0px) + 12px);
      background: var(--bg-surface);
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      z-index: 20;
    }

    .brand-group {
      display: flex;
      align-items: center;
      gap: 9px;
      min-width: 0;
    }

    .brand-logo {
      width: 32px;
      height: 32px;
      border-radius: 9px;
      flex-shrink: 0;
    }

    .brand-text {
      min-width: 0;
    }

    .brand-title {
      margin: 0;
      font-size: 16px;
      font-weight: 800;
      letter-spacing: -0.2px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .brand-sub {
      font-size: 11px;
      color: var(--text-muted);
      white-space: nowrap;
    }

    .top-actions {
      display: flex;
      align-items: center;
      gap: 6px;
      flex-shrink: 0;
    }

    .top-pill-btn {
      border: 1px solid var(--border-subtle);
      background: var(--bg-elevated);
      color: var(--text-main);
      border-radius: 999px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 4px;
      white-space: nowrap;
    }

    .top-pill-btn.gps-active {
      background: var(--accent);
      color: var(--accent-text);
      border-color: var(--accent);
    }

    /* 2. Middle Independent Scroll Container */
    #mainScroller {
      flex: 1 1 0%;
      min-height: 0;
      overflow-y: auto;
      overflow-x: hidden;
      -webkit-overflow-scrolling: touch;
      overscroll-behavior-y: contain;
      padding: 10px calc(env(safe-area-inset-right, 0px) + 12px) 76px calc(env(safe-area-inset-left, 0px) + 12px);
      scroll-behavior: auto;
    }

    .tab-panel {
      display: none;
    }
    .tab-panel.active {
      display: block;
    }

    /* Map Pane (Tab 2 on mobile, right split column on >=900px) */
    #mapPane {
      display: none;
      flex: 1 1 0%;
      min-height: 0;
      position: relative;
      background: var(--map-bg);
      overflow: hidden;
    }
    #mapPane.mobile-active {
      display: flex;
      flex-direction: column;
    }

    /* 3. Bottom Fixed Tab Bar INSIDE .app-shell */
    .bottom-tabs {
      flex: 0 0 auto;
      display: grid;
      grid-template-columns: repeat(4, 1fr);
      background: var(--bg-surface);
      border-top: 1px solid var(--border-subtle);
      padding: 4px env(safe-area-inset-right, 0px) calc(env(safe-area-inset-bottom, 0px) + 4px) env(safe-area-inset-left, 0px);
      z-index: 20;
    }

    .tab-btn {
      appearance: none;
      border: none;
      background: transparent;
      color: var(--text-muted);
      padding: 6px 4px;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      gap: 2px;
      font-size: 11px;
      font-weight: 600;
      position: relative;
    }

    .tab-btn .tab-ico {
      font-size: 18px;
      line-height: 1.1;
    }

    .tab-btn.active {
      color: var(--accent);
    }

    .fav-count-badge {
      position: absolute;
      top: 2px;
      right: calc(50% - 22px);
      background: var(--accent);
      color: #fff;
      font-size: 10px;
      font-weight: 700;
      min-width: 16px;
      height: 16px;
      border-radius: 999px;
      padding: 0 4px;
      display: none;
      align-items: center;
      justify-content: center;
    }
    .fav-count-badge.has-items {
      display: inline-flex;
    }

    /* Desktop >= 900px Split View */
    @media (min-width: 900px) {
      .app-shell {
        display: grid;
        grid-template-columns: minmax(430px, 490px) 1fr;
        grid-template-rows: auto minmax(0, 1fr) auto;
      }
      .top-bar {
        grid-column: 1 / -1;
        grid-row: 1;
      }
      #mainScroller {
        grid-column: 1;
        grid-row: 2;
        display: block !important;
        border-right: 1px solid var(--border-subtle);
      }
      #mapPane {
        grid-column: 2;
        grid-row: 2 / 4;
        display: flex !important;
        flex-direction: column;
      }
      .bottom-tabs {
        grid-column: 1;
        grid-row: 3;
        border-right: 1px solid var(--border-subtle);
      }
      .floating-scroll-btns {
        right: auto !important;
        left: 432px;
      }
    }

    /* Location & Search Controls */
    .control-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 14px;
      padding: 11px;
      margin-bottom: 10px;
      box-shadow: var(--shadow-card);
    }

    .loc-header-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
      margin-bottom: 8px;
      flex-wrap: wrap;
    }

    .loc-status {
      font-size: 13px;
      font-weight: 700;
      color: var(--text-main);
      display: flex;
      align-items: center;
      gap: 6px;
      min-width: 0;
    }

    .loc-btns {
      display: flex;
      gap: 6px;
      flex-wrap: wrap;
    }

    .btn-sm {
      border: 1px solid var(--border-subtle);
      background: var(--bg-elevated);
      color: var(--text-main);
      border-radius: 8px;
      padding: 6px 10px;
      font-size: 12px;
      font-weight: 600;
    }
    .btn-sm.accent {
      background: var(--accent);
      color: var(--accent-text);
      border-color: var(--accent);
    }

    .loc-notice {
      display: none;
      margin: 6px 0 8px;
      padding: 8px 10px;
      border-radius: 9px;
      background: var(--accent-soft);
      color: var(--text-main);
      font-size: 12px;
      align-items: center;
      justify-content: space-between;
      gap: 8px;
    }
    .loc-notice.show {
      display: flex;
    }

    /* Horizontal capsule strips */
    .chip-strip {
      display: flex;
      gap: 6px;
      overflow-x: auto;
      padding-bottom: 4px;
      margin-bottom: 6px;
      scrollbar-width: none;
      -ms-overflow-style: none;
    }
    .chip-strip::-webkit-scrollbar {
      display: none;
    }

    .chip {
      flex: 0 0 auto;
      border: 1px solid var(--border-subtle);
      background: var(--bg-pill);
      color: var(--text-sub);
      border-radius: 999px;
      padding: 5px 11px;
      font-size: 12px;
      font-weight: 600;
      white-space: nowrap;
    }
    .chip.active {
      background: var(--accent);
      color: var(--accent-text);
      border-color: var(--accent);
    }

    .search-sort-row {
      display: flex;
      gap: 8px;
      margin: 8px 0;
    }

    .search-box {
      position: relative;
      flex: 1 1 auto;
      min-width: 0;
    }

    .search-input {
      width: 100%;
      height: 40px;
      padding: 0 32px 0 32px;
      border-radius: 10px;
      border: 1px solid var(--border-strong);
      background: var(--bg-elevated);
      outline: none;
    }
    .search-input:focus {
      border-color: var(--accent);
    }

    .search-ico {
      position: absolute;
      left: 10px;
      top: 50%;
      transform: translateY(-50%);
      font-size: 14px;
      pointer-events: none;
    }

    .clear-search-btn {
      position: absolute;
      right: 6px;
      top: 50%;
      transform: translateY(-50%);
      border: none;
      background: transparent;
      color: var(--text-muted);
      font-size: 16px;
      padding: 4px;
      display: none;
    }

    .sort-select, .landmark-select {
      height: 40px;
      border-radius: 10px;
      border: 1px solid var(--border-strong);
      background: var(--bg-elevated);
      padding: 0 8px;
      max-width: 138px;
    }

    .landmark-picker-row {
      display: flex;
      gap: 6px;
      align-items: center;
      margin-bottom: 6px;
    }
    .landmark-select {
      max-width: none;
      flex: 1 1 auto;
      height: 36px;
    }

    .result-summary-bar {
      display: flex;
      align-items: center;
      justify-content: space-between;
      font-size: 12px;
      color: var(--text-sub);
      margin: 6px 2px 8px;
      gap: 8px;
    }

    /* Restaurant Cards */
    .card-stack {
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .rest-card {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 14px;
      padding: 12px;
      box-shadow: var(--shadow-card);
      transition: border-color 0.15s ease;
    }
    .rest-card.selected-card {
      border-color: var(--accent);
      box-shadow: 0 0 0 2px var(--accent-soft);
    }
    .rest-card.is-black-card {
      border-left: 4px solid #ef4444;
    }
    .rest-card.is-red-card {
      border-left: 4px solid var(--accent);
    }

    .card-head {
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 8px;
    }

    .card-title-wrap {
      min-width: 0;
      flex: 1 1 auto;
    }

    .card-title {
      margin: 0 0 5px;
      font-size: 16px;
      font-weight: 800;
      line-height: 1.3;
      color: var(--text-main);
    }

    .card-branch {
      font-size: 13px;
      font-weight: 500;
      color: var(--text-sub);
    }

    .card-meta {
      display: flex;
      flex-wrap: wrap;
      align-items: center;
      gap: 5px;
      font-size: 12px;
    }

    .tier-badge {
      padding: 2px 7px;
      border-radius: 6px;
      font-weight: 700;
      font-size: 11px;
    }
    .tier-top { background: var(--tier-top-bg); color: var(--tier-top-fg); }
    .tier-good { background: var(--tier-good-bg); color: var(--tier-good-fg); }
    .tier-mid { background: var(--tier-mid-bg); color: var(--tier-mid-fg); }
    .tier-low { background: var(--tier-low-bg); color: var(--tier-low-fg); }
    .tier-black { background: var(--tier-black-bg); color: var(--tier-black-fg); }

    .walk-badge {
      padding: 2px 8px;
      border-radius: 6px;
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 700;
      font-size: 11.5px;
    }

    .res-badge {
      padding: 2px 7px;
      border-radius: 6px;
      background: rgba(59, 130, 246, 0.16);
      color: #60a5fa;
      border: 1px solid rgba(59, 130, 246, 0.35);
      font-weight: 700;
      font-size: 11px;
    }
    [data-theme="light"] .res-badge,
    [data-theme="sunlight"] .res-badge {
      background: #dbeafe;
      color: #1d4ed8;
      border-color: #93c5fd;
    }

    .res-alert-box {
      border: 1px solid rgba(59, 130, 246, 0.45);
      background: rgba(59, 130, 246, 0.12);
      color: #93c5fd;
      border-radius: 12px;
      padding: 9px 12px;
      margin-bottom: 12px;
      font-size: 13px;
      font-weight: 600;
    }
    [data-theme="light"] .res-alert-box,
    [data-theme="sunlight"] .res-alert-box {
      background: #eff6ff;
      color: #1e40af;
      border-color: #93c5fd;
    }

    .price-pill {
      font-weight: 700;
      color: var(--text-main);
    }

    .meta-dot {
      color: var(--text-sub);
    }

    .series-pill {
      padding: 1px 6px;
      border-radius: 5px;
      background: var(--bg-pill);
      color: var(--text-muted);
      font-size: 11px;
    }

    .fav-btn {
      border: 1px solid var(--border-subtle);
      background: var(--bg-elevated);
      color: var(--text-muted);
      width: 34px;
      height: 34px;
      border-radius: 50%;
      font-size: 17px;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      flex-shrink: 0;
    }
    .fav-btn.is-fav {
      color: #f59e0b;
      border-color: rgba(245, 158, 11, 0.45);
      background: rgba(245, 158, 11, 0.14);
    }

    .card-address {
      margin: 6px 0 4px;
      font-size: 12px;
      color: var(--text-muted);
    }

    .card-summary {
      margin: 6px 0;
      font-size: 13px;
      color: var(--text-sub);
    }

    .review-quotes {
      margin: 6px 0;
      padding: 7px 9px;
      border-radius: 9px;
      background: var(--bg-elevated);
      font-size: 12px;
      color: var(--text-sub);
      display: flex;
      flex-direction: column;
      gap: 3px;
    }

    .dish-row {
      display: flex;
      flex-wrap: wrap;
      gap: 5px;
      margin: 6px 0;
    }

    .dish-tag {
      font-size: 11.5px;
      padding: 2px 7px;
      border-radius: 6px;
      font-weight: 600;
    }
    .dish-tag.good {
      background: var(--tier-good-bg);
      color: var(--tier-good-fg);
    }
    .dish-tag.bad {
      background: var(--tier-black-bg);
      color: var(--tier-black-fg);
    }

    .card-actions {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      margin-top: 8px;
      padding-top: 8px;
      border-top: 1px dashed var(--border-subtle);
    }

    .act-btn {
      text-decoration: none;
      border: 1px solid var(--border-subtle);
      background: var(--bg-elevated);
      color: var(--text-main);
      padding: 6px 9px;
      border-radius: 8px;
      font-size: 12px;
      font-weight: 600;
      display: inline-flex;
      align-items: center;
      gap: 3px;
    }
    .act-btn.primary {
      background: var(--accent);
      color: var(--accent-text);
      border-color: var(--accent);
    }

    .load-more-wrap {
      text-align: center;
      padding: 16px 0 8px;
    }

    /* Floating Quick Scroll Buttons */
    .floating-scroll-btns {
      position: fixed;
      right: calc(env(safe-area-inset-right, 0px) + 12px);
      bottom: calc(env(safe-area-inset-bottom, 0px) + 66px);
      display: flex;
      flex-direction: column;
      gap: 6px;
      z-index: 25;
    }

    .float-btn {
      width: 38px;
      height: 38px;
      border-radius: 50%;
      border: 1px solid var(--border-strong);
      background: var(--bg-surface);
      color: var(--text-main);
      box-shadow: 0 3px 10px rgba(0, 0, 0, 0.28);
      font-size: 13px;
      font-weight: 800;
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0.9;
    }

    /* SVG Map Styles */
    .map-toolbar {
      position: absolute;
      top: 10px;
      left: 10px;
      right: 10px;
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 8px;
      pointer-events: none;
      z-index: 10;
    }
    .map-tool-group {
      display: flex;
      flex-wrap: wrap;
      gap: 6px;
      pointer-events: auto;
    }
    .map-chip-btn {
      border: 1px solid var(--border-strong);
      background: var(--bg-surface);
      color: var(--text-main);
      border-radius: 10px;
      padding: 7px 10px;
      font-size: 12px;
      font-weight: 700;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.25);
    }
    .map-chip-btn.active {
      background: var(--accent);
      color: var(--accent-text);
      border-color: var(--accent);
    }

    .map-canvas-wrap {
      flex: 1 1 0%;
      width: 100%;
      height: 100%;
      touch-action: none;
      user-select: none;
      -webkit-user-select: none;
      cursor: grab;
      position: relative;
    }
    .map-canvas-wrap.pick-mode {
      cursor: crosshair;
    }

    #shanghaiSvg {
      width: 100%;
      height: 100%;
      display: block;
      background: var(--map-bg);
    }

    .map-legend {
      position: absolute;
      left: 10px;
      bottom: 12px;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 10px;
      padding: 6px 9px;
      font-size: 11px;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
      z-index: 9;
      pointer-events: none;
      opacity: 0.92;
    }
    .leg-dot {
      display: inline-block;
      width: 8px;
      height: 8px;
      border-radius: 50%;
      margin-right: 3px;
    }

    .map-preview-drawer {
      position: absolute;
      left: 10px;
      right: 10px;
      bottom: 10px;
      background: var(--bg-surface);
      border: 1px solid var(--border-strong);
      border-radius: 14px;
      padding: 12px;
      box-shadow: 0 8px 28px rgba(0, 0, 0, 0.45);
      z-index: 12;
      display: none;
    }
    .map-preview-drawer.show {
      display: block;
    }

    /* Red/Black Quick Tab */
    .rb-stat-grid {
      display: grid;
      grid-template-columns: repeat(2, 1fr);
      gap: 8px;
      margin-bottom: 10px;
    }
    @media (min-width: 520px) {
      .rb-stat-grid { grid-template-columns: repeat(4, 1fr); }
    }
    .rb-stat-card {
      text-decoration: none;
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 10px;
      text-align: center;
      color: var(--text-main);
    }
    .rb-stat-num {
      font-size: 22px;
      font-weight: 900;
      color: var(--accent);
    }
    .rb-stat-card.dark .rb-stat-num {
      color: #ef4444;
    }
    .rb-stat-lbl {
      font-size: 11.5px;
      color: var(--text-sub);
      font-weight: 600;
    }
    .pwa-banner-link {
      display: block;
      text-decoration: none;
      background: var(--accent-soft);
      color: var(--accent);
      border: 1px solid var(--accent);
      border-radius: 10px;
      padding: 9px 12px;
      font-size: 12.5px;
      font-weight: 700;
      text-align: center;
      margin-bottom: 14px;
    }
    .rb-section {
      margin-bottom: 22px;
    }
    .rb-sec-header h3 {
      margin: 0 0 3px;
      font-size: 16px;
    }
    .rb-sec-header p {
      margin: 0 0 10px;
      font-size: 12px;
      color: var(--text-muted);
    }
    .pwa-steps {
      display: grid;
      grid-template-columns: 1fr;
      gap: 10px;
    }
    @media (min-width: 640px) {
      .pwa-steps { grid-template-columns: repeat(3, 1fr); }
    }
    .pwa-step {
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      border-radius: 12px;
      padding: 12px;
      text-align: center;
    }
    .pwa-step-badge {
      display: inline-block;
      font-size: 10px;
      font-weight: 800;
      padding: 2px 8px;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      margin-bottom: 6px;
    }
    .pwa-step h4 {
      margin: 6px 0 4px;
      font-size: 14px;
    }
    .pwa-step p {
      margin: 0;
      font-size: 12px;
      color: var(--text-sub);
    }

    /* Order / Taxi Big-Print Modal */
    .modal-backdrop {
      position: fixed;
      inset: 0;
      background: rgba(0, 0, 0, 0.72);
      z-index: 100;
      display: none;
      align-items: flex-end;
      justify-content: center;
      padding: env(safe-area-inset-top, 12px) 0 0;
    }
    .modal-backdrop.open {
      display: flex;
    }
    @media (min-width: 640px) {
      .modal-backdrop {
        align-items: center;
        padding: 20px;
      }
    }

    .modal-sheet {
      width: 100%;
      max-width: 540px;
      max-height: 90dvh;
      background: var(--bg-surface);
      border-radius: 20px 20px 0 0;
      border: 1px solid var(--border-strong);
      display: flex;
      flex-direction: column;
      overflow: hidden;
    }
    @media (min-width: 640px) {
      .modal-sheet {
        border-radius: 20px;
      }
    }

    .modal-header {
      padding: 12px 16px;
      border-bottom: 1px solid var(--border-subtle);
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .modal-body {
      padding: 14px 16px calc(env(safe-area-inset-bottom, 12px) + 16px);
      overflow-y: auto;
      -webkit-overflow-scrolling: touch;
    }

    .taxi-card {
      background: var(--bg-elevated);
      border: 2px solid var(--border-strong);
      border-radius: 14px;
      padding: 14px;
      margin-bottom: 12px;
    }

    .taxi-label {
      font-size: 11px;
      font-weight: 700;
      color: var(--accent);
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }

    .taxi-shop-name {
      margin: 4px 0;
      font-size: 24px;
      font-weight: 900;
      line-height: 1.25;
    }

    .taxi-address {
      margin: 6px 0 10px;
      font-size: 18px;
      font-weight: 700;
      color: var(--text-main);
      line-height: 1.35;
    }

    .order-list-box {
      margin-bottom: 12px;
    }

    .order-item-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 8px 10px;
      border-radius: 10px;
      background: var(--bg-elevated);
      margin-bottom: 6px;
      gap: 8px;
    }

    .stepper {
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }
    .step-btn {
      width: 30px;
      height: 30px;
      border-radius: 8px;
      border: 1px solid var(--border-strong);
      background: var(--bg-surface);
      color: var(--text-main);
      font-size: 16px;
      font-weight: 800;
    }
    .step-qty {
      min-width: 20px;
      text-align: center;
      font-weight: 800;
    }

    .avoid-alert-box {
      border: 2px solid #ef4444;
      background: var(--tier-black-bg);
      color: var(--tier-black-fg);
      border-radius: 12px;
      padding: 10px 12px;
      margin-bottom: 12px;
      font-size: 13px;
      font-weight: 700;
    }

    .toast {
      position: fixed;
      left: 50%;
      bottom: calc(env(safe-area-inset-bottom, 0px) + 74px);
      transform: translateX(-50%);
      background: rgba(20, 21, 25, 0.94);
      color: #ffffff;
      border: 1px solid rgba(255, 255, 255, 0.18);
      padding: 8px 16px;
      border-radius: 999px;
      font-size: 13px;
      font-weight: 600;
      z-index: 200;
      opacity: 0;
      pointer-events: none;
      transition: opacity 0.2s ease;
      white-space: nowrap;
    }
    .toast.show {
      opacity: 1;
    }
  </style>
</head>
<body>
  <div class="app-shell">
    <!-- 1. Top Fixed Bar -->
    <header class="top-bar">
      <div class="brand-group">
        <img src="./apple-touch-icon.png" alt="上海美食雷达" class="brand-logo" width="32" height="32">
        <div class="brand-text">
          <h1 class="brand-title">上海美食雷达</h1>
          <div class="brand-sub">王师傅和小毛毛 · 164家探店红黑榜</div>
        </div>
      </div>
      <div class="top-actions">
        <button type="button" id="btnQuickGps" class="top-pill-btn" title="GPS实时定位">🎯 <span id="topLocLabel">定位</span></button>
        <button type="button" id="btnThemeToggle" class="top-pill-btn" title="切换深浅色/OLED/户外强光模式">🌙 OLED</button>
      </div>
    </header>

    <!-- 2. Middle Independent Scroll Container -->
    <main id="mainScroller">
      <!-- TAB 1: Nearby Explore -->
      <section id="panelNearby" class="tab-panel active">
        <div class="control-card">
          <div class="loc-header-row">
            <div class="loc-status" id="locStatusText">📍 当前基准：全城浏览（点选商圈或开启定位算步程）</div>
            <div class="loc-btns">
              <button type="button" class="btn-sm accent" id="btnLocateMe">📡 GPS定位</button>
              <button type="button" class="btn-sm" id="btnDemoJingan">⚡ 静安寺演示</button>
              <button type="button" class="btn-sm" id="btnClearLoc" style="display:none;">✖ 清除定位</button>
            </div>
          </div>

          <div class="loc-notice" id="locNoticeBar">
            <span id="locNoticeMsg">检测到当前不在上海范围内，已可一键切换「静安寺」体验周边探店</span>
            <button type="button" class="btn-sm accent" id="btnNoticeJingan">定位静安寺</button>
          </div>

          <!-- 35 Shanghai Landmarks Selector + Quick Chips -->
          <div class="landmark-picker-row">
            <select id="landmarkSelect" class="landmark-select" aria-label="选择上海35大热门商圈或地铁枢纽">
              <option value="">🚇 快速切换 35 大上海热门商圈 / 地铁站...</option>
            </select>
          </div>
          <div class="chip-strip" id="hotLandmarkChips" aria-label="热门商圈快捷点选"></div>

          <!-- Radius Chips -->
          <div class="chip-strip" id="radiusChips" aria-label="搜索半径">
            <button type="button" class="chip" data-radius="600">600m</button>
            <button type="button" class="chip" data-radius="1000">1km</button>
            <button type="button" class="chip" data-radius="1500">1.5km</button>
            <button type="button" class="chip" data-radius="3000">3km</button>
            <button type="button" class="chip active" data-radius="0">全城</button>
          </div>

          <!-- Search + Sort -->
          <div class="search-sort-row">
            <div class="search-box">
              <span class="search-ico">🔍</span>
              <input type="search" id="searchInput" class="search-input" placeholder="搜店名 / 推荐菜 / 路名 / 评价..." autocomplete="off">
              <button type="button" id="btnClearSearch" class="clear-search-btn" aria-label="清空搜索">✕</button>
            </div>
            <select id="sortSelect" class="sort-select" aria-label="排序方式">
              <option value="smart">智能排序</option>
              <option value="distance">距离最近</option>
              <option value="tier">红榜优先</option>
              <option value="price_asc">人均低→高</option>
              <option value="price_desc">人均高→低</option>
              <option value="newest">最新探店</option>
            </select>
          </div>

          <!-- Tier / Reservation / Series / Cuisine / District Capsule Filters -->
          <div class="chip-strip" id="tierChips" aria-label="评级筛选"></div>
          <div class="chip-strip" id="reservationChips" aria-label="预约要求筛选"></div>
          <div class="chip-strip" id="seriesChips" aria-label="系列筛选"></div>
          <div class="chip-strip" id="cuisineChips" aria-label="菜系筛选"></div>
          <div class="chip-strip" id="districtChips" aria-label="行政区筛选"></div>
        </div>

        <div class="result-summary-bar">
          <span id="resultCountText">正在加载餐厅...</span>
          <button type="button" class="btn-sm" id="btnResetFilters" style="padding:3px 8px;font-size:11px;">重置筛选</button>
        </div>

        <div id="nearbyList" class="card-stack"></div>
        <div id="loadMoreWrap" class="load-more-wrap">
          <button type="button" id="btnLoadMore" class="btn-sm" style="display:none;">加载更多餐厅</button>
          <div id="lazySentinel" style="height:8px;"></div>
        </div>
      </section>

      <!-- TAB 3: Pre-rendered Red/Black Quick Lookup + iOS Add-to-Home-Screen Guide -->
      <section id="panelRedBlack" class="tab-panel">
        __PRERENDERED_RED_BLACK__
      </section>

      <!-- TAB 4: Favorites Wishlist -->
      <section id="panelFavs" class="tab-panel">
        <div class="control-card">
          <div class="loc-header-row" style="margin-bottom:4px;">
            <div class="loc-status">⭐ 我的想吃收藏夹</div>
            <div class="loc-btns">
              <button type="button" class="btn-sm" id="btnClearFavs">清空收藏</button>
            </div>
          </div>
          <p style="margin:0;font-size:12px;color:var(--text-muted);">保存在本机浏览器中（离线可用）；开启定位或点选商圈后自动按离你最近排序。</p>
        </div>
        <div id="favsList" class="card-stack"></div>
      </section>
    </main>

    <!-- Pure Vector SVG Map Pane (Tab 2 on mobile, Right Column on Desktop >=900px) -->
    <section id="mapPane" aria-label="上海美食矢量触控地图">
      <div class="map-toolbar">
        <div class="map-tool-group">
          <button type="button" class="map-chip-btn" id="btnPickLocationMode">🎯 点地图设我的位置</button>
          <button type="button" class="map-chip-btn" id="btnMapCenterMe">📍 回到定位</button>
          <button type="button" class="map-chip-btn" id="btnMapReset">🗺️ 全城视野</button>
        </div>
        <div class="map-tool-group">
          <button type="button" class="map-chip-btn" id="btnZoomIn" aria-label="放大地图">＋</button>
          <button type="button" class="map-chip-btn" id="btnZoomOut" aria-label="缩小地图">－</button>
        </div>
      </div>

      <div class="map-canvas-wrap" id="mapCanvasWrap">
        <svg id="shanghaiSvg" viewBox="0 0 1000 1000" preserveAspectRatio="xMidYMid slice">
          <g id="mapViewport">
            <g id="layerBaseGeo"></g>
            <g id="layerLandmarks"></g>
            <g id="layerUserRadius"></g>
            <g id="layerPins"></g>
            <g id="layerUserPin"></g>
          </g>
        </svg>
      </div>

      <div class="map-legend" id="mapLegend">
        <span><i class="leg-dot" style="background:#ff4d2a;"></i>强烈推荐</span>
        <span><i class="leg-dot" style="background:#10b981;"></i>值得一试</span>
        <span><i class="leg-dot" style="background:#94a3b8;"></i>中规/低性价</span>
        <span><i class="leg-dot" style="background:#a855f7;"></i>严重踩雷</span>
        <span><i class="leg-dot" style="background:#10b981;border-radius:0;width:12px;height:3px;vertical-align:middle;"></i>2号线</span>
      </div>

      <div class="map-preview-drawer" id="mapPreviewDrawer"></div>
    </section>

    <!-- 3. Bottom Fixed Tab Bar INSIDE .app-shell -->
    <nav class="bottom-tabs" aria-label="底部主导航">
      <button type="button" class="tab-btn active" data-tab="nearby">
        <span class="tab-ico">📍</span>
        <span>周边探店</span>
      </button>
      <button type="button" class="tab-btn" data-tab="map">
        <span class="tab-ico">🗺️</span>
        <span>触控地图</span>
      </button>
      <button type="button" class="tab-btn" data-tab="redblack">
        <span class="tab-ico">⚡</span>
        <span>红黑速查</span>
      </button>
      <button type="button" class="tab-btn" data-tab="favs">
        <span class="tab-ico">⭐</span>
        <span>收藏夹</span>
        <span class="fav-count-badge" id="favCountBadge">0</span>
      </button>
    </nav>
  </div>

  <!-- Floating Quick Scroll Buttons -->
  <div class="floating-scroll-btns" id="floatingScrollBtns">
    <button type="button" class="float-btn" id="btnScrollTop" title="回到顶部" aria-label="回到顶部">↑</button>
    <button type="button" class="float-btn" id="btnPageDown" title="向下翻页" aria-label="向下翻页">↓</button>
  </div>

  <!-- Order / Taxi Big-Print Modal -->
  <div class="modal-backdrop" id="orderModal" role="dialog" aria-modal="true" aria-labelledby="modalShopTitle">
    <div class="modal-sheet">
      <div class="modal-header">
        <strong style="font-size:15px;">🗣️ 到店点单 / 打车大字卡</strong>
        <button type="button" class="btn-sm" id="btnCloseModal">关闭 ✕</button>
      </div>
      <div class="modal-body" id="orderModalBody"></div>
    </div>
  </div>

  <div class="toast" id="toastMsg" role="status" aria-live="polite"></div>

  <script>
    const RESTAURANTS = __RESTAURANTS_JSON__;
    const LANDMARKS = __LANDMARKS_JSON__;

    (() => {
      'use strict';

      // --- Constants & Lookups ---
      const REST_BY_ID = new Map(RESTAURANTS.map(r => [r.entry_id, r]));
      const LANDMARK_BY_ID = new Map(LANDMARKS.map(l => [l.id, l]));
      const HOT_LANDMARK_IDS = [
        'jingan_temple', 'peoples_square', 'xintiandi', 'bund', 'nanjing_west_road',
        'xujiahui', 'lujiazui', 'huaihai_middle_road', 'wukang_road', 'jufuchang',
        'zhongshan_park', 'dingxi_road', 'wujiaochang', 'qianshuiwan_qiantan', 'hongqiao_hub'
      ];
      const TIER_RANK = { '强烈推荐': 5, '值得一试': 4, '中规中矩': 3, '性价比低': 2, '严重踩雷': 1 };
      const TIER_META = {
        '强烈推荐': { cls: 'tier-top', icon: '🏆', color: '#ff4d2a' },
        '值得一试': { cls: 'tier-good', icon: '👍', color: '#10b981' },
        '中规中矩': { cls: 'tier-mid', icon: '😐', color: '#94a3b8' },
        '性价比低': { cls: 'tier-low', icon: '💸', color: '#f59e0b' },
        '严重踩雷': { cls: 'tier-black', icon: '💣', color: '#a855f7' }
      };

      const PAGE_SIZE = 30;
      const FAV_STORAGE_KEY = 'shanghai_food_favs_v1';
      const THEME_STORAGE_KEY = 'shanghai_food_theme_v1';

      // --- App State ---
      const state = {
        activeTab: 'nearby',
        userLoc: null, // { lat, lng, label, source }
        radiusMeters: 0, // 0 = all city
        query: '',
        sortBy: 'smart',
        tierFilter: 'ALL',
        reservationFilter: 'ALL',
        seriesFilter: 'ALL',
        cuisineFilter: 'ALL',
        districtFilter: 'ALL',
        visibleCount: PAGE_SIZE,
        filteredList: [],
        selectedEid: null,
        favIds: new Set(),
        pickLocationMode: false,
        mapTransform: { x: 0, y: 0, scale: 1.35 },
        modalOrderQty: {},
        themeMode: 'auto' // 'auto' | 'light' | 'oled' | 'sunlight'
      };

      // Load Favorites
      try {
        const rawFav = localStorage.getItem(FAV_STORAGE_KEY);
        if (rawFav) {
          JSON.parse(rawFav).forEach(id => { if (REST_BY_ID.has(id)) state.favIds.add(id); });
        }
      } catch (_) {}

      // --- Theme Management ---
      const metaThemeEl = document.getElementById('metaThemeColor');
      const btnThemeToggle = document.getElementById('btnThemeToggle');
      const darkMql = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : { matches: true };

      function applyTheme(mode) {
        state.themeMode = mode;
        let effective = mode;
        if (mode === 'auto') {
          effective = darkMql.matches ? 'oled' : 'light';
        }
        document.documentElement.setAttribute('data-theme', effective);
        const colorMap = { light: '#f5f5f7', oled: '#000000', sunlight: '#ffffff' };
        if (metaThemeEl) metaThemeEl.setAttribute('content', colorMap[effective] || '#000000');

        const labelMap = {
          auto: effective === 'oled' ? '🌗 自动(黑)' : '🌗 自动(浅)',
          light: '☀️ 浅色',
          oled: '🌙 OLED黑',
          sunlight: '🔆 强光高对比'
        };
        btnThemeToggle.textContent = labelMap[mode] || '🌙 OLED';
      }

      try {
        const savedTheme = localStorage.getItem(THEME_STORAGE_KEY) || 'auto';
        applyTheme(savedTheme);
      } catch (_) {
        applyTheme('auto');
      }

      if (darkMql.addEventListener) {
        darkMql.addEventListener('change', () => {
          if (state.themeMode === 'auto') applyTheme('auto');
        });
      }

      btnThemeToggle.addEventListener('click', () => {
        const order = ['auto', 'light', 'oled', 'sunlight'];
        const next = order[(order.indexOf(state.themeMode) + 1) % order.length];
        applyTheme(next);
        try { localStorage.setItem(THEME_STORAGE_KEY, next); } catch (_) {}
        showToast('主题已切换：' + btnThemeToggle.textContent);
      });

      // --- Geo Math (Haversine + Bearing + Projection) ---
      const DEG2RAD = Math.PI / 180;
      function haversineMeters(lat1, lng1, lat2, lng2) {
        const dLat = (lat2 - lat1) * DEG2RAD;
        const dLng = (lng2 - lng1) * DEG2RAD;
        const a = Math.sin(dLat / 2) ** 2 +
          Math.cos(lat1 * DEG2RAD) * Math.cos(lat2 * DEG2RAD) * Math.sin(dLng / 2) ** 2;
        return 6371000 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
      }

      function bearingLabel(lat1, lng1, lat2, lng2) {
        const dLng = (lng2 - lng1) * DEG2RAD;
        const y = Math.sin(dLng) * Math.cos(lat2 * DEG2RAD);
        const x = Math.cos(lat1 * DEG2RAD) * Math.sin(lat2 * DEG2RAD) -
          Math.sin(lat1 * DEG2RAD) * Math.cos(lat2 * DEG2RAD) * Math.cos(dLng);
        const brng = ((Math.atan2(y, x) * 180 / Math.PI) + 360) % 360;
        const dirs = ['↑北', '↗东北', '→东', '↘东南', '↓南', '↙西南', '←西', '↖西北'];
        return dirs[Math.round(brng / 45) % 8];
      }

      function formatWalkInfo(meters, dir) {
        const mins = Math.max(1, Math.round(meters / 64));
        const distStr = meters < 1000 ? `${Math.round(meters)}m` : `${(meters / 1000).toFixed(1)}km`;
        return `🚶 ${mins}分 · ${distStr} ${dir}`;
      }

      // Projection centered at People's Square / Jing'an (31.225, 121.465)
      const PROJ_LAT0 = 31.225;
      const PROJ_LNG0 = 121.465;
      const PROJ_COS = Math.cos(PROJ_LAT0 * DEG2RAD);
      const PROJ_SCALE = 3600;
      const METERS_TO_SVG = PROJ_SCALE / 111320;

      function project(lat, lng) {
        return {
          x: 500 + (lng - PROJ_LNG0) * PROJ_COS * PROJ_SCALE,
          y: 500 - (lat - PROJ_LAT0) * PROJ_SCALE
        };
      }

      function unproject(x, y) {
        return {
          lng: +(PROJ_LNG0 + (x - 500) / (PROJ_COS * PROJ_SCALE)).toFixed(6),
          lat: +(PROJ_LAT0 - (y - 500) / PROJ_SCALE).toFixed(6)
        };
      }

      function escapeHtml(s) {
        return String(s || '')
          .replace(/&/g, '&amp;')
          .replace(/</g, '&lt;')
          .replace(/>/g, '&gt;')
          .replace(/"/g, '&quot;');
      }

      // --- Toast & Clipboard ---
      let toastTimer = null;
      const toastEl = document.getElementById('toastMsg');
      function showToast(msg) {
        toastEl.textContent = msg;
        toastEl.classList.add('show');
        clearTimeout(toastTimer);
        toastTimer = setTimeout(() => toastEl.classList.remove('show'), 2200);
      }

      function copyTextCompat(text, okMsg) {
        if (navigator.clipboard && window.isSecureContext) {
          navigator.clipboard.writeText(text).then(() => {
            showToast(okMsg || '已复制到剪贴板');
          }).catch(() => fallbackExecCopy(text, okMsg));
        } else {
          fallbackExecCopy(text, okMsg);
        }
      }

      function fallbackExecCopy(text, okMsg) {
        const ta = document.createElement('textarea');
        ta.value = text;
        ta.setAttribute('readonly', '');
        ta.style.position = 'fixed';
        ta.style.top = '-9999px';
        ta.style.fontSize = '16px';
        document.body.appendChild(ta);
        ta.focus();
        ta.select();
        ta.setSelectionRange(0, text.length);
        let ok = false;
        try { ok = document.execCommand('copy'); } catch (_) {}
        document.body.removeChild(ta);
        showToast(ok ? (okMsg || '已复制到剪贴板') : '复制失败，请长按文字复制');
      }

      // --- Populate Filter Chips & Landmark Controls ---
      const landmarkSelect = document.getElementById('landmarkSelect');
      LANDMARKS.forEach(lm => {
        const opt = document.createElement('option');
        opt.value = lm.id;
        opt.textContent = `${lm.district} · ${lm.name} (${lm.type})`;
        landmarkSelect.appendChild(opt);
      });

      const hotLandmarkChips = document.getElementById('hotLandmarkChips');
      HOT_LANDMARK_IDS.forEach(id => {
        const lm = LANDMARK_BY_ID.get(id);
        if (!lm) return;
        const btn = document.createElement('button');
        btn.type = 'button';
        btn.className = 'chip';
        btn.dataset.lmId = lm.id;
        btn.textContent = lm.short_name || lm.name;
        btn.addEventListener('click', () => setLocationFromLandmark(lm.id, true));
        hotLandmarkChips.appendChild(btn);
      });

      landmarkSelect.addEventListener('change', () => {
        if (landmarkSelect.value) {
          setLocationFromLandmark(landmarkSelect.value, true);
        }
      });

      function buildChipRow(containerId, items, stateKey) {
        const wrap = document.getElementById(containerId);
        wrap.innerHTML = '';
        items.forEach(([val, label]) => {
          const btn = document.createElement('button');
          btn.type = 'button';
          btn.className = 'chip' + (state[stateKey] === val ? ' active' : '');
          btn.dataset.val = val;
          btn.textContent = label;
          btn.addEventListener('click', () => {
            state[stateKey] = val;
            Array.from(wrap.children).forEach(c => c.classList.toggle('active', c.dataset.val === val));
            state.visibleCount = PAGE_SIZE;
            recomputeAndRender();
          });
          wrap.appendChild(btn);
        });
      }

      buildChipRow('tierChips', [
        ['ALL', '全部评级'],
        ['RED_ALL', '🔥 红榜合集'],
        ['强烈推荐', '🏆 强烈推荐'],
        ['值得一试', '👍 值得一试'],
        ['中规中矩', '😐 中规中矩'],
        ['性价比低', '💸 性价比低'],
        ['严重踩雷', '💣 严重踩雷']
      ], 'tierFilter');

      buildChipRow('reservationChips', [
        ['ALL', '全部预约状态'],
        ['REQUIRED', '📅 需预约'],
        ['WALKIN', '🚶 免预约随到随吃']
      ], 'reservationFilter');

      buildChipRow('seriesChips', [
        ['ALL', '全部系列'],
        ['怎么这么值', '💰 怎么这么值'],
        ['凭啥这么贵', '💎 凭啥这么贵'],
        ['还愿挑战', '🎯 还愿挑战'],
        ['就得这么晚', '🌙 就得这么晚'],
        ['常规探店', '🍽️ 常规探店']
      ], 'seriesFilter');

      buildChipRow('cuisineChips', [
        ['ALL', '全部菜系'],
        ['本帮江浙', '本帮江浙'],
        ['粤菜顺德', '粤菜顺德'],
        ['火锅涮肉', '火锅涮肉'],
        ['川湘江湖', '川湘江湖'],
        ['日韩料理', '日韩料理'],
        ['西餐牛排', '西餐牛排'],
        ['烧烤夜宵', '烧烤夜宵'],
        ['小吃面点', '小吃面点'],
        ['异域自助', '异域自助']
      ], 'cuisineFilter');

      buildChipRow('districtChips', [
        ['ALL', '全部行政区'],
        ['黄浦区', '黄浦区'],
        ['静安区', '静安区'],
        ['浦东新区', '浦东新区'],
        ['徐汇区', '徐汇区'],
        ['长宁区', '长宁区'],
        ['闵行区', '闵行区'],
        ['虹口区', '虹口区'],
        ['普陀区', '普陀区'],
        ['松江区', '松江区']
      ], 'districtFilter');

      // Radius chips
      const radiusChipsWrap = document.getElementById('radiusChips');
      radiusChipsWrap.addEventListener('click', (e) => {
        const btn = e.target.closest('button[data-radius]');
        if (!btn) return;
        const r = Number(btn.dataset.radius);
        if (r > 0 && !state.userLoc) {
          setLocationFromLandmark('jingan_temple', false);
          showToast('已默认定位至「静安寺」以按半径筛选');
        }
        setRadius(r);
        recomputeAndRender();
      });

      function setRadius(r) {
        state.radiusMeters = r;
        Array.from(radiusChipsWrap.children).forEach(c => {
          c.classList.toggle('active', Number(c.dataset.radius) === r);
        });
      }

      // --- Location Logic ---
      const locStatusText = document.getElementById('locStatusText');
      const topLocLabel = document.getElementById('topLocLabel');
      const btnQuickGps = document.getElementById('btnQuickGps');
      const btnClearLoc = document.getElementById('btnClearLoc');
      const locNoticeBar = document.getElementById('locNoticeBar');
      const locNoticeMsg = document.getElementById('locNoticeMsg');

      function applyUserLocation(lat, lng, label, source, autoRadius1500) {
        state.userLoc = { lat, lng, label, source };
        locStatusText.textContent = `📍 当前定位：${label} (${lat.toFixed(4)}, ${lng.toFixed(4)})`;
        topLocLabel.textContent = label.length > 5 ? label.slice(0, 5) : label;
        btnQuickGps.classList.add('gps-active');
        btnClearLoc.style.display = 'inline-block';

        Array.from(hotLandmarkChips.children).forEach(c => {
          const lm = LANDMARK_BY_ID.get(c.dataset.lmId);
          c.classList.toggle('active', Boolean(lm && lm.name === label));
        });

        if (autoRadius1500 && state.radiusMeters === 0) {
          setRadius(1500);
        }
        state.visibleCount = PAGE_SIZE;
        recomputeAndRender();
        centerMapOn(lat, lng, 2.3);
      }

      function setLocationFromLandmark(lmId, autoRadius) {
        const lm = LANDMARK_BY_ID.get(lmId);
        if (!lm) return;
        locNoticeBar.classList.remove('show');
        landmarkSelect.value = lm.id;
        applyUserLocation(lm.lat, lm.lng, lm.name, 'landmark', autoRadius);
      }

      function clearUserLocation() {
        state.userLoc = null;
        landmarkSelect.value = '';
        locStatusText.textContent = '📍 当前基准：全城浏览（点选商圈或开启定位算步程）';
        topLocLabel.textContent = '定位';
        btnQuickGps.classList.remove('gps-active');
        btnClearLoc.style.display = 'none';
        Array.from(hotLandmarkChips.children).forEach(c => c.classList.remove('active'));
        setRadius(0);
        recomputeAndRender();
      }

      function triggerBrowserGps() {
        if (!navigator.geolocation) {
          locNoticeMsg.textContent = '当前浏览器不支持 GPS 定位，可一键使用「静安寺」演示定位';
          locNoticeBar.classList.add('show');
          return;
        }
        showToast('正在请求 GPS 实时定位...');
        navigator.geolocation.getCurrentPosition(
          (pos) => {
            const { latitude, longitude } = pos.coords;
            const inShanghai = latitude >= 30.65 && latitude <= 31.90 && longitude >= 120.85 && longitude <= 122.25;
            if (!inShanghai) {
              locNoticeMsg.textContent = `检测到您当前位于上海以外 (${latitude.toFixed(2)}, ${longitude.toFixed(2)})，已为您切换「静安寺」演示定位`;
              locNoticeBar.classList.add('show');
              setLocationFromLandmark('jingan_temple', true);
            } else {
              locNoticeBar.classList.remove('show');
              applyUserLocation(latitude, longitude, '我的实时位置', 'gps', true);
              showToast('GPS 定位成功！');
            }
          },
          (err) => {
            locNoticeMsg.textContent = '未开启定位权限或信号受限，推荐点选「静安寺」或35大商圈查周边';
            locNoticeBar.classList.add('show');
          },
          { enableHighAccuracy: true, timeout: 7000, maximumAge: 60000 }
        );
      }

      document.getElementById('btnLocateMe').addEventListener('click', triggerBrowserGps);
      document.getElementById('btnQuickGps').addEventListener('click', () => {
        if (state.activeTab !== 'nearby' && window.innerWidth < 900) switchTab('nearby');
        triggerBrowserGps();
      });
      document.getElementById('btnDemoJingan').addEventListener('click', () => setLocationFromLandmark('jingan_temple', true));
      document.getElementById('btnNoticeJingan').addEventListener('click', () => setLocationFromLandmark('jingan_temple', true));
      btnClearLoc.addEventListener('click', clearUserLocation);

      // Search & Sort listeners
      const searchInput = document.getElementById('searchInput');
      const btnClearSearch = document.getElementById('btnClearSearch');
      const sortSelect = document.getElementById('sortSelect');

      searchInput.addEventListener('input', () => {
        state.query = searchInput.value.trim().toLowerCase();
        btnClearSearch.style.display = state.query ? 'block' : 'none';
        state.visibleCount = PAGE_SIZE;
        recomputeAndRender();
      });

      btnClearSearch.addEventListener('click', () => {
        searchInput.value = '';
        state.query = '';
        btnClearSearch.style.display = 'none';
        state.visibleCount = PAGE_SIZE;
        recomputeAndRender();
      });

      sortSelect.addEventListener('change', () => {
        state.sortBy = sortSelect.value;
        state.visibleCount = PAGE_SIZE;
        recomputeAndRender();
      });

      document.getElementById('btnResetFilters').addEventListener('click', () => {
        searchInput.value = '';
        state.query = '';
        btnClearSearch.style.display = 'none';
        state.sortBy = 'smart';
        sortSelect.value = 'smart';
        state.tierFilter = 'ALL';
        state.reservationFilter = 'ALL';
        state.seriesFilter = 'ALL';
        state.cuisineFilter = 'ALL';
        state.districtFilter = 'ALL';
        setRadius(state.userLoc ? 1500 : 0);
        ['tierChips', 'reservationChips', 'seriesChips', 'cuisineChips', 'districtChips'].forEach(id => {
          Array.from(document.getElementById(id).children).forEach((c, idx) => c.classList.toggle('active', idx === 0));
        });
        state.visibleCount = PAGE_SIZE;
        recomputeAndRender();
      });

      // --- Card HTML Renderer ---
      function renderCardHtml(r) {
        const tm = TIER_META[r.verdict_tier] || TIER_META['中规中矩'];
        const isFav = state.favIds.has(r.entry_id);
        const isBlack = r.verdict_tier === '严重踩雷';
        const isRed = r.verdict_tier === '强烈推荐';
        const isSelected = state.selectedEid === r.entry_id;

        const walkHtml = r._distMeters != null
          ? `<span class="walk-badge">${escapeHtml(r._walkText)}</span>`
          : '';
        const priceStr = r.price_per_person ? `¥${r.price_per_person}/人` : '时价';
        const branchHtml = r.branch_name ? ` <span class="card-branch">(${escapeHtml(r.branch_name)})</span>` : '';
        const resBadgeHtml = r.reservation_required ? `<span class="res-badge" title="${escapeHtml(r.reservation_note || '建议提前预约')}">📅 需预约</span>` : '';

        const recPills = (r.recommended_dishes || []).slice(0, 4)
          .map(d => `<span class="dish-tag good">👍 ${escapeHtml(d)}</span>`).join('');
        const avoidPills = (r.avoid_dishes || []).slice(0, 3)
          .map(d => `<span class="dish-tag bad">⚠️ 避雷：${escapeHtml(d)}</span>`).join('');
        const dishBlock = (recPills || avoidPills) ? `<div class="dish-row">${recPills}${avoidPills}</div>` : '';

        const qShop = encodeURIComponent(`${r.name} ${r.address || ''}`.trim());
        const appleUrl = `https://maps.apple.com/?q=${qShop}&ll=${r.lat},${r.lng}`;
        const amapUrl = `https://uri.amap.com/search?keyword=${encodeURIComponent(r.name)}&center=${r.lng},${r.lat}&city=310000&src=shanghai_food_radar`;

        return `<article class="rest-card ${isBlack ? 'is-black-card' : (isRed ? 'is-red-card' : '')} ${isSelected ? 'selected-card' : ''}" data-eid="${escapeHtml(r.entry_id)}">
          <div class="card-head">
            <div class="card-title-wrap">
              <h3 class="card-title">${escapeHtml(r.name)}${branchHtml}</h3>
              <div class="card-meta">
                ${walkHtml}
                <span class="tier-badge ${tm.cls}">${tm.icon} ${escapeHtml(r.verdict_tier)}</span>
                ${resBadgeHtml}
                <span class="price-pill">${priceStr}</span>
                <span class="meta-dot">${escapeHtml(r.district)} · ${escapeHtml(r.commercial_area)}</span>
                <span class="meta-dot">${escapeHtml(r.cuisine_category)}</span>
                <span class="series-pill">${escapeHtml(r.series_name)}</span>
              </div>
            </div>
            <button type="button" class="fav-btn ${isFav ? 'is-fav' : ''}" data-fav-toggle="${escapeHtml(r.entry_id)}" aria-label="收藏 ${escapeHtml(r.name)}">${isFav ? '★' : '☆'}</button>
          </div>
          <div class="card-address">📍 ${escapeHtml(r.address)}</div>
          <p class="card-summary">${escapeHtml(r.overall_review_summary)}</p>
          ${dishBlock}
          <div class="card-actions">
            <button type="button" class="act-btn primary" data-open-modal="${escapeHtml(r.entry_id)}">🗣️ 点单/打车卡</button>
            <button type="button" class="act-btn" data-focus-map="${escapeHtml(r.entry_id)}">🗺️ 地图定位</button>
            <a class="act-btn" href="${appleUrl}" target="_blank" rel="noopener">🍎 Apple地图</a>
            <a class="act-btn" href="${amapUrl}" target="_blank" rel="noopener">🧭 高德</a>
            <a class="act-btn" href="${escapeHtml(r.video_url)}" target="_blank" rel="noopener">📺 B站</a>
            <a class="act-btn" href="${escapeHtml(r.dianping_url)}" target="_blank" rel="noopener">🍜 点评</a>
          </div>
        </article>`;
      }

      // --- Filtering, Sorting & Rendering ---
      const nearbyListEl = document.getElementById('nearbyList');
      const resultCountText = document.getElementById('resultCountText');
      const btnLoadMore = document.getElementById('btnLoadMore');

      function recomputeAndRender() {
        const u = state.userLoc;
        const q = state.query;

        const list = [];
        for (const r of RESTAURANTS) {
          if ( u ) {
            const d = haversineMeters(u.lat, u.lng, r.lat, r.lng);
            const dir = bearingLabel(u.lat, u.lng, r.lat, r.lng);
            r._distMeters = d;
            r._walkText = formatWalkInfo(d, dir);
            if (state.radiusMeters > 0 && d > state.radiusMeters) continue;
          } else {
            r._distMeters = null;
            r._walkText = '';
          }

          if (state.tierFilter === 'RED_ALL') {
            if (r.verdict_tier !== '强烈推荐' && r.verdict_tier !== '值得一试') continue;
          } else if (state.tierFilter !== 'ALL' && r.verdict_tier !== state.tierFilter) {
            continue;
          }

          if (state.reservationFilter === 'REQUIRED' && !r.reservation_required) continue;
          if (state.reservationFilter === 'WALKIN' && r.reservation_required) continue;
          if (state.seriesFilter !== 'ALL' && r.series_name !== state.seriesFilter) continue;
          if (state.cuisineFilter !== 'ALL' && r.cuisine_group !== state.cuisineFilter) continue;
          if (state.districtFilter !== 'ALL' && r.district !== state.districtFilter) continue;

          if (q) {
            if (!r._searchBlob.includes(q)) continue;
          }

          list.push(r);
        }

        const sortMode = state.sortBy;
        list.sort((a, b) => {
          if (sortMode === 'distance' || (sortMode === 'smart' && u)) {
            const da = a._distMeters ?? 1e9;
            const db = b._distMeters ?? 1e9;
            if (Math.abs(da - db) > 1) return da - db;
          }
          if (sortMode === 'tier' || (sortMode === 'smart' && !u)) {
            const ta = TIER_RANK[a.verdict_tier] || 0;
            const tb = TIER_RANK[b.verdict_tier] || 0;
            if (ta !== tb) return tb - ta;
          }
          if (sortMode === 'price_asc') {
            return (a.price_per_person || 99999) - (b.price_per_person || 99999);
          }
          if (sortMode === 'price_desc') {
            return (b.price_per_person || 0) - (a.price_per_person || 0);
          }
          return (b.pubdate_str || '').localeCompare(a.pubdate_str || '');
        });

        state.filteredList = list;

        const radLabel = state.radiusMeters > 0
          ? (state.radiusMeters >= 1000 ? `${state.radiusMeters / 1000}km内` : `${state.radiusMeters}m内`)
          : '全上海';
        resultCountText.textContent = u
          ? `${u.label} · ${radLabel} 共找到 ${list.length} 家餐厅`
          : `全上海共筛出 ${list.length} 家餐厅`;

        renderNearbySlice();
        renderFavsPanel();
        renderMapPins();
      }

      function renderNearbySlice() {
        const slice = state.filteredList.slice(0, state.visibleCount);
        if (slice.length === 0) {
          nearbyListEl.innerHTML = `<div class="control-card" style="text-align:center;padding:28px 16px;">
            <p style="margin:0 0 10px;font-size:15px;font-weight:700;">当前半径或筛选条件下暂无餐厅</p>
            <p style="margin:0 0 14px;font-size:12px;color:var(--text-muted);">试试扩大搜索半径到 3km / 全城，或重置筛选条件</p>
            <button type="button" class="btn-sm accent" id="btnExpandAllCity">切换全城范围查看</button>
          </div>`;
          const expBtn = document.getElementById('btnExpandAllCity');
          if (expBtn) expBtn.addEventListener('click', () => { setRadius(0); recomputeAndRender(); });
          btnLoadMore.style.display = 'none';
          return;
        }

        nearbyListEl.innerHTML = slice.map(renderCardHtml).join('');
        const remaining = state.filteredList.length - slice.length;
        if (remaining > 0) {
          btnLoadMore.style.display = 'inline-block';
          btnLoadMore.textContent = `继续加载剩余 ${remaining} 家餐厅`;
        } else {
          btnLoadMore.style.display = 'none';
        }
      }

      btnLoadMore.addEventListener('click', () => {
        state.visibleCount += PAGE_SIZE;
        renderNearbySlice();
      });

      // IntersectionObserver for auto lazy-loading
      if ('IntersectionObserver' in window) {
        const io = new IntersectionObserver((entries) => {
          if (entries[0].isIntersecting && state.activeTab === 'nearby' && state.visibleCount < state.filteredList.length) {
            state.visibleCount += PAGE_SIZE;
            renderNearbySlice();
          }
        }, { root: document.getElementById('mainScroller'), rootMargin: '220px' });
        io.observe(document.getElementById('lazySentinel'));
      }

      // --- Favorites Panel ---
      const favsListEl = document.getElementById('favsList');
      const favCountBadge = document.getElementById('favCountBadge');

      function saveFavs() {
        try {
          localStorage.setItem(FAV_STORAGE_KEY, JSON.stringify(Array.from(state.favIds)));
        } catch (_) {}
        favCountBadge.textContent = String(state.favIds.size);
        favCountBadge.classList.toggle('has-items', state.favIds.size > 0);
        // Sync prerendered heart/star buttons in Red/Black tab too
        document.querySelectorAll('[data-fav-toggle]').forEach(btn => {
          const id = btn.getAttribute('data-fav-toggle');
          const on = state.favIds.has(id);
          btn.classList.toggle('is-fav', on);
          btn.textContent = on ? '★' : '☆';
        });
      }

      function renderFavsPanel() {
        saveFavs();
        const items = Array.from(state.favIds).map(id => REST_BY_ID.get(id)).filter(Boolean);
        if (state.userLoc) {
          items.forEach(r => {
            const d = haversineMeters(state.userLoc.lat, state.userLoc.lng, r.lat, r.lng);
            const dir = bearingLabel(state.userLoc.lat, state.userLoc.lng, r.lat, r.lng);
            r._distMeters = d;
            r._walkText = formatWalkInfo(d, dir);
          });
          items.sort((a, b) => (a._distMeters ?? 1e9) - (b._distMeters ?? 1e9));
        }
        if (items.length === 0) {
          favsListEl.innerHTML = `<div class="control-card" style="text-align:center;padding:30px 16px;">
            <p style="margin:0 0 6px;font-size:15px;font-weight:700;">还没有收藏任何餐厅</p>
            <p style="margin:0;font-size:12px;color:var(--text-muted);">点击任意餐厅卡片右上角的 ☆ 即可加入想吃清单</p>
          </div>`;
          return;
        }
        favsListEl.innerHTML = items.map(renderCardHtml).join('');
      }

      document.getElementById('btnClearFavs').addEventListener('click', () => {
        if (state.favIds.size === 0) return;
        state.favIds.clear();
        renderFavsPanel();
        renderNearbySlice();
        showToast('已清空收藏夹');
      });

      // --- Pure Vector SVG Shanghai Map ---
      const shanghaiSvg = document.getElementById('shanghaiSvg');
      const mapViewport = document.getElementById('mapViewport');
      const layerBaseGeo = document.getElementById('layerBaseGeo');
      const layerLandmarks = document.getElementById('layerLandmarks');
      const layerUserRadius = document.getElementById('layerUserRadius');
      const layerPins = document.getElementById('layerPins');
      const layerUserPin = document.getElementById('layerUserPin');
      const mapPreviewDrawer = document.getElementById('mapPreviewDrawer');
      const mapCanvasWrap = document.getElementById('mapCanvasWrap');
      const btnPickLocationMode = document.getElementById('btnPickLocationMode');

      function ptsToPath(coords) {
        return coords.map(([lat, lng], idx) => {
          const p = project(lat, lng);
          return `${idx === 0 ? 'M' : 'L'}${p.x.toFixed(1)},${p.y.toFixed(1)}`;
        }).join(' ');
      }

      function initBaseVectorMap() {
        // Huangpu River realistic polyline (Minhang -> Xuhui Riverside -> Lupu -> Nanpu -> Bund/Lujiazui -> Yangpu -> Wusong)
        const huangpu = [
          [31.115, 121.452], [31.148, 121.460], [31.175, 121.463], [31.191, 121.482],
          [31.206, 121.499], [31.224, 121.498], [31.239, 121.494], [31.247, 121.503],
          [31.255, 121.535], [31.278, 121.558], [31.320, 121.552], [31.360, 121.515]
        ];
        // Suzhou Creek polyline
        const suzhou = [
          [31.216, 121.345], [31.221, 121.392], [31.224, 121.414], [31.230, 121.428],
          [31.244, 121.442], [31.243, 121.464], [31.245, 121.480], [31.244, 121.493]
        ];
        // Inner Ring loop
        const innerRing = [
          [31.192, 121.436], [31.218, 121.416], [31.246, 121.429], [31.268, 121.464],
          [31.276, 121.496], [31.255, 121.535], [31.212, 121.558], [31.204, 121.502],
          [31.198, 121.472], [31.192, 121.436]
        ];
        // Metro Line 2
        const metro2 = [
          [31.1942, 121.3186], [31.2182, 121.3595], [31.2163, 121.3740], [31.2111, 121.4040],
          [31.2185, 121.4165], [31.2205, 121.4307], [31.2238, 121.4459], [31.2297, 121.4598],
          [31.2328, 121.4754], [31.2381, 121.4846], [31.2389, 121.5015], [31.2333, 121.5155],
          [31.2286, 121.5221], [31.2195, 121.5443], [31.2033, 121.5578], [31.2054, 121.5924]
        ];

        const pBund = project(31.233, 121.496);
        const pSuzhou = project(31.247, 121.454);

        layerBaseGeo.innerHTML = `
          <path d="${ptsToPath(innerRing)}" fill="none" stroke="var(--map-ring)" stroke-width="5" stroke-dasharray="9 7" stroke-linejoin="round"/>
          <path d="${ptsToPath(huangpu)}" fill="none" stroke="var(--map-water-stroke)" stroke-width="22" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="${ptsToPath(huangpu)}" fill="none" stroke="var(--map-water)" stroke-width="18" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="${ptsToPath(suzhou)}" fill="none" stroke="var(--map-water)" stroke-width="6.5" stroke-linecap="round" stroke-linejoin="round"/>
          <path d="${ptsToPath(metro2)}" fill="none" stroke="var(--map-metro)" stroke-width="3.2" stroke-dasharray="5 3" opacity="0.82"/>
          <text x="${(pBund.x + 14).toFixed(1)}" y="${pBund.y.toFixed(1)}" font-size="11" font-weight="700" fill="var(--text-muted)" opacity="0.75">黄浦江</text>
          <text x="${pSuzhou.x.toFixed(1)}" y="${(pSuzhou.y - 8).toFixed(1)}" font-size="9.5" font-weight="700" fill="var(--text-muted)" opacity="0.75">苏州河</text>
        `;

        // Landmarks labels
        layerLandmarks.innerHTML = LANDMARKS.map(lm => {
          const p = project(lm.lat, lm.lng);
          return `<g class="lm-node" data-lm="${escapeHtml(lm.id)}" style="cursor:pointer;">
            <rect x="${(p.x - 24).toFixed(1)}" y="${(p.y - 19).toFixed(1)}" width="48" height="14" rx="4" fill="var(--bg-surface)" opacity="0.78"/>
            <text x="${p.x.toFixed(1)}" y="${(p.y - 9).toFixed(1)}" text-anchor="middle" font-size="9.2" font-weight="700" fill="var(--text-sub)">${escapeHtml(lm.short_name || lm.name)}</text>
          </g>`;
        }).join('');
      }

      function renderMapPins() {
        // User pin + radius circle
        if (state.userLoc) {
          const up = project(state.userLoc.lat, state.userLoc.lng);
          const rSvg = (state.radiusMeters > 0 ? state.radiusMeters : 1500) * METERS_TO_SVG;
          layerUserRadius.innerHTML = `<circle cx="${up.x.toFixed(1)}" cy="${up.y.toFixed(1)}" r="${rSvg.toFixed(1)}"
            fill="rgba(59, 130, 246, 0.10)" stroke="#3b82f6" stroke-width="1.6" stroke-dasharray="5 4"/>`;
          layerUserPin.innerHTML = `
            <circle cx="${up.x.toFixed(1)}" cy="${up.y.toFixed(1)}" r="12" fill="rgba(59, 130, 246, 0.28)"/>
            <circle cx="${up.x.toFixed(1)}" cy="${up.y.toFixed(1)}" r="6" fill="#2563eb" stroke="#ffffff" stroke-width="2.2"/>
          `;
        } else {
          layerUserRadius.innerHTML = '';
          layerUserPin.innerHTML = '';
        }

        // Group identical coordinates so same-mall restaurants fan out cleanly
        const coordGroups = new Map();
        for (const r of state.filteredList) {
          const key = `${r.lat.toFixed(4)},${r.lng.toFixed(4)}`;
          if (!coordGroups.has(key)) coordGroups.set(key, []);
          coordGroups.get(key).push(r.entry_id);
        }

        // Restaurant pins (draw selected on top)
        const list = state.filteredList.slice();
        list.sort((a, b) => {
          if (a.entry_id === state.selectedEid) return 1;
          if (b.entry_id === state.selectedEid) return -1;
          return (TIER_RANK[a.verdict_tier] || 0) - (TIER_RANK[b.verdict_tier] || 0);
        });

        const invScale = 1 / Math.max(0.6, Math.min(4.5, state.mapTransform.scale));
        layerPins.innerHTML = list.map(r => {
          const baseP = project(r.lat, r.lng);
          const key = `${r.lat.toFixed(4)},${r.lng.toFixed(4)}`;
          const siblings = coordGroups.get(key) || [r.entry_id];
          let px = baseP.x;
          let py = baseP.y;
          if (siblings.length > 1) {
            const idx = siblings.indexOf(r.entry_id);
            const ang = (2 * Math.PI * idx) / siblings.length - Math.PI / 2;
            const spread = (9 + siblings.length * 1.4) * Math.pow(invScale, 0.55);
            px += Math.cos(ang) * spread;
            py += Math.sin(ang) * spread;
          }
          const tm = TIER_META[r.verdict_tier] || TIER_META['中规中矩'];
          const sel = r.entry_id === state.selectedEid;
          const rad = (sel ? 9.5 : (r.verdict_tier === '强烈推荐' ? 6.8 : 5.4)) * Math.pow(invScale, 0.45);
          const strokeW = (sel ? 2.6 : 1.3) * Math.pow(invScale, 0.45);
          const labelHtml = sel
            ? `<text x="${px.toFixed(1)}" y="${(py - rad - 5).toFixed(1)}" text-anchor="middle" font-size="${(11.5 * Math.pow(invScale, 0.45)).toFixed(1)}" font-weight="800" fill="var(--text-main)" stroke="var(--bg-surface)" stroke-width="3" paint-order="stroke">${escapeHtml(r.name)}</text>`
            : '';
          return `<g class="rest-pin" data-pin-eid="${escapeHtml(r.entry_id)}" style="cursor:pointer;">
            <circle cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="${(rad * 1.75).toFixed(1)}" fill="transparent"/>
            <circle cx="${px.toFixed(1)}" cy="${py.toFixed(1)}" r="${rad.toFixed(1)}" fill="${tm.color}" stroke="#ffffff" stroke-width="${strokeW.toFixed(2)}"/>
            ${labelHtml}
          </g>`;
        }).join('');
      }

      function applyMapTransform() {
        const { x, y, scale } = state.mapTransform;
        mapViewport.setAttribute('transform', `translate(${x.toFixed(2)}, ${y.toFixed(2)}) scale(${scale.toFixed(4)})`);
      }

      function centerMapOn(lat, lng, targetScale) {
        const p = project(lat, lng);
        const s = targetScale || state.mapTransform.scale;
        state.mapTransform.scale = Math.max(0.55, Math.min(8, s));
        state.mapTransform.x = 500 - p.x * state.mapTransform.scale;
        state.mapTransform.y = 500 - p.y * state.mapTransform.scale;
        applyMapTransform();
        renderMapPins();
      }

      function showMapPreview(eid) {
        const r = REST_BY_ID.get(eid);
        if (!r) {
          mapPreviewDrawer.classList.remove('show');
          return;
        }
        state.selectedEid = eid;
        const tm = TIER_META[r.verdict_tier] || TIER_META['中规中矩'];
        const qShop = encodeURIComponent(`${r.name} ${r.address || ''}`.trim());
        const appleUrl = `https://maps.apple.com/?q=${qShop}&ll=${r.lat},${r.lng}`;
        const amapUrl = `https://uri.amap.com/search?keyword=${encodeURIComponent(r.name)}&center=${r.lng},${r.lat}&city=310000&src=shanghai_food_radar`;
        const walk = r._walkText ? `<span class="walk-badge">${escapeHtml(r._walkText)}</span>` : '';
        const resBadge = r.reservation_required ? `<span class="res-badge">📅 需预约</span>` : '';

        mapPreviewDrawer.innerHTML = `
          <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:8px;">
            <div>
              <strong style="font-size:16px;">${escapeHtml(r.name)}</strong>
              <div class="card-meta" style="margin-top:4px;">
                ${walk}
                <span class="tier-badge ${tm.cls}">${tm.icon} ${escapeHtml(r.verdict_tier)}</span>
                ${resBadge}
                <span class="price-pill">${r.price_per_person ? '¥' + r.price_per_person + '/人' : '时价'}</span>
                <span class="meta-dot">${escapeHtml(r.district)} · ${escapeHtml(r.commercial_area)}</span>
              </div>
            </div>
            <button type="button" class="btn-sm" id="btnClosePreview" style="padding:3px 8px;">✕</button>
          </div>
          <p style="margin:6px 0;font-size:12px;color:var(--text-sub);">${escapeHtml(r.overall_review_summary)}</p>
          <div class="card-actions" style="margin-top:6px;padding-top:6px;">
            <button type="button" class="act-btn primary" data-open-modal="${escapeHtml(r.entry_id)}">🗣️ 点单/打车卡</button>
            <a class="act-btn" href="${appleUrl}" target="_blank" rel="noopener">🍎 Apple地图</a>
            <a class="act-btn" href="${amapUrl}" target="_blank" rel="noopener">🧭 高德</a>
            <a class="act-btn" href="${escapeHtml(r.video_url)}" target="_blank" rel="noopener">📺 B站</a>
          </div>
        `;
        mapPreviewDrawer.classList.add('show');
        const closeBtn = document.getElementById('btnClosePreview');
        if (closeBtn) closeBtn.addEventListener('click', () => {
          state.selectedEid = null;
          mapPreviewDrawer.classList.remove('show');
          renderMapPins();
        });
        renderMapPins();
      }

      // Map Pan & Pinch-to-Zoom gestures (isolated to mapCanvasWrap)
      function clientToSvgCoords(clientX, clientY) {
        const pt = shanghaiSvg.createSVGPoint();
        pt.x = clientX;
        pt.y = clientY;
        const ctm = shanghaiSvg.getScreenCTM();
        if (!ctm) return { x: 500, y: 500 };
        return pt.matrixTransform(ctm.inverse());
      }

      function zoomAroundSvgPoint(factor, svgX, svgY) {
        const oldS = state.mapTransform.scale;
        const newS = Math.max(0.55, Math.min(8.0, oldS * factor));
        const ratio = newS / oldS;
        state.mapTransform.x = svgX - (svgX - state.mapTransform.x) * ratio;
        state.mapTransform.y = svgY - (svgY - state.mapTransform.y) * ratio;
        state.mapTransform.scale = newS;
        applyMapTransform();
        renderMapPins();
      }

      let dragState = null;
      let pinchState = null;

      mapCanvasWrap.addEventListener('wheel', (e) => {
        e.preventDefault();
        const p = clientToSvgCoords(e.clientX, e.clientY);
        zoomAroundSvgPoint(e.deltaY < 0 ? 1.22 : 0.82, p.x, p.y);
      }, { passive: false });

      mapCanvasWrap.addEventListener('mousedown', (e) => {
        if (e.button !== 0) return;
        const startSvg = clientToSvgCoords(e.clientX, e.clientY);
        dragState = {
          startClientX: e.clientX,
          startClientY: e.clientY,
          startSvg,
          origX: state.mapTransform.x,
          origY: state.mapTransform.y,
          moved: false
        };
      });

      window.addEventListener('mousemove', (e) => {
        if (!dragState) return;
        if (Math.hypot(e.clientX - dragState.startClientX, e.clientY - dragState.startClientY) > 4) {
          dragState.moved = true;
        }
        const curSvg = clientToSvgCoords(e.clientX, e.clientY);
        state.mapTransform.x = dragState.origX + (curSvg.x - dragState.startSvg.x);
        state.mapTransform.y = dragState.origY + (curSvg.y - dragState.startSvg.y);
        applyMapTransform();
      });

      window.addEventListener('mouseup', (e) => {
        if (!dragState) return;
        const wasMoved = dragState.moved;
        dragState = null;
        if (!wasMoved) handleMapTap(e.target, e.clientX, e.clientY);
      });

      // Touch 1-finger drag + 2-finger pinch zoom
      mapCanvasWrap.addEventListener('touchstart', (e) => {
        if (e.touches.length === 1) {
          const t = e.touches[0];
          dragState = {
            startClientX: t.clientX,
            startClientY: t.clientY,
            startSvg: clientToSvgCoords(t.clientX, t.clientY),
            origX: state.mapTransform.x,
            origY: state.mapTransform.y,
            moved: false
          };
          pinchState = null;
        } else if (e.touches.length === 2) {
          dragState = null;
          const [t1, t2] = [e.touches[0], e.touches[1]];
          const dist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
          const midSvg = clientToSvgCoords((t1.clientX + t2.clientX) / 2, (t1.clientY + t2.clientY) / 2);
          pinchState = {
            startDist: Math.max(10, dist),
            startScale: state.mapTransform.scale,
            worldX: (midSvg.x - state.mapTransform.x) / state.mapTransform.scale,
            worldY: (midSvg.y - state.mapTransform.y) / state.mapTransform.scale
          };
        }
      }, { passive: true });

      mapCanvasWrap.addEventListener('touchmove', (e) => {
        e.preventDefault();
        if (e.touches.length === 1 && dragState) {
          const t = e.touches[0];
          if (Math.hypot(t.clientX - dragState.startClientX, t.clientY - dragState.startClientY) > 5) {
            dragState.moved = true;
          }
          const curSvg = clientToSvgCoords(t.clientX, t.clientY);
          state.mapTransform.x = dragState.origX + (curSvg.x - dragState.startSvg.x);
          state.mapTransform.y = dragState.origY + (curSvg.y - dragState.startSvg.y);
          applyMapTransform();
        } else if (e.touches.length === 2 && pinchState) {
          const [t1, t2] = [e.touches[0], e.touches[1]];
          const dist = Math.hypot(t2.clientX - t1.clientX, t2.clientY - t1.clientY);
          const midSvg = clientToSvgCoords((t1.clientX + t2.clientX) / 2, (t1.clientY + t2.clientY) / 2);
          const newScale = Math.max(0.55, Math.min(8.0, pinchState.startScale * (dist / pinchState.startDist)));
          state.mapTransform.scale = newScale;
          state.mapTransform.x = midSvg.x - pinchState.worldX * newScale;
          state.mapTransform.y = midSvg.y - pinchState.worldY * newScale;
          applyMapTransform();
        }
      }, { passive: false });

      mapCanvasWrap.addEventListener('touchend', (e) => {
        if (pinchState && e.touches.length < 2) {
          pinchState = null;
          renderMapPins();
          return;
        }
        if (dragState && e.changedTouches.length === 1) {
          const t = e.changedTouches[0];
          const wasMoved = dragState.moved;
          dragState = null;
          if (!wasMoved) {
            const el = document.elementFromPoint(t.clientX, t.clientY);
            handleMapTap(el, t.clientX, t.clientY);
          }
        }
      });

      function handleMapTap(targetEl, clientX, clientY) {
        if (state.pickLocationMode) {
          const svgPt = clientToSvgCoords(clientX, clientY);
          const worldX = (svgPt.x - state.mapTransform.x) / state.mapTransform.scale;
          const worldY = (svgPt.y - state.mapTransform.y) / state.mapTransform.scale;
          const coords = unproject(worldX, worldY);
          state.pickLocationMode = false;
          btnPickLocationMode.classList.remove('active');
          mapCanvasWrap.classList.remove('pick-mode');
          applyUserLocation(coords.lat, coords.lng, '地图选点位置', 'map', true);
          showToast('已将该处设为「我的位置」并更新周边距离');
          return;
        }
        if (!targetEl) return;
        const pin = targetEl.closest ? targetEl.closest('[data-pin-eid]') : null;
        if (pin) {
          const eid = pin.getAttribute('data-pin-eid');
          showMapPreview(eid);
          return;
        }
        const lmNode = targetEl.closest ? targetEl.closest('[data-lm]') : null;
        if (lmNode) {
          setLocationFromLandmark(lmNode.getAttribute('data-lm'), true);
          showToast('已切换商圈定位');
        }
      }

      btnPickLocationMode.addEventListener('click', () => {
        state.pickLocationMode = !state.pickLocationMode;
        btnPickLocationMode.classList.toggle('active', state.pickLocationMode);
        mapCanvasWrap.classList.toggle('pick-mode', state.pickLocationMode);
        if (state.pickLocationMode) {
          showToast('请轻点地图任意位置设为「我的位置」');
        }
      });

      document.getElementById('btnZoomIn').addEventListener('click', () => zoomAroundSvgPoint(1.35, 500, 500));
      document.getElementById('btnZoomOut').addEventListener('click', () => zoomAroundSvgPoint(0.74, 500, 500));
      document.getElementById('btnMapReset').addEventListener('click', () => centerMapOn(31.225, 121.465, 1.35));
      document.getElementById('btnMapCenterMe').addEventListener('click', () => {
        if (state.userLoc) {
          centerMapOn(state.userLoc.lat, state.userLoc.lng, 2.6);
        } else {
          setLocationFromLandmark('jingan_temple', true);
        }
      });

      // --- Order / Taxi Modal ---
      const orderModal = document.getElementById('orderModal');
      const orderModalBody = document.getElementById('orderModalBody');

      function openOrderModal(eid) {
        const r = REST_BY_ID.get(eid);
        if (!r) return;
        state.modalOrderQty = {};
        (r.recommended_dishes || []).forEach(d => { state.modalOrderQty[d] = 1; });
        renderOrderModalContent(r);
        orderModal.classList.add('open');
      }

      function renderOrderModalContent(r) {
        const qShop = encodeURIComponent(`${r.name} ${r.address || ''}`.trim());
        const appleUrl = `https://maps.apple.com/?q=${qShop}&ll=${r.lat},${r.lng}`;
        const amapUrl = `https://uri.amap.com/search?keyword=${encodeURIComponent(r.name)}&center=${r.lng},${r.lat}&city=310000&src=shanghai_food_radar`;

        const dishes = r.recommended_dishes || [];
        const dishRows = dishes.length > 0
          ? dishes.map(d => {
              const qty = state.modalOrderQty[d] || 0;
              return `<div class="order-item-row">
                <span style="font-weight:700;font-size:15px;">${qty > 0 ? '✅' : '⬜'} ${escapeHtml(d)}</span>
                <div class="stepper">
                  <button type="button" class="step-btn" data-step-dish="${escapeHtml(d)}" data-delta="-1">−</button>
                  <span class="step-qty">${qty}</span>
                  <button type="button" class="step-btn" data-step-dish="${escapeHtml(d)}" data-delta="1">＋</button>
                </div>
              </div>`;
            }).join('')
          : `<p style="font-size:13px;color:var(--text-muted);">本期视频暂无明确必点单品推荐，可参考下方评价按喜好点餐。</p>`;

        const avoidList = r.avoid_dishes || [];
        const avoidHtml = avoidList.length > 0
          ? `<div class="avoid-alert-box">⚠️ 避雷菜品警告：${avoidList.map(escapeHtml).join('、')}</div>`
          : '';
        const resAlertHtml = r.reservation_required
          ? `<div class="res-alert-box">📅 需提前预约：${escapeHtml(r.reservation_note || '建议提前预订座位后再前往')}</div>`
          : '';

        const selectedSummary = Object.entries(state.modalOrderQty)
          .filter(([, q]) => q > 0)
          .map(([d, q]) => `${d} ×${q}`)
          .join('、');

        orderModalBody.innerHTML = `
          <div class="taxi-card">
            <div class="taxi-label">🚕 出示给司机 / 到店核对地址</div>
            <h2 class="taxi-shop-name" id="modalShopTitle">${escapeHtml(r.name)} ${r.branch_name ? '<span style="font-size:16px;font-weight:600;">(' + escapeHtml(r.branch_name) + ')</span>' : ''}</h2>
            <div class="taxi-address">${escapeHtml(r.address)}</div>
            <div style="display:flex;flex-wrap:wrap;gap:6px;">
              <button type="button" class="btn-sm accent" id="btnCopyAddr">📋 复制地址</button>
              <button type="button" class="btn-sm" id="btnCopyName">📋 复制店名</button>
              <a class="act-btn" href="${appleUrl}" target="_blank" rel="noopener">🍎 Apple地图</a>
              <a class="act-btn" href="${amapUrl}" target="_blank" rel="noopener">🧭 高德导航</a>
            </div>
          </div>

          ${resAlertHtml}
          ${avoidHtml}

          <div class="order-list-box">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
              <strong style="font-size:14px;">👍 必点推荐菜勾选 (${Object.values(state.modalOrderQty).reduce((a, b) => a + b, 0)} 份)</strong>
              ${dishes.length ? '<button type="button" class="btn-sm" id="btnCopyOrder">📋 复制点菜单</button>' : ''}
            </div>
            ${dishRows}
          </div>

          <div class="review-quotes">
            <div><strong>🧔 王师傅评价：</strong>${escapeHtml(r.wang_shifu_review || '暂无')}</div>
            <div><strong>👩 小毛毛评价：</strong>${escapeHtml(r.xiao_maomao_review || '暂无')}</div>
            <div><strong>💰 价格参考：</strong>${escapeHtml(r.price_info || (r.price_per_person ? '人均约 ' + r.price_per_person + ' 元' : '暂无'))}</div>
          </div>

          <div class="card-actions" style="margin-top:10px;">
            <a class="act-btn primary" href="${escapeHtml(r.video_url)}" target="_blank" rel="noopener">📺 观看B站原探店视频 (${escapeHtml(r.pubdate_str)})</a>
            <a class="act-btn" href="${escapeHtml(r.dianping_url)}" target="_blank" rel="noopener">🍜 打开大众点评</a>
          </div>
        `;

        document.getElementById('btnCopyAddr').addEventListener('click', () => {
          copyTextCompat(`${r.name} ${r.address}`, '已复制店名与详细地址');
        });
        document.getElementById('btnCopyName').addEventListener('click', () => {
          copyTextCompat(r.name, '已复制店名');
        });
        const copyOrderBtn = document.getElementById('btnCopyOrder');
        if (copyOrderBtn) {
          copyOrderBtn.addEventListener('click', () => {
            copyTextCompat(`【${r.name}】点单备忘：${selectedSummary || '尚未勾选'}`, '已复制点单清单');
          });
        }
        orderModalBody.querySelectorAll('[data-step-dish]').forEach(btn => {
          btn.addEventListener('click', () => {
            const dish = btn.getAttribute('data-step-dish');
            const delta = Number(btn.getAttribute('data-delta'));
            state.modalOrderQty[dish] = Math.max(0, (state.modalOrderQty[dish] || 0) + delta);
            renderOrderModalContent(r);
          });
        });
      }

      document.getElementById('btnCloseModal').addEventListener('click', () => orderModal.classList.remove('open'));
      orderModal.addEventListener('click', (e) => {
        if (e.target === orderModal) orderModal.classList.remove('open');
      });

      // --- Delegated Clicks on Cards (Favs, Modal, Map Focus) ---
      document.addEventListener('click', (e) => {
        const favBtn = e.target.closest('[data-fav-toggle]');
        if (favBtn) {
          const eid = favBtn.getAttribute('data-fav-toggle');
          if (state.favIds.has(eid)) {
            state.favIds.delete(eid);
            showToast('已从收藏夹移除');
          } else {
            state.favIds.add(eid);
            showToast('⭐ 已加入收藏夹');
          }
          renderFavsPanel();
          renderNearbySlice();
          return;
        }

        const modalBtn = e.target.closest('[data-open-modal]');
        if (modalBtn) {
          openOrderModal(modalBtn.getAttribute('data-open-modal'));
          return;
        }

        const mapFocusBtn = e.target.closest('[data-focus-map]');
        if (mapFocusBtn) {
          const eid = mapFocusBtn.getAttribute('data-focus-map');
          const r = REST_BY_ID.get(eid);
          if (r) {
            if (window.innerWidth < 900) switchTab('map');
            centerMapOn(r.lat, r.lng, 3.2);
            showMapPreview(eid);
          }
        }
      });

      // --- Bottom Tab Switching ---
      const mainScroller = document.getElementById('mainScroller');
      const mapPane = document.getElementById('mapPane');
      const floatingScrollBtns = document.getElementById('floatingScrollBtns');
      const tabButtons = document.querySelectorAll('.bottom-tabs .tab-btn');

      function switchTab(tabName) {
        state.activeTab = tabName;
        tabButtons.forEach(b => b.classList.toggle('active', b.dataset.tab === tabName));

        const isMobile = window.innerWidth < 900;
        if (tabName === 'map' && isMobile) {
          mainScroller.style.display = 'none';
          mapPane.classList.add('mobile-active');
          floatingScrollBtns.style.display = 'none';
          renderMapPins();
        } else {
          mainScroller.style.display = 'block';
          mapPane.classList.remove('mobile-active');
          floatingScrollBtns.style.display = 'flex';
          const panelMap = { nearby: 'panelNearby', redblack: 'panelRedBlack', favs: 'panelFavs', map: 'panelNearby' };
          const targetPanelId = panelMap[tabName] || 'panelNearby';
          document.querySelectorAll('.tab-panel').forEach(p => {
            p.classList.toggle('active', p.id === targetPanelId);
          });
          mainScroller.scrollTop = 0;
        }
      }

      tabButtons.forEach(btn => {
        btn.addEventListener('click', () => switchTab(btn.dataset.tab));
      });

      window.addEventListener('resize', () => {
        if (window.innerWidth >= 900 && state.activeTab === 'map') {
          mainScroller.style.display = 'block';
          floatingScrollBtns.style.display = 'flex';
        }
      });

      // --- Quick Scroll Buttons + Iframe-Only Touch/Pointer Fallback ---
      document.getElementById('btnScrollTop').addEventListener('click', () => {
        mainScroller.scrollTo({ top: 0, behavior: 'smooth' });
      });
      document.getElementById('btnPageDown').addEventListener('click', () => {
        mainScroller.scrollBy({ top: Math.round(mainScroller.clientHeight * 0.82), behavior: 'smooth' });
      });

      const isInIframe = (() => {
        try { return window.self !== window.top; } catch (_) { return true; }
      })();

      if (isInIframe) {
        let iframeDrag = null;
        mainScroller.addEventListener('pointerdown', (e) => {
          if (e.pointerType === 'mouse' && e.button !== 0) return;
          if (e.target.closest('button, a, input, select, .chip-strip')) return;
          iframeDrag = { startY: e.clientY, startScroll: mainScroller.scrollTop };
        });
        mainScroller.addEventListener('pointermove', (e) => {
          if (!iframeDrag) return;
          mainScroller.scrollTop = iframeDrag.startScroll - (e.clientY - iframeDrag.startY);
        });
        window.addEventListener('pointerup', () => { iframeDrag = null; });
      }

      // --- Precompute Search Index & Boot ---
      RESTAURANTS.forEach(r => {
        r._searchBlob = [
          r.name, r.branch_name, (r.aliases || []).join(' '),
          r.district, r.commercial_area, r.address,
          r.cuisine_category, r.cuisine_group, r.series_name,
          r.reservation_required ? '需预约 预约 预订' : '免预约',
          r.reservation_note || '',
          (r.recommended_dishes || []).join(' '),
          (r.avoid_dishes || []).join(' '),
          r.overall_review_summary, r.wang_shifu_review, r.xiao_maomao_review, r.video_title
        ].join(' ').toLowerCase();
      });

      initBaseVectorMap();
      applyMapTransform();
      recomputeAndRender();

      // Register Service Worker using relative path ./sw.js
      if ('serviceWorker' in navigator && (location.protocol === 'https:' || location.hostname === 'localhost' || location.hostname === '127.0.0.1')) {
        window.addEventListener('load', () => {
          navigator.serviceWorker.register('./sw.js', { scope: './' }).catch(() => {});
        });
      }
    })();
  </script>
</body>
</html>
"""


def main():
    os.makedirs(DOCS_DIR, exist_ok=True)
    with open(os.path.join(DATA_DIR, "shanghai_restaurants_verified.json"), "r", encoding="utf-8") as f:
        restaurants = json.load(f)
    with open(os.path.join(DATA_DIR, "shanghai_landmarks.json"), "r", encoding="utf-8") as f:
        landmarks = json.load(f)

    # Enrich cuisine_group without mutating original schema fields
    enriched = []
    for r in restaurants:
        item = dict(r)
        item["cuisine_group"] = classify_cuisine_group(r.get("cuisine_category", ""))
        enriched.append(item)

    prerendered_rb = build_red_black_html(enriched)
    rest_json = json.dumps(enriched, ensure_ascii=False, separators=(",", ":"))
    lm_json = json.dumps(landmarks, ensure_ascii=False, separators=(",", ":"))

    final_html = (
        HTML_TEMPLATE
        .replace("__PRERENDERED_RED_BLACK__", prerendered_rb)
        .replace("__RESTAURANTS_JSON__", rest_json)
        .replace("__LANDMARKS_JSON__", lm_json)
    )

    out_path = os.path.join(DOCS_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(final_html)

    group_counts = Counter(r["cuisine_group"] for r in enriched)
    print(f"Generated {out_path} ({len(final_html):,} bytes)")
    print(f"Cuisine groups: {dict(group_counts)}")


if __name__ == "__main__":
    main()
