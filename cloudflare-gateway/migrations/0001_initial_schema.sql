-- AI Trading Agent D1 initial schema
-- Migration: 0001_initial_schema

CREATE TABLE IF NOT EXISTS agent_state (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    state_version INTEGER NOT NULL,
    status TEXT NOT NULL,
    position_json TEXT,
    last_signal TEXT,
    last_timestamp TEXT,
    last_decision_json TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS positions (
    trade_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    entry_timestamp TEXT NOT NULL,
    entry_price REAL NOT NULL,
    initial_sl REAL NOT NULL,
    current_sl REAL NOT NULL,
    tp REAL NOT NULL,
    risk REAL NOT NULL,
    rr REAL NOT NULL,
    adx REAL,
    rsi REAL,
    atr REAL,
    bars_held INTEGER NOT NULL DEFAULT 0,
    trail_activated INTEGER NOT NULL DEFAULT 0,
    trail_activation_r REAL NOT NULL DEFAULT 3.0,
    max_hold INTEGER NOT NULL DEFAULT 30,
    exit_reason TEXT,
    exit_price REAL,
    exit_timestamp TEXT,
    r_multiple REAL,
    position_status TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS trade_journal (
    trade_id TEXT PRIMARY KEY,
    symbol TEXT NOT NULL,
    side TEXT NOT NULL,
    entry_timestamp TEXT NOT NULL,
    entry_price REAL NOT NULL,
    initial_sl REAL NOT NULL,
    tp REAL NOT NULL,
    exit_timestamp TEXT,
    exit_price REAL,
    exit_reason TEXT,
    r_multiple REAL,
    bars_held INTEGER,
    status TEXT NOT NULL,
    mode TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_positions_status
ON positions(position_status);

CREATE INDEX IF NOT EXISTS idx_positions_entry_timestamp
ON positions(entry_timestamp);

CREATE INDEX IF NOT EXISTS idx_trade_journal_entry_timestamp
ON trade_journal(entry_timestamp);

CREATE INDEX IF NOT EXISTS idx_trade_journal_status
ON trade_journal(status);
