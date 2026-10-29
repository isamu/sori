"""草の色を変える出来事。日付の出典は各項目の source。選挙は公示日と投開票日、災害は発生日だけ持ち、窓の長さは by_year が決める。"""

KINDS = [{"id": "election", "label": "選挙"}, {"id": "quake", "label": "地震"}, {"id": "rain", "label": "豪雨"}]

WIKI = "https://ja.wikipedia.org/wiki/"
JMA_QUAKES = "https://www.data.jma.go.jp/eqev/data/higai/higai1996-new.html"


def election(name, start, end, page):
    return {"kind": "election", "name": name, "start": start, "end": end, "source": WIKI + page}


def quake(name, start, source=JMA_QUAKES, last=None):
    return {"kind": "quake", "name": name, "start": start, "last": last or start, "source": source}


def rain(name, start, source):
    return {"kind": "rain", "name": name, "start": start, "last": start, "source": source}


EVENTS = [
    election("第46回衆院選", "2012-12-04", "2012-12-16", "第46回衆議院議員総選挙"),
    election("第23回参院選", "2013-07-04", "2013-07-21", "第23回参議院議員通常選挙"),
    election("第47回衆院選", "2014-12-02", "2014-12-14", "第47回衆議院議員総選挙"),
    election("第24回参院選", "2016-06-22", "2016-07-10", "第24回参議院議員通常選挙"),
    election("第48回衆院選", "2017-10-10", "2017-10-22", "第48回衆議院議員総選挙"),
    election("第25回参院選", "2019-07-04", "2019-07-21", "第25回参議院議員通常選挙"),
    election("第49回衆院選", "2021-10-19", "2021-10-31", "第49回衆議院議員総選挙"),
    election("第26回参院選", "2022-06-22", "2022-07-10", "第26回参議院議員通常選挙"),
    election("第50回衆院選", "2024-10-15", "2024-10-27", "第50回衆議院議員総選挙"),
    election("第27回参院選", "2025-07-03", "2025-07-20", "第27回参議院議員通常選挙"),
    election("第51回衆院選", "2026-01-27", "2026-02-08", "第51回衆議院議員総選挙"),
    quake("東日本大震災（東北地方太平洋沖地震）", "2011-03-11"),
    quake("平成28年熊本地震", "2016-04-14", last="2016-04-16"),
    quake("平成30年北海道胆振東部地震", "2018-09-06"),
    quake("令和6年能登半島地震", "2024-01-01"),
    quake("令和8年熊本地震", "2026-07-28", source="https://www.jma.go.jp/jma/press/2607/28a/202607281730.html"),
    rain("平成30年7月豪雨（西日本豪雨）", "2018-07-06", "https://www.data.jma.go.jp/obd/stats/data/bosai/report/2018/20180713/jyun_sokuji20180628-0708.pdf"),
    rain("令和元年東日本台風（台風第19号）", "2019-10-12", "https://www.jma.go.jp/jma/kishou/know/jirei/sokuhou/R011012.pdf"),
    rain("令和2年7月豪雨", "2020-07-04", "https://www.jma.go.jp/jma/kishou/know/jirei/sokuhou/R020704.pdf"),
    rain("熊本の大雨（令和7年8月、大雨特別警報）", "2025-08-11", "https://www.jma.go.jp/jma/kishou/know/jirei/sokuhou/R070811.pdf"),
    rain("令和8年8月千葉豪雨", "2026-08-13", "https://www.data.jma.go.jp/stats/data/bosai/report/2026/20260916/20260916.html"),
]
