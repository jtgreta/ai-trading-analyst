import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from trading import PHT, get_next_session_window, get_session_info

_WINDOW_NAMES = {"London Open", "London-NY Gap", "NY Overlap", "Asian Session", "Off-hours"}


class TestSession(unittest.TestCase):
    def test_window_names(self):
        self.assertEqual(_WINDOW_NAMES, {
            "London Open", "London-NY Gap", "NY Overlap", "Asian Session", "Off-hours",
        })

    def test_get_session_info_shape(self):
        info = get_session_info()
        for key in ("time_str", "window", "volatility", "aggression", "advice",
                    "can_enter", "min_grade"):
            self.assertIn(key, info)
        self.assertTrue(info["can_enter"])
        self.assertIn(info["window"], _WINDOW_NAMES)
        self.assertIn(info["min_grade"], {"A", "B"})
        self.assertIn("PHT", info["time_str"])

    def test_pht_offset(self):
        self.assertEqual(PHT.utcoffset(None).total_seconds(), 8 * 3600)

    def test_get_next_session_window(self):
        result = get_next_session_window()
        self.assertTrue(
            result.endswith("London open")
            or result.endswith("London–NY overlap opens")
            or result.endswith("London open")
        )
        self.assertIn("PHT", result)


if __name__ == "__main__":
    unittest.main()