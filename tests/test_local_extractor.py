import os
import stat
import tempfile
import unittest
from unittest import mock

from services import local_extractor
from services.local_extractor import (
    DEFAULT_OUTPUT_PATH,
    extract_first_line,
    extract_from_reader,
)
from services.passwd_reader import PasswdReadResult

SAMPLE = (
    "root:x:0:0:root:/root:/bin/bash\n"
    "ec2-user:x:1000:1000::/home/ec2-user:/bin/bash\n"
)


class ExtractFirstLineTests(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.out = os.path.join(self.tmpdir.name, "out.txt")

    def test_writes_first_line(self):
        result = extract_first_line(SAMPLE, self.out)

        self.assertTrue(result.ok)
        self.assertEqual(result.output_path, self.out)
        self.assertEqual(result.line, "root:x:0:0:root:/root:/bin/bash")
        self.assertIsNone(result.error)
        with open(self.out, "r", encoding="utf-8") as handle:
            self.assertEqual(handle.read(), "root:x:0:0:root:/root:/bin/bash\n")

    def test_skips_leading_blank_lines(self):
        result = extract_first_line("\n   \n\tfirst real line\nsecond\n", self.out)

        self.assertTrue(result.ok)
        self.assertEqual(result.line, "\tfirst real line")

    def test_output_is_owner_only(self):
        extract_first_line(SAMPLE, self.out)

        mode = stat.S_IMODE(os.stat(self.out).st_mode)
        self.assertEqual(mode, 0o600)

    def test_tightens_existing_loose_permissions(self):
        with open(self.out, "w", encoding="utf-8") as handle:
            handle.write("stale")
        os.chmod(self.out, 0o644)

        extract_first_line(SAMPLE, self.out)

        mode = stat.S_IMODE(os.stat(self.out).st_mode)
        self.assertEqual(mode, 0o600)

    def test_default_output_path(self):
        self.assertEqual(DEFAULT_OUTPUT_PATH, "/tmp/ec2-file-test-output.txt")

    def test_empty_string(self):
        result = extract_first_line("", self.out)

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "empty")
        self.assertFalse(os.path.exists(self.out))

    def test_none_input(self):
        result = extract_first_line(None, self.out)

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "empty")

    def test_whitespace_only(self):
        result = extract_first_line("\n   \n\t\n", self.out)

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "empty")

    def test_invalid_output_path(self):
        missing = os.path.join(self.tmpdir.name, "nope", "out.txt")

        result = extract_first_line(SAMPLE, missing)

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "invalid_output_path")

    def test_permission_denied(self):
        with mock.patch("os.open", side_effect=PermissionError):
            result = extract_first_line(SAMPLE, self.out)

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "permission_denied")

    def test_other_write_error(self):
        with mock.patch("os.open", side_effect=OSError("boom")):
            result = extract_first_line(SAMPLE, self.out)

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "write_error")

    def test_contents_never_logged(self):
        with self.assertLogs(local_extractor.logger, level="DEBUG") as captured:
            extract_first_line(SAMPLE, self.out)

        logged = "\n".join(captured.output)
        self.assertNotIn("root:x:0:0", logged)
        self.assertNotIn("ec2-user", logged)


class ExtractFromReaderTests(unittest.TestCase):
    """The reader is stubbed so these tests never touch the host /etc/passwd."""

    def setUp(self):
        self.tmpdir = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmpdir.cleanup)
        self.out = os.path.join(self.tmpdir.name, "out.txt")

    def test_uses_reader_output(self):
        ok = PasswdReadResult(ok=True, content=SAMPLE)
        with mock.patch.object(local_extractor, "read_passwd", return_value=ok) as rp:
            result = extract_from_reader(self.out, source_path="/some/path")

        rp.assert_called_once_with("/some/path")
        self.assertTrue(result.ok)
        self.assertEqual(result.line, "root:x:0:0:root:/root:/bin/bash")

    def test_propagates_reader_error(self):
        err = PasswdReadResult(ok=False, error="not_found")
        with mock.patch.object(local_extractor, "read_passwd", return_value=err):
            result = extract_from_reader(self.out)

        self.assertFalse(result.ok)
        self.assertEqual(result.error, "not_found")
        self.assertFalse(os.path.exists(self.out))


if __name__ == "__main__":
    unittest.main()
