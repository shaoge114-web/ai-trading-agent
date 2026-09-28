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
