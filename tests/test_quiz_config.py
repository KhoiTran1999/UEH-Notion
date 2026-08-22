import unittest
from pydantic import ValidationError
from src.api.main import QuizRequest
from src.services.study_logic import clear_quiz_cache

class TestQuizCustomConfig(unittest.TestCase):
    def test_quiz_request_valid_custom_config(self):
        valid_uuid = "2eba5eb5-b9bd-81ef-830c-e6f5378ee35b"
        req = QuizRequest(
            topic_id=valid_uuid,
            force_refresh=True,
            num_questions=20,
            difficulty="hard",
            question_type="calculation"
        )
        self.assertEqual(req.topic_id, valid_uuid)
        self.assertTrue(req.force_refresh)
        self.assertEqual(req.num_questions, 20)
        self.assertEqual(req.difficulty, "hard")
        self.assertEqual(req.question_type, "calculation")

    def test_quiz_request_defaults(self):
        valid_uuid = "2eba5eb5b9bd81ef830ce6f5378ee35b"
        req = QuizRequest(topic_id=valid_uuid)
        self.assertEqual(req.num_questions, 15)
        self.assertEqual(req.difficulty, "medium")
        self.assertEqual(req.question_type, "balanced")

    def test_quiz_request_invalid_limits(self):
        valid_uuid = "2eba5eb5-b9bd-81ef-830c-e6f5378ee35b"
        with self.assertRaises(ValidationError):
            QuizRequest(topic_id=valid_uuid, num_questions=0)
        with self.assertRaises(ValidationError):
            QuizRequest(topic_id=valid_uuid, num_questions=50)

    def test_quiz_request_fallback_enum(self):
        valid_uuid = "2eba5eb5-b9bd-81ef-830c-e6f5378ee35b"
        req = QuizRequest(topic_id=valid_uuid, difficulty="invalid_diff", question_type="invalid_type")
        self.assertEqual(req.difficulty, "medium")
        self.assertEqual(req.question_type, "balanced")

if __name__ == "__main__":
    unittest.main()
