import random, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from tedori_payload import BURDEN_ESTIMATE_YEARS, INDEX_YEAR, burden, hidden, national_income, payslip, real_income, tedori_payload

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
        return [{"year": str(y), "cpi_2020base": str(100 + cpi_step * (y - INDEX_YEAR)), "real_wage_index_2020base": "90"} for y in years]

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


class PayloadTest(unittest.TestCase):
    def test_empty_inputs_give_empty_sections(self):
        payload = tedori_payload([], [], [], [], [])
        self.assertEqual((payload["payslip"], payload["burden"], payload["hidden"], payload["real"]), ([], [], [], []))
        self.assertIsNone(payload["nationalIncome"])


if __name__ == "__main__":
    unittest.main()
