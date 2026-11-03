import random, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from zaisei_payload import (CELLS, LINK_YEAR, NEW_BASE, OLD_BASE, SPEND_GROUPS, pay_amounts, pay_payload, pay_years, shares_pct,
                            household_cells, link_ratios, spending_amounts, spending_payload, spending_tables, spending_years, to_hundred)

SEED = 20261103
DATA_FILE = Path(__file__).resolve().parents[1] / "zaisei" / "spending_by_function.csv"
FIRST_SPENDING_YEAR = 1995
TRIALS = 2000


class ToHundredTest(unittest.TestCase):
    def test_random_amounts_always_sum_to_hundred(self):
        rng = random.Random(SEED)
        for _ in range(TRIALS):
            n = rng.randint(1, 12)
            amounts = {f"k{i}": rng.choice([0.0, rng.random(), rng.random() * 1e6]) for i in range(n)}
            if sum(amounts.values()) == 0:
                continue
            cells = to_hundred(amounts)
            self.assertEqual(sum(cells.values()), CELLS, (SEED, amounts))
            total = sum(amounts.values())
            for k, v in amounts.items():
                self.assertLess(abs(cells[k] - CELLS * v / total), 1, (SEED, k, amounts))

    def test_exact_shares_are_kept(self):
        self.assertEqual(to_hundred({"a": 50, "b": 30, "c": 20}), {"a": 50, "b": 30, "c": 20})

    def test_thirds_give_the_extra_cell_to_the_first(self):
        self.assertEqual(to_hundred({"a": 1, "b": 1, "c": 1}), {"a": 34, "b": 33, "c": 33})

    def test_tiny_share_rounds_to_zero_but_total_holds(self):
        cells = to_hundred({"big": 1000, "tiny": 1})
        self.assertEqual(cells, {"big": 100, "tiny": 0})

    def test_empty_zero_and_negative(self):
        self.assertEqual(to_hundred({}), {})
        self.assertEqual(to_hundred({"a": 0, "b": 0}), {"a": 0, "b": 0})
        self.assertEqual(to_hundred({"a": -5}), {"a": 0})
        self.assertEqual(sum(to_hundred({"a": 10, "b": -3}).values()), CELLS)


def spending_row(year, base, code, value):
    return {"fiscal_year": str(year), "sna_base": base, "cofog_code": code, "billion_yen": str(value)}


def full_year(year, base, value, with_interest=False):
    rows = [spending_row(year, base, str(i), value * i) for i in range(1, 11)]
    if with_interest:
        rows.append(spending_row(year, NEW_BASE, "interest", 7.0))
    return rows


class SharesTest(unittest.TestCase):
    def test_random_shares_sum_to_hundred(self):
        rng = random.Random(SEED)
        for _ in range(TRIALS):
            amounts = {f"k{i}": rng.random() * 1e6 for i in range(rng.randint(1, 12))}
            self.assertAlmostEqual(sum(shares_pct(amounts).values()), 100, delta=0.1, msg=(SEED, amounts))

    def test_negative_counts_as_zero_and_empty_is_zero(self):
        self.assertEqual(shares_pct({"a": 3, "b": -1, "c": 1}), {"a": 75.0, "b": 0.0, "c": 25.0})
        self.assertEqual(shares_pct({"a": 0}), {"a": 0})
        self.assertEqual(shares_pct({}), {})


class SpendingTest(unittest.TestCase):
    def setUp(self):
        rows = full_year(LINK_YEAR - 1, OLD_BASE, 1.0) + full_year(LINK_YEAR, OLD_BASE, 1.0)
        rows += full_year(LINK_YEAR, NEW_BASE, 2.0, with_interest=True)
        rows.append(spending_row(LINK_YEAR - 1, NEW_BASE, "interest", 5.0))
        self.tables = spending_tables(rows)

    def test_old_years_are_scaled_by_the_link_year_ratio(self):
        ratios = link_ratios(self.tables)
        self.assertEqual(set(ratios.values()), {2.0})
        old = spending_amounts(self.tables, LINK_YEAR - 1, ratios)
        new = spending_amounts(self.tables, LINK_YEAR, ratios)
        for key, _, codes, _ in SPEND_GROUPS:
            if codes != ["interest"]:
                self.assertEqual(old[key], new[key], key)
        self.assertEqual(old["interest"], 5.0)
        self.assertEqual(new["interest"], 7.0)

    def test_year_missing_any_function_is_skipped(self):
        rows = full_year(LINK_YEAR, NEW_BASE, 1.0, with_interest=True) + full_year(LINK_YEAR + 1, NEW_BASE, 1.0, with_interest=True)
        rows = [r for r in rows if not (r["fiscal_year"] == str(LINK_YEAR + 1) and r["cofog_code"] == "4")]
        self.assertEqual(spending_years(spending_tables(rows)), [LINK_YEAR])

    def test_year_without_interest_or_functions_is_skipped(self):
        self.assertEqual(spending_years(self.tables), [LINK_YEAR - 1, LINK_YEAR])
        tables = spending_tables(full_year(LINK_YEAR + 1, NEW_BASE, 1.0))
        self.assertEqual(spending_years(tables), [])
        self.assertEqual(spending_years(spending_tables([])), [])


