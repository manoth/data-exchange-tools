import unittest
from datetime import date, time

from main import _build_deceased_service_rows


class DeceasedServiceAuditGroupingTests(unittest.TestCase):
    def test_groups_person_and_keeps_only_visits_after_central_death_date(self):
        people = [
            {
                "person_id": 10, "cid": "1234567890123", "patient_hn": "000001",
                "pname": "นาย", "fname": "ทดสอบ", "lname": "ระบบ",
            },
            {
                "person_id": 11, "cid": "1234567890123", "patient_hn": "000002",
                "pname": "นาย", "fname": "ทดสอบ", "lname": "ระบบ",
            },
        ]
        central = {
            "1234567890123": {
                "pid": "1234567890123", "death_date": "2026-01-10",
                "death_cause_code": "I64",
            },
        }
        visits = [
            {"vn": "before", "hn": "000001", "vstdate": date(2026, 1, 9), "vsttime": time(8, 0)},
            {"vn": "same-day", "hn": "000001", "vstdate": date(2026, 1, 10), "vsttime": time(9, 0)},
            {"vn": "after-1", "hn": "000001", "vstdate": date(2026, 1, 11), "vsttime": time(10, 0)},
            {"vn": "after-2", "hn": "000002", "vstdate": date(2026, 1, 15), "vsttime": time(11, 30)},
        ]

        rows = _build_deceased_service_rows(people, central, visits)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["PERSON_CID"], "1234567890123")
        self.assertEqual(rows[0]["HN"], "000001, 000002")
        self.assertEqual(rows[0]["SERVICE_COUNT"], 2)
        self.assertEqual(rows[0]["DEATH_CAUSE"], "I64")
        self.assertEqual(rows[0]["FIRST_SERVICE_DATE"], "2026-01-11")
        self.assertEqual(rows[0]["LAST_SERVICE_DATE"], "2026-01-15")
        self.assertEqual(rows[0]["MAX_DAYS_AFTER_DEATH"], 5)
        self.assertEqual([item["VN"] for item in rows[0]["_services"]], ["after-1", "after-2"])

    def test_ignores_central_matches_without_death_date(self):
        people = [{"person_id": 1, "cid": "1234567890123", "patient_hn": "1"}]
        central = {"1234567890123": {"pid": "1234567890123", "death_date": ""}}
        visits = [{"vn": "1", "hn": "1", "vstdate": "2026-01-01", "vsttime": "08:00:00"}]

        self.assertEqual(_build_deceased_service_rows(people, central, visits), [])


if __name__ == "__main__":
    unittest.main()
