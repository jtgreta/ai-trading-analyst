import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from trading import (
    calc_atr_stop,
    calc_atr_stop_swing,
    calculate_ote_zone,
    correlation_warning,
    detect_bos_choch,
    detect_fvg,
    detect_liquidity,
    detect_market_structure,
    detect_order_blocks,
    find_fvg,
)


def candle(o, h, l, c):
    return [0.0, o, h, l, c, 1000.0, 0.0, 100000.0, 10, 0, 0.0, 0]


def flat(c):
    """A candle whose true range is exactly 6.0."""
    return candle(c - 0.1, c + 3.0, c - 3.0, c)


def zigzag(path, wick=0.1):
    candles = []
    for i, c in enumerate(path):
        o = path[i - 1] if i else c - 0.5
        candles.append(candle(o, c + wick, c - wick, c))
    return candles


def negative_zigzag(path, wick=0.1):
    candles = []
    for i, c in enumerate(path):
        o = path[i - 1] if i else c + 0.5
        candles.append(candle(o, c + wick, c - wick, c))
    return candles


class TestSMC(unittest.TestCase):
    def test_detect_bos_choch_bullish(self):
        # HH + HL then close above last swing high => bullish BOS_up
        path = [
            100.0, 101.0, 102.0, 103.0, 104.5, 106.0, 105.0, 103.5, 102.0, 101.0,
            100.5, 101.5, 103.0, 104.5, 106.0, 107.5, 109.0, 110.5, 112.0, 114.0,
            116.0, 115.0, 114.0, 113.0, 112.5, 114.0, 116.0, 118.0, 120.0, 122.0,
            124.0, 126.0, 128.0, 130.0, 132.0, 134.0,
        ]
        ms = detect_bos_choch(zigzag(path), lookback=50)
        self.assertEqual(ms["trend"], "bullish")
        self.assertEqual(ms["last_event"], "BOS_up")
        self.assertFalse(ms["mss"])
        self.assertIsNotNone(ms["swing_high"])
        self.assertIsNotNone(ms["swing_low"])
        for key in ("swing_highs", "swing_lows", "bos_level", "choch_pivot"):
            self.assertIn(key, ms)

    def test_detect_bos_choch_bearish(self):
        path = [
            134.0, 132.0, 130.0, 128.0, 126.0, 124.0, 125.0, 126.5, 128.0, 129.0,
            129.5, 128.0, 126.0, 124.5, 123.0, 121.5, 120.0, 118.5, 117.0, 116.0,
            114.0, 114.5, 115.0, 116.0, 116.5, 115.0, 113.0, 111.0, 109.0, 107.0,
            105.0, 103.0, 101.0, 99.0, 97.0, 95.0,
        ]
        ms = detect_bos_choch(negative_zigzag(path), lookback=50)
        self.assertEqual(ms["trend"], "bearish")
        self.assertEqual(ms["last_event"], "BOS_down")
        self.assertFalse(ms["mss"])

    def test_detect_bos_choch_too_short(self):
        ms = detect_bos_choch(zigzag([100.0, 101.0, 102.0]))
        self.assertEqual(ms["trend"], "ranging")
        self.assertFalse(ms["mss"])

    def test_detect_market_structure_alias(self):
        self.assertIs(detect_market_structure, detect_bos_choch)

    def test_find_fvg_bullish(self):
        # only three bars exist: bar0.high = 10 < bar2.low = 12 -> bullish gap 10-12
        candles = [
            candle(9.0, 10.0, 8.0, 9.0),
            candle(10.0, 11.0, 9.0, 10.0),
            candle(13.0, 14.0, 12.0, 13.0),
        ]
        fvgs = find_fvg(candles, lookback=3)
        self.assertTrue(fvgs)
        fvg = fvgs[0]
        self.assertEqual(fvg["type"], "bullish")
        self.assertEqual(fvg["top"], 12.0)
        self.assertEqual(fvg["bottom"], 10.0)
        self.assertEqual(fvg["midpoint"], 11.0)
        self.assertFalse(fvg["filled"])

    def test_detect_fvg_alias(self):
        self.assertIs(detect_fvg, find_fvg)

    def test_detect_order_blocks(self):
        candles = [
            candle(9.0, 10.0, 8.0, 9.0),       # small green (untouched)
            candle(11.0, 11.0, 10.0, 10.0),    # small red: body 1
            candle(10.0, 14.5, 9.5, 14.0),     # big green: body 4 >= 1.5x1
            candle(15.0, 15.5, 14.5, 15.0),
            candle(16.0, 16.5, 15.5, 16.0),
        ]
        obs = detect_order_blocks(candles, lookback=5)
        self.assertTrue(obs)
        self.assertEqual(obs[0]["type"], "bullish")
        self.assertEqual(obs[0]["top"], 11.0)
        self.assertEqual(obs[0]["bottom"], 10.0)
        self.assertFalse(obs[0]["mitigated"])

    def test_calculate_ote_zone_bullish(self):
        zone = calculate_ote_zone(100.0, 200.0, "bullish")
        self.assertAlmostEqual(zone["ote_top"], 138.2, places=6)
        self.assertAlmostEqual(zone["ote_mid"], 129.5, places=6)
        self.assertAlmostEqual(zone["ote_bottom"], 121.4, places=6)
        self.assertEqual(zone["direction"], "bullish")

    def test_calculate_ote_zone_bearish_order(self):
        zone = calculate_ote_zone(200.0, 100.0, "bearish")
        self.assertEqual(zone["ote_top"], 178.6)
        self.assertEqual(zone["ote_mid"], 170.5)
        self.assertEqual(zone["ote_bottom"], 161.8)
        self.assertGreater(zone["ote_top"], zone["ote_bottom"])

    def test_calculate_ote_zone_flat(self):
        zone = calculate_ote_zone(100.0, 100.0, "bullish")
        self.assertEqual(zone["ote_top"], 100.0)
        self.assertEqual(zone["ote_mid"], 100.0)
        self.assertEqual(zone["ote_bottom"], 100.0)

    def test_calc_atr_stop_long(self):
        candles = [flat(100.0 + i) for i in range(16)]
        stops = calc_atr_stop(candles, entry=100.0, direction="LONG")
        # ATR = 6.0 -> sl_dist = min(6*1.5, entry*0.20=20) = 9.0
        self.assertEqual(stops["sl"], 91.0)
        self.assertEqual(stops["tp1"], 118.0)
        self.assertEqual(stops["tp2"], 131.5)
        self.assertEqual(stops["tp3"], 145.0)
        self.assertAlmostEqual(stops["sl_pct"], 0.09, places=6)

    def test_calc_atr_stop_capped(self):
        candles = [flat(100.0 + i) for i in range(16)]
        stops = calc_atr_stop(candles, entry=100.0, direction="SHORT", max_sl_pct=0.05)
        self.assertEqual(stops["sl"], 105.0)
        self.assertEqual(stops["tp1"], 90.0)

    def test_calc_atr_stop_fallback_missing_data(self):
        stops = calc_atr_stop([flat(100.0)], entry=100.0, direction="LONG")
        # atr None -> ATR substituted by entry*0.01 = 1.0, SL = 1.0 * multiplier 1.5
        self.assertEqual(stops["sl"], 98.5)
        self.assertEqual(stops["sl_pct"], 0.015)

    def test_calc_atr_stop_swing_fallback(self):
        result = calc_atr_stop_swing([flat(100.0)], entry_price=100.0, direction="LONG")
        self.assertIsNone(result["atr_value"])
        self.assertEqual(result["sl"], 95.0)  # max_sl_pct 0.05
        self.assertEqual(result["sl_pct"], 0.05)
        self.assertEqual(result["tp1"], 110.0)
        self.assertEqual(result["tp2"], 117.5)

    def test_calc_atr_stop_swing_ok(self):
        klines = [flat(100.0 + i) for i in range(30)]
        result = calc_atr_stop_swing(klines, entry_price=100.0, direction="LONG")
        self.assertEqual(result["atr_value"], 6.0)
        # sl_dist = min(6*2=12, 100*0.05=5) = 5
        self.assertEqual(result["sl"], 95.0)
        self.assertEqual(result["tp1"], 110.0)
        self.assertEqual(result["tp2"], 117.5)
        self.assertEqual(result["tp3"], "Trailing")

    def test_detect_liquidity_no_cluster(self):
        path = [100.0 + i for i in range(40)]
        liq = detect_liquidity(zigzag(path))
        self.assertIn("eqh", liq)
        self.assertIn("eql", liq)
        self.assertIn("nearest_eqh", liq)
        self.assertIn("nearest_eql", liq)

    def test_correlation_warning(self):
        self.assertIsNone(correlation_warning([], "BTCUSDT"))
        self.assertIsNone(correlation_warning(["BTCUSDT"], "SOLUSDT"))
        warning = correlation_warning(["BTCUSDT"], "ETHUSDT")
        self.assertIsNotNone(warning)
        self.assertIn("MAJORS", warning)


if __name__ == "__main__":
    unittest.main()