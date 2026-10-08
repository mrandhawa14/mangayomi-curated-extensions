import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parent.parent / "scripts" / "build_index.py"
SPEC = importlib.util.spec_from_file_location("build_index", MODULE_PATH)
assert SPEC and SPEC.loader
build_index = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = build_index
SPEC.loader.exec_module(build_index)


class BuildIndexTests(unittest.TestCase):
    def test_version_key_compares_numeric_parts(self):
        self.assertGreater(build_index.version_key("0.3.10"), build_index.version_key("0.3.9"))

    def test_normalized_name_ignores_spacing_and_case(self):
        self.assertEqual(build_index.normalized_name("Hi Anime"), build_index.normalized_name("hi-anime"))

    def test_exclusion_can_target_a_language(self):
        entry = {"name": "Example", "lang": "en"}
        rules = [{"name": "example", "lang": "en", "reason": "test"}]
        self.assertEqual(build_index.exclusion_for(entry, rules), "test")
        self.assertIsNone(build_index.exclusion_for({"name": "Example", "lang": "fr"}, rules))

    def test_shape_rejects_missing_source_url(self):
        entry = {"id": 1, "name": "Example", "baseUrl": "https://example.com", "lang": "en", "version": "1"}
        self.assertIn("sourceCodeUrl", build_index.validate_shape(entry))

    def test_override_updates_only_matching_source(self):
        entry = {"name": "SFlix", "lang": "en", "baseUrl": "https://old.example"}
        rules = [{"name": "sflix", "lang": "en", "set": {"baseUrl": "https://new.example"}}]
        build_index.apply_overrides(entry, rules)
        self.assertEqual(entry["baseUrl"], "https://new.example")


if __name__ == "__main__":
    unittest.main()
