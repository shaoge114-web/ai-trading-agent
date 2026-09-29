import { loadAgentState, saveAgentState } from "./d1_state.js";

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    try {
      if (url.pathname === "/") {
        return Response.json({
          status: "OK",
          service: "ai-trading-gateway",
          version: "GATEWAY_V1",
          paper_trading: true,
          real_order_enabled: false
        });
      }

      if (url.pathname === "/health") {
        return Response.json({
          status: "healthy",
          service: "ai-trading-gateway",
          paper_trading: true,
          real_order_enabled: false
        });
      }

      if (url.pathname === "/db-test") {
        const result = await env.DB
          .prepare("SELECT 1 AS ok")
          .first();

        return Response.json({
          status: "OK",
          database: "CONNECTED",
          result
        });
      }

      if (url.pathname === "/db-state-test") {
        const before = await loadAgentState(env);

        const testState = {
          version: 5,
          status: "D1_TEST",
          position: null,
          last_signal: "D1_TEST",
          last_timestamp: new Date().toISOString(),
          last_decision: null
        };

        await saveAgentState(env, testState);

        const after = await loadAgentState(env);

        return Response.json({
          status: "OK",
          database: "CONNECTED",
          state_write: "PASS",
          state_read: after ? "PASS" : "FAIL",
          previous_state_exists: before !== null,
          real_order_enabled: false,
          paper_trading: true
        });
      }

      return Response.json({
        status: "NOT_FOUND"
      }, { status: 404 });

    } catch (error) {
      return Response.json({
        status: "ERROR",
        error: String(error)
      }, { status: 500 });
    }
  }
};
