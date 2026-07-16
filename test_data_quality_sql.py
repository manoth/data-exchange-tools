import unittest

from fastapi import HTTPException

from main import (
    _data_quality_query_parts,
    _filter_cached_data_quality_rows,
    _summarize_data_quality_rows,
    _validate_data_quality_sql,
)
from models import DataQualityQueryRequest


class DataQualitySqlValidationTests(unittest.TestCase):
    def test_allows_safe_tokens_inside_quoted_text(self):
        sql = "SELECT CONCAT_WS('; ', 'a--b', '#') AS detail"
        self.assertEqual(_validate_data_quality_sql(sql), sql)

    def test_rejects_multiple_statements_and_comments(self):
        for sql in ("SELECT 1; DELETE FROM person", "SELECT 1 -- comment", "SELECT 1 # comment"):
            with self.subTest(sql=sql), self.assertRaises(HTTPException):
                _validate_data_quality_sql(sql)

    def test_rejects_forbidden_functions(self):
        with self.assertRaises(HTTPException):
            _validate_data_quality_sql("SELECT SLEEP(1)")

    def test_dynamic_abnormal_groups_use_report_metadata(self):
        report = {
            "reportCode": "custom-report",
            "columns": [{"field": "abnormal_type", "sortable": True}],
            "filters": [{
                "name": "abnormal_group", "field": "abnormal_type", "operator": "abnormal_group",
                "options": [{"value": "group_a", "matches": ["a", "both"]}, {"value": "group_b", "matches": ["b"]}],
            }],
        }
        rows = [
            {"quality_status": "abnormal", "abnormal_type": "a"},
            {"quality_status": "abnormal", "abnormal_type": "both"},
            {"quality_status": "abnormal", "abnormal_type": "b"},
            {"quality_status": "normal", "abnormal_type": "normal"},
        ]
        summary = _summarize_data_quality_rows(rows, report)
        self.assertEqual(summary["abnormal_groups"], {"group_a": 2, "group_b": 1})

        request = DataQualityQueryRequest(filters={"abnormal_group": "group_a"})
        filtered = _filter_cached_data_quality_rows(report, {"rows": rows}, request)
        self.assertEqual([row["abnormal_type"] for row in filtered], ["a", "both"])

        where_sql, _order_sql, params = _data_quality_query_parts(report, request)
        self.assertIn("report_data.`abnormal_type` IN (%s, %s)", where_sql)
        self.assertEqual(params, ["a", "both"])


if __name__ == "__main__":
    unittest.main()
