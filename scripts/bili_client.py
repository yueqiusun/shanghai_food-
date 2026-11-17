import gzip
import hashlib
import http.cookiejar
import json
import random
import time
import urllib.error
import urllib.parse
import urllib.request
from functools import reduce

MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Referer": "https://space.bilibili.com/452606628/video",
    "Origin": "https://space.bilibili.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip",
}


class BiliClient:
    def __init__(self, delay_range=(0.45, 0.75)):
        self.cj = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.cj)
        )
        self.delay_range = delay_range
        self.img_key = ""
        self.sub_key = ""
        self._last_req = 0.0

    def _sleep(self):
        now = time.time()
        elapsed = now - self._last_req
        target = random.uniform(*self.delay_range)
        if elapsed < target:
            time.sleep(target - elapsed)
        self._last_req = time.time()

    def get_json(self, url, params=None, headers=None, retries=3):
        if params:
            qs = urllib.parse.urlencode(params)
            sep = "&" if "?" in url else "?"
            url = f"{url}{sep}{qs}"
        hdrs = dict(DEFAULT_HEADERS)
        if headers:
            hdrs.update(headers)

        for attempt in range(retries):
            self._sleep()
            req = urllib.request.Request(url, headers=hdrs, method="GET")
            try:
                with self.opener.open(req, timeout=20) as resp:
                    raw = resp.read()
                    if resp.headers.get("Content-Encoding") == "gzip":
                        raw = gzip.decompress(raw)
                    return json.loads(raw.decode("utf-8"))
            except urllib.error.HTTPError as e:
                body = ""
                try:
                    raw = e.read()
                    if e.headers.get("Content-Encoding") == "gzip":
                        raw = gzip.decompress(raw)
                    body = raw.decode("utf-8", errors="replace")[:200]
                except Exception:
                    pass
                if e.code in (412, 429) and attempt < retries - 1:
                    wait = 3.0 * (attempt + 1)
                    print(f"[WARN] HTTP {e.code} on {url}, sleeping {wait}s...")
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"HTTP {e.code} on {url}: {body}") from e
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(1.5 * (attempt + 1))
                    continue
                raise

    def init_session(self):
        # Visit bilibili.com and spi to populate cookies (buvid3, buvid4, etc.)
        try:
            req = urllib.request.Request(
                "https://www.bilibili.com/", headers=DEFAULT_HEADERS
            )
            with self.opener.open(req, timeout=15) as resp:
                resp.read(1024)
        except Exception as e:
            print(f"[WARN] init homepage failed: {e}")

        try:
            spi = self.get_json("https://api.bilibili.com/x/frontend/finger/spi")
            if spi.get("code") == 0 and spi.get("data"):
                b3 = spi["data"].get("b_3", "")
                b4 = spi["data"].get("b_4", "")
                if b3:
                    self._set_cookie("buvid3", b3)
                if b4:
                    self._set_cookie("buvid4", b4)
        except Exception as e:
            print(f"[WARN] spi failed: {e}")

        nav = self.get_json("https://api.bilibili.com/x/web-interface/nav")
        wbi_img = (nav.get("data") or {}).get("wbi_img") or {}
        img_url = wbi_img.get("img_url", "")
        sub_url = wbi_img.get("sub_url", "")
        self.img_key = img_url.rsplit("/", 1)[-1].split(".")[0]
        self.sub_key = sub_url.rsplit("/", 1)[-1].split(".")[0]
        if not self.img_key or not self.sub_key:
            raise RuntimeError(f"Failed to obtain WBI keys from nav: {nav}")

    def _set_cookie(self, name, value):
        c = http.cookiejar.Cookie(
            version=0,
            name=name,
            value=value,
            port=None,
            port_specified=False,
            domain=".bilibili.com",
            domain_specified=True,
            domain_initial_dot=True,
            path="/",
            path_specified=True,
            secure=False,
            expires=None,
            discard=True,
            comment=None,
            comment_url=None,
            rest={},
        )
        self.cj.set_cookie(c)

    def _mixin_key(self):
        orig = self.img_key + self.sub_key
        return reduce(lambda s, i: s + orig[i], MIXIN_KEY_ENC_TAB, "")[:32]

    def sign_wbi(self, params: dict) -> dict:
        mixin = self._mixin_key()
        curr_time = round(time.time())
        signed = dict(params)
        signed["wts"] = curr_time
        signed = dict(sorted(signed.items()))
        cleaned = {
            k: "".join(ch for ch in str(v) if ch not in "!'()*")
            for k, v in signed.items()
        }
        query = urllib.parse.urlencode(cleaned)
        wbi_sign = hashlib.md5((query + mixin).encode("utf-8")).hexdigest()
        cleaned["w_rid"] = wbi_sign
        return cleaned

    def get_wbi_json(self, url, params, headers=None, retries=3):
        signed_params = self.sign_wbi(params)
        return self.get_json(url, params=signed_params, headers=headers, retries=retries)
