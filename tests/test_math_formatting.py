import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.study_logic import replace_currency_dollars
import re

class TestMathAndCurrencyFormatting(unittest.TestCase):

    def test_strip_markdown_inside_math_dollars(self):
        line = "phương trình định giá cốt lõi: **$*V = B + S*$**"
        cleaned = re.sub(r'\$\*+(.*?)\*+\$', r'$\1$', line)
        self.assertEqual(cleaned, "phương trình định giá cốt lõi: **$V = B + S$**")

    def test_replace_standalone_currency_dollars(self):
        text = "Giá cổ phiếu là $10 và tổng nợ là $1.000."
        res = replace_currency_dollars(text)
        self.assertEqual(res, "Giá cổ phiếu là USD 10 và tổng nợ là USD 1.000.")

    def test_preserve_latex_math_expressions(self):
        text = "Phương trình $V = B + S$ và $$FV = PV \\times (1 + r)^n$$"
        res = replace_currency_dollars(text)
        self.assertEqual(res, "Phương trình $V = B + S$ và $$FV = PV \\times (1 + r)^n$$")

if __name__ == '__main__':
    unittest.main()
