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

    def test_normalized_name_keeps_non_latin_names_distinct(self):
        self.assertNotEqual(
            build_index.normalized_name("非凡资源"),
            build_index.normalized_name("华为吧资源"),
        )

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

    def test_legacy_uri_bridge_pattern_is_reported(self):
        source = '''
        final uri = Uri.parse(baseUrl).replace(
          queryParameters: <String, String>{"q": query},
        );
        '''
        warnings = build_index.source_compatibility_warnings(source)
        self.assertTrue(any("Mangayomi 0.8.9" in warning for warning in warnings))

    def test_loopback_dependency_is_reported(self):
        warnings = build_index.source_compatibility_warnings(
            'const proxy = "http://localhost:8080";'
        )
        self.assertTrue(any("loopback" in warning for warning in warnings))

    def test_normal_source_has_no_compatibility_warning(self):
        self.assertEqual(
            build_index.source_compatibility_warnings(
                'const baseUrl = "https://example.com";'
            ),
            (),
        )

    def test_compatibility_examples_in_comments_are_ignored(self):
        self.assertEqual(
            build_index.source_compatibility_warnings(
                "// Avoid Uri.replace(queryParameters: ...) on legacy apps"
            ),
            (),
        )

    def test_shutdown_placeholder_is_not_treated_as_a_healthy_site(self):
        original_fetch_bytes = build_index.fetch_bytes
        build_index.fetch_bytes = lambda *_args, **_kwargs: (
            200,
            b"<html><body>The website has been stopped by the administrator</body></html>",
        )
        try:
            result = build_index.check_site("https://example.com", 1, False)
        finally:
            build_index.fetch_bytes = original_fetch_bytes

        self.assertFalse(result.ok)
        self.assertEqual(result.status, 200)
        self.assertIn("stopped", result.detail)


if __name__ == "__main__":
    unittest.main()
