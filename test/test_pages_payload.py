import json, re, sys, unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import build_pages
from tedori_payload import tedori_payload
from zaisei_payload import pay_payload, spending_payload

TEDORI_CSVS = ("household_by_income", "burden_ratio", "social_contributions", "consumption_tax", "prices_wages", "household_by_age")


def embedded_data(page):
    text = (ROOT / "site" / page).read_text(encoding="utf-8")
    return json.loads(re.search(r"const DATA = (.*?);\n", text).group(1).replace("<\\/", "</"))


def without_date(payload):
    return {k: v for k, v in payload.items() if k != "generated"}


def round_trip(payload):
    return json.loads(json.dumps(payload, ensure_ascii=False))


class PublishedPagesTest(unittest.TestCase):
    """The committed pages must carry exactly what the committed CSVs produce, so a stale page or a CSV/payload mismatch goes red."""

    def setUp(self):
        self.tedori = tedori_payload(*(build_pages.zaisei_rows(f"{name}.csv") for name in TEDORI_CSVS))

    def test_tedori_page_matches_the_csvs(self):
        self.assertEqual(without_date(embedded_data("tedori.html")), round_trip(self.tedori))

    def test_zaisei_page_matches_the_csvs(self):
        expected = {"pay": pay_payload(build_pages.zaisei_rows("household_by_income.csv")),
                    "spend": spending_payload(build_pages.zaisei_rows("spending_by_function.csv"))}
        self.assertEqual(without_date(embedded_data("zaisei.html")), round_trip(expected))

    def test_article_figures_from_the_real_data(self):
        t = self.tedori
        b = t["breakdown"]
        self.assertAlmostEqual((1 + b["income_real"] / 100) * (1 + b["kept_share"] / 100), 1 + b["takehome_real"] / 100, delta=0.002)
        self.assertEqual((b["first"], b["cpi"], b["takehome_real"], b["head_real"]), (2000, 15.0, -2.4, -11.0))
        forties = next(c for c in t["ages"]["classes"] if c["id"] == "40-49")
        self.assertEqual((forties["head"], forties["head_nominal"]), (-9.2, 4.5))
        self.assertEqual(t["ages"]["reweighted"]["head"], -6.8)
        self.assertEqual(t["hidden"][-1], {"year": 2024, "consumption_tax": 7.1, "employer": 8.4})
        self.assertEqual(t["real"][-1]["real"], 97.6)
        self.assertEqual([b["year"] for b in t["burden"] if b["estimate"]], [2025, 2026])


if __name__ == "__main__":
    unittest.main()
