import json
import os
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.services.study_logic import generate_quiz, parse_quiz_response


class TestQuizResponseParsing(unittest.TestCase):
    def test_extracts_json_array_from_fenced_ai_response(self):
        response = 'Kết quả:\n```json\n[{"q":"Câu hỏi?","options":["A","B"]}]\n```'

        questions = parse_quiz_response(response, 15)

        self.assertEqual(len(questions), 1)
        self.assertEqual(questions[0]["q"], "Câu hỏi?")
        self.assertEqual(questions[0]["id"], 1)

    def test_extracts_questions_from_multiple_chunk_arrays(self):
        response = '[{"q":"Câu 1?","options":["A","B"]}]\n[{"q":"Câu 2?","options":["A","B"]}]'

        questions = parse_quiz_response(response, 15)

        self.assertEqual([question["q"] for question in questions], ["Câu 1?", "Câu 2?"])
        self.assertEqual([question["id"] for question in questions], [1, 2])

    def test_uses_generated_quiz_when_latex_review_returns_invalid_response(self):
        raw_quiz = json.dumps([
            {"q": "Câu hỏi gốc?", "options": ["A", "B"], "correct": 0}
        ], ensure_ascii=False)
        ai = Mock()
        ai.generate_quiz.return_value = raw_quiz
        ai.enhance_quiz.return_value = "Phản hồi nâng cấp không hợp lệ"
        ai.review_latex_quiz.return_value = "Phản hồi rà soát không hợp lệ"

        with patch("src.services.study_logic.NotionService") as notion_service, \
             patch("src.services.study_logic.AIService", return_value=ai), \
             patch("src.services.study_logic.get_page_title", return_value="Bài học"), \
             patch("src.services.study_logic.get_redis", return_value=None):
            notion_service.return_value.fetch_page_content.return_value = ["Nội dung bài học"]
            result = generate_quiz("test-topic", force_refresh=True, num_questions=1)

        self.assertEqual(result["questions"][0]["q"], "Câu hỏi gốc?")
        self.assertEqual(result["num_questions"], 1)


if __name__ == "__main__":
    unittest.main()
