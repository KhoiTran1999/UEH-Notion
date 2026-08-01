import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.study_logic import sanitize_quiz_text, sanitize_quiz_item

class TestMathAndCurrencyFormatting(unittest.TestCase):

    def test_sanitize_broken_backslashes_and_currency(self):
        sample = "A. Lỗ ròng \\USD 250 do giá trị vốn cổ phần S giảm từ \\$1.000 xuống \\$750."
        res = sanitize_quiz_text(sample)
        self.assertEqual(res, "A. Lỗ ròng 250 USD do giá trị vốn cổ phần S giảm từ 1.000 USD xuống 750 USD.")

    def test_sanitize_complex_explanation_text(self):
        sample = "Khi V tăng từ \\ 1.000 lên $1.250, giá trị vốn cổ phần S còn lại trong công ty là \\1.250 - $500 = $750 USD (cổ đông bị lỗ vốn -\\ 250 USD). Tuy nhiên, cổ đông nhận được +\\ 500 USD tiền mặt cổ tức, nên tổng lợi ích ròng là -\\$250 + \\$500 = +\\$250 USD, tương ứng đúng bằng phần giá trị công ty tăng thêm."
        res = sanitize_quiz_text(sample)
        self.assertNotIn("\\USD", res)
        self.assertNotIn("\\$", res)
        self.assertNotIn("$1.250", res)
        self.assertIn("1.250 USD", res)
        self.assertIn("+250 USD", res)

    def test_unwrap_fake_math_vietnamese_text(self):
        sample = "giá trị vốn cổ phần S còn lại trong công ty là 1.250 USD"
        res = sanitize_quiz_text(sample)
        self.assertEqual(res, "giá trị vốn cổ phần S còn lại trong công ty là 1.250 USD")

    def test_preserve_real_katex_math(self):
        sample = "Phương trình $V = B + S$ và $$FV = PV \\times (1 + r)^n$$"
        res = sanitize_quiz_text(sample)
        self.assertEqual(res, "Phương trình $V = B + S$ và $$FV = PV \\times (1 + r)^n$$")

    def test_sanitize_quiz_item_dict(self):
        item = {
            "q": "Giả sử $100 nợ",
            "options": ["A. \\$100", "B. \\USD 200"],
            "explanation": "Do \\$100 giảm"
        }
        res = sanitize_quiz_item(item)
        self.assertEqual(res["q"], "Giả sử 100 USD nợ")
        self.assertEqual(res["options"][0], "A. 100 USD")
        self.assertEqual(res["options"][1], "B. 200 USD")
        self.assertEqual(res["explanation"], "Do 100 USD giảm")

if __name__ == '__main__':
    unittest.main()
