import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from trading import MAX_RISK, calc_position, classify_token


class TestSizing(unittest.TestCase):
    def test_classify_token(self):
        self.assertEqual(classify_token("BTCUSDT", 1_000_000), "major")
        self.assertEqual(classify_token("ETHUSDT", 1_000_000), "major")
        self.assertEqual(classify_token("SOLUSDT", 600_000_000), "midcap")
        self.assertEqual(classify_token("SOLUSDT", 400_000_000), "new")
        self.assertEqual(classify_token("PEPEUSDT", 400_000_000), "new")

    def test_calc_position_grade_a(self):
        result = calc_position("major", sl_pct=0.02, mode="scalp", setup_grade="A")
        self.assertEqual(result["lev"], 10)
        self.assertEqual(result["margin"], 10.0)
        self.assertEqual(result["position"], 100.0)
        self.assertAlmostEqual(result["risk"], 2.0, places=6)
        self.assertEqual(result["label"], "BTC/ETH/BNB")
        self.assertEqual(result["grade"], "A")

    def test_calc_position_grade_b_half_margin(self):
        result = calc_position("major", sl_pct=0.02, mode="scalp", setup_grade="B")
        self.assertEqual(result["margin"], 5.0)
        self.assertEqual(result["position"], 50.0)
        self.assertAlmostEqual(result["risk"], 1.0, places=6)
        self.assertEqual(result["grade"], "B")

    def test_calc_position_risk_cap(self):
        # raw risk would be 100 * 0.06 = 6.0 > MAX_RISK -> shrink margin
        result = calc_position("major", sl_pct=0.06, mode="scalp", setup_grade="A")
        self.assertAlmostEqual(result["margin"], 4.0 / (10 * 0.06), places=2)
        self.assertAlmostEqual(result["risk"], MAX_RISK, places=6)

    def test_calc_position_swing_rules(self):
        result = calc_position("new", sl_pct=0.10, mode="swing", setup_grade="A")
        self.assertEqual(result["lev"], 2)
        self.assertEqual(result["margin"], 5.0)
        self.assertEqual(result["position"], 10.0)
        self.assertEqual(result["label"], "New/Meme/AI")

    def test_calc_position_unknown_grade(self):
        result = calc_position("midcap", sl_pct=0.02, mode="scalp", setup_grade="X")
        self.assertEqual(result["margin"], 3.5)  # defaults to grade-B half margin
        self.assertEqual(result["grade"], "X")


if __name__ == "__main__":
    unittest.main()