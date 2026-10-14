#!/usr/bin/env python3
"""Regenerate the theme-picker screenshots in assets/themes/.

Every card in the picker is a real screenshot of the home page in that
theme, the same way omarchy.org's picker shows its desktop in each theme.
Re-run this whenever the home page changes noticeably.

    pip install playwright pillow && python3 -m playwright install chromium
    python3 tools/theme-previews.py              # all themes
    python3 tools/theme-previews.py nord white   # just these

Writes assets/themes/<id>.webp   (1600x900, desktop layout, 16:9)
   and assets/themes/<id>-m.webp (800x1000, phone layout, 4:5)
"""
import asyncio
import functools
import http.server
import io
import pathlib
import re
import sys
import threading

from PIL import Image
from playwright.async_api import async_playwright

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "assets" / "themes"
PAGE = "index.html"

SHOTS = {
    "":   dict(viewport={"width": 1280, "height": 720}, device_scale_factor=1.25),   # -> 1600x900
    "-m": dict(viewport={"width": 400, "height": 500}, device_scale_factor=2,         # -> 800x1000
               is_mobile=True, has_touch=True),
}


def theme_ids():
    js = (ROOT / "themes.js").read_text(encoding="utf-8")
    block = js[js.index("var THEMES"):js.index("];", js.index("var THEMES"))]
    return re.findall(r'id:\s*"([a-z0-9-]+)"', block)


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


def serve():
    handler = functools.partial(QuietHandler, directory=str(ROOT))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


async def main(only):
    ids = theme_ids()
    if only:
        unknown = sorted(set(only) - set(ids))
        if unknown:
            raise SystemExit(f"unknown theme(s): {', '.join(unknown)}")
        ids = [i for i in ids if i in only]
    OUT.mkdir(parents=True, exist_ok=True)
    httpd = serve()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/{PAGE}"
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        for suffix, opts in SHOTS.items():
            ctx = await browser.new_context(reduced_motion="reduce", **opts)
            for tid in ids:
                page = await ctx.new_page()
                await page.add_init_script(
                    "try{localStorage.setItem('ak-site-theme','%s');"
                    "localStorage.setItem('ak-theme-hint-seen','true')}catch(e){}" % tid)
                await page.goto(url, wait_until="networkidle")
                await page.evaluate("document.fonts.ready")
                await page.wait_for_timeout(250)
                png = await page.screenshot(type="png")
                await page.close()
                dest = OUT / f"{tid}{suffix}.webp"
                Image.open(io.BytesIO(png)).convert("RGB").save(dest, "WEBP", quality=80, method=6)
                print(f"  {dest.relative_to(ROOT)}  {dest.stat().st_size // 1024} KB")
            await ctx.close()
        await browser.close()
    httpd.shutdown()


if __name__ == "__main__":
    asyncio.run(main(set(sys.argv[1:])))
