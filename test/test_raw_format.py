import io, sys, tempfile, unittest, zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import xlsx_read
from raw_format import XLS_MAGIC, content_problem

RAW_DIR = Path(__file__).resolve().parents[1] / "raw" / "zaisei"
HTML_PAGE = b"<!DOCTYPE html><html><body>Not Found</body></html>"


def zip_bytes(members):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        for name, data in members.items():
            z.writestr(name, data)
    return buf.getvalue()


class ContentProblemTest(unittest.TestCase):
    def test_each_format_accepts_its_own_signature(self):
        self.assertIsNone(content_problem(".xls", XLS_MAGIC + b"rest"))
        self.assertIsNone(content_problem(".xlsx", zip_bytes({"xl/workbook.xml": "<workbook/>"})))
        self.assertIsNone(content_problem(".pdf", b"%PDF-1.7 rest"))
        self.assertIsNone(content_problem(".csv", "類・品目,総合\n1970,30.9\n".encode("shift_jis")))

    def test_an_html_error_page_is_rejected_under_every_extension(self):
        for suffix in (".xls", ".xlsx", ".pdf", ".csv"):
            self.assertIsNotNone(content_problem(suffix, HTML_PAGE), suffix)
            self.assertIsNotNone(content_problem(suffix, b"\xef\xbb\xbf  \n" + HTML_PAGE), suffix)

    def test_empty_unknown_and_wrong_zip_are_rejected(self):
        for suffix in (".xls", ".xlsx", ".pdf", ".csv"):
            self.assertIsNotNone(content_problem(suffix, b""), suffix)
        self.assertIsNotNone(content_problem(".txt", b"anything"))
        self.assertIsNotNone(content_problem(".xlsx", zip_bytes({"word/document.xml": "<w/>"})))
        self.assertIsNotNone(content_problem(".xlsx", XLS_MAGIC))

    @unittest.skipUnless(RAW_DIR.exists(), "raw/zaisei/ is local only")
    def test_every_file_already_fetched_passes(self):
        files = [p for p in RAW_DIR.rglob("*") if p.is_file() and p.suffix in (".xls", ".xlsx", ".pdf", ".csv")]
        self.assertTrue(files)
        for p in files:
            self.assertIsNone(content_problem(p.suffix, p.read_bytes()), p)


class XlsxSizeLimitTest(unittest.TestCase):
    def test_too_large_or_too_many_entries_is_refused_before_parsing(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "big.xlsx"
            path.write_bytes(zip_bytes({"xl/workbook.xml": "x" * 2000, "a": "1", "b": "2"}))
            for limit, value in (("MAX_UNCOMPRESSED_BYTES", 1000), ("MAX_ENTRIES", 2)):
                original = getattr(xlsx_read, limit)
                setattr(xlsx_read, limit, value)
                try:
                    with self.assertRaises(ValueError, msg=limit):
                        list(xlsx_read.read(path))
                finally:
                    setattr(xlsx_read, limit, original)


if __name__ == "__main__":
    unittest.main()
