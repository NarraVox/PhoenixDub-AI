import unittest

from nexus.dj.style_analyzer.adapters import demucs
from nexus.dj.style_analyzer.service import parse_options


class DemucsDjConfigurationTests(unittest.TestCase):
    def test_openunmix_remains_default(self):
        self.assertEqual(parse_options({})["separator"], "openunmix")

    def test_explicit_htdemucs_and_auto_fallback_are_available(self):
        self.assertEqual(parse_options({"separator": "demucs"})["separator"], "demucs")
        self.assertEqual(parse_options({"separator": "auto"})["separator"], "auto")
        with self.assertRaisesRegex(ValueError, "separator"):
            parse_options({"separator": "unknown"})

    def test_htdemucs_refuses_cpu_instead_of_silently_downgrading(self):
        with self.assertRaisesRegex(ValueError, "CUDA"):
            demucs.separate("not-used.wav", "not-used", device="cpu")

    def test_model_is_standard_htdemucs_with_bounded_segment(self):
        self.assertEqual(demucs.MODEL, "htdemucs")
        self.assertLessEqual(demucs.SEGMENT_SECONDS, 8)


if __name__ == "__main__":
    unittest.main()
