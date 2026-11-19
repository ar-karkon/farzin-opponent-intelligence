"""Offline tests for the metadata generation utility; no Kaggle access."""

import importlib.util
import unittest
from pathlib import Path

path = Path(__file__).resolve().parents[1] / "scripts" / "configure_kaggle.py"
spec = importlib.util.spec_from_file_location("configure_kaggle", path)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


class TestMetadata(unittest.TestCase):
    def test_private_gpu_metadata(self):
        m = mod.build_metadata("example_user")
        self.assertEqual(m["id"], "example_user/foi-v1-gpu-smoke")
        self.assertTrue(m["is_private"])
        self.assertTrue(m["enable_gpu"])
        self.assertTrue(m["enable_internet"])
        self.assertEqual(m["machine_shape"], "NvidiaTeslaT4")
        self.assertEqual(m["code_file"], "foi_kaggle_smoke.py")

    def test_reject_bad_username(self):
        with self.assertRaises(ValueError):
            mod.build_metadata("me/secrets")


if __name__ == "__main__":
    unittest.main()
