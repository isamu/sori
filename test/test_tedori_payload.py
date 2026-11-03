import random, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from tedori_payload import (AGE_CLASSES, BURDEN_ESTIMATE_YEARS, DECILES, INDEX_YEAR, age_changes, burden, decile_changes, earners, hidden,
                            national_income, payslip,
                            real_income, tedori_payload)

SEED = 20261103
TRIALS = 1000
PCT_TOLERANCE = 0.15


def household(year, cls="avg", **items):
    return [{"year": str(year), "income_class": cls, "item": k, "yen_per_month": str(v)} for k, v in items.items()]


def full_household(year, income=500000, tax=30000, insurance=50000, other=1000, cls="avg"):
    return household(year, cls, 実収入=income, 直接税=tax, 社会保険料=insurance, 可処分所得=income - tax - insurance - other)


def burden_row(year, deficit=5.0, income=400.0):
    return {"fiscal_year": str(year), "national_tax_pct": "14", "local_tax_pct": "9", "social_security_burden_pct": "13",
            "national_burden_pct": "36", "fiscal_deficit_pct": str(deficit), "potential_burden_pct": str(36 + deficit),
            "national_income_trillion_yen": str(income)}


def price_rows(years, cpi_step=1.0):
    def row(y):
        cpi = str(100 + cpi_step * (y - INDEX_YEAR))
        return {"year": str(y), "cpi_2020base": cpi, "cpi_food_2020base": cpi, "cpi_energy_2020base": cpi, "real_wage_index_2020base": "90"}
    return [row(y) for y in years]


