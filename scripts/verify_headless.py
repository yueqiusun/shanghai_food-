import base64
import functools
import http.client
import http.server
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import threading
import time
import urllib.request

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(ROOT_DIR, "docs")
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


class RecordingHandler(http.server.SimpleHTTPRequestHandler):
    requests_log = []

    def log_request(self, code="-", size="-"):
        RecordingHandler.requests_log.append((self.path, int(code) if str(code).isdigit() else str(code)))

    def log_message(self, format, *args):
        pass


class SimpleWSClient:
    """Minimal RFC 6455 WebSocket client using Python stdlib only."""

    def __init__(self, ws_url: str):
        # ws://127.0.0.1:port/devtools/page/ID
        rest = ws_url.replace("ws://", "", 1)
        host_port, path = rest.split("/", 1)
        path = "/" + path
        host, port_s = host_port.split(":")
        self.sock = socket.create_connection((host, int(port_s)), timeout=15)
        key = base64.b64encode(os.urandom(16)).decode("ascii")
        handshake = (
            f"GET {path} HTTP/1.1\r\n"
            f"Host: {host_port}\r\n"
            f"Upgrade: websocket\r\n"
            f"Connection: Upgrade\r\n"
            f"Sec-WebSocket-Key: {key}\r\n"
            f"Sec-WebSocket-Version: 13\r\n\r\n"
        )
        self.sock.sendall(handshake.encode("ascii"))
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.sock.recv(4096)
        if b"101" not in buf.split(b"\r\n", 1)[0]:
            raise RuntimeError(f"WS handshake failed: {buf[:200]}")
        self._leftover = buf.split(b"\r\n\r\n", 1)[1]
        self._msg_id = 0
        self.events = []

    def _recv_exact(self, n: int) -> bytes:
        out = bytearray()
        if self._leftover:
            take = min(n, len(self._leftover))
            out.extend(self._leftover[:take])
            self._leftover = self._leftover[take:]
        while len(out) < n:
            chunk = self.sock.recv(n - len(out))
            if not chunk:
                raise EOFError("WS closed")
            out.extend(chunk)
        return bytes(out)

    def send_json(self, payload: dict):
        raw = json.dumps(payload).encode("utf-8")
        mask_key = os.urandom(4)
        header = bytearray([0x81])  # FIN + text frame
        length = len(raw)
        if length < 126:
            header.append(0x80 | length)
        elif length < 65536:
            header.append(0x80 | 126)
            header.extend(struct.pack("!H", length))
        else:
            header.append(0x80 | 127)
            header.extend(struct.pack("!Q", length))
        header.extend(mask_key)
        masked = bytes(b ^ mask_key[i % 4] for i, b in enumerate(raw))
        self.sock.sendall(bytes(header) + masked)

    def recv_frame_json(self) -> dict | None:
        b1, b2 = self._recv_exact(2)
        opcode = b1 & 0x0F
        masked = bool(b2 & 0x80)
        length = b2 & 0x7F
        if length == 126:
            length = struct.unpack("!H", self._recv_exact(2))[0]
        elif length == 127:
            length = struct.unpack("!Q", self._recv_exact(8))[0]
        mask_key = self._recv_exact(4) if masked else b""
        payload = self._recv_exact(length)
        if masked:
            payload = bytes(b ^ mask_key[i % 4] for i, b in enumerate(payload))
        if opcode == 0x8:  # Close
            return None
        if opcode == 0x9:  # Ping -> Pong
            self.sock.sendall(b"\x8a\x80" + os.urandom(4))
            return self.recv_frame_json()
        if opcode == 0x1:
            return json.loads(payload.decode("utf-8"))
        return {}

    def call(self, method: str, params: dict | None = None) -> dict:
        self._msg_id += 1
        mid = self._msg_id
        self.send_json({"id": mid, "method": method, "params": params or {}})
        while True:
            msg = self.recv_frame_json()
            if msg is None:
                raise RuntimeError("WS closed during call")
            if msg.get("id") == mid:
                if "error" in msg:
                    raise RuntimeError(f"CDP error on {method}: {msg['error']}")
                return msg.get("result") or {}
            if "method" in msg:
                self.events.append(msg)

    def drain_events(self, duration: float = 0.5):
        self.sock.settimeout(0.1)
        end = time.time() + duration
        while time.time() < end:
            try:
                msg = self.recv_frame_json()
                if msg and "method" in msg:
                    self.events.append(msg)
            except (socket.timeout, BlockingIOError):
                pass
        self.sock.settimeout(15)

    def eval_js(self, expr: str):
        res = self.call("Runtime.evaluate", {"expression": expr, "returnByValue": True, "awaitPromise": True})
        if "exceptionDetails" in res:
            raise RuntimeError(f"JS exception: {res['exceptionDetails']}")
        return (res.get("result") or {}).get("value")

    def close(self):
        try:
            self.sock.close()
        except Exception:
            pass


