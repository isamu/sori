"""dousei の日を暦年に振り分け、年ごとの有効範囲と在任区間を出す。ファイルも日付の現在値も引数で受け取る。"""
import datetime

COVERAGE_START = "2011-03-11"
ONE_DAY = datetime.timedelta(days=1)
DISASTER_WINDOW_DAYS = 7


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


def event_window(event):
    """選挙は公示日から投開票日まで。災害は発生日（震度 7 が複数日なら最後の日）から 1 週間。"""
    if "end" in event:
        return event["start"], event["end"]
    last = datetime.date.fromisoformat(event["last"])
    return event["start"], (last + (DISASTER_WINDOW_DAYS - 1) * ONE_DAY).isoformat()


def events_in(events, start, end):
    """[start, end] と重なる出来事を、その範囲に切り詰めて返す。"""
    windows = [(e, *event_window(e)) for e in events]
    return [{"kind": e["kind"], "name": e["name"], "start": max(s, start), "end": min(t, end)}
            for e, s, t in windows if s <= end and t >= start]


def event_list(events):
    """出来事ごとの窓と出典を新しい順に。ページ下部の一覧用。"""
    rows = [{"kind": e["kind"], "name": e["name"], "start": s, "end": t, "source": e["source"]}
            for e in events for s, t in [event_window(e)]]
    return sorted(rows, key=lambda r: r["start"], reverse=True)


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
