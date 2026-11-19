import tempfile
import unittest
from pathlib import Path

from scripts.publication_safety import check_tree


class PublicationSafetyTests(unittest.TestCase):
    def test_accepts_text_source_and_example_config(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "configs").mkdir()
            (root / "configs" / "players.example.yaml").write_text("players: []\n", encoding="utf-8")
            (root / "module.py").write_text("value = 1\n", encoding="utf-8")
            self.assertEqual(check_tree(root), [])

    def test_rejects_private_game_data_and_token_pattern(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "private.pgn").write_text("synthetic", encoding="utf-8")
            (root / "module.py").write_text("token = 'ghp_" + "A" * 30 + "'\n", encoding="utf-8")
            problems = check_tree(root)
            self.assertTrue(any("private or binary artifact" in item for item in problems))
            self.assertTrue(any("possible credential" in item for item in problems))


if __name__ == "__main__":
    unittest.main()
