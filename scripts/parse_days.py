import re, html, json, glob, gzip, os, sys
from config import DOUSEI_DIR

def strip(s):
    t = html.unescape(re.sub(r'<[^>]+>', '\n', s))
    return [x.strip() for x in t.split('\n') if x.strip()]

def hhmm_to_min(s):
    m = re.fullmatch(r'(\d{1,2}):(\d{2})', s or '')
    return int(m.group(1)) * 60 + int(m.group(2)) if m else None


MIN_PER_DAY = 24 * 60
ALLOC_NOTE = '※ 時間配分・居所滞在は記録に基づく推定値'
SEG_RE = re.compile(r'(?:aria-label="(\d{1,2}:\d{2})[–-](\d{1,2}:\d{2}) ([^："]+)：([^"]*)"[^>]*)?style="width:([\d.]+)%;background:var\(--color-([a-z-]+)\)')
LEGEND_RE = re.compile(r'background:var\(--color-([a-z-]+)\)"></span>([^<]+)</span>')

def parse_allocation(h):
    """The day's 24h bar: each segment is a (start, end, category, label) interval; width% of 24h gives minutes."""
    note = h.find(ALLOC_NOTE)
    section = h[:note] if note > 0 else ''
    legend = {var: name.strip() for var, name in LEGEND_RE.findall(h)}
    intervals, alloc = [], {}
    for start, end, cat, label, pct, var in SEG_RE.findall(section):
        minutes = round(float(pct) * MIN_PER_DAY / 100)
        category = cat or legend.get(var, var)
        intervals.append({"start": start or None, "end": end or None, "category": category, "label": html.unescape(label) if label else None, "minutes": minutes})
        alloc[category] = alloc.get(category, 0) + minutes
    return intervals, alloc

def parse(path):
    opener = gzip.open if str(path).endswith('.gz') else open
    with opener(path, 'rt', encoding='utf-8', errors='replace') as f:
        h = f.read()
    date = os.path.basename(path)[:10]
    t = re.search(r'<title>(\d{4})年(\d{1,2})月(\d{1,2})日の首相動静（([^）]+)）', h)
    if not t:
        return {"date": date, "missing": True, "title": (re.search(r'<title>([^<]*)', h) or [None, ''])[1]}
    pm = t.group(4)
    metrics = {}
    for lab, val in re.findall(r'metric-cell"><div[^>]*>([^<]+)</div><div[^>]*>([^<]+)', h):
        metrics[lab.strip()] = val.strip()
    src = re.search(r'出典：([^<]+)', h)
    summ = re.search(r'<p class="mt-5 text-\[11px\] text-dim"[^>]*>([^<]*)</p>', h)
    # timeline section
    a = h.find('首相動静の時系列'); b = h.find('首相動静の週間推移')
    sec = h[a:b] if a > 0 and b > a else ''
    rows = re.split(r'<div class="grid items-start gap-x-\[14px\][^>]*>', sec)[1:]
    events = []
    for r in rows:
        parts = strip(r)
        if not parts: continue
        time = parts[0] if re.fullmatch(r'\d{1,2}:\d{2}|—', parts[0]) else None
        rest = [p for p in parts[1:] if p != '·']
        events.append({"time": None if time in (None, '—') else time,
                       "label": rest[0] if rest else '',
                       "place": rest[1] if len(rest) > 1 else '',
                       "category": rest[2] if len(rest) > 2 else ''})
    intervals, alloc = parse_allocation(h)
    timed = [hhmm_to_min(e["time"]) for e in events if e["time"]]
    span = (max(timed) - min(timed)) if timed else 0
    return {
        "date": date, "pm": pm, "source": src.group(1).strip() if src else None,
        "work_min": hhmm_to_min(metrics.get('公務の合計時間')),
        "residence_min": hhmm_to_min(metrics.get('居所での滞在時間')),
        "meetings": int(re.sub(r'\D', '', metrics.get('面会・会談件数', '0')) or 0),
        "first_work": metrics.get('最初の公務'),
        "summary": summ.group(1).strip() if summ else '',
        "span_min": span, "n_events": len(events), "n_timed": len(timed),
        "events": events, "intervals": intervals, "alloc_min": alloc,
    }


def load_dousei(pm_id):
    """dousei/<pm>/*.json を日付順に読む。"""
    return [json.load(open(f, encoding="utf-8")) for f in sorted(glob.glob(str(DOUSEI_DIR / pm_id / "*.json")))]


if __name__ == '__main__':
    print(json.dumps(parse(sys.argv[1]), ensure_ascii=False, indent=1)[:3000])
