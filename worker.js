const API_PREFIX = "/api";

function backendRequest(request, env) {
  if (!env.BACKEND_URL) {
    return new Response("BACKEND_URL is not configured", { status: 500 });
  }

  const incoming = new URL(request.url);
  const backendBase = new URL(env.BACKEND_URL);
  const target = new URL(incoming.pathname + incoming.search, backendBase);

  const headers = new Headers(request.headers);
  headers.delete("host");
  headers.delete("content-length");

  return fetch(new Request(target.toString(), {
    method: request.method,
    headers,
    body: ["GET", "HEAD"].includes(request.method) ? undefined : request.body,
    redirect: "follow",
  }));
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);

    if (url.pathname === API_PREFIX || url.pathname.startsWith(`${API_PREFIX}/`)) {
      return backendRequest(request, env);
    }

    return env.ASSETS.fetch(request);
  },
};
