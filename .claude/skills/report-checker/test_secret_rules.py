"""Password and image-caption rules in check_reports.py and render_report.py.

Run: python -m unittest discover -s .claude/skills/report-checker -p "test_*.py"
"""

import importlib.util
import sys
import unittest
from pathlib import Path

from docx import Document

SKILLS = Path(__file__).resolve().parent.parent


def load(name: str, relative: str):
    spec = importlib.util.spec_from_file_location(name, SKILLS / relative)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


checker = load("check_reports", "report-checker/check_reports.py")
renderer = load("render_report", "report-renderer/render_report.py")


def table_report(label: str, value: str) -> Document:
    document = Document()
    row = document.add_table(rows=1, cols=2).rows[0]
    row.cells[0].text, row.cells[1].text = label, value
    return document


def paragraph_report(text: str) -> Document:
    document = Document()
    document.add_paragraph(text)
    return document


class PasswordRuleTests(unittest.TestCase):
    def test_descriptive_password_text_passes(self):
        self.assertFalse(checker.document_has_unmasked_secret(
            table_report("Password", "The normal password from the login page")))
        self.assertEqual(renderer.check_secrets("Password | The normal password from the login page"), [])

    def test_demo_password_in_table_fails(self):
        self.assertTrue(checker.document_has_unmasked_secret(table_report("Password", "admin123")))
        self.assertTrue(renderer.check_secrets("Password | admin123"))

    def test_labelled_password_with_symbols_fails(self):
        self.assertTrue(checker.document_has_unmasked_secret(paragraph_report("password=Xy7!kq2")))
        self.assertTrue(renderer.check_secrets("password=Xy7!kq2"))


class SensitiveCaptionTests(unittest.TestCase):
    def test_sensitive_label_is_parsed(self):
        self.assertEqual(renderer.sensitive_label(" SENSITIVE: email, bearer token"), (True, "email, bearer token"))

    def test_other_caption_text_is_ignored(self):
        self.assertEqual(renderer.sensitive_label(" Warning: restrict sharing"), (False, ""))


if __name__ == "__main__":
    unittest.main()
