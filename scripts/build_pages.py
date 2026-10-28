"""dousei/ と parsed/ から site/ の HTML を生成する。

  python3 build_pages.py index    # site/index.html（歴代 1 年目の草だけ。時系列は埋めない）
  python3 build_pages.py multi    # site/pm-first-year-grass.html（歴代 1 年目、比較表と commit log つき）
"""
import datetime, json, re, sys
from config import PARSED_DIR, SITE_DIR, TEMPLATE_DIR
from parse_days import load_dousei


def compact_day(d):
    return {"d": d["date"], "m": d["work_min"] or 0, "k": d["meetings"], "f": d["first_work"], "src": d["source"],
            "e": [[e["time"] or "", e["label"], e["category"]] for e in d["events"]]}


def render(template_name, payload, out_name):
    text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    page = (TEMPLATE_DIR / template_name).read_text(encoding="utf-8").replace("__DATA__", text)
    SITE_DIR.mkdir(exist_ok=True)
    (SITE_DIR / out_name).write_text(page, encoding="utf-8")
    print("wrote", SITE_DIR / out_name, len(page.encode("utf-8")), "bytes")


def with_data(pms):
    """収録が 1 日もない総理（鳩山）はページに出さない。"""
    return [p for p in pms if p["days"]]


FLIGHT = re.compile(r"空港|政府専用機|チャーター機")
MIN_PER_DAY = 24 * 60


def is_abroad(d):
    """外遊で終日扱いの日、または外遊・空港利用の行がある日。「最も長い国内の一日」から除く。"""
    return (d["work_min"] or 0) >= MIN_PER_DAY or any(e["category"] == "外遊" or FLIGHT.search(e["label"] or "") for e in d["events"])


def lean_day(d):
    return {"d": d["date"], "m": d["work_min"] or 0, "k": d["meetings"], "f": d["first_work"], "a": 1 if is_abroad(d) else 0}


def build_index():
    pms = with_data(json.load(open(PARSED_DIR / "pms-first-year.json")))
    render("vue_index_template.html", {
        "pms": [{"id": p["id"], "name": p["name"], "party": p["party"], "start": p["start"], "fyEnd": p["fy_end"], "note": p["note"],
                 "days": [lean_day(d) for d in p["days"]]} for p in pms],
        "generated": datetime.date.today().isoformat(),
    }, "index.html")


def build_multi():
    pms = with_data(json.load(open(PARSED_DIR / "pms-first-year.json")))
    render("vue_multi_template.html", {
        "pms": [{"id": p["id"], "name": p["name"], "party": p["party"], "start": p["start"], "fyEnd": p["fy_end"], "note": p["note"],
                 "days": [compact_day(d) for d in p["days"]]} for p in pms],
        "generated": datetime.date.today().isoformat(),
    }, "pm-first-year-grass.html")


if __name__ == "__main__":
    {"index": build_index, "multi": build_multi}[sys.argv[1]]()
