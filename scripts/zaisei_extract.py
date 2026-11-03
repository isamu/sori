"""raw/zaisei/ の元資料から zaisei/ の CSV を作る。先に zaisei_fetch.py を回すこと。

  spending_by_function.csv  一般政府（国・地方・社会保障基金）の機能別支出（COFOG）と利払い、10 億円
  burden_ratio.csv          国民負担率（対国民所得比）の推移、%
  household_by_income.csv   家計調査 勤労者世帯の年間収入階級別、円/月
  social_contributions.csv  社会保障負担の雇主（会社）と家計の分、10 億円、年度
  consumption_tax.csv       消費税収（国の一般会計と地方消費税）、億円、年度
  prices_wages.csv          消費者物価指数（総合）と実質賃金指数、2020 年＝100、暦年
"""
import csv, re, subprocess, unicodedata
from config import ROOT
from xlsx_read import read
from zaisei_fetch import CONV_DIR, RAW_DIR

OUT_DIR = ROOT / "zaisei"

COFOG_NAMES = {"1": "一般公共サービス", "2": "防衛", "3": "公共の秩序・安全", "4": "経済業務", "5": "環境保護",
               "6": "住宅・地域アメニティ", "7": "保健", "8": "娯楽・文化・宗教", "9": "教育", "10": "社会保護"}
# 最終消費支出・補助金・社会給付・その他の経常移転・総固定資本形成・在庫・資本移転（個別・集合の 2 列は最終消費支出の内訳なので足さない）
COFOG_SUM_COLS = [1, 4, 5, 6, 7, 8, 9]
OLD_BASE_YEARS = range(1995, 2010)
INTEREST_LABEL = "(参考)支払利子（ＦＩＳＩＭ調整前）"


def nfkc(s):
    return unicodedata.normalize("NFKC", str(s or ""))


def fiscal_year_of(cell):
    m = re.search(r"\((\d{4})\)", nfkc(cell))
    return int(m.group(1)) if m else None


def cofog_row_total(row):
    return round(sum(row[i] for i in COFOG_SUM_COLS if i < len(row) and isinstance(row[i], float)), 1)


def cofog_sheet(rows):
    year = next(y for r in rows[:4] for c in r if (y := fiscal_year_of(c)))
    found = {}
    for r in rows:
        label = nfkc(r[0]).strip()
        if m := re.match(r"(\d+)\.(\d+)\s*(.*)", label):
            found[f"{m.group(1)}.{m.group(2)}"] = (m.group(3).strip(), cofog_row_total(r))
        elif m := re.match(r"(\d+)\.", label):
            found[m.group(1)] = (COFOG_NAMES[m.group(1)], cofog_row_total(r))
    return year, found


def cofog(path, base, years, with_sub):
    out = []
    for _, rows in read(path):
        year, found = cofog_sheet(rows)
        if year not in years:
            continue
        for code, (name, value) in found.items():
            if "." in code and not with_sub:
                continue
            out.append([year, base, code, name, value])
    return out


def interest_paid(path):
    _, rows = next(iter(read(path)))
    years, sectors = rows[2], rows[3]
    total_col = {}
    for i, cell in enumerate(years):
        if year := fiscal_year_of(cell):
            total_col[year] = next(j for j in range(i, i + 5) if sectors[j] == "合計")
    row = next(r for r in rows if str(r[0] or "").startswith(INTEREST_LABEL))
    return [[y, "2020年基準", "interest", "利払い（一般政府、非連結、FISIM調整前）", row[j]] for y, j in total_col.items()]


def spending():
    rows = cofog(CONV_DIR / "cofog_2000base_2009.xlsx", "2000年基準", OLD_BASE_YEARS, with_sub=False)
    rows += cofog(RAW_DIR / "esri" / "cofog_2020base_2024.xlsx", "2020年基準", range(2005, 2100), with_sub=True)
    rows += [r for r in interest_paid(RAW_DIR / "esri" / "sector_2020base_2024.xlsx") if r[0] >= OLD_BASE_YEARS[0]]
    return ["fiscal_year", "sna_base", "cofog_code", "function", "billion_yen"], sorted(rows, key=lambda r: (r[0], r[1], r[2]))


