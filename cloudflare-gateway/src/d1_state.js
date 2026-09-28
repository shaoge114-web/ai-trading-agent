export async function loadAgentState(env) {
  const row = await env.DB
    .prepare(`
      SELECT
        state_version,
        status,
        position_json,
        last_signal,
        last_timestamp,
        last_decision_json,
        updated_at
      FROM agent_state
      WHERE id = 1
      LIMIT 1
    `)
    .first();

  if (!row) {
    return null;
  }

  return {
    state_version: row.state_version,
    status: row.status,
    position: row.position_json
      ? JSON.parse(row.position_json)
      : null,
    last_signal: row.last_signal,
    last_timestamp: row.last_timestamp,
    last_decision: row.last_decision_json
      ? JSON.parse(row.last_decision_json)
      : null,
    updated_at: row.updated_at,
  };
}


export async function saveAgentState(env, state) {
  const now = new Date().toISOString();

  await env.DB
    .prepare(`
      INSERT INTO agent_state (
        id,
        state_version,
        status,
        position_json,
        last_signal,
        last_timestamp,
        last_decision_json,
        updated_at
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?)
      ON CONFLICT(id) DO UPDATE SET
        state_version = excluded.state_version,
        status = excluded.status,
        position_json = excluded.position_json,
        last_signal = excluded.last_signal,
        last_timestamp = excluded.last_timestamp,
        last_decision_json = excluded.last_decision_json,
        updated_at = excluded.updated_at
    `)
    .bind(
      1,
      Number(state.version ?? state.state_version ?? 5),
      String(state.status ?? "READY"),
      state.position
        ? JSON.stringify(state.position)
        : null,
      state.last_signal ?? null,
      state.last_timestamp ?? null,
      state.last_decision
        ? JSON.stringify(state.last_decision)
        : null,
      now
    )
    .run();

  return {
    status: "OK",
    updated_at: now,
  };
}
