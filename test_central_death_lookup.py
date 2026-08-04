import unittest
from unittest.mock import patch

import transform


class CentralDeathLookupDetailTests(unittest.TestCase):
    @patch.object(transform, "_ensure_agent_api_key_for_lookup")
    @patch.object(transform, "_request_central_death_lookup")
    def test_maps_date_and_cause_from_matched_persons(self, request_lookup, ensure_key):
        ensure_key.return_value = None
        request_lookup.return_value = {
            "ok": True,
            "data": {
                "matchedPids": ["1234567890123"],
                "matchedPersons": [{
                    "pid": "1234567890123",
                    "deathDate": "2026-01-10",
                    "deathCauseCode": "I64",
                }],
            },
        }

        result = transform.lookup_central_death_pids(["1234567890123"])

        self.assertTrue(result["available"])
        self.assertEqual(result["matched"], {"1234567890123"})
        self.assertEqual(result["matched_persons"]["1234567890123"]["death_date"], "2026-01-10")
        self.assertEqual(result["matched_persons"]["1234567890123"]["death_cause_code"], "I64")


if __name__ == "__main__":
    unittest.main()
