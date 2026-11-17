#!/usr/bin/env python3
"""Generate crisp Nagoya Food Map PWA icons (180x180 apple-touch-icon.png, 512x512 icon-512.png, and icon.svg)."""
import math
import os
import struct
import zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def write_png(path: str, width: int, height: int, rgba_bytes: bytes) -> None:
    def chunk(tag: bytes, data: bytes) -> bytes:
        return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    raw = bytearray()
    stride = width * 4
    for y in range(height):
        raw.append(0)
        raw.extend(rgba_bytes[y * stride : (y + 1) * stride])

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    idat = zlib.compress(bytes(raw), 9)
    png = b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", idat) + chunk(b"IEND", b"")
    with open(path, "wb") as f:
        f.write(png)


def render_icon(size: int) -> bytes:
    buf = bytearray(size * size * 4)
    cx, cy = size * 0.5, size * 0.5
    r_outer = size * 0.42

    for y in range(size):
        for x in range(size):
            nx = (x + 0.5) / size
            ny = (y + 0.5) / size

            # Rich Nagoya miso-crimson to gold-amber gradient background
            t = 0.65 * ny + 0.35 * nx
            bg_r = int(165 * (1 - t) + 110 * t)
            bg_g = int(28 * (1 - t) + 18 * t)
            bg_b = int(28 * (1 - t) + 22 * t)
            r, g, b, a = bg_r, bg_g, bg_b, 255

            dx = x + 0.5 - cx
            dy = y + 0.5 - cy
            dist = math.hypot(dx, dy)

            # Gold ring (Kinshachi gold)
            ring_r = size * 0.36
            ring_w = size * 0.028
            if abs(dist - ring_r) < ring_w:
                edge = max(0.0, 1.0 - abs(dist - ring_r) / ring_w)
                r = int(r * (1 - edge) + 245 * edge)
                g = int(g * (1 - edge) + 196 * edge)
                b = int(b * (1 - edge) + 66 * edge)

            # Warm cream bowl silhouette in center
            bowl_cy = size * 0.54
            b_dx = x + 0.5 - cx
            b_dy = y + 0.5 - bowl_cy
            if 0 <= b_dy <= size * 0.20:
                half_w = size * 0.23 * math.sqrt(max(0.0, 1.0 - (b_dy / (size * 0.22)) ** 2))
                if abs(b_dx) <= half_w:
                    r, g, b = 255, 248, 235
            # Bowl rim
            if abs(y + 0.5 - (bowl_cy - size * 0.01)) <= size * 0.022 and abs(b_dx) <= size * 0.24:
                r, g, b = 245, 196, 66
            # Bowl foot
            if size * 0.20 <= b_dy <= size * 0.24 and abs(b_dx) <= size * 0.10:
                r, g, b = 245, 196, 66

            # Three golden steam / kinshachi arcs above bowl
            for offset_x in (-0.10, 0.0, 0.10):
                sx = cx + size * offset_x
                sy_top = size * 0.26
                sy_bot = size * 0.45
                if sy_top <= y <= sy_bot:
                    wave = math.sin((y - sy_top) / (sy_bot - sy_top) * math.pi * 2) * size * 0.018
                    if abs((x + 0.5) - (sx + wave)) <= size * 0.016:
                        r, g, b = 252, 211, 77

            idx = (y * size + x) * 4
            buf[idx] = r
            buf[idx + 1] = g
            buf[idx + 2] = b
            buf[idx + 3] = a
    return bytes(buf)


def main() -> None:
    svg = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 512 512">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#A51C1C"/>
      <stop offset="100%" stop-color="#6E1216"/>
    </linearGradient>
  </defs>
  <rect width="512" height="512" rx="112" fill="url(#bg)"/>
  <circle cx="256" cy="256" r="184" fill="none" stroke="#F5C442" stroke-width="14"/>
  <path d="M134 270 H378 C378 345 330 386 256 386 C182 386 134 345 134 270 Z" fill="#FFF8EB"/>
  <rect x="130" y="258" width="252" height="18" rx="9" fill="#F5C442"/>
  <rect x="206" y="384" width="100" height="20" rx="6" fill="#F5C442"/>
  <path d="M204 234 Q192 204 204 174 Q216 144 204 124" fill="none" stroke="#FCD34D" stroke-width="14" stroke-linecap="round"/>
  <path d="M256 234 Q244 204 256 174 Q268 144 256 124" fill="none" stroke="#FCD34D" stroke-width="14" stroke-linecap="round"/>
  <path d="M308 234 Q296 204 308 174 Q320 144 308 124" fill="none" stroke="#FCD34D" stroke-width="14" stroke-linecap="round"/>
</svg>
"""
    with open(os.path.join(ROOT, "icon.svg"), "w", encoding="utf-8") as f:
        f.write(svg)
    write_png(os.path.join(ROOT, "apple-touch-icon.png"), 180, 180, render_icon(180))
    write_png(os.path.join(ROOT, "icon-512.png"), 512, 512, render_icon(512))
    print("Generated icon.svg, apple-touch-icon.png (180x180), icon-512.png (512x512)")


if __name__ == "__main__":
    main()
