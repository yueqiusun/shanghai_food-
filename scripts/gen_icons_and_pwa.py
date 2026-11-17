import json
import math
import os
import struct
import zlib

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(ROOT_DIR, "docs")


def encode_png(width: int, height: int, rgb_bytes: bytes) -> bytes:
    """Encode raw RGB or RGBA bytes (len = width * height * 4) into a valid PNG."""
    def chunk(tag: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(tag + data) & 0xFFFFFFFF
        return struct.pack("!I", len(data)) + tag + data + struct.pack("!I", crc)

    # Filter type 0 (None) prepended to each scanline
    stride = width * 4
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        raw.extend(rgb_bytes[y * stride : (y + 1) * stride])

    ihdr = struct.pack("!IIBBBBB", width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA
    idat = zlib.compress(bytes(raw), level=9)
    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", idat)
        + chunk(b"IEND", b"")
    )


def render_radar_icon(size: int) -> bytes:
    """Render a crisp Shanghai Food Radar icon with 2x supersampling."""
    buf = bytearray(size * size * 4)
    half = size / 2.0

    # 2x2 subpixel offsets for smooth edges
    sub = (-0.25, 0.25)

    def sample(nx: float, ny: float) -> tuple[float, float, float, float]:
        # nx, ny in [-1, 1]
        # Rounded squircle / full-bleed background (iOS clips apple-touch-icon automatically,
        # so full-bleed dark gradient ensures zero white corners on iOS!)
        # Rich dark espresso-charcoal to warm ember radial gradient
        r2 = nx * nx + ny * ny
        r = math.sqrt(r2)

        # Base background gradient
        bg_t = min(1.0, r / 1.35)
        br = 28.0 * (1.0 - bg_t) + 12.0 * bg_t
        bg = 18.0 * (1.0 - bg_t) + 11.0 * bg_t
        bb = 18.0 * (1.0 - bg_t) + 15.0 * bg_t

        # Warm ambient glow in center
        glow = math.exp(-r2 * 2.8)
        br += 65.0 * glow
        bg += 22.0 * glow
        bb += 10.0 * glow

        # Radar sweep sector (top-right quadrant, -75 deg to +15 deg)
        if r < 0.78:
            ang = math.atan2(ny, nx)  # [-pi, pi], y down
            # Target sweep around -0.65 rad (up-right)
            diff = (ang - (-0.65) + math.pi) % (2 * math.pi) - math.pi
            if -0.95 < diff < 0.05:
                trail = (diff + 0.95) / 1.0  # 0 -> 1 toward leading edge
                fade = (1.0 - r / 0.78) * 0.4 + 0.6
                intensity = (trail ** 2.2) * fade * 0.55
                br = br * (1 - intensity) + 255 * intensity
                bg = bg * (1 - intensity) + 94 * intensity
                bb = bb * (1 - intensity) + 58 * intensity

        # Concentric radar rings at r = 0.26, 0.52, 0.78
        ring_w = 0.016
        for rr in (0.26, 0.52, 0.78):
            d = abs(r - rr)
            if d < ring_w:
                a = (1.0 - d / ring_w) * 0.38
                br = br * (1 - a) + 255 * a
                bg = bg * (1 - a) + 138 * a
                bb = bb * (1 - a) + 92 * a

        # Crosshair subtle lines
        if r < 0.80:
            line_w = 0.011
            if abs(nx) < line_w or abs(ny) < line_w:
                a = 0.20
                br = br * (1 - a) + 255 * a
                bg = bg * (1 - a) + 145 * a
                bb = bb * (1 - a) + 105 * a

        # Radar blip dots (representing nearby Shanghai food spots)
        blips = [
            (0.34, -0.28, 0.052, (255, 209, 102)),  # gold star blip
            (-0.36, -0.18, 0.040, (52, 211, 153)),  # emerald blip
            (0.26, 0.36, 0.042, (255, 115, 75)),    # coral blip
        ]
        for bx, by, br_rad, bcol in blips:
            bd = math.hypot(nx - bx, ny - by)
            if bd < br_rad * 1.9:
                halo = max(0.0, 1.0 - bd / (br_rad * 1.9)) ** 2 * 0.45
                br = br * (1 - halo) + bcol[0] * halo
                bg = bg * (1 - halo) + bcol[1] * halo
                bb = bb * (1 - halo) + bcol[2] * halo
            if bd < br_rad:
                a = min(1.0, (br_rad - bd) / 0.012)
                br = br * (1 - a) + bcol[0] * a
                bg = bg * (1 - a) + bcol[1] * a
                bb = bb * (1 - a) + bcol[2] * a

        # Center location pin (teardrop pointing to (0, 0.24), head at (0, -0.10))
        px, py = nx, ny + 0.08
        head_r = 0.22
        hd = math.hypot(px, py)
        in_pin = False
        pin_edge = 0.0
        if hd <= head_r:
            in_pin = True
            pin_edge = min(1.0, (head_r - hd) / 0.015)
        elif 0.0 < py < 0.34:
            # Cone tapering from head tangent down to tip at (0, 0.34)
            t = py / 0.34
            half_w = head_r * (1.0 - t) * 0.92
            if abs(px) <= half_w:
                in_pin = True
                pin_edge = min(1.0, (half_w - abs(px)) / 0.015)

        if in_pin:
            # Vibrant vermilion-orange pin gradient
            pt = max(0.0, min(1.0, (ny + 0.30) / 0.56))
            pr = 255.0 * (1 - pt) + 230.0 * pt
            pg = 108.0 * (1 - pt) + 52.0 * pt
            pb = 58.0 * (1 - pt) + 42.0 * pt
            # Inner white cut-out bowl/circle inside pin head
            if hd < 0.095:
                ia = min(1.0, (0.095 - hd) / 0.014)
                pr = pr * (1 - ia) + 255.0 * ia
                pg = pg * (1 - ia) + 248.0 * ia
                pb = pb * (1 - ia) + 240.0 * ia
            br = br * (1 - pin_edge) + pr * pin_edge
            bg = bg * (1 - pin_edge) + pg * pin_edge
            bb = bb * (1 - pin_edge) + pb * pin_edge

        return (
            max(0.0, min(255.0, br)),
            max(0.0, min(255.0, bg)),
            max(0.0, min(255.0, bb)),
            255.0,
        )

    idx = 0
    for y in range(size):
        for x in range(size):
            sr = sg = sb = sa = 0.0
            for oy in sub:
                ny = ((y + 0.5 + oy) - half) / half
                for ox in sub:
                    nx = ((x + 0.5 + ox) - half) / half
                    c = sample(nx, ny)
                    sr += c[0]
                    sg += c[1]
                    sb += c[2]
                    sa += c[3]
            buf[idx] = int(sr * 0.25 + 0.5)
            buf[idx + 1] = int(sg * 0.25 + 0.5)
            buf[idx + 2] = int(sb * 0.25 + 0.5)
            buf[idx + 3] = int(sa * 0.25 + 0.5)
            idx += 4

    return encode_png(size, size, bytes(buf))


SVG_ICON = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <radialGradient id="bg" cx="50%" cy="48%" r="65%">
      <stop offset="0%" stop-color="#3a1c14"/>
      <stop offset="55%" stop-color="#171112"/>
      <stop offset="100%" stop-color="#0b0b0f"/>
    </radialGradient>
    <linearGradient id="pin" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#ff6e40"/>
      <stop offset="100%" stop-color="#e53935"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="112" fill="url(#bg)"/>
  <circle cx="256" cy="256" r="198" fill="none" stroke="#ff8a5c" stroke-opacity="0.32" stroke-width="5"/>
  <circle cx="256" cy="256" r="132" fill="none" stroke="#ff8a5c" stroke-opacity="0.35" stroke-width="5"/>
  <circle cx="256" cy="256" r="66" fill="none" stroke="#ff8a5c" stroke-opacity="0.38" stroke-width="5"/>
  <line x1="56" y1="256" x2="456" y2="256" stroke="#ff9169" stroke-opacity="0.2" stroke-width="3"/>
  <line x1="256" y1="56" x2="256" y2="456" stroke="#ff9169" stroke-opacity="0.2" stroke-width="3"/>
  <path d="M256 256 L396 116 A198 198 0 0 1 446 202 Z" fill="#ff5e3a" fill-opacity="0.35"/>
  <circle cx="344" cy="184" r="13" fill="#ffd166"/>
  <circle cx="164" cy="210" r="10" fill="#34d399"/>
  <circle cx="322" cy="348" r="11" fill="#ff734b"/>
  <path d="M256 164 C224 164 198 190 198 222 C198 264 256 326 256 326 C256 326 314 264 314 222 C314 190 288 164 256 164 Z" fill="url(#pin)"/>
  <circle cx="256" cy="220" r="24" fill="#fff8f0"/>
</svg>
"""

MANIFEST = {
    "name": "上海美食雷达 · 王师傅和小毛毛探店地图",
    "short_name": "上海美食雷达",
    "description": "164家上海餐厅红黑榜、35大商圈周边步行导航与离线到店点单助手",
    "lang": "zh-CN",
    "start_url": "./",
    "scope": "./",
    "display": "standalone",
    "orientation": "portrait-primary",
    "background_color": "#000000",
    "theme_color": "#ff5722",
    "icons": [
        {
            "src": "./apple-touch-icon.png",
            "sizes": "180x180",
            "type": "image/png"
        },
        {
            "src": "./icon-512.png",
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "any maskable"
        },
        {
            "src": "./icon.svg",
            "sizes": "any",
            "type": "image/svg+xml"
        }
    ]
}

SW_JS = """const CACHE_NAME = 'shanghai-food-radar-v1.0.3';
const PRECACHE_URLS = [
  './',
  './index.html',
  './manifest.webmanifest',
  './apple-touch-icon.png',
  './icon-512.png',
  './icon.svg'
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(PRECACHE_URLS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(
        keys
          .filter((key) => key !== CACHE_NAME && key.startsWith('shanghai-food-radar-'))
          .map((key) => caches.delete(key))
      )
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // Stale-While-Revalidate for same-origin static assets
  event.respondWith(
    caches.open(CACHE_NAME).then((cache) =>
      cache.match(req).then((cachedResp) => {
        const fetchPromise = fetch(req)
          .then((networkResp) => {
            if (networkResp && networkResp.status === 200) {
              cache.put(req, networkResp.clone());
            }
            return networkResp;
          })
          .catch(() => cachedResp);
        return cachedResp || fetchPromise;
      })
    )
  );
});
"""


def main():
    os.makedirs(DOCS_DIR, exist_ok=True)

    icon_180 = render_radar_icon(180)
    with open(os.path.join(DOCS_DIR, "apple-touch-icon.png"), "wb") as f:
        f.write(icon_180)

    icon_512 = render_radar_icon(512)
    with open(os.path.join(DOCS_DIR, "icon-512.png"), "wb") as f:
        f.write(icon_512)

    with open(os.path.join(DOCS_DIR, "icon.svg"), "w", encoding="utf-8") as f:
        f.write(SVG_ICON)

    with open(os.path.join(DOCS_DIR, "manifest.webmanifest"), "w", encoding="utf-8") as f:
        json.dump(MANIFEST, f, ensure_ascii=False, indent=2)

    with open(os.path.join(DOCS_DIR, "sw.js"), "w", encoding="utf-8") as f:
        f.write(SW_JS)

    print(
        f"Generated icons & PWA assets in {DOCS_DIR}: "
        f"180px={len(icon_180)}B, 512px={len(icon_512)}B"
    )


if __name__ == "__main__":
    main()
