"""zaisei/ の CSV の行から、ページ「税と保険料の 100 円」に埋めるデータを作る純粋関数。"""
import math
from collections import defaultdict

CELLS = 100
NEW_BASE = "2020年基準"
OLD_BASE = "2000年基準"
LINK_YEAR = 2005

# (key, ページの名前, 足す COFOG の分類, 元の分類名)。並びはマスを塗る順
SPEND_GROUPS = [
    ("welfare", "年金・介護・子育てなど", ["10"], "社会保護"),
    ("health", "医療", ["7"], "保健"),
    ("economy", "道路・産業の支援", ["4"], "経済業務"),
    ("education", "教育", ["9"], "教育"),
    ("admin", "役所の仕事", ["1"], "一般公共サービス"),
    ("interest", "借金の利子", ["interest"], "利払い（一般政府の支払利子）"),
    ("safety", "警察・消防・裁判", ["3"], "公共の秩序・安全"),
    ("defense", "防衛", ["2"], "防衛"),
    ("environment", "ごみ・下水・環境", ["5"], "環境保護"),
    ("housing", "住宅・まちづくり", ["6"], "住宅・地域アメニティ"),
    ("culture", "文化・スポーツ", ["8"], "娯楽・文化・宗教"),
]

# (key, ページの名前, 足す家計調査の項目)。手取りを最後に置く
PAY_GROUPS = [
    ("pension", "年金の保険料", ["公的年金保険料"]),
    ("medical", "医療・介護の保険料", ["健康保険料", "介護保険料", "他の社会保険料"]),
    ("resident", "住民税", ["個人住民税"]),
    ("income", "所得税", ["勤労所得税"]),
    ("other", "その他の税など", ["他の税", "他の非消費支出"]),
    ("takehome", "手取り", ["可処分所得"]),
]
DECILES = [f"D{i:02d}" for i in range(1, 11)]
GRID_DECILE = "D05"


SHARE_DECIMALS = 2


def positive_parts(amounts):
    """負の値（家計の「その他」や在庫の増減）は 0 とみなす。"""
    positive = {k: max(v, 0) for k, v in amounts.items()}
    return positive, sum(positive.values())


def shares_pct(amounts):
    """金額の比を % にする（グラフの棒の高さ用）。"""
    positive, total = positive_parts(amounts)
    return {k: round(100 * v / total, SHARE_DECIMALS) if total > 0 else 0 for k, v in positive.items()}


def to_hundred(amounts):
    """金額の比を、合計がちょうど 100 になる整数のマス数に丸める（最大剰余法）。"""
    positive, total = positive_parts(amounts)
    if total <= 0:
        return {k: 0 for k in amounts}
    exact = {k: CELLS * v / total for k, v in positive.items()}
    cells = {k: math.floor(x) for k, x in exact.items()}
    order = sorted(exact, key=lambda k: (-(exact[k] - cells[k]), list(amounts).index(k)))
    for k in order[: CELLS - sum(cells.values())]:
        cells[k] += 1
    return cells


def spending_tables(rows):
    """CSV の行 → {(基準, 年度): {分類: 10 億円}}。"""
    tables = defaultdict(dict)
    for r in rows:
        tables[(r["sna_base"], int(r["fiscal_year"]))][r["cofog_code"]] = float(r["billion_yen"])
    return tables


def link_ratios(tables):
    """古い基準の値に掛けて今の基準に合わせる、分類ごとの比（重なる最初の年度で取る）。"""
    old, new = tables[(OLD_BASE, LINK_YEAR)], tables[(NEW_BASE, LINK_YEAR)]
    return {code: new[code] / old[code] for code in old if old[code]}


def spending_amounts(tables, year, ratios):
    """年度の使い道ごとの金額（10 億円）。2005 年度より前は古い基準を比でつなぐ。利払いはどの年も今の基準。"""
    new = tables.get((NEW_BASE, year), {})
    old = tables.get((OLD_BASE, year), {})
    use_old = year < LINK_YEAR

    def value(code):
        if code == "interest" or not use_old:
            return new[code]
        return old[code] * ratios[code]

    return {key: sum(value(c) for c in codes) for key, _, codes, _ in SPEND_GROUPS}


def spending_years(tables):
    """利払いがあり、その年度に使う基準の表に 10 分類がそろう年度。"""
    def complete(year):
        base = OLD_BASE if year < LINK_YEAR else NEW_BASE
        return "interest" in tables.get((NEW_BASE, year), {}) and "10" in tables.get((base, year), {})

    return sorted(y for y in {y for _, y in tables} if complete(y))


def spending_payload(rows):
    tables = spending_tables(rows)
    ratios = link_ratios(tables)
    years = []
    for y in spending_years(tables):
        amounts = spending_amounts(tables, y, ratios)
        years.append({"year": y, "linked": y < LINK_YEAR, "total_trillion": round(sum(amounts.values()) / 1000, 1),
                      "cells": to_hundred(amounts), "shares": shares_pct(amounts)})
    groups = [{"key": k, "label": label, "source": src} for k, label, _, src in SPEND_GROUPS]
    return {"groups": groups, "years": years, "linkYear": LINK_YEAR}


def household_cells(rows):
    """CSV の行 → {(年, 階級): {項目: 円/月}}。"""
    cells = defaultdict(dict)
    for r in rows:
        cells[(int(r["year"]), r["income_class"])][r["item"]] = float(r["yen_per_month"])
    return cells


def pay_amounts(cell):
    return {key: sum(cell.get(item, 0.0) for item in items) for key, _, items in PAY_GROUPS}


def pay_years(cells):
    """十分位があり、社会保険料の内訳もそろう年。"""
    return sorted({y for (y, c), v in cells.items() if c == DECILES[0] and "公的年金保険料" in v})


def pay_class(cells, years, decile):
    return {"id": decile,
            "incomes": [cells[(y, decile)].get("年間収入_万円") for y in years],
            "shares": [shares_pct(pay_amounts(cells[(y, decile)])) for y in years]}


def pay_payload(rows):
    cells = household_cells(rows)
    years = pay_years(cells)
    groups = [{"key": k, "label": label} for k, label, _ in PAY_GROUPS]
    payload = {"groups": groups, "years": years, "classes": [pay_class(cells, years, d) for d in DECILES]}
    if years:
        middle = cells[(years[-1], GRID_DECILE)]
        payload["grid"] = {"year": years[-1], "income_man_yen": middle.get("年間収入_万円"), "cells": to_hundred(pay_amounts(middle))}
    return payload
