import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from parse_days import hhmm_to_min, is_unrecorded

EVENT = {"time": "08:13", "label": "公邸発", "place": "公邸", "category": "移動"}


class UnrecordedTest(unittest.TestCase):
    def test_no_metric_and_no_events_is_unrecorded(self):
        self.assertTrue(is_unrecorded(None, []))

    def test_zero_hours_with_events_is_recorded(self):
        self.assertFalse(is_unrecorded(0, [EVENT]))

    def test_zero_hours_without_events_is_recorded(self):
        self.assertFalse(is_unrecorded(0, []))

    def test_events_without_metric_is_recorded(self):
        self.assertFalse(is_unrecorded(None, [EVENT]))


class HhmmTest(unittest.TestCase):
    def test_parses_hours_and_minutes(self):
        self.assertEqual(hhmm_to_min("8:05"), 485)

    def test_dash_none_and_garbage_are_none(self):
        for s in ("—", None, "", "abc", "8:5"):
            self.assertIsNone(hhmm_to_min(s))


if __name__ == "__main__":
    unittest.main()