def main():
    http_port = find_free_port()
    cdp_port = find_free_port()

    handler = functools.partial(RecordingHandler, directory=DOCS_DIR)
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", http_port), handler)
    srv_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    srv_thread.start()
    base_url = f"http://127.0.0.1:{http_port}"
    print(f"[HTTP] Started temporary server on {base_url}")

    # Direct HTTP check of critical PWA assets
    for asset in ["/index.html", "/manifest.webmanifest", "/sw.js", "/apple-touch-icon.png", "/icon-512.png", "/icon.svg"]:
        with urllib.request.urlopen(base_url + asset, timeout=5) as r:
            assert r.status == 200, f"Expected 200 for {asset}, got {r.status}"
            body_len = len(r.read())
            print(f"  [200 OK] {asset} ({body_len:,} bytes)")

    tmp_profile = tempfile.mkdtemp(prefix="chrome_verify_")
    proc = None
    ws = None
    try:
        cmd = [
            CHROME_PATH,
            "--headless=new",
            f"--remote-debugging-port={cdp_port}",
            "--remote-allow-origins=*",
            f"--user-data-dir={tmp_profile}",
            "--window-size=390,844",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-gpu",
            "about:blank",
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Wait for CDP /json endpoint
        ws_url = None
        for _ in range(40):
            time.sleep(0.25)
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{cdp_port}/json", timeout=2) as r:
                    targets = json.loads(r.read().decode("utf-8"))
                for t in targets:
                    if t.get("type") == "page" and t.get("webSocketDebuggerUrl"):
                        ws_url = t["webSocketDebuggerUrl"]
                        break
                if ws_url:
                    break
            except Exception:
                pass

        if not ws_url:
            raise RuntimeError("Failed to connect to headless Chrome CDP")

        ws = SimpleWSClient(ws_url)
        ws.call("Runtime.enable")
        ws.call("Log.enable")
        ws.call("Network.enable")
        ws.call("Page.enable")
        ws.call(
            "Emulation.setDeviceMetricsOverride",
            {"width": 390, "height": 844, "deviceScaleFactor": 3, "mobile": True},
        )

        print(f"[CDP] Navigating iPhone viewport (390x844) to {base_url}/index.html ...")
        ws.call("Page.navigate", {"url": f"{base_url}/index.html"})
        ws.drain_events(1.8)

        # 1. Check layout, font sizes >= 16px, initial card render, and scrollability
        initial_check = ws.eval_js("""(() => {
          const scroller = document.getElementById('mainScroller');
          const shell = document.querySelector('.app-shell');
          const inputs = Array.from(document.querySelectorAll('input, select'));
          const minFont = Math.min(...inputs.map(el => parseFloat(getComputedStyle(el).fontSize)));
          const cards = document.querySelectorAll('#nearbyList .rest-card').length;
          const swReady = 'serviceWorker' in navigator;
          return {
            viewportW: window.innerWidth,
            viewportH: window.innerHeight,
            shellH: shell.getBoundingClientRect().height,
            scrollHeight: scroller.scrollHeight,
            clientHeight: scroller.clientHeight,
            minInputFontPx: minFont,
            initialCards: cards,
            swReady
          };
        })()""")
        print(f"[CHECK 1] Viewport & Layout: {initial_check}")
        assert initial_check["viewportW"] == 390 and initial_check["viewportH"] == 844
        assert initial_check["minInputFontPx"] >= 16, f"Input font < 16px: {initial_check['minInputFontPx']}"
        assert initial_check["initialCards"] == 30, f"Expected 30 initial cards, got {initial_check['initialCards']}"
        assert initial_check["scrollHeight"] > initial_check["clientHeight"], "mainScroller is not scrollable!"

        # 2. Test #mainScroller scrolling + lazy loading
        scroll_check = ws.eval_js("""(() => {
          const scroller = document.getElementById('mainScroller');
          scroller.scrollTop = 520;
          return { scrollTop: scroller.scrollTop, clientHeight: scroller.clientHeight, scrollHeight: scroller.scrollHeight };
        })()""")
        print(f"[CHECK 2] #mainScroller scroll test: {scroll_check}")
        assert scroll_check["scrollTop"] >= 500, f"Scroll failed: {scroll_check}"

        # 3. Locate to 静安寺 and verify walking distance & nearby list
        jingan_check = ws.eval_js("""(() => {
          document.getElementById('btnDemoJingan').click();
          const status = document.getElementById('locStatusText').textContent;
          const summary = document.getElementById('resultCountText').textContent;
          const cards = Array.from(document.querySelectorAll('#nearbyList .rest-card'));
          const sampleWalks = cards.slice(0, 5).map(c => ({
            name: c.querySelector('.card-title')?.textContent?.trim(),
            walk: c.querySelector('.walk-badge')?.textContent?.trim()
          }));
          return { status, summary, countRendered: cards.length, sampleWalks };
        })()""")
        print(f"[CHECK 3] Jing'an Temple location test: {json.dumps(jingan_check, ensure_ascii=False)}")
        assert "静安寺" in jingan_check["status"]
        assert jingan_check["countRendered"] > 0
        assert all(w["walk"] and "🚶" in w["walk"] and "分" in w["walk"] for w in jingan_check["sampleWalks"])

        # 4. Test Modal, Favorites, SVG Map tab, and Red/Black tab
        ui_check = ws.eval_js("""(() => {
          // Open first restaurant's Order/Taxi modal
          document.querySelector('[data-open-modal]').click();
          const modalOpen = document.getElementById('orderModal').classList.contains('open');
          const taxiTitle = document.getElementById('modalShopTitle')?.textContent?.trim();
          document.getElementById('btnCloseModal').click();

          // Toggle favorite
          document.querySelector('[data-fav-toggle]').click();
          const favCount = document.getElementById('favCountBadge').textContent;

          // Switch to Map tab
          document.querySelector('.tab-btn[data-tab="map"]').click();
          const pinsCount = document.querySelectorAll('#layerPins .rest-pin').length;

          // Switch to Red/Black tab
          document.querySelector('.tab-btn[data-tab="redblack"]').click();
          const rbSections = document.querySelectorAll('#panelRedBlack .rb-section').length;

          // Switch back to Nearby and test reservation filter chip
          document.querySelector('.tab-btn[data-tab="nearby"]').click();
          const resChip = document.querySelector('#reservationChips .chip[data-val="REQUIRED"]');
          resChip.click();
          const resCountText = document.getElementById('resultCountText').textContent;
          const resBadges = document.querySelectorAll('#nearbyList .res-badge').length;

          return { modalOpen, taxiTitle, favCount, pinsCount, rbSections, resCountText, resBadges };
        })()""")
        print(f"[CHECK 4] Interactive Tabs & Modal: {ui_check}")
        assert ui_check["modalOpen"] is True and bool(ui_check["taxiTitle"])
        assert ui_check["favCount"] == "1"
        assert ui_check["pinsCount"] > 0
        assert ui_check["rbSections"] == 5
        assert ui_check["resBadges"] > 0, "Expected .res-badge tags when filtering by 需预约"

        ws.drain_events(0.8)

        # 5. Inspect CDP console errors, exceptions, and HTTP status codes
        console_errors = []
        network_404s = []
        for ev in ws.events:
            m = ev.get("method")
            p = ev.get("params") or {}
            if m == "Runtime.exceptionThrown":
                console_errors.append(str(p))
            elif m == "Runtime.consoleAPICalled" and p.get("type") == "error":
                console_errors.append(str(p.get("args")))
            elif m == "Log.entryAdded" and (p.get("entry") or {}).get("level") == "error":
                entry = p.get("entry") or {}
                if "favicon.ico" not in (entry.get("url") or ""):
                    console_errors.append(str(entry))
            elif m == "Network.responseReceived":
                resp = p.get("response") or {}
                if resp.get("status", 200) >= 400 and "favicon.ico" not in (resp.get("url") or ""):
                    network_404s.append((resp.get("status"), resp.get("url")))

        bad_http = [(path, code) for path, code in RecordingHandler.requests_log if code not in (200, 304) and "favicon.ico" not in path]
        print(f"[CHECK 5] Server requests logged: {RecordingHandler.requests_log}")
        print(f"[CHECK 5] Console errors: {len(console_errors)}, Network >=400: {len(network_404s)}, Non-200 server hits: {len(bad_http)}")

        assert not console_errors, f"Console errors found: {console_errors}"
        assert not network_404s, f"Network errors found: {network_404s}"
        assert not bad_http, f"Server non-200 responses: {bad_http}"

        print("\n✅ ALL HEADLESS CHROME IPHONE (390x844) & PWA CHECKS PASSED!")

    finally:
        if ws:
            ws.close()
        if proc:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        httpd.shutdown()
        httpd.server_close()
        shutil.rmtree(tmp_profile, ignore_errors=True)
        print("[CLEANUP] Closed headless Chrome and shut down temporary HTTP server.")


if __name__ == "__main__":
    main()
