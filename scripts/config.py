from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_HTML_DIR = ROOT / "raw" / "html"   # 手元のみ（.gitignore）
DOUSEI_DIR = ROOT / "dousei"           # 動静の事実部分だけ。git 管理するのはこちら
PARSED_DIR = ROOT / "parsed"
TEMPLATE_DIR = ROOT / "templates"
SITE_DIR = ROOT / "site"

DAY_URL = "https://www.kanteilog.com/day/{date}"
FIRST_YEAR_DAYS = 365
MIN_PAGE_BYTES = 50000

# 就任日は官邸ログの各総理ページと一致させてある。end は退任日（現職は None）。
PMS = [
    {"id": "hatoyama", "name": "鳩山由紀夫", "party": "民主党", "start": "2009-09-16", "end": "2010-06-08", "note": "官邸ログの収録は 2011-03-11 からのため、1 年目のデータなし"},
    {"id": "kan", "name": "菅直人", "party": "民主党", "start": "2010-06-08", "end": "2011-09-02", "note": "収録開始の 2011-03-11 以降のみ（1 年目のうち 89 日）"},
    {"id": "noda", "name": "野田佳彦", "party": "民主党", "start": "2011-09-02", "end": "2012-12-26", "note": ""},
    {"id": "abe", "name": "安倍晋三", "party": "自由民主党（第2次）", "start": "2012-12-26", "end": "2020-09-16", "note": ""},
    {"id": "suga", "name": "菅義偉", "party": "自由民主党", "start": "2020-09-16", "end": "2021-10-04", "note": ""},
    {"id": "kishida", "name": "岸田文雄", "party": "自由民主党", "start": "2021-10-04", "end": "2024-10-01", "note": ""},
    {"id": "ishiba", "name": "石破茂", "party": "自由民主党", "start": "2024-10-01", "end": "2025-10-21", "note": ""},
    {"id": "takaichi", "name": "高市早苗", "party": "自由民主党", "start": "2025-10-21", "end": None, "note": "現職。1 年目の 365 日分のみ表示"},
]
