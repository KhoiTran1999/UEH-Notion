import unittest
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from pydantic import ValidationError
from src.api.main import QuizRequest, BatchQuizRequest, TopicConfigItem
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

    def test_batch_quiz_request(self):
        valid_uuid_1 = "2eba5eb5-b9bd-81ef-830c-e6f5378ee35b"
        valid_uuid_2 = "39ca5eb5-b9bd-8066-a924-e857ee94c557"
        req = BatchQuizRequest(
            course="Tài chính doanh nghiệp",
            topics=[
                TopicConfigItem(topic_id=valid_uuid_1, title="Bài 1", num_questions=10, difficulty="easy", question_type="theory"),
                TopicConfigItem(topic_id=valid_uuid_2, title="Bài 2", num_questions=20, difficulty="hard", question_type="calculation")
            ]
        )
        self.assertEqual(req.course, "Tài chính doanh nghiệp")
        self.assertEqual(len(req.topics), 2)
        self.assertEqual(req.topics[0].num_questions, 10)
        self.assertEqual(req.topics[1].difficulty, "hard")

        with self.assertRaises(ValidationError):
            BatchQuizRequest(course="Test", topics=[])

if __name__ == "__main__":
    unittest.main()
