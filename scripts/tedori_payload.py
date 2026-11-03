"""zaisei/ の CSV の行から、記事ページ「手取りが激減、は本当？」に埋めるデータを作る純粋関数。"""

AVERAGE_CLASS = "avg"
INDEX_YEAR = 2000
# 財務省の国民負担率の表は、直近 2 年度が実績見込みと見通し
BURDEN_ESTIMATE_YEARS = 2
PCT_DECIMALS = 1


def by_key(rows, key):
    return {int(r[key]): r for r in rows}


def number(cell):
    return float(cell) if cell not in (None, "") else None


def payslip(household_rows):
    """勤労者世帯の平均で、実収入のうち税と社会保険料に引かれる割合と手取り（円/月）。"""
    cells = {}
    for r in household_rows:
        if r["income_class"] == AVERAGE_CLASS:
            cells.setdefault(int(r["year"]), {})[r["item"]] = float(r["yen_per_month"])
    years = [y for y in sorted(cells) if {"実収入", "可処分所得", "直接税", "社会保険料"} <= cells[y].keys()]
    return [payslip_year(y, cells[y]) for y in years]


def payslip_year(year, cell):
    income, deducted = cell["実収入"], cell["実収入"] - cell["可処分所得"]
    tax, insurance = cell["直接税"], cell["社会保険料"]
    return {"year": year, "takehome_yen": cell["可処分所得"], "deducted_pct": pct(deducted, income),
            "tax": pct(tax, income), "insurance": pct(insurance, income), "other": pct(max(deducted - tax - insurance, 0), income)}


def pct(part, whole):
    return round(100 * part / whole, PCT_DECIMALS) if whole else None


def burden(burden_rows, first_year):
    """国民負担率の内訳と、財政赤字を足した潜在的国民負担率（対国民所得比、%）。"""
    rows = [r for r in sorted(burden_rows, key=lambda r: int(r["fiscal_year"])) if int(r["fiscal_year"]) >= first_year]
    estimate_from = len(rows) - BURDEN_ESTIMATE_YEARS
    return [{"year": int(r["fiscal_year"]), "estimate": i >= estimate_from,
             "national_tax": float(r["national_tax_pct"]), "local_tax": float(r["local_tax_pct"]),
             "insurance": float(r["social_security_burden_pct"]), "deficit": max(float(r["fiscal_deficit_pct"]), 0),
             "national_burden": float(r["national_burden_pct"]), "potential_burden": float(r["potential_burden_pct"])}
            for i, r in enumerate(rows)]


def national_income(burden_rows, first_year):
    """負担率の分母の国民所得（兆円）の、最初の年度と実績の最後の年度。"""
    rows = burden(burden_rows, first_year)
    actual = [r for r in rows if not r["estimate"]]
    if not actual:
        return None
    income = {int(r["fiscal_year"]): float(r["national_income_trillion_yen"]) for r in burden_rows}
    return {"first": {"year": actual[0]["year"], "trillion": income[actual[0]["year"]]},
            "last": {"year": actual[-1]["year"], "trillion": income[actual[-1]["year"]]}}


def hidden(burden_rows, contribution_rows, consumption_rows):
    """給料明細に出ない負担: 消費税（国＋地方）と会社負担の社会保険料、それと働く人などが払う社会保険料（対国民所得比、%）。"""
    income = {y: float(r["national_income_trillion_yen"]) for y, r in by_key(burden_rows, "fiscal_year").items()}
    contributions = by_key(contribution_rows, "fiscal_year")
    taxes = by_key(consumption_rows, "fiscal_year")
    years = sorted(y for y in income.keys() & contributions.keys() & taxes.keys() if number(taxes[y]["local_100m_yen"]))
    return [{"year": y,
             "consumption_tax": pct((float(taxes[y]["national_100m_yen"]) + float(taxes[y]["local_100m_yen"])) / 1e4, income[y]),
             "employer": pct(float(contributions[y]["employer_billion_yen"]) / 1e3, income[y]),
             "household": pct(float(contributions[y]["household_billion_yen"]) / 1e3, income[y])} for y in years]


def real_income(slip, price_rows):
    """手取り（名目）、物価を差し引いた手取り、実質賃金を、2000 年＝100 の指数にそろえる。"""
    prices = by_key(price_rows, "year")
    takehome = {s["year"]: s["takehome_yen"] for s in slip}
    years = sorted(y for y in takehome.keys() & prices.keys() if number(prices[y]["real_wage_index_2020base"]))
    if INDEX_YEAR not in years:
        return []
    cpi = {y: float(prices[y]["cpi_2020base"]) for y in years}
    wage = {y: float(prices[y]["real_wage_index_2020base"]) for y in years}
    real = {y: takehome[y] / cpi[y] for y in years}

    def index(series, y):
        return round(100 * series[y] / series[INDEX_YEAR], PCT_DECIMALS)

    food = {y: float(prices[y]["cpi_food_2020base"]) for y in years}
    energy = {y: float(prices[y]["cpi_energy_2020base"]) for y in years}
    return [{"year": y, "nominal": index(takehome, y), "real": index(real, y), "wage": index(wage, y),
             "cpi": index(cpi, y), "food": index(food, y), "energy": index(energy, y)} for y in years]


