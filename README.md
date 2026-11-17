# 🍽️ 上海美食雷达 · 王师傅和小毛毛探店地图 (iOS PWA 离线版)

收录 Bilibili「王师傅和小毛毛」（UID `452606628`）**164 家上海实体餐厅探店红黑榜**与 **35 大上海热门商圈/地铁枢纽**坐标，零外部 CDN 依赖，单 URL 同时适配 **iPhone Safari（PWA 全屏离线）**、Android 与桌面端分栏视图。

---

## 🚀 3 步一键发布到 GitHub Pages（并在 iPhone 添加到主屏幕）

### 第 1 步：创建仓库并推送代码
在 GitHub 新建一个公开仓库（例如 `shanghai-food-radar`），在项目根目录执行：

```bash
git init
git add .
git commit -m "feat: Shanghai Food Radar PWA (164 restaurants + 35 landmarks)"
git branch -M main
git remote add origin https://github.com/<你的用户名>/<你的仓库名>.git
git push -u origin main
```

### 第 2 步：开启 GitHub Pages（二选一，均已预配好）
- **方式 A（推荐，全自动 GitHub Actions）**：进入仓库 **Settings → Pages → Build and deployment → Source**，选择 **GitHub Actions**，推送后会自动运行 `.github/workflows/pages.yml` 部署 `./docs` 目录。
- **方式 B（分支目录直出）**：进入 **Settings → Pages → Source**，选择 **Deploy from a branch**，分支选 `main`、文件夹选 **`/docs`**，点击 **Save** 即可。

约 30 秒后即可访问：`https://<你的用户名>.github.io/<你的仓库名>/`（HTTPS 环境下自动支持 iOS GPS 精确定位与 Service Worker 离线缓存）。

### 第 3 步：在 iPhone Safari 添加到主屏幕（原生 120Hz 全屏离线体验）
1. 用 iPhone 自带 **Safari** 打开上方 GitHub Pages 链接；
2. 点击屏幕底部正中间的 **「分享」按钮 `[↑]`**；
3. 上滑菜单点击 **「添加到主屏幕」 → 右上角「添加」**。
4. 从桌面「上海美食雷达」图标启动，即可隐藏地址栏全屏浏览（适配灵动岛与底部安全区），即使在地下商场或地铁无信号环境也能离线查周边、看避雷菜、打开到店打车大字卡！

---

## 🛠️ 本地命令行与重新构建指南

### 1. 命令行查询周边餐厅 (`find_nearby.py`)
```bash
# 查询静安寺 1.5km 内的红榜餐厅（强烈推荐 + 值得一试）
python3 find_nearby.py "静安寺" --radius 1500 --red-only

# 查询人民广场 1km 内人均 ≤ 100 元的餐厅
python3 find_nearby.py "人民广场" --radius 1000 --max-price 100

# 按自定义经纬度或菜系筛选
python3 find_nearby.py "31.2194,121.4748" --radius 1200 --cuisine "粤菜"

# 查看全部内置的 35 个上海商圈/地铁枢纽
python3 find_nearby.py --list-landmarks
```

### 2. 重新生成网站与文字攻略
修改 `./data/shanghai_restaurants_verified.json` 或 `./data/shanghai_landmarks.json` 后运行：
```bash
python3 scripts/build_all.py
```

---

## 📂 核心目录结构

- `./docs/index.html`：单文件零外部依赖 Web App（内置 164 家餐厅 + 35 商圈 + 纯 SVG 上海矢量触控地图 + 到店点单/打车大字卡）
- `./docs/manifest.webmanifest` / `./docs/sw.js` / `./docs/apple-touch-icon.png` / `./docs/icon-512.png`：相对路径 PWA 配置与离线缓存脚本（完美兼容 GitHub Pages 子路径）
- `./shanghai_food_map.md`：完整文字版上海美食红黑榜与全行政区商圈速查手册
- `./find_nearby.py`：终端周边餐厅检索脚本
- `./.github/workflows/pages.yml`：GitHub Pages 自动构建部署配置