BURDEN_HEADER = ["fiscal_year", "national_tax_pct", "general_account_tax_pct", "local_tax_pct", "tax_burden_pct",
                 "social_security_burden_pct", "national_burden_pct", "fiscal_deficit_pct", "potential_burden_pct",
                 "national_income_trillion_yen", "national_burden_pct_of_gdp", "gdp_trillion_yen"]
BURDEN_ROW = re.compile(r"((?:19|20)\d\d)\s+((?:-?[\d.]+\s+){10}-?[\d.]+)\s*$")


def burden():
    text = subprocess.run(["pdftotext", "-layout", str(RAW_DIR / "mof" / "burden_ratio_fy2026.pdf"), "-"],
                          capture_output=True, text=True, check=True).stdout
    rows = [[int(m.group(1))] + [float(v) for v in m.group(2).split()]
            for line in text.splitlines() if (m := BURDEN_ROW.search(line))]
    return BURDEN_HEADER, rows


KAKEI_ITEMS = ["年間収入_万円", "実収入", "勤め先収入", "非消費支出", "直接税", "勤労所得税", "個人住民税", "他の税",
               "社会保険料", "公的年金保険料", "健康保険料", "介護保険料", "他の社会保険料", "他の非消費支出",
               "可処分所得", "消費支出"]
DECILE_CLASSES = ["avg"] + [f"D{i:02d}" for i in range(1, 11)]
FURIGANA_TAIL = re.compile(r"[ァ-ヶー]+$")


def squeeze(s):
    return re.sub(r"[\s　]+", "", s or "")


def kakei_item(row):
    texts = [squeeze(c) for c in row[:13] if isinstance(c, str)]
    texts = [t for t in texts if re.search(r"[一-龥ぁ-んァ-ン]", t)]
    joined = "".join(texts)
    for t in texts:
        base = FURIGANA_TAIL.sub("", t)
        if base.startswith("年間収入") and "万円" in joined and "十分位" not in base:
            return "年間収入_万円"
        if base in KAKEI_ITEMS:
            return base
    return None


def worker_sheet(path):
    for _, rows in read(path):
        head = "".join(squeeze(str(c)) for r in rows[:8] for c in r if isinstance(c, str))
        if "勤労者世帯" in head:
            return rows
    raise ValueError(f"勤労者世帯のシートがない: {path}")


def decile_year(year, path):
    found = {}
    for r in worker_sheet(path):
        item = kakei_item(r) if len(r) >= 11 else None
        values = r[-11:]
        if item and item not in found and all(isinstance(v, (int, float)) for v in values):
            found[item] = values
    return [(year, cls, item, v) for item in KAKEI_ITEMS if item in found for cls, v in zip(DECILE_CLASSES, found[item])]


def decile_paths():
    paths = {}
    for directory in (RAW_DIR / "kakei", CONV_DIR):
        for p in sorted(directory.glob("kakei_decile_worker_*.xlsx")):
            paths.setdefault(int(p.stem.rsplit("_", 1)[1]), p)
    return dict(sorted(paths.items()))


# 統計局「日本の長期統計系列」表 20-7-c（農林漁家世帯を除く勤労者世帯、五分位）の列位置
QUINTILE_COLS = {"実収入": 6, "勤め先収入": 8, "消費支出": 20, "非消費支出": 36, "直接税": 37, "勤労所得税": 38,
                 "個人住民税": 39, "他の税": 40, "社会保険料": 41, "可処分所得": 45}
QUINTILE_YEARS = range(1995, 2000)


def quintile_class(row, year):
    if m := re.match(r"\s*(\d{4})", row[1]):
        return int(m.group(1)), "avg"
    q = re.match(r"第(\d)階級", nfkc(squeeze(str(row[0]))))
    return (year, f"Q{q.group(1)}") if q and year else (year, None)


def quintile_old(path):
    _, rows = next(iter(read(path)))
    header = [squeeze(str(c)) for c in rows[9]]
    assert "#直接税" in header[37] and "#社会保険料" in header[41], header[36:42]
    out, year = [], None
    for r in rows:
        if len(r) < 2 or not isinstance(r[1], str):
            continue
        year, cls = quintile_class(r, year)
        if cls is None or year not in QUINTILE_YEARS:
            continue
        out += [(year, cls, item, r[j]) for item, j in QUINTILE_COLS.items()]
        out.append((year, cls, "他の非消費支出", r[36] - r[37] - r[41]))
    return out


