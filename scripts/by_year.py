"""dousei の日を暦年に振り分け、年ごとの有効範囲と在任区間を出す。ファイルも日付の現在値も引数で受け取る。"""
import datetime

COVERAGE_START = "2011-03-11"
ONE_DAY = datetime.timedelta(days=1)


def term_of(pm, until):
    """在任の初日と最終日（退任日の前日。現職は until、取得済みの最終日）。収録開始前に退任した総理は None。"""
    last = (datetime.date.fromisoformat(pm["end"]) - ONE_DAY).isoformat() if pm["end"] else until
    if last < COVERAGE_START:
        return None
    return {"id": pm["id"], "name": pm["name"], "party": pm["party"], "first": max(pm["start"], COVERAGE_START), "last": last}


def terms_of(pms, until):
    return [t for t in (term_of(pm, until) for pm in pms) if t]


def year_span(year, until):
    """その年の有効範囲。収録開始前と取得済みの最終日より後は含めない。"""
    return max(f"{year}-01-01", COVERAGE_START), min(f"{year}-12-31", until)


def years_covered(until):
    return list(range(int(COVERAGE_START[:4]), int(until[:4]) + 1))


def days_in_year(year):
    return datetime.date(year, 12, 31).timetuple().tm_yday


def segments_in(terms, start, end):
    """[start, end] と重なる在任区間を、その範囲に切り詰めて返す。"""
    return [{"id": t["id"], "name": t["name"], "start": max(t["first"], start), "end": min(t["last"], end)}
            for t in terms if t["first"] <= end and t["last"] >= start]


def group_by_year(days):
    """date キーで暦年ごとに日付順に並べる。同じ日付が重なったら先のものを残す。"""
    seen, by_year = set(), {}
    for d in sorted(days, key=lambda d: d["date"]):
        if d["date"] in seen:
            continue
        seen.add(d["date"])
        by_year.setdefault(int(d["date"][:4]), []).append(d)
    return by_year


def pm_id_of(name, terms):
    """日の記録にある総理名を config の id に寄せる。見つからなければ名前のまま。"""
    stripped = (name or "").replace(" ", "")
    return next((t["id"] for t in terms if t["name"] == stripped), stripped)
