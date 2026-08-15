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
        save_res = client.post("/api/study/progress", json={"telegram_id": telegram_id, "progress": progress_payload})
        self.assertEqual(save_res.status_code, 200)
        self.assertTrue(save_res.json().get("success"))

        # 2. Get progress
        get_res = client.get(f"/api/study/progress?telegram_id={telegram_id}")
        self.assertEqual(get_res.status_code, 200)
        retrieved = get_res.json().get("progress")
        self.assertIsNotNone(retrieved)
        self.assertEqual(retrieved["topic"]["id"], "test-topic-1")
        self.assertEqual(len(retrieved["quiz"]), 1)

        # 3. Clear progress
        del_res = client.delete(f"/api/study/progress/{telegram_id}")
        self.assertEqual(del_res.status_code, 200)
        self.assertTrue(del_res.json().get("success"))

        # 4. Verify cleared
        get_res_after = client.get(f"/api/study/progress?telegram_id={telegram_id}")
        self.assertEqual(get_res_after.status_code, 200)
        self.assertIsNone(get_res_after.json().get("progress"))


if __name__ == "__main__":
    unittest.main()
