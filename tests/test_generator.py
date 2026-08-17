import unittest
from datetime import time
from generate_calendars import make_calendar, parse_matches, stable_uid
import json
from pathlib import Path
HTML = """<table><tr><td>SAB 22.08.2026</td><td>17:00</td><td>Real Oviedo VS CD Leganés</td><td>LALIGA HYPERMOTION</td><td>LALIGA TV HYPERMOTION</td><td><a href="/partido/abc">Ver</a></td></tr><tr><td>DOM 13.09.2026</td><td>-- : --</td><td>CD Leganés VS Granada CF</td><td>LALIGA HYPERMOTION</td><td>-</td></tr></table>"""
class Tests(unittest.TestCase):
    def test_parser(self):
        matches = parse_matches(HTML, "https://www.laliga.com")
        self.assertEqual((matches[0].home, matches[0].away), ("Real Oviedo", "CD Leganés")); self.assertEqual(matches[0].kickoff, time(17, 0))
        self.assertEqual(matches[0].broadcaster, "LALIGA TV HYPERMOTION"); self.assertIsNone(matches[1].kickoff)
    def test_stable_uid(self):
        match = parse_matches(HTML, "https://www.laliga.com")[0]
        changed = match.__class__(match.match_date.replace(day=23), time(18, 30), match.home, match.away, match.competition, match.broadcaster, match.source_url)
        self.assertEqual(stable_uid(match), stable_uid(changed))
    def test_calendar_contains_timed_and_all_day_events(self):
        matches = parse_matches(HTML, "https://www.laliga.com")
        config = json.loads((Path(__file__).parents[1] / "config.json").read_text())
        calendar = make_calendar(matches, config["clubs"][1], config).decode()
        self.assertIn("DTSTART;TZID=Europe/Madrid:20260822T170000", calendar)
        self.assertIn("DTSTART;VALUE=DATE:20260913", calendar)
        self.assertIn("TRIGGER:-PT1440M", calendar)
        self.assertTrue(calendar.endswith("END:VCALENDAR\r\n"))
if __name__ == "__main__": unittest.main()
