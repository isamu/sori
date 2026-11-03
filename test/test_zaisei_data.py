import csv, unittest
from collections import defaultdict
from pathlib import Path

ZAISEI_DIR = Path(__file__).resolve().parents[1] / "zaisei"
PCT_ROUNDING = 0.15
YEN_ROUNDING = 2
BILLION_YEN_ROUNDING = 1.0
FIRST_YEAR = 1995
INDEX_BASE_YEAR = 2020
LOCAL_CONSUMPTION_TAX_FIRST_FULL_YEAR = 1998


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
            if "世帯主収入" in c:
                self.assert_sum(c, "勤め先収入", ["世帯主収入", "世帯主の配偶者の収入", "他の世帯員収入"], key)
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


def consecutive_from(test, years, first):
    test.assertEqual(years, list(range(years[0], years[-1] + 1)))
    test.assertLessEqual(years[0], first)


class SocialContributionsTest(unittest.TestCase):
    def test_employer_and_household_add_up_and_years_are_consecutive(self):
        data = rows("social_contributions.csv")
        consecutive_from(self, [int(r["fiscal_year"]) for r in data], FIRST_YEAR)
        for r in data:
            v = {k: float(x) for k, x in r.items()}
            self.assertAlmostEqual(v["employer_billion_yen"] + v["household_billion_yen"], v["total_billion_yen"], delta=BILLION_YEN_ROUNDING, msg=r)
            self.assertGreater(v["employer_billion_yen"], 0, r)


class ConsumptionTaxTest(unittest.TestCase):
    def test_national_every_year_and_local_from_its_first_full_year(self):
        data = rows("consumption_tax.csv")
        consecutive_from(self, [int(r["fiscal_year"]) for r in data], FIRST_YEAR)
        for r in data:
            self.assertGreater(float(r["national_100m_yen"]), 0, r)
        local_years = [int(r["fiscal_year"]) for r in data if r["local_100m_yen"]]
        self.assertEqual(local_years, list(range(LOCAL_CONSUMPTION_TAX_FIRST_FULL_YEAR, local_years[-1] + 1)))


class PricesWagesTest(unittest.TestCase):
    def test_both_indices_are_100_in_the_base_year_and_cover_every_year(self):
        data = {int(r["year"]): r for r in rows("prices_wages.csv")}
        consecutive_from(self, sorted(data), FIRST_YEAR)
        self.assertEqual(float(data[INDEX_BASE_YEAR]["cpi_2020base"]), 100.0)
        self.assertEqual(float(data[INDEX_BASE_YEAR]["real_wage_index_2020base"]), 100.0)
        for y, r in data.items():
            self.assertTrue(all(r.values()), y)
        for column in ("cpi_food_2020base", "cpi_energy_2020base"):
            self.assertEqual(float(data[INDEX_BASE_YEAR][column]), 100.0, column)


AGE_CLASSES = ["-29", "30-39", "40-49", "50-59", "60-69", "70-"]
AGE_ITEMS = ["世帯数分布", "世帯主の年齢", "有業人員", "実収入", "勤め先収入", "世帯主収入", "世帯主の配偶者の収入", "可処分所得"]
SHARE_TOTAL = 10000
AGE_FIRST_YEAR = 2000
SHARE_ROUNDING = 3


class HouseholdByAgeTest(unittest.TestCase):
    def setUp(self):
        self.cells = defaultdict(dict)
        for r in rows("household_by_age.csv"):
            self.cells[(int(r["year"]), r["age_class"])][r["item"]] = float(r["value"])

    def test_every_year_has_every_class_and_item(self):
        years = sorted({y for y, _ in self.cells})
        consecutive_from(self, years, AGE_FIRST_YEAR)
        for y in years:
            for cls in ["avg"] + AGE_CLASSES:
                self.assertEqual(set(self.cells[(y, cls)]), set(AGE_ITEMS), (y, cls))

    def test_class_shares_add_up_and_ages_fall_in_their_class(self):
        for y in sorted({y for y, _ in self.cells}):
            self.assertAlmostEqual(sum(self.cells[(y, c)]["世帯数分布"] for c in AGE_CLASSES), SHARE_TOTAL, delta=SHARE_ROUNDING, msg=y)
            for cls in AGE_CLASSES[1:-1]:
                low, high = map(int, cls.split("-"))
                self.assertTrue(low <= self.cells[(y, cls)]["世帯主の年齢"] <= high, (y, cls))
            for cls in ["avg"] + AGE_CLASSES:
                c = self.cells[(y, cls)]
                self.assertGreaterEqual(c["勤め先収入"] + YEN_ROUNDING, c["世帯主収入"] + c["世帯主の配偶者の収入"], (y, cls))


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
    ("household_by_income.csv", ("2025", "avg", "世帯主収入"), "yen_per_month"): 470986,
    ("household_by_income.csv", ("2025", "avg", "世帯主の配偶者の収入"), "yen_per_month"): 107549,
    ("social_contributions.csv", ("2000",), "employer_billion_yen"): 22458.2,
    ("social_contributions.csv", ("2000",), "household_billion_yen"): 25512.8,
    ("consumption_tax.csv", ("2000",), "national_100m_yen"): 98221.0,
    # 地方消費税 is in 百万円 in the source (2,528,247), stored in 億円.
    ("consumption_tax.csv", ("2000",), "local_100m_yen"): 25282.5,
    ("prices_wages.csv", ("2025",), "cpi_2020base"): 111.9,
    ("prices_wages.csv", ("2025",), "cpi_food_2020base"): 125.8,
    ("prices_wages.csv", ("2025",), "cpi_energy_2020base"): 123.0,
    ("prices_wages.csv", ("2000",), "real_wage_index_2020base"): 113.9,
    ("household_by_age.csv", ("2025", "40-49", "世帯主収入"), "value"): 538091,
}
KEY_COLUMNS = {"burden_ratio.csv": ["fiscal_year"], "household_by_income.csv": ["year", "income_class", "item"],
               "spending_by_function.csv": ["fiscal_year", "sna_base", "cofog_code"], "social_contributions.csv": ["fiscal_year"],
               "consumption_tax.csv": ["fiscal_year"], "prices_wages.csv": ["year"], "household_by_age.csv": ["year", "age_class", "item"]}


class SourceValueTest(unittest.TestCase):
    def test_values_match_the_source_tables(self):
        for (name, key, column), expected in SOURCE_VALUES.items():
            matches = [r for r in rows(name) if tuple(r[k] for k in KEY_COLUMNS[name]) == key]
            self.assertEqual(len(matches), 1, (name, key))
            self.assertEqual(float(matches[0][column]), expected, (name, key, column))


if __name__ == "__main__":
    unittest.main()
