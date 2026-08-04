"""Собирает самодостаточный dist/rezerv-dashboard.html (данные + логотип + иконка внутри).
Запуск: python -m dashboard.pipeline.publish"""
import base64, json, re, shutil
from . import config as C

WEB = C.DASH / "web"
BUILD = C.DASH / "build" / "data.json"
DIST = C.DASH / "dist" / "rezerv-dashboard.html"
FAV = ("<link rel=\"icon\" href=\"data:image/svg+xml,"
       "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'>"
       "<text y='.9em' font-size='88'>%F0%9F%92%B0</text></svg>\">")


def build_html():
    html = (WEB / "index.html").read_text(encoding="utf-8")
    data = BUILD.read_text(encoding="utf-8")
    logo = base64.b64encode((WEB / "assets" / "logo.png").read_bytes()).decode()
    html = html.replace('src="assets/logo.png"', f'src="data:image/png;base64,{logo}"')
    html = html.replace("</head>", FAV + "\n</head>", 1)
    html = html.replace("fetch('../build/data.json').then(r=>r.json())", "Promise.resolve(window.__DATA__)")
    html = html.replace("<body>", "<body>\n<script>window.__DATA__=" + data + ";</script>", 1)
    DIST.parent.mkdir(parents=True, exist_ok=True)
    DIST.write_text(html, encoding="utf-8")
    shutil.copy(WEB / "apple-touch-icon.png", DIST.parent / "apple-touch-icon.png")  # иконка для экрана «Домой»
    # метка свежести: страница на телефоне спрашивает этот файл мимо кэша и
    # перезагружается, если сервер отдал более свежую дату (см. checkFresh в index.html)
    stamp = json.loads(data).get("updated_at", "")
    (DIST.parent / "stamp.txt").write_text(stamp, encoding="utf-8")
    shutil.copy(WEB / "sw.js", DIST.parent / "sw.js")  # «сначала сеть» для иконки на экране «Домой»
    return len(html)


if __name__ == "__main__":
    n = build_html()
    print(f"OK -> {DIST}  ({n//1024} КБ)")
