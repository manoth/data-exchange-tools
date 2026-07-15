import unittest
from unittest.mock import patch

import pymysql

from db_compat import connect_compatible, parse_server_version, start_read_only_transaction


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False

    def execute(self, sql):
        self.connection.statements.append(sql)
        if sql == "START TRANSACTION READ ONLY" and self.connection.reject_read_only:
            raise pymysql.err.ProgrammingError(1064, "unsupported syntax")


class FakeConnection:
    def __init__(self, version="5.5.68-MariaDB", reject_read_only=False):
        self.version = version
        self.reject_read_only = reject_read_only
        self.statements = []
        self.rollback_count = 0

    def get_server_info(self):
        return self.version

    def cursor(self):
        return FakeCursor(self)

    def rollback(self):
        self.rollback_count += 1


class DatabaseCompatibilityTests(unittest.TestCase):
    def test_parses_mariadb_versions_with_and_without_legacy_prefix(self):
        self.assertEqual(parse_server_version("5.5.68-MariaDB"), (5, 5, 68))
        self.assertEqual(parse_server_version("5.5.5-10.11.6-MariaDB"), (10, 11, 6))
        self.assertEqual(parse_server_version("12.3.1-MariaDB"), (12, 3, 1))

    @patch("db_compat.pymysql.connect")
    def test_falls_back_to_utf8_when_old_server_rejects_utf8mb4(self, connect):
        connection = FakeConnection()
        connect.side_effect = [
            pymysql.err.OperationalError(2019, "Can't initialize character set utf8mb4"),
            connection,
        ]

        result, server = connect_compatible(
            {"host": "db", "port": 3306, "database": "his", "username": "agent", "password": "secret"},
            inspect=False,
        )

        self.assertIs(result, connection)
        self.assertEqual(server["connection_charset"], "utf8")
        self.assertEqual([call.kwargs["charset"] for call in connect.call_args_list], ["utf8mb4", "utf8"])

    def test_falls_back_to_normal_transaction_on_mariadb_5_syntax(self):
        connection = FakeConnection(reject_read_only=True)

        enforced = start_read_only_transaction(connection)

        self.assertFalse(enforced)
        self.assertEqual(connection.rollback_count, 1)
        self.assertEqual(connection.statements, ["START TRANSACTION READ ONLY", "START TRANSACTION"])


if __name__ == "__main__":
    unittest.main()
