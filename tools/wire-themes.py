#!/usr/bin/env python3
"""Wire the theme picker into every HTML page of the site.

Adds, per page (idempotent — already-wired pages only get their boot script
refreshed to the current version):
  1. the <head> boot script that applies the saved theme before first paint,
  2. <link rel="stylesheet" href="…/themes.css"> after the page's last stylesheet,
  3. the palette button in the header nav (just before the CV button),
  4. a "Theme: …" link in the footer,
  5. <script src="…/themes.js" defer> before </body>.

Usage:  python3 tools/wire-themes.py            (from the repo root)
        python3 tools/wire-themes.py path.html  (specific pages, e.g. a new post)
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent

# Runs in <head> before any CSS is applied, so the first paint is already in
# the right theme. Kept list-free on purpose: themes.js stores the scheme next
# to the theme, so adding a theme never requires touching the HTML pages.
# (Defaults for first-time visitors: Original on a light OS, Tokyo Night on a
# dark OS — keep in sync with DEFAULT_LIGHT / DEFAULT_DARK in themes.js.)
BOOT = (
    '<script>/* Theme boot: apply the saved theme before first paint (see themes.js) */'
    '(function(){var d=document.documentElement,t,s;'
    'try{t=localStorage.getItem("ak-site-theme");s=localStorage.getItem("ak-site-scheme")}catch(e){}'
    'if(!/^[a-z0-9-]{1,40}$/.test(t||"")){t=window.matchMedia&&matchMedia("(prefers-color-scheme: dark)").matches?"tokyo-night":"original";s=t=="original"?"light":"dark"}'
    'd.setAttribute("data-theme",t);d.setAttribute("data-scheme",s=="dark"?"dark":"light")})()</script>'
)
BOOT_RE = re.compile(r"<script>/\* Theme boot:.*?</script>", re.S)

PALETTE_PATH = ("M2 12C2 6.71457 6.51697 2.5 12 2.5C17.483 2.5 22 6.71457 22 12C22 13.8878 21.4937 15.1519 20.4345 15.8123C19.4491 16.4266 18.2002 16.3605 17.1496 16.2236C16.7813 16.1757 16.397 16.1121 16.0307 16.0515C15.8617 16.0235 15.6965 15.9962 15.5384 15.9713C15.0184 15.8895 14.5499 15.8295 14.1335 15.8234C13.298 15.8112 12.8925 16.0091 12.671 16.4526C12.539 16.7171 12.5395 17.0363 12.6858 17.4705C12.8149 17.8538 13.0214 18.2277 13.2435 18.63C13.2828 18.7012 13.3226 18.7734 13.3626 18.8465C13.4857 19.0721 13.6169 19.3217 13.7077 19.5624C13.7926 19.7875 13.8875 20.117 13.8161 20.466C13.7303 20.8858 13.4434 21.1713 13.0891 21.3241C12.7768 21.4588 12.3992 21.5 12 21.5C6.51697 21.5 2 17.2854 2 12ZM10.25 6.25C9.42157 6.25 8.75 6.92157 8.75 7.75C8.75 8.57843 9.42157 9.25 10.25 9.25C11.0784 9.25 11.75 8.57843 11.75 7.75C11.75 6.92157 11.0784 6.25 10.25 6.25ZM7.25 10.5C6.42157 10.5 5.75 11.1716 5.75 12C5.75 12.8284 6.42157 13.5 7.25 13.5C8.07843 13.5 8.75 12.8284 8.75 12C8.75 11.1716 8.07843 10.5 7.25 10.5ZM15.25 7.75C14.4216 7.75 13.75 8.42157 13.75 9.25C13.75 10.0784 14.4216 10.75 15.25 10.75C16.0784 10.75 16.75 10.0784 16.75 9.25C16.75 8.42157 16.0784 7.75 15.25 7.75Z")

HEADER_BTN = (
    '<button type="button" class="theme-btn" data-theme-picker aria-haspopup="dialog" '
    'aria-expanded="false" aria-label="Change website theme">'
    f'<svg viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" fill-rule="evenodd" clip-rule="evenodd" d="{PALETTE_PATH}"/></svg>'
    '<span class="theme-btn-tip" aria-hidden="true">Change website theme<kbd>T</kbd></span></button>'
)

FOOTER_BTN = (
    '<button type="button" class="footer-theme" data-theme-picker aria-haspopup="dialog" '
    'aria-expanded="false">Theme: <span data-theme-name>Original</span><kbd aria-hidden="true">T</kbd></button>'
)


def indent_before(text, pos):
    line_start = text.rfind("\n", 0, pos) + 1
    m = re.match(r"[ \t]*", text[line_start:pos])
    return m.group(0) if m else ""


def wire(path: pathlib.Path) -> str:
    html = path.read_text(encoding="utf-8")
    if "themes.js" in html:
        # Already wired: just refresh the boot script to the current version.
        refreshed = BOOT_RE.sub(lambda _m: BOOT, html, count=1)
        if refreshed == html:
            return "up to date"
        path.write_text(refreshed, encoding="utf-8")
        return "boot script refreshed"
    depth = len(path.relative_to(ROOT).parts) - 1
    prefix = "../" * depth

    # 1. boot script: before the first <link> in <head>
    head_end = html.index("</head>")
    first_link = html.index("<link", 0, head_end)
    ind = indent_before(html, first_link)
    html = html[:first_link] + BOOT + "\n" + ind + html[first_link:]

    # 2. themes.css after the last stylesheet in <head>
    head_end = html.index("</head>")
    sheets = [m for m in re.finditer(r"<link\b[^>]*stylesheet[^>]*>", html[:head_end])]
    last = sheets[-1]
    ind = indent_before(html, last.start())
    tag = f'<link rel="stylesheet" href="{prefix}themes.css">'
    html = html[:last.end()] + "\n" + ind + tag + html[last.end():]

    # 3. header palette button, right before the CV call-to-action
    cta = re.search(r'<a\b[^>]*class="nav-primary"[^>]*>', html)
    if not cta:
        raise SystemExit(f"{path}: no .nav-primary link found in the header")
    ind = indent_before(html, cta.start())
    html = html[:cta.start()] + HEADER_BTN + "\n" + ind + html[cta.start():]

    # 4. footer theme link
    foot = html.index("</footer>")
    ind = indent_before(html, foot)
    inner = ind + ("  " if ind else "")
    html = html[:foot].rstrip(" \t") + ("" if html[:foot].rstrip(" \t").endswith("\n") else "\n") \
        + inner + FOOTER_BTN + "\n" + ind + html[foot:]

    # 5. themes.js before </body>
    body_end = html.rindex("</body>")
    ind = indent_before(html, body_end)
    script_ind = ind + "  " if ind == "" and re.search(r"\n  <script", html) else ind
    html = html[:body_end].rstrip(" \t") + script_ind + f'<script src="{prefix}themes.js" defer></script>\n' + ind + html[body_end:]

    path.write_text(html, encoding="utf-8")
    return "wired"


def main(argv):
    if len(argv) > 1:
        pages = [pathlib.Path(p).resolve() for p in argv[1:]]
    else:
        pages = [ROOT / "index.html", *sorted((ROOT / "blog").glob("*.html")),
                 *sorted((ROOT / "blog" / "posts").glob("*.html"))]
    for page in pages:
        print(f"{page.relative_to(ROOT)}: {wire(page)}")


if __name__ == "__main__":
    main(sys.argv)