def household():
    rows = [row for year, path in decile_paths().items() for row in decile_year(year, path)]
    rows += quintile_old(CONV_DIR / "kakei_quintile_worker_nonfarm_1976-2007_20-07-c.xlsx")
    rows.sort(key=lambda x: (x[0], x[1], KAKEI_ITEMS.index(x[2])))
    return ["year", "income_class", "item", "yen_per_month"], [[y, c, i, int(v) if float(v).is_integer() else v] for y, c, i, v in rows]


def social_contributions():
    _, rows = next(iter(read(RAW_DIR / "esri" / "social_contributions_2020base_2024.xlsx")))
    total = next(r for r in rows if squeeze(str(r[0])) == "合計")
    out = [[year, total[j - 1], total[j], total[j + 1]] for j, c in enumerate(rows[2]) if (year := fiscal_year_of(c))]
    return ["fiscal_year", "employer_billion_yen", "household_billion_yen", "total_billion_yen"], out


ERA_START = {"昭和": 1925, "平成": 1988, "令和": 2018}
FIRST_LOCAL_CONSUMPTION_TAX_FULL_YEAR = 1998


def era_year(cell):
    m = re.match(r"(昭和|平成|令和)(\d+|元)年度", nfkc(squeeze(str(cell or ""))))
    return ERA_START[m.group(1)] + (1 if m.group(2) == "元" else int(m.group(2))) if m else None


def local_consumption_tax():
    """地方消費税（道府県の収入額、交付金を控除する前）、億円。"""
    out = {}
    for _, rows in read(RAW_DIR / "soumu" / "local_tax_by_item_r08.xlsx"):
        row = next((r for r in rows if len(r) > 1 and squeeze(str(r[1])) == "地方消費税"), None)
        if row is None:
            continue
        for j, c in enumerate(rows[2]):
            if (year := era_year(c)) and isinstance(row[j], float):
                out[year] = round(row[j] / 100, 1)
    return out


def consumption_tax():
    _, rows = next(iter(read(CONV_DIR / "tax_revenue_general_account.xlsx")))
    national = {int(r[3]): r[7] for r in rows if len(r) > 7 and isinstance(r[3], float) and isinstance(r[7], float)}
    local = local_consumption_tax()
    out = [[y, national[y], local.get(y, "") if y >= FIRST_LOCAL_CONSUMPTION_TAX_FULL_YEAR else ""] for y in sorted(national) if y >= OLD_BASE_YEARS[0]]
    return ["fiscal_year", "national_100m_yen", "local_100m_yen"], out


def cpi():
    text = (RAW_DIR / "cpi" / "cpi_2020base_calendar_year.csv").read_bytes().decode("shift_jis")
    out = {}
    for line in csv.reader(text.splitlines()):
        if line and re.fullmatch(r"\d{4}", line[0].strip()):
            out[int(line[0])] = float(line[1])
    return out


def real_wage():
    rows = next(rows for name, rows in read(CONV_DIR / "real_wage_index_hon-t25.xlsx") if name == "TL")
    out = {}
    for r in rows:
        if isinstance(r[0], float) and isinstance(r[1], float):
            out.setdefault(int(r[0]), r[1])
    return out


def prices_wages():
    prices, wages = cpi(), real_wage()
    years = [y for y in sorted(prices) if y >= OLD_BASE_YEARS[0]]
    return ["year", "cpi_2020base", "real_wage_index_2020base"], [[y, prices[y], wages.get(y, "")] for y in years]


def write(name, header, rows):
    OUT_DIR.mkdir(exist_ok=True)
    with open(OUT_DIR / name, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)
    print(name, len(rows), "行")


def main():
    write("spending_by_function.csv", *spending())
    write("burden_ratio.csv", *burden())
    write("household_by_income.csv", *household())
    write("social_contributions.csv", *social_contributions())
    write("consumption_tax.csv", *consumption_tax())
    write("prices_wages.csv", *prices_wages())


if __name__ == "__main__":
    main()
