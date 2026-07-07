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


if __name__ == "__main__":
    unittest.main()
