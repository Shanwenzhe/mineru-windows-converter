"""Regression tests for conversion output safety; no OCR or GUI session required."""
import importlib.machinery
import importlib.util
from pathlib import Path
import queue
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader("converter", str(ROOT / "MinerU转换器.pyw"))
spec = importlib.util.spec_from_loader(loader.name, loader)
converter = importlib.util.module_from_spec(spec)
loader.exec_module(converter)


class ConversionSafetyTests(unittest.TestCase):
    def app(self, runner):
        app = converter.App.__new__(converter.App)
        app.q = queue.Queue()
        app.run = runner
        return app

    def test_success_writes_separate_pdf_and_preserves_original(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "课本.pdf"
            source.write_bytes(b"original-pdf")
            output = Path(directory) / "课本_mineru"

            def run(command):
                script = next(item for item in command if item.endswith(".ps1"))
                if Path(script).name == "pdf2md.ps1":
                    output.mkdir()
                    (output / "课本.md").write_text("识别结果", encoding="utf-8")
                else:
                    Path(command[-1]).with_suffix(".pdf").write_bytes(b"new-pdf")
                return 0

            app = self.app(run)
            app.work([str(source)], "all", True, True)
            self.assertEqual(source.read_bytes(), b"original-pdf")
            self.assertTrue((output / "课本.pdf").is_file())
            self.assertEqual((output / "课本.md").read_text(encoding="utf-8"), "识别结果")

    def test_parse_failure_does_not_consume_or_delete_stale_markdown(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "book.pdf"
            source.write_bytes(b"original-pdf")
            stale = source.with_suffix(".md")
            stale.write_text("previous-result", encoding="utf-8")
            app = self.app(lambda command: 1)
            app.work([str(source)], "all", True, False)
            self.assertTrue(stale.is_file(), "A failed conversion deleted a pre-existing Markdown file")
            self.assertEqual(stale.read_text(encoding="utf-8"), "previous-result")
            self.assertEqual(source.read_bytes(), b"original-pdf")

    def test_worker_exception_always_signals_gui_recovery(self):
        def fail(command):
            raise OSError("Cannot start PowerShell")

        app = self.app(fail)
        app.work(["missing.pdf"], "all", True, False)
        messages = list(app.q.queue)
        self.assertTrue(messages)
        self.assertIsNone(messages[-1], "The GUI must be re-enabled after an error")
        self.assertTrue(any(isinstance(item, str) and "Cannot start PowerShell" in item for item in messages))

    def test_existing_output_directory_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "book.pdf"
            source.write_bytes(b"original-pdf")
            output = Path(directory) / "book_mineru"
            output.mkdir()
            markdown = output / "book.md"
            pdf = output / "book.pdf"
            markdown.write_bytes(b"previous-markdown")
            pdf.write_bytes(b"previous-pdf")
            app = self.app(lambda command: 0)
            app.work([str(source)], "all", True, False)
            self.assertEqual(markdown.read_bytes(), b"previous-markdown")
            self.assertEqual(pdf.read_bytes(), b"previous-pdf")
            self.assertEqual(source.read_bytes(), b"original-pdf")

    def test_failed_or_missing_parse_output_never_reaches_pdf_conversion(self):
        for code, content in [(1, b"partial"), (0, None), (0, b"")]:
            with self.subTest(code=code, content=content), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "book.pdf"
                source.write_bytes(b"original-pdf")
                output = Path(directory) / "book_mineru"

                def run(command):
                    script = next(item for item in command if item.endswith(".ps1"))
                    if Path(script).name == "pdf2md.ps1":
                        output.mkdir()
                        if content is not None:
                            (output / "book.md").write_bytes(content)
                        return code
                    (output / "book.pdf").write_bytes(b"should-not-be-created")
                    return 0

                app = self.app(run)
                app.work([str(source)], "all", True, False)
                self.assertFalse((output / "book.pdf").exists())
                self.assertEqual(source.read_bytes(), b"original-pdf")

    def test_pdf_failure_keeps_this_runs_markdown(self):
        for code, content in [(1, b"partial-pdf"), (0, None), (0, b"")]:
            with self.subTest(code=code, content=content), tempfile.TemporaryDirectory() as directory:
                source = Path(directory) / "book.pdf"
                source.write_bytes(b"original-pdf")
                output = Path(directory) / "book_mineru"

                def run(command):
                    script = next(item for item in command if item.endswith(".ps1"))
                    if Path(script).name == "pdf2md.ps1":
                        output.mkdir()
                        (output / "book.md").write_bytes(b"this-runs-markdown")
                        return 0
                    if content is not None:
                        (output / "book.pdf").write_bytes(content)
                    return code

                app = self.app(run)
                app.work([str(source)], "all", True, False)
                self.assertEqual((output / "book.md").read_bytes(), b"this-runs-markdown")
                self.assertEqual(source.read_bytes(), b"original-pdf")


if __name__ == "__main__":
    unittest.main()
