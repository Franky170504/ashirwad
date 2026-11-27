export class ApiError extends Error {
  fieldErrors: Record<string, string>;
  status: number;
  constructor(message: string, fieldErrors: Record<string, string> = {}) {
    super(message);
    this.fieldErrors = fieldErrors;
  }
}

function getCookie(name: string) {
  if (typeof document === "undefined") return null; // server-side: no cookies
  const m = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return m ? decodeURIComponent(m[1]) : null;
}

/** Make sure Django has set the csrftoken cookie (browser only). */
async function ensureCsrf() {
  if (typeof window === "undefined" || getCookie("csrftoken")) return;
  await fetch("/api/csrf/", { credentials: "include" });
}

/** POST JSON to Django (via the /api proxy). Handles DRF-style errors. */
export async function post<T = Record<string, unknown>>(path: string, body: unknown): Promise<T> {
  await ensureCsrf();
  const csrf = getCookie("csrftoken");
  const res = await fetch(`/api${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json", ...(csrf ? { "X-CSRFToken": csrf } : {}) },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (res.ok) return data as T;

  // DRF returns {detail: "..."} or {field: ["msg"], non_field_errors: ["msg"]}
  const fieldErrors: Record<string, string> = {};
  let message = data?.detail || "";
  for (const [k, v] of Object.entries(data ?? {})) {
    if (k === "detail") continue;
    const text = Array.isArray(v) ? String(v[0]) : String(v);
    if (k === "non_field_errors") message = message || text;
    else fieldErrors[k] = text;
  }
  throw new ApiError(message || (Object.keys(fieldErrors).length ? "" : "Something went wrong. Please try again."), fieldErrors);
}