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

| BTC-USDT-SHORT-20260925-133000 | SHORT | 2026-09-25 13:30:00 | 84016.60000000 | 84316.38286407 | 82817.46854373 | 2026-09-25 21:15:00 | 83778.00000000 | MAX_HOLD | 0.7959 | 30 | CLOSED | BOOTSTRAP |

| BTC-USDT-SHORT-20260925-214500 | SHORT | 2026-09-25 21:45:00 | 83800.50000000 | 83995.78827358 | 83019.34690566 | 2026-09-25 22:30:00 | 83995.78827358 | SL | -1.0000 | 2 | CLOSED | PAPER |

| BTC-USDT-LONG-20260926-014500 | LONG | 2026-09-26 01:45:00 | 84081.40000000 | 83956.25377366 | 84581.98490537 | 2026-09-26 03:00:00 | 83956.25377366 | SL | -1.0000 | 4 | CLOSED | PAPER |

| BTC-USDT-LONG-20260926-031500 | LONG | 2026-09-26 03:15:00 | 84018.80000000 | 83904.65234217 | 84475.39063131 | 2026-09-26 04:15:00 | 83904.65234217 | SL | -1.0000 | 3 | CLOSED | PAPER |

| BTC-USDT-LONG-20260926-074500 | LONG | 2026-09-26 07:45:00 | 84126.10000000 | 84039.50524325 | 84472.47902701 | 2026-09-26 08:15:00 | 84039.50524325 | SL | -1.0000 | 1 | CLOSED | PAPER |

| BTC-USDT-LONG-20260926-100000 | LONG | 2026-09-26 10:00:00 | 84116.20000000 | 84019.16995776 | 84504.32016896 |  |  |  |  | 0 | OPEN | PAPER |
