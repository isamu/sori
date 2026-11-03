import csv, unittest
from collections import defaultdict
from pathlib import Path

ZAISEI_DIR = Path(__file__).resolve().parents[1] / "zaisei"
PCT_ROUNDING = 0.15
YEN_ROUNDING = 2
BILLION_YEN_ROUNDING = 1.0
FIRST_YEAR = 1995


def rows(name):
    with open(ZAISEI_DIR / name, encoding="utf-8") as f:
        return list(csv.DictReader(f))


class BurdenRatioTest(unittest.TestCase):
    def test_components_add_up(self):
        for r in rows("burden_ratio.csv"):
            v = {k: float(x) for k, x in r.items()}
            year = r["fiscal_year"]
            self.assertAlmostEqual(v["national_tax_pct"] + v["local_tax_pct"], v["tax_burden_pct"], delta=PCT_ROUNDING, msg=year)
            self.assertAlmostEqual(v["tax_burden_pct"] + v["social_security_burden_pct"], v["national_burden_pct"], delta=PCT_ROUNDING, msg=year)
            self.assertAlmostEqual(v["national_burden_pct"] + v["fiscal_deficit_pct"], v["potential_burden_pct"], delta=PCT_ROUNDING, msg=year)

    def test_years_are_consecutive(self):
        years = [int(r["fiscal_year"]) for r in rows("burden_ratio.csv")]
        self.assertEqual(years, list(range(years[0], years[-1] + 1)))
        self.assertLessEqual(years[0], FIRST_YEAR)


class HouseholdTest(unittest.TestCase):
    def setUp(self):
        self.cells = defaultdict(dict)
        for r in rows("household_by_income.csv"):
            self.cells[(r["year"], r["income_class"])][r["item"]] = float(r["yen_per_month"])

    def assert_sum(self, cell, total, parts, key):
        self.assertAlmostEqual(cell[total], sum(cell.get(p, 0.0) for p in parts), delta=YEN_ROUNDING, msg=key)

    def test_identities(self):
        for key, c in self.cells.items():
            self.assert_sum(c, "非消費支出", ["直接税", "社会保険料", "他の非消費支出"], key)
            self.assert_sum(c, "直接税", ["勤労所得税", "個人住民税", "他の税"], key)
            self.assertAlmostEqual(c["可処分所得"], c["実収入"] - c["非消費支出"], delta=YEN_ROUNDING, msg=key)
            if "公的年金保険料" in c:
                self.assert_sum(c, "社会保険料", ["公的年金保険料", "健康保険料", "介護保険料", "他の社会保険料"], key)

    def test_every_year_has_average_and_classes(self):
        years = sorted({int(y) for y, _ in self.cells})
        self.assertEqual(years, list(range(FIRST_YEAR, years[-1] + 1)))
        for y in years:
            classes = {c for yy, c in self.cells if int(yy) == y}
            expected = 6 if y < 2000 else 11
            self.assertEqual(len(classes), expected, y)


class SpendingTest(unittest.TestCase):
    def setUp(self):
        self.by_year = defaultdict(dict)
        for r in rows("spending_by_function.csv"):
            self.by_year[(int(r["fiscal_year"]), r["sna_base"])][r["cofog_code"]] = float(r["billion_yen"])

    def test_every_year_has_ten_functions_and_interest(self):
        years = sorted({y for y, _ in self.by_year})
        self.assertEqual(years, list(range(FIRST_YEAR, years[-1] + 1)))
        for y in years:
            base = "2000年基準" if y < 2005 else "2020年基準"
            codes = self.by_year[(y, base)]
            for code in map(str, range(1, 11)):
                self.assertIn(code, codes, (y, code))
            self.assertIn("interest", self.by_year[(y, "2020年基準")], y)

    def test_sub_functions_add_up_to_their_function(self):
        for (y, base), codes in self.by_year.items():
            for top in map(str, range(1, 11)):
                subs = [v for c, v in codes.items() if c.startswith(top + ".")]
                if subs:
                    self.assertAlmostEqual(sum(subs), codes[top], delta=BILLION_YEN_ROUNDING, msg=(y, top))


# Read by hand from the raw files in raw/zaisei/, not from the extraction code, so a wrong cell mapping goes red.
SOURCE_VALUES = {
    ("burden_ratio.csv", ("1995",), "national_burden_pct"): 35.1,
    ("burden_ratio.csv", ("2024",), "potential_burden_pct"): 50.3,
    ("household_by_income.csv", ("1995", "avg", "実収入"), "yen_per_month"): 570817,
    ("household_by_income.csv", ("2000", "D05", "実収入"), "yen_per_month"): 500650,
    ("household_by_income.csv", ("2025", "avg", "可処分所得"), "yen_per_month"): 532408,
    # 勤め先収入 matches two labelled rows in the 2000–2017 decile sheets; these come from the separate age table (第 3-2 表).
    ("household_by_income.csv", ("2000", "avg", "勤め先収入"), "yen_per_month"): 527818,
    ("household_by_income.csv", ("2010", "avg", "勤め先収入"), "yen_per_month"): 485340,
    ("spending_by_function.csv", ("1995", "2000年基準", "10"), "billion_yen"): 46648.0,
    ("spending_by_function.csv", ("2024", "2020年基準", "10"), "billion_yen"): 99742.8,
    ("spending_by_function.csv", ("2024", "2020年基準", "interest"), "billion_yen"): 9375.1,
}
KEY_COLUMNS = {"burden_ratio.csv": ["fiscal_year"], "household_by_income.csv": ["year", "income_class", "item"],
               "spending_by_function.csv": ["fiscal_year", "sna_base", "cofog_code"]}


class SourceValueTest(unittest.TestCase):
    def test_values_match_the_source_tables(self):
        for (name, key, column), expected in SOURCE_VALUES.items():
            matches = [r for r in rows(name) if tuple(r[k] for k in KEY_COLUMNS[name]) == key]
            self.assertEqual(len(matches), 1, (name, key))
            self.assertEqual(float(matches[0][column]), expected, (name, key, column))


if __name__ == "__main__":
    unittest.main()
