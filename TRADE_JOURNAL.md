# AI Trading Agent — Trade Journal

## Purpose

Permanent human-readable journal for all trading decisions and positions.

This journal records:
- Entry
- Initial Stop Loss
- Take Profit
- Exit
- Exit reason
- R multiple
- Position duration
- Strategy indicators
- Paper/Real trading mode
- Timestamp
- Run ID

## Safety

Current trading mode:

- PAPER_TRADING: true
- REAL_ORDER: false

No real order is permitted until explicitly enabled and separately verified.

## Trades

| Trade ID | Symbol | Side | Entry Time | Entry | Initial SL | TP | Exit Time | Exit | Exit Reason | R | Bars Held | Status |
|---|---|---|---|---:|---:|---:|---|---:|---|---:|---:|---|
| — | — | — | — | — | — | — | — | — | — | — | — | — |

## Audit Notes

- Heartbeat #10 successfully restored state and processed 8 pending confirmed candles sequentially.
- Current paper position at the end of Heartbeat #10:
  - Symbol: BTC-USDT
  - Side: LONG
  - Entry: 84659.0
  - Initial SL: 84456.0735332374
  - TP: 85470.70586705036
  - Entry Time: 2026-09-25 00:00:00
  - Bars Held: 3
  - Status: OPEN
- This existing position must not be duplicated as a new entry by the journal.
