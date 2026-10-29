import datetime, sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from by_year import COVERAGE_START, event_window
from events import EVENTS, KINDS


class EventListTest(unittest.TestCase):
    def test_kinds_are_known(self):
        ids = {k["id"] for k in KINDS}
        for e in EVENTS:
            self.assertIn(e["kind"], ids, e["name"])

    def test_dates_are_iso_and_ordered(self):
        for e in EVENTS:
            start, end = event_window(e)
            datetime.date.fromisoformat(start), datetime.date.fromisoformat(end)
            self.assertLessEqual(start, end, e["name"])
            self.assertGreaterEqual(start, COVERAGE_START, e["name"])

    def test_elections_have_vote_day_and_disasters_have_last_day(self):
        for e in EVENTS:
            self.assertIn("end" if e["kind"] == "election" else "last", e, e["name"])

    def test_names_and_sources_present(self):
        for e in EVENTS:
            self.assertTrue(e["name"] and e["source"].startswith("https://"), e["name"])

    def test_kind_and_start_unique(self):
        self.assertEqual(len({(e["kind"], e["start"]) for e in EVENTS}), len(EVENTS))


if __name__ == "__main__":
    unittest.main()
