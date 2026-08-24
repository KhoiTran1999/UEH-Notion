import unittest
import os
import json
import warnings
from dotenv import load_dotenv

# Setup path
import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

load_dotenv()
warnings.filterwarnings('ignore')


class TestUEHNotion(unittest.TestCase):

    def setUp(self):
        from src.config.settings import Config
        self.config = Config
        # Ensure we have access to variables
        self.assertTrue(Config.NOTION_TOKEN, "NOTION_TOKEN is missing")
        self.assertTrue(Config.REDIS_URL, "REDIS_URL is missing")

    def test_redis_cache_module(self):
        """Test utils/cache singleton & constants."""
        from src.utils.cache import get_redis, CACHE_QUIZ_TTL
        r = get_redis()
        self.assertIsNotNone(r, "Redis client should be initialized")
        self.assertTrue(r.ping(), "Redis ping failed")

        r.set("test_key_integration", "ok", ex=10)
        self.assertEqual(r.get("test_key_integration"), "ok")
        r.delete("test_key_integration")
        self.assertIsNone(r.get("test_key_integration"))
        self.assertEqual(CACHE_QUIZ_TTL, 14 * 24 * 3600)

    def test_notion_service_connection(self):
        """Test NotionService initialization and database query."""
        from src.services.notion import NotionService
        notion = NotionService()
        self.assertIsNotNone(notion.headers)
        self.assertIn("Authorization", notion.headers)

        # Retrieve a page or candidate just to verify API credentials
        candidates = notion.get_review_notes()
        self.assertIsInstance(candidates, list)

    def test_study_logic_candidates(self):
        """Test study_logic functions."""
        from src.services.study_logic import get_candidates
        # Call with force_refresh to fetch raw from Notion and save to Redis
        candidates = get_candidates(force_refresh=True)
        self.assertIsInstance(candidates, list)
        if candidates:
            first = candidates[0]
            self.assertIn("id", first)
            self.assertIn("title", first)

    def test_get_page_title(self):
        """Test get_page_title with cache and fallback."""
        from src.services.study_logic import get_candidates, get_page_title
        candidates = get_candidates()
        if candidates:
            title = get_page_title(candidates[0]["id"])
            self.assertEqual(title, candidates[0]["title"])

    def test_clear_quiz_cache(self):
        """Test clear_quiz_cache function."""
        from src.services.study_logic import clear_quiz_cache
        from src.utils.cache import get_redis
        r = get_redis()
        if r:
            r.set("quiz_test-uuid-123", "dummy_quiz")
            self.assertEqual(r.get("quiz_test-uuid-123"), "dummy_quiz")
            res = clear_quiz_cache("test-uuid-123")
            self.assertTrue(res)
            self.assertIsNone(r.get("quiz_test-uuid-123"))

    def test_run_background_safe(self):
        """Test background task safety wrapper."""
        from src.api.main import run_background_safe

        # Test success case
        runs = []
        run_background_safe(lambda x: runs.append(x), "ok")
        self.assertEqual(runs, ["ok"])

        # Test crash case (should swallow exception, log it, and not raise it)
        def crashing_func():
            raise ValueError("Test error alert")

        # This shouldn't raise any exception
        run_background_safe(crashing_func)

    def test_generate_quick_review_filter_and_all_questions(self):
        """Test generate_quick_review logic with course filtering and taking all questions."""
        from unittest.mock import patch
        from src.services.study_logic import generate_quick_review

        mock_candidates = [
            {"id": "uuid-1", "title": "Bài 1", "course": "Tài chính doanh nghiệp"},
            {"id": "uuid-2", "title": "Bài 2", "course": "Tài chính doanh nghiệp"},
            {"id": "uuid-3", "title": "Bài 3", "course": "Kinh tế vi mô"}
        ]

        def mock_generate_quiz(topic_id, **kwargs):
            if topic_id == "uuid-1":
                return {"id": topic_id, "title": "Bài 1", "questions": [{"q": f"Q1-{i}", "options": ["A"], "correct": 0} for i in range(6)]}
            elif topic_id == "uuid-2":
                return {"id": topic_id, "title": "Bài 2", "questions": [{"q": f"Q2-{i}", "options": ["A"], "correct": 0} for i in range(6)]}
            elif topic_id == "uuid-3":
                return {"id": topic_id, "title": "Bài 3", "questions": [{"q": f"Q3-{i}", "options": ["A"], "correct": 0} for i in range(4)]}
            return None

        with patch("src.services.study_logic.get_candidates", return_value=mock_candidates), \
             patch("src.services.study_logic.generate_quiz", side_effect=mock_generate_quiz):
            # 1. Test filtered by course -> should get 6 + 6 = 12 questions (more than 10)
            res_course = generate_quick_review(course="Tài chính doanh nghiệp")
            self.assertIsNotNone(res_course)
            self.assertEqual(len(res_course["questions"]), 12)
            self.assertEqual(res_course["title"], "Ôn tập nhanh - Tài chính doanh nghiệp")
            for q in res_course["questions"]:
                self.assertIn(q["topic_title"], ["Bài 1", "Bài 2"])

            # 2. Test All courses -> should get 6 + 6 + 4 = 16 questions
            res_all = generate_quick_review()
            self.assertIsNotNone(res_all)
            self.assertEqual(len(res_all["questions"]), 16)
            self.assertEqual(res_all["title"], "Ôn tập tổng hợp")

            # 3. Test non-existent course -> returns None
            res_none = generate_quick_review(course="Môn không tồn tại")
            self.assertIsNone(res_none)

    def test_quiz_progress_endpoints(self):
        """Test quiz progress save, get, and clear endpoints."""
        from fastapi.testclient import TestClient
        from src.api.main import app

        client = TestClient(app)
        telegram_id = "test_user_9999"
        progress_payload = {
            "topic": {"id": "test-topic-1", "title": "Test Topic"},
            "quiz": [{"q": "Q1", "options": ["A", "B"], "correct": 0, "selected": 0}],
            "currentIndex": 0,
            "savedAt": 1234567890
        }

        # 1. Save progress
        save_res = client.post("/api/study/progress", json={"telegram_id": telegram_id, "topic_id": "test-topic-1", "progress": progress_payload})
        self.assertEqual(save_res.status_code, 200)
        self.assertTrue(save_res.json().get("success"))

        # 2. Get progress by topic
        get_res = client.get(f"/api/study/progress?telegram_id={telegram_id}&topic_id=test-topic-1")
        self.assertEqual(get_res.status_code, 200)
        retrieved = get_res.json().get("progress")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["topic"]["id"], "test-topic-1")
        self.assertEqual(len(retrieved["quiz"]), 1)

        # 3. Get all progress
        get_all_res = client.get(f"/api/study/progress?telegram_id={telegram_id}")
        self.assertEqual(get_all_res.status_code, 200)
        all_progress = get_all_res.json().get("progress")
        self.assertIsNotNone(all_progress)
        self.assertIn("test-topic-1", all_progress)

        # 4. Clear progress for topic
        del_res = client.delete(f"/api/study/progress/{telegram_id}?topic_id=test-topic-1")
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.json().get("success"))

        # 5. Verify cleared
        get_res_after = client.get(f"/api/study/progress?telegram_id={telegram_id}&topic_id=test-topic-1")
        self.assertEqual(get_res_after.status_code, 200)
        self.assertIsNone(get_res_after.json().get("progress"))

    def test_uuid_validation_pattern(self):
        """Test UUID validation accepts both 36-char hyphenated and 32-char hex Notion IDs."""
        from src.api.main import UUID_PATTERN
        self.assertTrue(UUID_PATTERN.match("2eba5eb5-b9bd-81ef-830c-e6f5378ee35b"))
        self.assertTrue(UUID_PATTERN.match("2eba5eb5b9bd81ef830ce6f5378ee35b"))
        self.assertIsNone(UUID_PATTERN.match("invalid-uuid-format"))

    def test_update_status_cache_invalidation_pattern(self):
        """Test that update_status clears all study_candidates* parameterized keys."""
        from src.services.study_logic import update_status
        from src.utils.cache import get_redis
        from unittest.mock import patch, MagicMock

        r = get_redis()
        if r:
            r.set("study_candidates_all", "dummy_all")
            r.set("study_candidates_10", "dummy_10")
            r.set("study_candidates_5", "dummy_5")

            with patch("src.services.notion.NotionService.update_page_property", return_value=True):
                res = update_status("test-uuid-topic", status="da_nam_vung")
                self.assertTrue(res)

            # All candidate cache variations must be cleared
            self.assertIsNone(r.get("study_candidates_all"))
            self.assertIsNone(r.get("study_candidates_10"))
            self.assertIsNone(r.get("study_candidates_5"))

    def test_quiz_generation_cache_poisoning_guard(self):
        """Test that invalid/failed quiz payloads are not cached into Redis."""
        from src.services.study_logic import generate_quiz
        from src.utils.cache import get_redis
        from unittest.mock import patch

        r = get_redis()
        test_topic_id = "test-error-topic-uuid"
        if r:
            r.delete(f"quiz_{test_topic_id}")

            with patch("src.services.notion.NotionService.fetch_page_content", return_value=["Some lesson content"]), \
                 patch("src.services.study_logic.get_page_title", return_value="Test Lesson"), \
                 patch("src.services.ai.AIService.generate_quiz", return_value="Broken AI raw response"), \
                 patch("src.services.ai.AIService.review_quiz", return_value="Still broken"), \
                 patch("src.services.ai.AIService.review_latex_quiz", return_value="Invalid JSON response not matching schema"):

                res = generate_quiz(test_topic_id, force_refresh=True)
                self.assertIsNotNone(res)
                self.assertEqual(res["questions"][0]["q"], "Lỗi tạo câu hỏi trắc nghiệm")

                # The cache MUST NOT store this broken quiz
                cached = r.get(f"quiz_{test_topic_id}")
                self.assertIsNone(cached, "Corrupted/error quiz should never be cached in Redis")

    def test_batch_quiz_stream_generation(self):
        """Test batch quiz generation streaming logic and endpoint."""
        from fastapi.testclient import TestClient
        from unittest.mock import patch
        from src.api.main import app

        client = TestClient(app)
        valid_uuid_1 = "2eba5eb5-b9bd-81ef-830c-e6f5378ee35b"
        valid_uuid_2 = "39ca5eb5-b9bd-8066-a924-e857ee94c557"

        def mock_generate_quiz(topic_id, **kwargs):
            return {
                "id": topic_id,
                "title": f"Title for {topic_id}",
                "num_questions": kwargs.get("num_questions", 15),
                "questions": [{"q": f"Question 1 for {topic_id}", "options": ["A", "B"], "correct": 0}]
            }

        with patch("src.services.study_logic.generate_quiz", side_effect=mock_generate_quiz):
            payload = {
                "course": "Tài chính doanh nghiệp",
                "topics": [
                    {"topic_id": valid_uuid_1, "title": "Topic 1", "num_questions": 5, "difficulty": "easy", "question_type": "theory"},
                    {"topic_id": valid_uuid_2, "title": "Topic 2", "num_questions": 10, "difficulty": "hard", "question_type": "calculation"}
                ]
            }
            res = client.post("/api/study/batch-quiz", json=payload)
            self.assertEqual(res.status_code, 200)
            lines = [json.loads(line) for line in res.text.strip().split("\n") if line.strip()]

            event_types = [item.get("type") for item in lines]
            self.assertIn("batch_started", event_types)
            self.assertIn("topic_completed", event_types)
            self.assertIn("batch_finished", event_types)

            finished_event = next(item for item in lines if item.get("type") == "batch_finished")
            self.assertEqual(finished_event["total_topics"], 2)
            self.assertEqual(finished_event["successful_topics"], 2)


if __name__ == "__main__":
    unittest.main()
