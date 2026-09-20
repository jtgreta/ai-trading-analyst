import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from trading import hunter_candidates, scanner_candidates


def ticker(symbol, low, high, last, qv, chg):
    return {
        "symbol": symbol,
        "lowPrice": str(low),
        "highPrice": str(high),
        "lastPrice": str(last),
        "quoteVolume": str(qv),
        "priceChangePercent": str(chg),
    }


class TestScannerCandidates(unittest.TestCase):
    def _universe_strict(self):
        # 5 strict passes (range > 10, |change| > 3, vol > $100M) -> no relaxation
        return [
            ticker("BTCUSDT", 90, 110, 105, 500_000_000, 5.0),    # range 22.2, pass
            ticker("ETHUSDT", 180, 200, 195, 400_000_000, 4.0),   # range 11.1, pass
            ticker("XRPUSDT", 50, 60, 58, 200_000_000, 6.0),      # range 20.0, pass
            ticker("AVAXUSDT", 100, 115, 110, 300_000_000, 3.5),  # range 15.0, pass
            ticker("LTCUSDT", 100, 112, 108, 250_000_000, 3.2),   # range 12.0, pass
            ticker("NEARUSDT", 100, 109, 105, 350_000_000, 4.0),  # range 9.0, strict-fail
            ticker("SOLUSDT", 100, 104, 102, 300_000_000, 0.5),   # change < 3, fail
            ticker("USDCUSDT", 1.0, 1.02, 1.01, 900_000_000, 0.1),  # excluded substring
            ticker("BTCDOMUSDT", 100, 115, 110, 300_000_000, 5.0),  # excluded exact
        ]

    def test_scanner_filters(self):
        cands, total = scanner_candidates(self._universe_strict())
        self.assertEqual({c["symbol"] for c in cands},
                        {"BTCUSDT", "ETHUSDT", "XRPUSDT", "AVAXUSDT", "LTCUSDT"})
        self.assertEqual(total, len(cands))

    def test_scanner_sorted_by_abs_change(self):
        cands, _ = scanner_candidates(self._universe_strict())
        changes = [c["absChange"] for c in cands]
        self.assertEqual(changes, sorted(changes, reverse=True))
        self.assertEqual([c["symbol"] for c in cands],
                        ["XRPUSDT", "BTCUSDT", "ETHUSDT", "AVAXUSDT", "LTCUSDT"])

    def test_scanner_relaxed(self):
        # Only low-range coins present -> relaxation to range > 7
        universe = [
            ticker("LINKUSDT", 100, 109, 105, 300_000_000, 4.0),   # range 9, relax-pass
            ticker("DOGEUSDT", 100, 108, 104, 200_000_000, 5.0),   # range 8, relax-pass
            ticker("SHIBUSDT", 100, 104, 102, 150_000_000, 0.5),   # change fail
            ticker("TRXUSDT", 90, 110, 105, 400_000_000, 6.0),     # range 22, strict-pass
        ]
        cands, total = scanner_candidates(universe)
        self.assertEqual({c["symbol"] for c in cands}, {"LINKUSDT", "DOGEUSDT", "TRXUSDT"})
        self.assertEqual(total, 3)

    def test_scanner_malformed_rows_skipped(self):
        universe = [
            ticker("OKUSDT", 90, 110, 105, 500_000_000, 5.0),
            {"symbol": "BADUSDT", "lowPrice": "garbage", "highPrice": "nan",
             "lastPrice": "x", "quoteVolume": "y", "priceChangePercent": "z"},
        ]
        cands, _ = scanner_candidates(universe)
        self.assertEqual([c["symbol"] for c in cands], ["OKUSDT"])


class TestHunterCandidates(unittest.TestCase):
    def _universe_strict(self):
        # 5 strict passes (3 < range < 25, |change| < 15, vol > $100M)
        return [
            ticker("BTCUSDT", 90, 110, 105, 900_000_000, 2.0),    # range 22.2, pass
            ticker("SOLUSDT", 100, 104, 102, 600_000_000, 3.0),   # range 4.0, pass
            ticker("XRPUSDT", 50, 58, 56, 500_000_000, -2.0),     # range 16.0, pass
            ticker("TRXUSDT", 1.0, 1.10, 1.05, 400_000_000, 12.0),  # range 10.0, pass
            ticker("LTCUSDT", 100, 108, 104, 350_000_000, 1.5),   # range 8.0, pass
            ticker("ADAUSDT", 1.0, 1.30, 1.20, 300_000_000, 20.0),  # |change| >= 15, fail
            ticker("NEARUSDT", 1.0, 1.28, 1.20, 280_000_000, 5.0),  # range 28, strict-fail
            ticker("USDCUSDT", 1.0, 1.02, 1.01, 900_000_000, 0.1),  # excluded substring
        ]

    def test_hunter_filters(self):
        cands, relaxed = hunter_candidates(self._universe_strict())
        self.assertFalse(relaxed)
        self.assertEqual({c["symbol"] for c in cands},
                        {"BTCUSDT", "SOLUSDT", "XRPUSDT", "TRXUSDT", "LTCUSDT"})

    def test_hunter_sorted_by_volume(self):
        cands, _ = hunter_candidates(self._universe_strict())
        volumes = [c["quoteVolume"] for c in cands]
        self.assertEqual(volumes, sorted(volumes, reverse=True))
        self.assertEqual([c["symbol"] for c in cands],
                        ["BTCUSDT", "SOLUSDT", "XRPUSDT", "TRXUSDT", "LTCUSDT"])

    def test_hunter_relaxed(self):
        universe = [
            ticker("AVAXUSDT", 100, 130, 120, 300_000_000, 4.0),  # range exactly 30 -> excluded
            ticker("LINKUSDT", 100, 128, 115, 200_000_000, 5.0),  # range 28, relax-pass
            ticker("DOGEUSDT", 100, 126, 110, 150_000_000, 6.0),  # range 26, relax-pass
            ticker("TRXUSDT", 90, 110, 105, 400_000_000, 6.0),    # range 22, strict-pass
        ]
        cands, relaxed = hunter_candidates(universe)
        self.assertTrue(relaxed)
        self.assertEqual({c["symbol"] for c in cands}, {"LINKUSDT", "DOGEUSDT", "TRXUSDT"})

    def test_hunter_malformed_rows_skipped(self):
        universe = [
            ticker("OKUSDT", 90, 110, 105, 500_000_000, 2.0),
            {"symbol": "BADUSDT", "lowPrice": "garbage", "highPrice": "nan",
             "lastPrice": "x", "quoteVolume": "y", "priceChangePercent": "z"},
        ]
        cands, _ = hunter_candidates(universe)
        self.assertEqual([c["symbol"] for c in cands], ["OKUSDT"])


if __name__ == "__main__":
    unittest.main()