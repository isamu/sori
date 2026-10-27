"""総理ごとに就任日から 365 日分を集め parsed/pms-first-year.json に書く。"""
import datetime, json, sys
from config import FIRST_YEAR_DAYS, PARSED_DIR, PMS
from parse_days import load_dousei


def first_year_end(start):
    return (datetime.date.fromisoformat(start) + datetime.timedelta(days=FIRST_YEAR_DAYS - 1)).isoformat()


def first_year(pm):
    fy_end = first_year_end(pm["start"])
    days, mismatch = [], []
    for d in load_dousei(pm["id"]):
        if d["date"] < pm["start"] or d["date"] > fy_end:
            continue
        if d["pm"].replace(" ", "") != pm["name"]:
            mismatch.append((d["date"], d["pm"]))
            continue
        days.append(d)
    print(pm["id"], pm["name"], pm["start"], "..", fy_end, "days", len(days), "mismatch", mismatch[:3], file=sys.stderr)
    return {**pm, "fy_end": fy_end, "days": days}


if __name__ == "__main__":
    out = [first_year(pm) for pm in PMS]
    PARSED_DIR.mkdir(exist_ok=True)
    json.dump(out, open(PARSED_DIR / "pms-first-year.json", "w"), ensure_ascii=False)
    print("wrote", PARSED_DIR / "pms-first-year.json", sum(len(p["days"]) for p in out), "days")
