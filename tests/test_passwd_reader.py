import os
import tempfile
import unittest
from unittest import mock

from services import passwd_reader
from services.passwd_reader import read_passwd

SAMPLE = (
    "root:x:0:0:root:/root:/bin/bash\n"
    "ec2-user:x:1000:1000::/home/ec2-user:/bin/bash\n"
)


class ReadPasswdTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)

    def _write(self, name, text):
        path = os.path.join(self.tmpdir.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(text)
        return path

    def test_reads_file_contents(self):
        path = self._write("passwd", SAMPLE)

        result = read_passwd(path)

        self.assertTrue(result.ok)
        self.assertEqual(result.content, SAMPLE)
        self.assertIsNone(result.error)

    def test_default_path_is_etc_passwd(self):
        with mock.patch("builtins.open", mock.mock_open(read_data=SAMPLE)) as opened:
            result = read_passwd()

        opened.assert_called_once_with("/etc/passwd", "r", encoding="utf-8")
        self.assertTrue(result.ok)

    def test_missing_file(self):
        result = read_passwd(os.path.join(self.tmpdir.name, "missing"))

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "not_found")
        self.assertIsNone(result.content)

    def test_permission_denied(self):
        path = self._write("passwd", SAMPLE)
        with mock.patch("builtins.open", side_effect=PermissionError):
            result = read_passwd(path)

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "permission_denied")
        self.assertIsNone(result.content)

    def test_empty_file(self):
        path = self._write("passwd", "")

        result = read_passwd(path)

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "empty")

    def test_whitespace_only_file_is_empty(self):
        path = self._write("passwd", "\n  \n")

        self.assertEqual(read_passwd(path).error, "empty")

    def test_directory_path(self):
        result = read_passwd(self.tmpdir.name)

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "not_a_file")

    def test_other_os_error(self):
        with mock.patch("builtins.open", side_effect=OSError("boom")):
            result = read_passwd("/etc/passwd")

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "read_error")

    def test_contents_never_logged(self):
        path = self._write("passwd", SAMPLE)
        with self.assertLogs(passwd_reader.logger, level="DEBUG") as captured:
            read_passwd(path)

        logged = "\n".join(captured.output)
        for line in SAMPLE.splitlines():
            self.assertNotIn(line, logged)
        self.assertNotIn("ec2-user", logged)


if __name__ == "__main__":
    unittest.main()
