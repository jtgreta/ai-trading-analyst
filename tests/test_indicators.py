import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from trading import (
    atr,
    calc_trail_callback_pct,
    distance_pct,
    ema,
    ma_stack_label,
    pct_from,
    rsi,
    sma,
)


def candle(close, high=None, low=None, volume=1000.0):
    high = close if high is None else high
    low = close if low is None else low
    return [0.0, close - 0.1, high, low, close, volume, 0.0, volume, 10, 0, 0.0, 0]


class TestIndicators(unittest.TestCase):
    def test_sma_basic(self):
        self.assertEqual(sma([1.0, 2.0, 3.0, 4.0], 3), 3.0)
        self.assertEqual(sma([1.0, 2.0, 3.0, 4.0], 4), 2.5)
        self.assertIsNone(sma([1.0, 2.0], 3))

    def test_ema_basic(self):
        values = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        result = ema(values, 3)
        self.assertIsNotNone(result)
        k = 2.0 / 4
        expected = 2.0  # SMA of [1,2,3]
        for v in values[3:]:
            expected = v * k + expected * (1 - k)
        self.assertAlmostEqual(result, expected, places=6)
        self.assertIsNone(ema([1.0, 2.0], 3))

    def test_atr(self):
        candles = [candle(100.0 + i, high=103.0 + i, low=97.0 + i) for i in range(16)]
        result = atr(candles, 14)
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result, 6.0, places=6)
        self.assertIsNone(atr(candles[:8], 14))

    def test_rsi_uptrend(self):
        closes = [100.0 + i for i in range(21)]
        result = rsi(closes, 14)
        self.assertIsNotNone(result)
        self.assertGreater(result, 50)
        self.assertLessEqual(result, 100.0)

    def test_rsi_downtrend(self):
        closes = [100.0 - i for i in range(21)]
        result = rsi(closes, 14)
        self.assertIsNotNone(result)
        self.assertLess(result, 50)
        self.assertGreaterEqual(result, 0.0)

    def test_rsi_too_short(self):
        self.assertIsNone(rsi([1.0, 2.0, 3.0], 14))

    def test_pct_from(self):
        self.assertAlmostEqual(pct_from(110.0, 100.0), 10.0)
        self.assertAlmostEqual(pct_from(90.0, 100.0), -10.0)
        self.assertEqual(pct_from(5.0, 0.0), 0.0)

    def test_distance_pct(self):
        self.assertAlmostEqual(distance_pct(100.0, 105.0), 5.0)
        self.assertAlmostEqual(distance_pct(100.0, 95.0), 5.0)
        self.assertEqual(distance_pct(0.0, 10.0), 0.0)

    def test_ma_stack_label(self):
        self.assertEqual(ma_stack_label(110, 105, 102, 100), "Bullish")
        self.assertEqual(ma_stack_label(90, 95, 98, 100), "Bearish")
        self.assertEqual(ma_stack_label(103, 105, 102, 100), "Mixed")
        self.assertEqual(ma_stack_label(110, None, 102, 100), "Mixed")

    def test_calc_trail_callback_pct(self):
        self.assertEqual(calc_trail_callback_pct(None, 100.0), 3.0)
        self.assertEqual(calc_trail_callback_pct(None, 0.0), 3.0)
        self.assertEqual(calc_trail_callback_pct(2.0, 100.0, "midcap"), 3.0)
        self.assertEqual(calc_trail_callback_pct(2.0, 100.0, "major"), 2.0)
        self.assertEqual(calc_trail_callback_pct(2.0, 100.0, "new"), 4.0)
        self.assertEqual(calc_trail_callback_pct(100.0, 100.0, "new"), 7.0)


if __name__ == "__main__":
    unittest.main()