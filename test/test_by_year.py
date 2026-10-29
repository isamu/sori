import sys, unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from by_year import days_in_year, event_list, event_window, events_in, group_by_year, pm_id_of, segments_in, term_of, terms_of, year_span, years_covered

PMS = [
    {"id": "hatoyama", "name": "鳩山由紀夫", "party": "民主党", "start": "2009-09-16", "end": "2010-06-08"},
    {"id": "kan", "name": "菅直人", "party": "民主党", "start": "2010-06-08", "end": "2011-09-02"},
    {"id": "noda", "name": "野田佳彦", "party": "民主党", "start": "2011-09-02", "end": "2012-12-26"},
    {"id": "takaichi", "name": "高市早苗", "party": "自由民主党", "start": "2025-10-21", "end": None},
]
UNTIL = "2026-10-29"


class TermTest(unittest.TestCase):
    def test_pm_before_coverage_is_dropped(self):
        self.assertIsNone(term_of(PMS[0], UNTIL))

    def test_term_starts_at_coverage_and_ends_the_day_before_successor(self):
        self.assertEqual(term_of(PMS[1], UNTIL), {"id": "kan", "name": "菅直人", "party": "民主党", "first": "2011-03-11", "last": "2011-09-01"})

    def test_incumbent_ends_at_until(self):
        self.assertEqual(term_of(PMS[3], UNTIL)["last"], UNTIL)

    def test_terms_of_keeps_order_and_drops_none(self):
        self.assertEqual([t["id"] for t in terms_of(PMS, UNTIL)], ["kan", "noda", "takaichi"])


class YearTest(unittest.TestCase):
    def test_first_year_starts_at_coverage(self):
        self.assertEqual(year_span(2011, UNTIL), ("2011-03-11", "2011-12-31"))

    def test_middle_year_is_full(self):
        self.assertEqual(year_span(2012, UNTIL), ("2012-01-01", "2012-12-31"))

    def test_current_year_ends_at_until(self):
        self.assertEqual(year_span(2026, UNTIL), ("2026-01-01", UNTIL))

    def test_years_covered(self):
        self.assertEqual(years_covered("2013-05-01"), [2011, 2012, 2013])

    def test_days_in_year_counts_leap_days(self):
        self.assertEqual([days_in_year(y) for y in (2011, 2024, 2026, 2100)], [365, 366, 365, 365])


class SegmentTest(unittest.TestCase):
    def test_segments_clipped_to_year(self):
        terms = terms_of(PMS, UNTIL)
        self.assertEqual(segments_in(terms, "2011-03-11", "2011-12-31"), [
            {"id": "kan", "name": "菅直人", "start": "2011-03-11", "end": "2011-09-01"},
            {"id": "noda", "name": "野田佳彦", "start": "2011-09-02", "end": "2011-12-31"}])
        self.assertEqual(segments_in(terms, "2012-01-01", "2012-12-31"), [{"id": "noda", "name": "野田佳彦", "start": "2012-01-01", "end": "2012-12-25"}])

    def test_no_segment_in_a_gap(self):
        self.assertEqual(segments_in(terms_of(PMS, UNTIL), "2015-01-01", "2015-12-31"), [])


ELECTION = {"kind": "election", "name": "第46回衆院選", "start": "2012-12-04", "end": "2012-12-16", "source": "https://example.test/e"}
QUAKE = {"kind": "quake", "name": "平成28年熊本地震", "start": "2016-04-14", "last": "2016-04-16", "source": "https://example.test/q"}
NEW_YEAR_QUAKE = {"kind": "quake", "name": "年またぎ", "start": "2023-12-29", "last": "2023-12-29", "source": "https://example.test/n"}


class EventTest(unittest.TestCase):
    def test_election_runs_from_announcement_to_vote(self):
        self.assertEqual(event_window(ELECTION), ("2012-12-04", "2012-12-16"))

    def test_disaster_window_is_one_week_from_the_last_day(self):
        self.assertEqual(event_window(QUAKE), ("2016-04-14", "2016-04-22"))
        self.assertEqual(event_window(NEW_YEAR_QUAKE), ("2023-12-29", "2024-01-04"))

    def test_events_clipped_to_year(self):
        events = [ELECTION, QUAKE, NEW_YEAR_QUAKE]
        self.assertEqual(events_in(events, "2024-01-01", "2024-12-31"),
                         [{"kind": "quake", "name": "年またぎ", "start": "2024-01-01", "end": "2024-01-04"}])
        self.assertEqual([e["name"] for e in events_in(events, "2023-01-01", "2023-12-31")], ["年またぎ"])
        self.assertEqual(events_in(events, "2016-01-01", "2016-12-31")[0]["end"], "2016-04-22")

    def test_no_event_outside(self):
        self.assertEqual(events_in([ELECTION, QUAKE], "2020-01-01", "2020-12-31"), [])

    def test_event_list_is_oldest_first_with_window_and_source(self):
        rows = event_list([NEW_YEAR_QUAKE, QUAKE, ELECTION])
        self.assertEqual([r["name"] for r in rows], [ELECTION["name"], QUAKE["name"], "年またぎ"])
        self.assertEqual(rows[1], {"kind": "quake", "name": QUAKE["name"], "start": "2016-04-14", "end": "2016-04-22", "source": QUAKE["source"]})
        self.assertEqual(rows[0]["end"], "2012-12-16")


class GroupTest(unittest.TestCase):
    def test_groups_sorted_and_deduped(self):
        days = [{"date": "2012-01-02"}, {"date": "2011-12-31"}, {"date": "2012-01-01"}, {"date": "2012-01-01", "dup": True}]
        self.assertEqual(group_by_year(days), {2011: [{"date": "2011-12-31"}], 2012: [{"date": "2012-01-01"}, {"date": "2012-01-02"}]})

    def test_empty(self):
        self.assertEqual(group_by_year([]), {})


class PmIdTest(unittest.TestCase):
    def test_name_with_space_maps_to_id(self):
        self.assertEqual(pm_id_of("菅 直人", terms_of(PMS, UNTIL)), "kan")

    def test_unknown_name_and_none_pass_through(self):
        terms = terms_of(PMS, UNTIL)
        self.assertEqual(pm_id_of("誰か", terms), "誰か")
        self.assertEqual(pm_id_of(None, terms), "")


if __name__ == "__main__":
    unittest.main()
