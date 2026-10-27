"""官邸ログの日別ページを raw/html/<pm>/<date>.html.gz に取り込む。

使い方:
  python3 fetch_days.py <pm-id> [start end]   # 省略時は就任日から 365 日
毎分 50 件以内に抑えること（2 本並行・毎分 150 件で 403 が返った）。
"""
import datetime, gzip, subprocess, sys, time
from config import DAY_URL, FIRST_YEAR_DAYS, MIN_PAGE_BYTES, PMS, RAW_HTML_DIR

PACE_S = 1.5
BACKOFF_S = 90
MAX_BACKOFFS = 20
BLOCKED_CODES = {"403", "429", "503"}


def day_path(pm_id, date):
    return RAW_HTML_DIR / pm_id / f"{date.isoformat()}.html.gz"


def already_fetched(path):
    if not path.exists():
        return False
    with gzip.open(path, "rb") as f:
        return len(f.read()) > MIN_PAGE_BYTES


def fetch_one(date):
    r = subprocess.run(["curl", "-s", "--compressed", "-A", "Mozilla/5.0", "-w", "\n%{http_code}", DAY_URL.format(date=date.isoformat())],
                       capture_output=True)
    body, _, code = r.stdout.rpartition(b"\n")
    return code.decode().strip(), body


def fetch_range(pm_id, start, end):
    (RAW_HTML_DIR / pm_id).mkdir(parents=True, exist_ok=True)
    backoffs = ok = 0
    date = start
    while date <= end:
        path = day_path(pm_id, date)
        if already_fetched(path):
            date += datetime.timedelta(days=1)
            continue
        code, body = fetch_one(date)
        if code == "200" and len(body) > MIN_PAGE_BYTES:
            with gzip.open(path, "wb") as f:
                f.write(body)
            ok += 1
            date += datetime.timedelta(days=1)
            time.sleep(PACE_S)
        elif code in BLOCKED_CODES:
            backoffs += 1
            print("BACKOFF", pm_id, date, code, "n=", backoffs, flush=True)
            if backoffs > MAX_BACKOFFS:
                sys.exit(2)
            time.sleep(BACKOFF_S)
        else:
            print("FAIL", pm_id, date, code, len(body), flush=True)
            date += datetime.timedelta(days=1)
            time.sleep(PACE_S)
    print("done", pm_id, "fetched", ok, flush=True)


if __name__ == "__main__":
    pm_id = sys.argv[1]
    pm = next(p for p in PMS if p["id"] == pm_id)
    start = datetime.date.fromisoformat(sys.argv[2] if len(sys.argv) > 2 else pm["start"])
    end = datetime.date.fromisoformat(sys.argv[3]) if len(sys.argv) > 3 else start + datetime.timedelta(days=FIRST_YEAR_DAYS - 1)
    fetch_range(pm_id, start, end)
