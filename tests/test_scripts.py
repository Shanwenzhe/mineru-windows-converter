"""Windows script regression tests; no real MinerU server or OCR is started.

Run: python -m unittest discover -s tests -p test_scripts.py -v
Set PANDOC_EXE and TYPST_EXE (or put them on PATH) for the real integration test.
Set SCRIPT_TEST_ARTIFACTS to retain that test's PDF, Typst source and PNG previews.
"""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
POWERSHELL = shutil.which("powershell.exe")
REAL_PANDOC = os.environ.get("PANDOC_EXE") or shutil.which("pandoc")
REAL_TYPST = os.environ.get("TYPST_EXE") or shutil.which("typst")

STUB = r'''
import json, os, pathlib, sys
kind, args = sys.argv[1], sys.argv[2:]
with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as log:
    log.write(json.dumps({"kind": kind, "args": args, "cwd": os.getcwd(),
        "home": os.environ.get("MINERU_HOME"), "encoding": os.environ.get("PYTHONIOENCODING")}) + "\n")
if kind == "mineru":
    if args[:2] == ["server", "start"]:
        sys.exit(int(os.environ.get("STUB_SERVER_EXIT", "0")))
    target = pathlib.Path(args[args.index("-o") + 1])
    if os.environ.get("STUB_MODE") != "empty":
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("# 新的中文结果\n", encoding="utf-8")
    if os.environ.get("STUB_MODE") == "failure":
        print("parse failed")
        sys.exit(7)
elif kind == "pandoc":
    target = pathlib.Path(args[args.index("-o") + 1])
    source = pathlib.Path(args[0]).read_text(encoding="utf-8-sig")
    with open(os.environ["STUB_LOG"], "a", encoding="utf-8") as log:
        log.write(json.dumps({"markdown": source}) + "\n")
    if os.environ.get("STUB_MODE") == "failure":
        sys.exit(8)
    target.write_text('= 中文\n$ integral_0^1 x^2 dif x = 1/3 $\n', encoding="utf-8")
elif kind == "typst":
    target = pathlib.Path(args[-1])
    if os.environ.get("STUB_MODE") == "failure":
        sys.exit(9)
    if "--format" in args:
        target = pathlib.Path(str(target).replace("{p}", "1"))
        target.write_bytes(b"PNG preview")
    else:
        target.write_bytes(b"%PDF-1.7\nscript test\n")
'''