class SpendingPayloadTest(unittest.TestCase):
    def test_payload_links_old_years_and_every_year_fills_100_cells(self):
        rows = full_year(LINK_YEAR - 1, OLD_BASE, 1.0) + full_year(LINK_YEAR, OLD_BASE, 1.0)
        rows += full_year(LINK_YEAR, NEW_BASE, 2.0, with_interest=True) + full_year(LINK_YEAR + 1, NEW_BASE, 3.0, with_interest=True)
        rows.append(spending_row(LINK_YEAR - 1, NEW_BASE, "interest", 5.0))
        payload = spending_payload(rows)
        self.assertEqual([g["key"] for g in payload["groups"]], [k for k, _, _, _ in SPEND_GROUPS])
        self.assertEqual(payload["linkYear"], LINK_YEAR)
        self.assertEqual([(y["year"], y["linked"]) for y in payload["years"]], [(LINK_YEAR - 1, True), (LINK_YEAR, False), (LINK_YEAR + 1, False)])
        for y in payload["years"]:
            self.assertEqual(sum(y["cells"].values()), CELLS, y["year"])
            self.assertAlmostEqual(sum(y["shares"].values()), 100, delta=0.1, msg=y["year"])
            self.assertEqual(set(y["cells"]), {k for k, _, _, _ in SPEND_GROUPS}, y["year"])
        self.assertEqual(payload["years"][1]["total_trillion"], round((2.0 * 55 + 7.0) / 1000, 1))

    @unittest.skipUnless(DATA_FILE.exists(), "zaisei/spending_by_function.csv is missing")
    def test_committed_data_gives_consecutive_years_from_1995(self):
        import csv
        with open(DATA_FILE, encoding="utf-8") as f:
            payload = spending_payload(list(csv.DictReader(f)))
        years = [y["year"] for y in payload["years"]]
        self.assertEqual(years[0], FIRST_SPENDING_YEAR)
        self.assertEqual(years, list(range(years[0], years[-1] + 1)))
        self.assertTrue(all(sum(y["cells"].values()) == CELLS for y in payload["years"]))


class PayTest(unittest.TestCase):
    def test_amounts_group_items_and_missing_items_count_as_zero(self):
        cell = {"公的年金保険料": 10, "健康保険料": 5, "介護保険料": 1, "個人住民税": 3, "勤労所得税": 2, "可処分所得": 79}
        self.assertEqual(pay_amounts(cell), {"pension": 10, "medical": 6, "resident": 3, "income": 2, "other": 0, "takehome": 79})

    def test_years_need_every_decile_with_insurance_breakdown(self):
        items = ["実収入", "可処分所得", "公的年金保険料"]
        rows = [{"year": str(y), "income_class": f"D{i:02d}", "item": k, "yen_per_month": "1"}
                for y in (2000, 2010, 2025) for i in range(1, 11) for k in items]
        rows += [{"year": "1999", "income_class": "Q1", "item": "実収入", "yen_per_month": "1"},
                 {"year": "2026", "income_class": "avg", "item": "公的年金保険料", "yen_per_month": "1"}]
        self.assertEqual(pay_years(household_cells(rows)), [2000, 2010, 2025])
        missing_decile = [r for r in rows if not (r["year"] == "2010" and r["income_class"] == "D07")]
        self.assertEqual(pay_years(household_cells(missing_decile)), [2000, 2025])
        missing_item = [r for r in rows if not (r["year"] == "2025" and r["income_class"] == "D10" and r["item"] == "公的年金保険料")]
        self.assertEqual(pay_years(household_cells(missing_item)), [2000, 2010])
        self.assertEqual(pay_years(household_cells([])), [])

    def test_payload_has_a_series_per_decile_and_a_grid_for_the_latest_year(self):
        items = {"実収入": 100, "公的年金保険料": 6, "健康保険料": 4, "個人住民税": 3, "勤労所得税": 2, "可処分所得": 85, "年間収入_万円": 700}
        rows = [{"year": str(y), "income_class": f"D{i:02d}", "item": k, "yen_per_month": str(v)}
                for y in (2000, 2001) for i in range(1, 11) for k, v in items.items()]
        payload = pay_payload(rows)
        self.assertEqual(payload["years"], [2000, 2001])
        self.assertEqual(len(payload["classes"]), 10)
        self.assertEqual(payload["classes"][0]["shares"][1]["takehome"], 85.0)
        self.assertEqual(payload["grid"]["year"], 2001)
        self.assertEqual(sum(payload["grid"]["cells"].values()), CELLS)
        self.assertNotIn("grid", pay_payload([]))


if __name__ == "__main__":
    unittest.main()
