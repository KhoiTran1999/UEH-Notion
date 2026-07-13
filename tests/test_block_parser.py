import unittest
import os
import sys

# Setup path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.utils.block_parser import parse_block, parse_rich_text


class TestBlockParserRobustness(unittest.TestCase):

    def test_parse_rich_text_invalid_types(self):
        # rich_text is None
        self.assertEqual(parse_rich_text(None), ("", "", [], True))
        # rich_text is not a list
        self.assertEqual(parse_rich_text("not a list"), ("", "", [], True))
        # rich_text elements that are not dicts are skipped
        self.assertEqual(parse_rich_text([None, "string"]), ("", "", [], True))
        # rich_text element is a dict without strikethrough
        self.assertEqual(parse_rich_text([None, "string", {}]), ("", "", [], False))

    def test_parse_rich_text_missing_or_none_fields(self):
        # plain_text is missing or None
        rich_text = [{"annotations": {"strikethrough": False}}]
        self.assertEqual(parse_rich_text(rich_text), ("", "", [], False))

        rich_text_none_plain = [{"plain_text": None, "annotations": {"strikethrough": False}}]
        self.assertEqual(parse_rich_text(rich_text_none_plain), ("", "", [], False))

        # annotations is None
        rich_text_none_annotations = [{"plain_text": "hello", "annotations": None}]
        self.assertEqual(parse_rich_text(rich_text_none_annotations), ("hello", "hello", [], False))

        # mention is None or missing type/date
        rich_text_mention = [
            {"plain_text": "@date", "mention": None},
            {"plain_text": "@date2", "mention": {"type": "date", "date": None}}
        ]
        self.assertEqual(parse_rich_text(rich_text_mention), ("@date@date2", "@date@date2", [], False))

    def test_parse_block_invalid_types(self):
        # block is None
        self.assertIsNone(parse_block(None))
        # block is not a dict
        self.assertIsNone(parse_block("not a dict"))
        # missing type
        self.assertIsNone(parse_block({}))
        # type exists but is None
        self.assertIsNone(parse_block({"type": None}))
        # type exists but data is missing/None
        self.assertIsNone(parse_block({"type": "to_do"}))
        self.assertIsNone(parse_block({"type": "to_do", "to_do": None}))

    def test_parse_block_callout_robustness(self):
        # callout property is None
        block_none_callout = {
            "type": "callout",
            "callout": None
        }
        self.assertIsNone(parse_block(block_none_callout))

        # callout with empty rich_text
        block_empty_text = {
            "type": "callout",
            "callout": {"rich_text": [], "icon": {"type": "emoji", "emoji": "💡"}}
        }
        self.assertIsNone(parse_block(block_empty_text))

        # callout icon is None
        block_none_icon = {
            "type": "callout",
            "callout": {
                "rich_text": [{"plain_text": "Callout message"}],
                "icon": None
            }
        }
        res = parse_block(block_none_icon)
        self.assertIsNotNone(res)
        self.assertEqual(res["text"], "💡 Callout message")

        # callout icon is missing
        block_missing_icon = {
            "type": "callout",
            "callout": {
                "rich_text": [{"plain_text": "Callout message"}]
            }
        }
        res = parse_block(block_missing_icon)
        self.assertIsNotNone(res)
        self.assertEqual(res["text"], "💡 Callout message")

        # callout icon type is file (emoji key missing)
        block_file_icon = {
            "type": "callout",
            "callout": {
                "rich_text": [{"plain_text": "Callout message"}],
                "icon": {"type": "file", "file": {"url": "https://example.com/icon.png"}}
            }
        }
        res = parse_block(block_file_icon)
        self.assertIsNotNone(res)
        self.assertEqual(res["text"], "💡 Callout message")

    def test_parse_block_todo_robustness(self):
        # todo checked is missing/None
        block_todo = {
            "type": "to_do",
            "to_do": {
                "rich_text": [{"plain_text": "Task to do"}],
                "checked": None
            }
        }
        res = parse_block(block_todo)
        self.assertIsNotNone(res)
        self.assertEqual(res["text"], "☐ Task to do")
        self.assertFalse(res["completed"])

        # todo checked is True
        block_todo_checked = {
            "type": "to_do",
            "to_do": {
                "rich_text": [{"plain_text": "Task done"}],
                "checked": True
            }
        }
        res_checked = parse_block(block_todo_checked)
        self.assertIsNotNone(res_checked)
        self.assertEqual(res_checked["text"], "☑ Task done")
        self.assertTrue(res_checked["completed"])

    def test_parse_block_divider(self):
        block_divider = {
            "type": "divider",
            "divider": {}
        }
        res = parse_block(block_divider)
        self.assertIsNotNone(res)
        self.assertEqual(res["text"], "---")

    def test_parse_block_strikethrough_completion(self):
        # A block containing any strikethrough element is considered completed
        block_partially_struck = {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "plain_text": "Done task ",
                        "annotations": {"strikethrough": True}
                    },
                    {
                        "plain_text": "and unstruck part",
                        "annotations": {"strikethrough": False}
                    }
                ]
            }
        }
        res = parse_block(block_partially_struck)
        self.assertIsNotNone(res)
        self.assertTrue(res["completed"])

        # A block with no strikethrough elements is not completed
        block_not_struck = {
            "type": "paragraph",
            "paragraph": {
                "rich_text": [
                    {
                        "plain_text": "Unstruck text",
                        "annotations": {"strikethrough": False}
                    }
                ]
            }
        }
        res2 = parse_block(block_not_struck)
        self.assertIsNotNone(res2)
        self.assertFalse(res2["completed"])


class TestTimelineSorting(unittest.TestCase):

    def test_parse_date_for_sorting(self):
        from src.services.timeline import _parse_date_for_sorting
        from datetime import datetime

        # Test ISO dates
        self.assertEqual(_parse_date_for_sorting("2026-07-15T09:00:00").year, 2026)
        self.assertEqual(_parse_date_for_sorting("2026-07-15T09:00:00").month, 7)
        self.assertEqual(_parse_date_for_sorting("2026-07-15T09:00:00").day, 15)
        self.assertEqual(_parse_date_for_sorting("2026-07-15T09:00:00").hour, 9)

        # Test standard DD/MM HH:MM dates
        parsed = _parse_date_for_sorting("15/07 09:00")
        self.assertEqual(parsed.month, 7)
        self.assertEqual(parsed.day, 15)
        self.assertEqual(parsed.hour, 9)

        # Test standard DD/MM dates
        parsed_day_only = _parse_date_for_sorting("20/07")
        self.assertEqual(parsed_day_only.month, 7)
        self.assertEqual(parsed_day_only.day, 20)
        self.assertEqual(parsed_day_only.hour, 0)

        # Test invalid or missing dates return max
        self.assertEqual(_parse_date_for_sorting(None), datetime.max)
        self.assertEqual(_parse_date_for_sorting("invalid_date"), datetime.max)


if __name__ == "__main__":
    unittest.main()
