import { loadAgentState, saveAgentState } from "./d1_state.js";

function isAuthorized(request, env) {
  const token = env.AGENT_STATE_TOKEN;

  if (!token) {
    return false;
  }

  return request.headers.get("Authorization") === "Bearer " + token;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    try {
      if (url.pathname === "/") {
        return Response.json({
          status: "OK",
          service: "ai-trading-gateway",
          version: "GATEWAY_V2",
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

      if (url.pathname === "/internal/state") {
        if (!env.AGENT_STATE_TOKEN) {
          return Response.json({
            status: "ERROR",
            error: "STATE_AUTH_NOT_CONFIGURED"
          }, { status: 503 });
        }

        if (!isAuthorized(request, env)) {
          return Response.json({
            status: "UNAUTHORIZED"
          }, { status: 401 });
        }

        if (request.method === "GET") {
          const state = await loadAgentState(env);

          return Response.json({
            status: "OK",
            state
          });
        }

        if (request.method === "PUT") {
          const body = await request.json();

          const required = [
            "version",
            "status",
            "position",
            "last_signal",
            "last_timestamp",
            "last_decision"
          ];

          for (const key of required) {
            if (!(key in body)) {
              return Response.json({
                status: "ERROR",
                error: "MISSING_STATE_FIELD: " + key
              }, { status: 400 });
            }
          }

          await saveAgentState(env, body);

          return Response.json({
            status: "OK",
            saved: true,
            paper_trading: true,
            real_order_enabled: false
          });
        }

        return Response.json({
          status: "METHOD_NOT_ALLOWED"
        }, { status: 405 });
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
