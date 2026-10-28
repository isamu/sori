"""草を 2 列に並べた画像 site/og-grass.png（1200×630）を生成する。

公開中の OGP 画像 site/og.png はユーザーが用意したスクリーンショットなので上書きしない。

ヘッドレス Chrome で描画する。パスは環境変数 CHROME で差し替え可（既定は macOS の Google Chrome）。
"""
import datetime, json, os, subprocess, sys, tempfile
from config import PARSED_DIR, SITE_DIR
from build_pages import with_data

WIDTH, HEIGHT = 1200, 630
CELL_PX, GAP_PX = 7, 2
LEVELS = ["#ebedf0", "#9be9a8", "#40c463", "#30a14e", "#216e39"]
HOURS_PER_LEVEL, LEVEL_CAP_HOURS = 4, 16
CHROME = os.environ.get("CHROME", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")


def commits_of(work_min):
    """ページ側の Math.round と同じく .5 は切り上げる（Python の round は偶数丸め）。"""
    return int(work_min / 60 + 0.5)


def level(work_min):
    hours = commits_of(work_min)
    return 0 if hours == 0 else min(4, -(-min(hours, LEVEL_CAP_HOURS) // HOURS_PER_LEVEL))


def grass_cells(pm):
    by_date = {d["date"]: d for d in pm["days"]}
    start = datetime.date.fromisoformat(pm["start"]); end = datetime.date.fromisoformat(pm["fy_end"])
    first = start - datetime.timedelta(days=(start.weekday() + 1) % 7)
    cells = []
    day = first
    while day <= end:
        d = by_date.get(day.isoformat())
        if day < start: color = "transparent"
        elif d is None: color = "transparent"
        else: color = LEVELS[level(d["work_min"] or 0)]
        cells.append(f'<i style="background:{color}"></i>')
        day += datetime.timedelta(days=1)
    return "".join(cells)


def html(pms):
    pitch = CELL_PX + GAP_PX
    blocks = "".join(
        f'<div class="pm"><div class="name">{pm["name"]}<span>{pm["start"][:4]}年就任 · {sum(commits_of(d["work_min"] or 0) for d in pm["days"]):,} commits</span></div>'
        f'<div class="grid">{grass_cells(pm)}</div></div>' for pm in pms)
    return f'''<!DOCTYPE html><html lang="ja"><head><meta charset="utf-8"><style>
html,body{{margin:0;width:{WIDTH}px;height:{HEIGHT}px;background:#fff;color:#1f2328;font-family:-apple-system,BlinkMacSystemFont,"Hiragino Sans","Noto Sans JP",sans-serif;overflow:hidden}}
.wrap{{padding:44px 56px 0}}
h1{{margin:0;font-size:60px;font-weight:700;letter-spacing:.02em;line-height:1}}
.sub{{margin:14px 0 26px;font-size:21px;color:#59636e}}
.cols{{display:grid;grid-template-columns:1fr 1fr;column-gap:48px;row-gap:16px}}
.name{{font-size:15px;font-weight:600;margin-bottom:5px}}
.name span{{font-weight:400;color:#59636e;margin-left:8px;font-size:13px}}
.grid{{display:grid;grid-auto-flow:column;grid-template-rows:repeat(7,{CELL_PX}px);grid-auto-columns:{CELL_PX}px;gap:{GAP_PX}px}}
.grid i{{display:block;width:{CELL_PX}px;height:{CELL_PX}px;border-radius:1.5px}}
.legend{{position:absolute;right:56px;top:60px;font-size:14px;color:#59636e;display:flex;align-items:center;gap:3px}}
.legend i{{display:inline-block;width:12px;height:12px;border-radius:2px}}
</style></head><body><div class="wrap">
<h1>総理の１年</h1>
<div class="legend">0h {"".join(f'<i style="background:{c}"></i>' for c in LEVELS)} 16h+</div>
<div class="sub">歴代総理の就任 1 年目の首相動静を、公務 1 時間 = 1 commit で GitHub の草に</div>
<div class="cols">{blocks}</div>
</div></body></html>'''


if __name__ == "__main__":
    pms = with_data(json.load(open(PARSED_DIR / "pms-first-year.json")))
    with tempfile.TemporaryDirectory() as tmp:
        src = os.path.join(tmp, "og.html")
        open(src, "w", encoding="utf-8").write(html(pms))
        out = SITE_DIR / "og-grass.png"
        subprocess.run([CHROME, "--headless=new", "--disable-gpu", "--no-first-run", f"--user-data-dir={tmp}/profile", "--hide-scrollbars",
                        f"--window-size={WIDTH},{HEIGHT}", f"--screenshot={out}", f"file://{src}"], check=True, capture_output=True, timeout=120)
        print("wrote", out, os.path.getsize(out), "bytes")
