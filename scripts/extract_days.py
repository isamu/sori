"""raw/html/<pm>/*.html.gz（手元のみ、git 管理外）から動静の事実部分だけを dousei/<pm>/<date>.json に書く。

残すもの: 日付・総理・出典、公務/居所の分数、面会件数、最初の公務、時系列（時刻・内容・場所・分類）、
一日の時間配分の区間と分類別分数。官邸ログの要約文やページの見た目は残さない。
"""
import glob, json, sys
from config import DOUSEI_DIR, RAW_HTML_DIR
from parse_days import parse

FACT_FIELDS = ("date", "pm", "source", "work_min", "residence_min", "meetings", "first_work", "events", "intervals", "alloc_min")


def extract(day):
    return {k: day.get(k) for k in FACT_FIELDS}


def extract_pm(pm_id):
    out_dir = DOUSEI_DIR / pm_id
    out_dir.mkdir(parents=True, exist_ok=True)
    written = skipped = 0
    for path in sorted(glob.glob(str(RAW_HTML_DIR / pm_id / "*.html*"))):
        day = parse(path)
        if day.get("missing"):
            skipped += 1
            continue
        (out_dir / f"{day['date']}.json").write_text(json.dumps(extract(day), ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
        written += 1
    print(pm_id, "written", written, "skipped", skipped)


if __name__ == "__main__":
    extract_pm(sys.argv[1])
