import unittest
import urllib.error
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

    @patch.object(transform.time, "sleep")
    @patch.object(transform, "_ensure_agent_api_key_for_lookup")
    @patch.object(transform, "_request_central_death_lookup")
    def test_retries_a_timeout_then_recovers(self, request_lookup, ensure_key, sleep):
        ensure_key.return_value = None
        request_lookup.side_effect = [
            urllib.error.URLError(TimeoutError("timed out")),
            {"ok": True, "data": {"matchedPids": [], "matchedPersons": []}},
        ]

        result = transform.lookup_central_death_pids(["1234567890123"])

        self.assertTrue(result["available"])
        self.assertEqual(request_lookup.call_count, 2)
        sleep.assert_called_once()

    @patch.object(transform.time, "sleep")
    @patch.object(transform, "_ensure_agent_api_key_for_lookup")
    @patch.object(transform, "_request_central_death_lookup")
    def test_stops_after_first_batch_when_network_is_unreachable(self, request_lookup, ensure_key, sleep):
        ensure_key.return_value = None
        request_lookup.side_effect = urllib.error.URLError(TimeoutError("timed out"))
        pids = [f"{index:013d}" for index in range(1, 501)]

        result = transform.lookup_central_death_pids(pids)

        self.assertFalse(result["available"])
        self.assertEqual(request_lookup.call_count, transform.CENTRAL_DEATH_LOOKUP_MAX_ATTEMPTS)
        self.assertIn("Firewall/Proxy", result["message"])


if __name__ == "__main__":
    unittest.main()