@unittest.skipUnless(os.name == "nt" and POWERSHELL, "Windows PowerShell 5.1 required")
class ScriptTests(unittest.TestCase):
    def setUp(self):
        scratch = Path(os.environ.get("SCRIPT_TEST_TEMP", str(Path.cwd() / "work" / "script-tests")))
        scratch.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix="mineru-script-tests-", dir=scratch)
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        self.repo = self.directory / "portable repo"
        self.repo.mkdir()
        self.bin = self.directory / "bin"
        self.bin.mkdir()
        self.log = self.directory / "calls.jsonl"
        stub = self.bin / "stub.py"
        stub.write_text(STUB, encoding="utf-8")
        for command in ("mineru", "pandoc", "typst"):
            (self.bin / (command + ".cmd")).write_text(
                f'@"{sys.executable}" "{stub}" {command} %*\n', encoding="utf-8"
            )
        for name in ("pdf2md.ps1", "md2pdf.ps1"):
            source = (ROOT / name).read_text(encoding="utf-8-sig")
            # Only the legacy dependency paths are redirected during RED runs.
            # This prevents the old script from starting the user's real server.
            source = source.replace(
                r'E:\Tools\MinerU\venv\Scripts\mineru.exe', str(self.bin / "mineru.cmd")
            ).replace(
                r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe',
                str(self.bin / "never-start-a-browser.exe"),
            )
            (self.repo / name).write_text(source, encoding="utf-8-sig")
        if (ROOT / "templates").is_dir():
            shutil.copytree(ROOT / "templates", self.repo / "templates")
        self.input = self.directory / "input files"
        self.input.mkdir()
        self.pdf = self.input / "sample.pdf"
        self.pdf.write_bytes(b"original input PDF; must never change")
        self.md = self.input / "notes.md"
        self.md.write_text("# 中文\n\n$\\int_0^1 x^2\\,dx=\\frac13$\n\n![Image block](figure.svg)\n", encoding="utf-8")
        self.env = os.environ.copy()
        for key in ("MINERU_HOME", "MINERU_TIER", "PANDOC_EXE", "TYPST_EXE", "STUB_MODE"):
            self.env.pop(key, None)
        self.env.update(
            STUB_LOG=str(self.log), MINERU_EXE=str(self.bin / "mineru.cmd"),
            PANDOC_EXE=str(self.bin / "pandoc.cmd"), TYPST_EXE=str(self.bin / "typst.cmd"),
            PATH=str(self.bin) + os.pathsep + os.environ.get("PATH", ""),
        )

    def run_script(self, script, *args, env=None):
        return subprocess.run(
            [POWERSHELL, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
             "-File", str(self.repo / script), *map(str, args)],
            env=env or self.env, capture_output=True, text=True, encoding="utf-8", errors="replace",
            timeout=40,
        )

    def calls(self):
        if not self.log.exists():
            return []
        return [json.loads(line) for line in self.log.read_text(encoding="utf-8").splitlines()]

    def assert_failed(self, result):
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)

    def test_pdf_existing_output_is_rejected_without_touching_input_or_old_result(self):
        output = self.input / "sample_mineru"
        output.mkdir()
        marker = output / "sample.md"
        marker.write_text("previous result", encoding="utf-8")
        original = self.pdf.read_bytes()
        self.assert_failed(self.run_script("pdf2md.ps1", self.pdf))
        self.assertEqual(self.pdf.read_bytes(), original)
        self.assertEqual(marker.read_text(encoding="utf-8"), "previous result")
        self.assertEqual(self.calls(), [])

    def test_pdf_invalid_pages_fail_before_dependencies_or_output_creation(self):
        for pages in ("0", "-1", "5-2", "1,,3", "1-0", "abc"):
            with self.subTest(pages=pages):
                self.assert_failed(self.run_script("pdf2md.ps1", self.pdf, pages))
        self.assertEqual(self.calls(), [])
        self.assertEqual(set(self.input.iterdir()), {self.pdf, self.md})

    def test_pdf_missing_configured_dependency_fails_before_output_creation(self):
        self.env["MINERU_EXE"] = str(self.bin / "missing.exe")
        self.assert_failed(self.run_script("pdf2md.ps1", self.pdf))
        self.assertFalse((self.input / "sample_mineru").exists())
        self.assertEqual(self.calls(), [])

    def test_pdf_success_uses_independent_directory_and_portable_defaults(self):
        result = self.run_script("pdf2md.ps1", self.pdf)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("新的中文结果", (self.input / "sample_mineru" / "sample.md").read_text(encoding="utf-8"))
        self.assertEqual(self.pdf.read_bytes(), b"original input PDF; must never change")
        parse = next(call for call in self.calls() if call.get("args", [None])[0] == "parse")
        self.assertEqual(parse["home"], str(self.repo / "home"))
        self.assertEqual(parse["encoding"], "utf-8")
        self.assertEqual(parse["args"][parse["args"].index("--tier") + 1], "standard")

    def test_pdf_page_selection_and_explicit_environment_are_respected(self):
        self.env.update(MINERU_HOME=str(self.directory / "custom home"), MINERU_TIER="fast")
        result = self.run_script("pdf2md.ps1", self.pdf, "1-5,8")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.input / "sample_mineru_p1-5,8" / "sample.md").is_file())
        parse = next(call for call in self.calls() if call.get("args", [None])[0] == "parse")
        self.assertEqual(parse["home"], self.env["MINERU_HOME"])
        self.assertEqual(parse["args"][parse["args"].index("--tier") + 1], "fast")

    def test_pdf_nonzero_parse_exit_fails_even_if_partial_markdown_exists(self):
        self.env["STUB_MODE"] = "failure"
        self.assert_failed(self.run_script("pdf2md.ps1", self.pdf))

    def test_pdf_zero_exit_without_nonempty_markdown_fails(self):
        self.env["STUB_MODE"] = "empty"
        self.assert_failed(self.run_script("pdf2md.ps1", self.pdf))

    def test_pdf_server_failure_is_not_reported_as_success(self):
        self.env["STUB_SERVER_EXIT"] = "6"
        self.assert_failed(self.run_script("pdf2md.ps1", self.pdf))
        self.assertFalse(any(call.get("args", [None])[0] == "parse" for call in self.calls()))

    def test_markdown_existing_pdf_or_typst_is_never_overwritten(self):
        for extension in (".pdf", ".typ"):
            with self.subTest(extension=extension):
                target = self.md.with_suffix(extension)
                target.write_bytes(b"original existing artifact")
                self.assert_failed(self.run_script("md2pdf.ps1", self.md))
                self.assertEqual(target.read_bytes(), b"original existing artifact")
                target.unlink()
        self.assertEqual(self.calls(), [])

    def test_markdown_missing_dependency_fails_without_creating_outputs(self):
        self.env["PANDOC_EXE"] = str(self.bin / "missing.exe")
        self.assert_failed(self.run_script("md2pdf.ps1", self.md))
        self.assertFalse(self.md.with_suffix(".typ").exists())
        self.assertFalse(self.md.with_suffix(".pdf").exists())
        self.assertFalse((self.input / "math-doc.typ").exists())
        self.assertEqual(self.calls(), [])

    def test_markdown_different_existing_template_is_preserved(self):
        template = self.input / "math-doc.typ"
        template.write_text("user's own template", encoding="utf-8")
        self.assert_failed(self.run_script("md2pdf.ps1", self.md))
        self.assertEqual(template.read_text(encoding="utf-8"), "user's own template")
        self.assertEqual(self.calls(), [])

    def test_markdown_pipeline_preserves_images_and_resolves_relative_paths(self):
        result = self.run_script("md2pdf.ps1", self.md)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        source = self.md.with_suffix(".typ").read_text(encoding="utf-8-sig")
        self.assertTrue(source.startswith('#import "math-doc.typ": *\n#show: doc.with(title: "notes", author: "")\n'))
        self.assertIn("integral_0^1", source)
        self.assertTrue(self.md.with_suffix(".pdf").stat().st_size > 0)
        self.assertTrue((self.input / "notes-preview-1.png").stat().st_size > 0)
        self.assertEqual((self.input / "math-doc.typ").read_bytes(), (self.repo / "templates" / "math-doc.typ").read_bytes())
        calls = self.calls()
        pandoc = next(call for call in calls if call.get("kind") == "pandoc")
        self.assertEqual(Path(pandoc["cwd"]), self.input)
        self.assertIn("typst", pandoc["args"])
        self.assertIn("![Image block](figure.svg)", next(call["markdown"] for call in calls if "markdown" in call))

    def test_markdown_nonzero_converter_exit_is_failure(self):
        self.env["STUB_MODE"] = "failure"
        self.assert_failed(self.run_script("md2pdf.ps1", self.md))
        self.assertFalse(self.md.with_suffix(".pdf").exists())

    @unittest.skipUnless(REAL_PANDOC and REAL_TYPST, "Set PANDOC_EXE/TYPST_EXE for real compile + preview")
    def test_real_pandoc_typst_chinese_math_and_relative_illustration(self):
        target = Path(os.environ.get("SCRIPT_TEST_ARTIFACTS", str(self.input / "real sample")))
        target.mkdir(parents=True, exist_ok=True)
        md = target / "中文公式验证.md"
        md.write_text(
            "# 中文与数学公式\n\n这是一份中文公式验证文档。\n\n"
            "$\\int_0^1 x^2\\,dx=\\frac{1}{3}$\n\n"
            "$$\\sum_{k=1}^{n}k=\\frac{n(n+1)}{2}$$\n\n"
            "![保留相对路径插图](figure.svg)\n", encoding="utf-8"
        )
        (target / "figure.svg").write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="180" height="80">'
            '<rect x="5" y="5" width="160" height="60" fill="#dbeafe" stroke="#2563eb"/>'
            '<circle cx="85" cy="35" r="20" fill="#16a34a"/></svg>', encoding="utf-8"
        )
        self.env.update(PANDOC_EXE=str(REAL_PANDOC), TYPST_EXE=str(REAL_TYPST))
        result = self.run_script("md2pdf.ps1", md)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertGreater(md.with_suffix(".pdf").stat().st_size, 1000)
        source = md.with_suffix(".typ").read_text(encoding="utf-8-sig")
        self.assertIn("中文", source)
        self.assertNotIn(r"\frac", source)
        self.assertNotIn(r"\int", source)
        previews = list(target.glob("中文公式验证-preview-*.png"))
        self.assertTrue(previews)
        self.assertTrue(all(path.stat().st_size > 1000 for path in previews))


if __name__ == "__main__":
    unittest.main()