DECILES = [f"D{i:02d}" for i in range(1, 11)]
EARNERS = [("head", "世帯主収入"), ("spouse", "世帯主の配偶者の収入"), ("others", "他の世帯員収入")]
MAN_YEN = 10000


def household_cells(household_rows):
    cells = {}
    for r in household_rows:
        cells.setdefault((int(r["year"]), r["income_class"]), {})[r["item"]] = float(r["yen_per_month"])
    return cells


def cpi_by_year(price_rows):
    return {y: float(r["cpi_2020base"]) for y, r in by_key(price_rows, "year").items()}


def earners(household_rows, price_rows):
    """勤労者世帯の平均の稼ぎ（世帯主・配偶者・ほかの家族）を、2020 年の物価にそろえた万円/月で。"""
    cells, cpi = household_cells(household_rows), cpi_by_year(price_rows)
    years = sorted(y for (y, c), v in cells.items() if c == AVERAGE_CLASS and y in cpi and all(item in v for _, item in EARNERS))
    return [{"year": y, **{key: round(cells[(y, AVERAGE_CLASS)][item] / cpi[y] * 100 / MAN_YEN, PCT_DECIMALS) for key, item in EARNERS}}
            for y in years]


def decile_changes(household_rows, price_rows):
    """年収 10 段階それぞれの、最初の年から最新の年までの、物価を差し引いた手取りの変化（%）。"""
    cells, cpi = household_cells(household_rows), cpi_by_year(price_rows)
    years = sorted({y for (y, c) in cells if c == DECILES[0] and y in cpi})
    if len(years) < 2:
        return None
    first, last = years[0], years[-1]

    def real(y, d):
        return cells[(y, d)]["可処分所得"] / cpi[y]

    return {"first": first, "last": last, "classes": [
        {"id": d, "income_first": cells[(first, d)].get("年間収入_万円"), "income_last": cells[(last, d)].get("年間収入_万円"),
         "real_change": round(100 * (real(last, d) / real(first, d) - 1), PCT_DECIMALS)} for d in DECILES]}


AGE_CLASSES = ["-29", "30-39", "40-49", "50-59", "60-69", "70-"]
WORKING_AGE_CLASSES = ["30-39", "40-49", "50-59", "60-69"]
AGE_VALUES = {"head": "世帯主収入", "spouse": "世帯主の配偶者の収入", "takehome": "可処分所得"}
SHARE_ITEM = "世帯数分布"


def age_cells(age_rows):
    cells = {}
    for r in age_rows:
        cells.setdefault((int(r["year"]), r["age_class"]), {})[r["item"]] = float(r["value"])
    return cells


def real_change(cells, cpi, first, last, cls, item):
    before, after = cells[(first, cls)][item] / cpi[first], cells[(last, cls)][item] / cpi[last]
    return round(100 * (after / before - 1), PCT_DECIMALS) + 0.0


def reweighted_change(cells, cpi, first, last, item):
    """最新年の年齢階級ごとの値を、最初の年の世帯の年齢構成で平均し直したときの実質の変化（%）。"""
    shares = {c: cells[(first, c)][SHARE_ITEM] for c in AGE_CLASSES}

    def average(y):
        return sum(shares[c] * cells[(y, c)][item] for c in AGE_CLASSES) / sum(shares.values())

    return round(100 * (average(last) / cpi[last] / (average(first) / cpi[first]) - 1), PCT_DECIMALS)


def age_changes(age_rows, price_rows):
    """世帯主の年齢をそろえた、最初の年から最新の年までの実質の変化。"""
    cells, cpi = age_cells(age_rows), cpi_by_year(price_rows)
    years = sorted({y for (y, c) in cells if c == AVERAGE_CLASS and y in cpi})
    if len(years) < 2:
        return None
    first, last = years[0], years[-1]

    def change(cls):
        return {key: real_change(cells, cpi, first, last, cls, item) for key, item in AGE_VALUES.items()}

    return {"first": first, "last": last,
            "classes": [{"id": c, "age_first": cells[(first, c)]["世帯主の年齢"], **change(c)} for c in WORKING_AGE_CLASSES],
            "average": change(AVERAGE_CLASS),
            "reweighted": {key: reweighted_change(cells, cpi, first, last, item) for key, item in AGE_VALUES.items()},
            "age": {"first": cells[(first, AVERAGE_CLASS)]["世帯主の年齢"], "last": cells[(last, AVERAGE_CLASS)]["世帯主の年齢"]},
            "sixties_share": {key: round(sum(cells[(y, c)][SHARE_ITEM] for c in ("60-69", "70-")) / 100, PCT_DECIMALS)
                              for key, y in (("first", first), ("last", last))}}


def tedori_payload(household_rows, burden_rows, contribution_rows, consumption_rows, price_rows, age_rows=()):
    slip = payslip(household_rows)
    first_year = slip[0]["year"] if slip else 0
    return {"payslip": slip, "burden": burden(burden_rows, first_year),
            "hidden": hidden(burden_rows, contribution_rows, consumption_rows),
            "nationalIncome": national_income(burden_rows, first_year),
            "real": real_income(slip, price_rows), "indexYear": INDEX_YEAR,
            "earners": earners(household_rows, price_rows), "deciles": decile_changes(household_rows, price_rows),
            "ages": age_changes(age_rows, price_rows)}
