import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.katex_validator import validate_katex_formatting, validate_quiz_item_katex

class TestKaTeXValidatorEngine(unittest.TestCase):

    def test_image7_unwrapped_latex_detection(self):
        # Case directly from screenshot [Image #7]
        sample_img7 = r"Ta thiết lập phương trình cân bằng EPS: $$\frac{EBIT}{400} = \frac{EBIT - 640}{240}$$. Giải phương trình: 240 USD \times \text{EBIT} = 400 \times (\text{EBIT} -640) \Leftrightarrow 160 \times \text{EBIT} = 256.000 \Leftrightarrow \text{EBIT} = 1.600 USD."
        valid, errors = validate_katex_formatting(sample_img7)
        self.assertFalse(valid)
        self.assertTrue(any(r"\times" in err for err in errors))
        self.assertTrue(any(r"\Leftrightarrow" in err for err in errors))

    def test_image4_prose_in_math_detection(self):
        # Case directly from screenshot [Image #4]
        sample_img4 = r"Giá trị vốn cổ phần mới $S = 1.250 - 500 = 750 USD (lỗ vốn - 250 USD so với 1.000 USD ban đầu). Cổ đông nhận 500 USD tiền mặt cổ tức.$"
        valid, errors = validate_katex_formatting(sample_img4)
        self.assertFalse(valid)
        self.assertTrue(any("Vietnamese prose" in err for err in errors))

    def test_clean_katex_valid_case(self):
        sample_clean = r"Ta thiết lập phương trình cân bằng EPS: $$\frac{EBIT}{400} = \frac{EBIT - 640}{240}$$. Giải phương trình: $240\text{ USD} \times \text{EBIT} = 400 \times (\text{EBIT} - 640) \Leftrightarrow 160 \times \text{EBIT} = 256.000 \Leftrightarrow \text{EBIT} = 1.600\text{ USD}$."
        valid, errors = validate_katex_formatting(sample_clean)
        self.assertTrue(valid, f"Expected valid clean KaTeX string, but got errors: {errors}")

if __name__ == '__main__':
    unittest.main()
