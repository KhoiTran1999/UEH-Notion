import unittest
from unittest.mock import MagicMock, patch
import sys
import os

# Add src to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.services.ai import AIService
from src.config.settings import Config

class TestAIServiceRotation(unittest.TestCase):
    def setUp(self):
        # Mock Config to have 3 fake keys
        self.original_keys = Config.GEMINI_API_KEYS
        Config.GEMINI_API_KEYS = ["key1", "key2", "key3"]

    def tearDown(self):
        Config.GEMINI_API_KEYS = self.original_keys

    @patch('src.services.ai.genai.Client')
    def test_rotation_on_failure(self, mock_client_cls):
        # Setup mock client
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        
        # Setup generate_content to fail on first 2 calls, succeed on 3rd
        # Side effect needs to handle re-instantiation of client
        
        # We need to control the behavior based on the key used or call count
        # Since AIService instantiates a new client (or updates), we can mock the generate_content 
        # of the *instance* returned by client.
        
        # Simulating failures:
        # call 1 (key1): raises Exception
        # call 2 (key2): raises Exception
        # call 3 (key3): returns success
        
        mock_models = MagicMock()
        mock_instance.models = mock_models
        
        # We act on the `generate_content` method of the `models` property
        # side_effect can be an iterable
        mock_models.generate_content.side_effect = [
            Exception("Quota limit reached"),
            Exception("Server error"),
            MagicMock(text="Success response")
        ]

        service = AIService()
        
        # Initial check
        self.assertEqual(service.current_key_index, 0)
        self.assertEqual(service.api_keys[0], "key1")

        # Run method
        result = service.generate_content("test prompt")
        
        # Verify result
        self.assertEqual(result, "Success response")
        
        # Verify rotation happened twice (index 0 -> 1 -> 2)
        self.assertEqual(service.current_key_index, 2)
        
        # Verify generate_content was called 3 times
        self.assertEqual(mock_models.generate_content.call_count, 3)

    @patch('src.services.ai.genai.Client')
    def test_all_keys_fail(self, mock_client_cls):
        mock_instance = MagicMock()
        mock_client_cls.return_value = mock_instance
        mock_instance.models.generate_content.side_effect = Exception("Fail")
        
        service = AIService()
        result = service.generate_content("test prompt")
        
        self.assertTrue(result.startswith("Error: All API keys failed"))
        self.assertEqual(mock_instance.models.generate_content.call_count, 3)

if __name__ == '__main__':
    unittest.main()