class PayslipTest(unittest.TestCase):
    def test_random_parts_add_up_to_what_is_deducted(self):
        rng = random.Random(SEED)
        for _ in range(TRIALS):
            income = rng.randint(100000, 2000000)
            tax, insurance, other = (rng.randint(0, income // 5) for _ in range(3))
            s = payslip(full_household(INDEX_YEAR, income, tax, insurance, other))[0]
            self.assertAlmostEqual(s["tax"] + s["insurance"] + s["other"], s["deducted_pct"], delta=PCT_TOLERANCE, msg=(SEED, income, tax, insurance, other))

    def test_only_average_class_with_every_item_is_used(self):
        rows = full_household(2001) + full_household(2002, cls="D01") + household(2003, 実収入=1, 可処分所得=1)
        self.assertEqual([s["year"] for s in payslip(rows)], [2001])
        self.assertEqual(payslip([]), [])

    def test_other_never_goes_negative(self):
        rows = household(2001, 実収入=100, 直接税=10, 社会保険料=10, 可処分所得=85)
        self.assertEqual(payslip(rows)[0]["other"], 0)


class BurdenTest(unittest.TestCase):
    def test_last_years_are_estimates_and_negative_deficit_is_zero(self):
        rows = [burden_row(y, deficit=-1.0 if y == 2000 else 5.0) for y in range(1999, 2006)]
        out = burden(rows, 2000)
        self.assertEqual(out[0]["year"], 2000)
        self.assertEqual(out[0]["deficit"], 0)
        self.assertEqual([b["estimate"] for b in out].count(True), BURDEN_ESTIMATE_YEARS)
        self.assertTrue(out[-1]["estimate"])
        self.assertEqual(burden([], 2000), [])

    def test_national_income_uses_the_last_actual_year(self):
        rows = [burden_row(y, income=300.0 + y - 2000) for y in range(2000, 2006)]
        self.assertEqual(national_income(rows, 2000), {"first": {"year": 2000, "trillion": 300.0}, "last": {"year": 2003, "trillion": 303.0}})
        self.assertIsNone(national_income([], 2000))


class HiddenTest(unittest.TestCase):
    def test_shares_of_national_income_and_years_without_local_tax_are_dropped(self):
        contributions = [{"fiscal_year": str(y), "employer_billion_yen": "20000", "household_billion_yen": "30000"} for y in (1997, 1998)]
        taxes = [{"fiscal_year": "1997", "national_100m_yen": "90000", "local_100m_yen": ""},
                 {"fiscal_year": "1998", "national_100m_yen": "100000", "local_100m_yen": "30000"}]
        out = hidden([burden_row(1997), burden_row(1998)], contributions, taxes)
        self.assertEqual(out, [{"year": 1998, "consumption_tax": 3.2, "employer": 5.0, "household": 7.5}])
        self.assertEqual(hidden([], [], []), [])


class RealIncomeTest(unittest.TestCase):
    def prices(self, years, cpi_step=1.0):
        return price_rows(years, cpi_step)

    def test_index_year_is_100_and_flat_takehome_falls_with_prices(self):
        slip = payslip([r for y in (INDEX_YEAR, INDEX_YEAR + 10) for r in full_household(y)])
        out = real_income(slip, self.prices([INDEX_YEAR, INDEX_YEAR + 10]))
        self.assertEqual({k: out[0][k] for k in ("nominal", "real", "wage", "cpi")}, {"nominal": 100, "real": 100, "wage": 100, "cpi": 100})
        self.assertEqual(out[1]["nominal"], 100)
        self.assertEqual(out[1]["cpi"], 110)
        self.assertEqual(out[1]["real"], round(100 / 1.1, 1))

    def test_years_before_the_index_year_are_measured_against_it(self):
        slip = payslip(full_household(INDEX_YEAR - 5, income=600000) + full_household(INDEX_YEAR))
        out = real_income(slip, self.prices([INDEX_YEAR - 5, INDEX_YEAR], cpi_step=0))
        self.assertEqual([r["year"] for r in out], [INDEX_YEAR - 5, INDEX_YEAR])
        self.assertEqual(out[1]["nominal"], 100)
        self.assertGreater(out[0]["nominal"], 100)

    def test_without_the_index_year_there_is_nothing_to_compare(self):
        slip = payslip(full_household(INDEX_YEAR + 1))
        self.assertEqual(real_income(slip, self.prices([INDEX_YEAR + 1])), [])
        self.assertEqual(real_income([], []), [])


class EarnersTest(unittest.TestCase):
    def test_earnings_are_in_index_year_prices_and_incomplete_years_are_dropped(self):
        rows = household(INDEX_YEAR, 世帯主収入=400000, 世帯主の配偶者の収入=50000, 他の世帯員収入=10000)
        rows += household(INDEX_YEAR + 10, 世帯主収入=440000, 世帯主の配偶者の収入=110000, 他の世帯員収入=11000)
        rows += household(INDEX_YEAR + 11, 世帯主収入=1)
        out = earners(rows, price_rows([INDEX_YEAR, INDEX_YEAR + 10, INDEX_YEAR + 11]))
        self.assertEqual(out, [{"year": INDEX_YEAR, "head": 40.0, "spouse": 5.0, "others": 1.0},
                               {"year": INDEX_YEAR + 10, "head": 40.0, "spouse": 10.0, "others": 1.0}])
        self.assertEqual(earners([], []), [])


class DecileChangesTest(unittest.TestCase):
    def test_real_change_from_first_to_last_year_for_each_decile(self):
        rows = []
        for i, d in enumerate(DECILES):
            rows += household(INDEX_YEAR, d, 可処分所得=100000, 年間収入_万円=300 + i)
            rows += household(INDEX_YEAR + 10, d, 可処分所得=110000 + 1000 * i, 年間収入_万円=330 + i)
        out = decile_changes(rows, price_rows([INDEX_YEAR, INDEX_YEAR + 10]))
        self.assertEqual((out["first"], out["last"]), (INDEX_YEAR, INDEX_YEAR + 10))
        self.assertEqual([c["id"] for c in out["classes"]], DECILES)
        self.assertEqual(out["classes"][0]["real_change"], 0.0)
        self.assertEqual(out["classes"][9]["real_change"], round(100 * (119000 / 110 / 1000 - 1), 1))
        self.assertEqual(out["classes"][9]["income_last"], 339)

    def test_one_year_is_not_enough(self):
        self.assertIsNone(decile_changes(household(INDEX_YEAR, "D01", 可処分所得=1), price_rows([INDEX_YEAR])))
        self.assertIsNone(decile_changes([], []))


def age_rows(year, head_by_class, shares):
    rows = []
    for cls in ["avg"] + AGE_CLASSES:
        head = head_by_class[cls]
        items = {"世帯数分布": shares.get(cls, 10000), "世帯主の年齢": 50, "有業人員": 1.5 + (year - INDEX_YEAR) / 100, "世帯主収入": head, "世帯主の配偶者の収入": head / 10, "可処分所得": head}
        rows += [{"year": str(year), "age_class": cls, "item": k, "value": str(v)} for k, v in items.items()]
    return rows


class AgeChangesTest(unittest.TestCase):
    def test_a_shift_toward_lower_paid_classes_lowers_the_average_but_not_the_reweighted_one(self):
        flat = {c: 400000 for c in AGE_CLASSES}
        first = age_rows(INDEX_YEAR, {**flat, "avg": 400000}, {c: 10000 / len(AGE_CLASSES) for c in AGE_CLASSES})
        older = {c: (5000 if c == "60-69" else 1000) for c in AGE_CLASSES}
        last = age_rows(INDEX_YEAR + 10, {**flat, "60-69": 200000, "avg": 300000}, older)
        out = age_changes(first + last, price_rows([INDEX_YEAR, INDEX_YEAR + 10], cpi_step=0))
        self.assertEqual(out["average"]["head"], -25.0)
        self.assertEqual({c["id"]: c["head"] for c in out["classes"]}, {"30-39": 0.0, "40-49": 0.0, "50-59": 0.0, "60-69": -50.0})
        self.assertAlmostEqual(out["reweighted"]["head"], -50 / len(AGE_CLASSES), places=1)

    def test_prices_are_taken_out_and_one_year_is_not_enough(self):
        rows = age_rows(INDEX_YEAR, {c: 100 for c in ["avg"] + AGE_CLASSES}, {})
        rows += age_rows(INDEX_YEAR + 10, {c: 110 for c in ["avg"] + AGE_CLASSES}, {})
        out = age_changes(rows, price_rows([INDEX_YEAR, INDEX_YEAR + 10]))
        self.assertEqual(out["average"]["head"], 0.0)
        self.assertEqual(out["reweighted"]["takehome"], 0.0)
        self.assertEqual(out["cpi_change"], 10.0)
        self.assertEqual(out["workers"], {"first": 1.5, "last": 1.6})
        self.assertEqual({c["head_nominal"] for c in out["classes"]}, {10.0})
        self.assertIsNone(age_changes(age_rows(INDEX_YEAR, {c: 1 for c in ["avg"] + AGE_CLASSES}, {}), price_rows([INDEX_YEAR])))
        self.assertIsNone(age_changes([], []))


class PayloadTest(unittest.TestCase):
    def test_empty_inputs_give_empty_sections(self):
        payload = tedori_payload([], [], [], [], [])
        self.assertEqual((payload["payslip"], payload["burden"], payload["hidden"], payload["real"]), ([], [], [], []))
        self.assertIsNone(payload["nationalIncome"])
        self.assertEqual(payload["earners"], [])
        self.assertIsNone(payload["deciles"])
        self.assertIsNone(payload["ages"])


if __name__ == "__main__":
    unittest.main()
