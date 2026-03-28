/**
 * gog email tracking worker - records email opens via a 1x1 tracking pixel.
 *
 * Routes:
 *   GET /t/:trackingId/:recipient? - Serve pixel and record open
 *   GET /opens?tracking_id=X&to=Y&since=Z - Query opens (requires ADMIN_KEY)
 *   GET /health - Health check
 */

const PIXEL = new Uint8Array([
  0x47, 0x49, 0x46, 0x38, 0x39, 0x61, 0x01, 0x00, 0x01, 0x00, 0x80, 0x00,
  0x00, 0xff, 0xff, 0xff, 0x00, 0x00, 0x00, 0x21, 0xf9, 0x04, 0x01, 0x00,
  0x00, 0x00, 0x00, 0x2c, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, 0x01, 0x00,
  0x00, 0x02, 0x02, 0x44, 0x01, 0x00, 0x3b,
]);

function verifyKey(request, env) {
  const auth = request.headers.get("Authorization") || "";
  const key = auth.replace(/^Bearer\s+/i, "");
  return key === env.ADMIN_KEY;
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const path = url.pathname;

    // Health check
    if (path === "/health") {
      return new Response("ok", { status: 200 });
    }

    // Track pixel
    if (path.startsWith("/t/")) {
      const parts = path.split("/").filter(Boolean);
      // parts: ["t", trackingId, optionalRecipient]
      const trackingId = decodeURIComponent(parts[1] || "");
      const recipient = parts[2] ? decodeURIComponent(parts[2]) : null;

      if (!trackingId) {
        return new Response(PIXEL, {
          headers: { "Content-Type": "image/gif", "Cache-Control": "no-store" },
        });
      }

      // Record open asynchronously (don't block pixel delivery)
      const cf = request.cf || {};
      const stmt = env.DB.prepare(
        "INSERT INTO opens (tracking_id, recipient, ip, user_agent, country, city) VALUES (?, ?, ?, ?, ?, ?)"
      ).bind(
        trackingId,
        recipient,
        request.headers.get("CF-Connecting-IP") || "",
        request.headers.get("User-Agent") || "",
        cf.country || "",
        cf.city || ""
      );

      // Fire and forget - don't delay the pixel
      request.ctx
        ? request.ctx.waitUntil(stmt.run())
        : await stmt.run();

      return new Response(PIXEL, {
        headers: { "Content-Type": "image/gif", "Cache-Control": "no-store" },
      });
    }

    // Query opens (admin only)
    if (path === "/opens") {
      if (!verifyKey(request, env)) {
        return Response.json({ error: "unauthorized" }, { status: 401 });
      }

      const trackingId = url.searchParams.get("tracking_id");
      const to = url.searchParams.get("to");
      const since = url.searchParams.get("since");

      let query = "SELECT * FROM opens WHERE 1=1";
      const params = [];

      if (trackingId) {
        query += " AND tracking_id = ?";
        params.push(trackingId);
      }
      if (to) {
        query += " AND recipient = ?";
        params.push(to);
      }
      if (since) {
        query += " AND opened_at >= ?";
        params.push(since);
      }

      query += " ORDER BY opened_at DESC LIMIT 500";

      const result = await env.DB.prepare(query).bind(...params).all();
      return Response.json({ opens: result.results, count: result.results.length });
    }

    return new Response("not found", { status: 404 });
  },
};
