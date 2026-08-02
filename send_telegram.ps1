# Load variables from .env
$envPath = Join-Path $PSScriptRoot ".env"
if (Test-Path $envPath) {
    Get-Content $envPath | Where-Object { $_ -match "^TG_TOKEN=(.*)$" } | ForEach-Object { $tgToken = $matches[1] }
    Get-Content $envPath | Where-Object { $_ -match "^TG_CHAT=(.*)$" } | ForEach-Object { $tgChat = $matches[1] }
} else {
    $tgToken = $env:TG_TOKEN
    $tgChat  = $env:TG_CHAT
}
$now = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
$tgMsg   = "BILLUSDT Scalper Analysis | Binance Futures | $now`n" +
           "`nDIRECTION: NEUTRAL - No trade" +
           "`nCONFLUENCE: 3/10 - SKIP" +
           "`n`nTIMEFRAME SUMMARY" +
           "`n5m  | Mixed   | Below | [WAIT]" +
           "`n15m | Mixed   | Below | [WAIT]" +
           "`n1h  | Bullish | Mixed | [WAIT]" +
           "`n4h  | Bullish | Above | [LONG]" +
           "`n1D  | Mixed   | Above | [WAIT]" +
           "`n`nREASON: Short-term downtrend, mixed MAs on lower timeframes, and shifting order book bias. Wait for clearer structure and higher confluence.`n" +
           "`nKEY LEVELS" +
           "`nResistance: 0.2069 / 0.2101 / 0.2163" +
           "`nSupport   : 0.1982 / 0.1845 / 0.1605" +
           "`n`nWait for break above 0.2069 or below 0.1982 with volume confirmation."
if ($tgMsg.Length -gt 4096) { $tgMsg = $tgMsg.Substring(0, 4093) + "..." }
Invoke-RestMethod -Uri "https://api.telegram.org/bot$tgToken/sendMessage" -Method POST -Body @{chat_id=$tgChat; text=$tgMsg}