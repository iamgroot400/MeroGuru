const origin = (
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000"
).replace(/\/+$/, "");
export const API_BASE = origin.endsWith("/api/v1")
  ? origin
  : `${origin}/api/v1`;

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
  ) {
    super(message);
    this.name = "ApiError";
  }
}

export async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const controller = new AbortController();
  const abort = () => controller.abort();
  if (options.signal?.aborted) controller.abort();
  options.signal?.addEventListener("abort", abort, { once: true });
  const timer = setTimeout(abort, 45000);
  try {
    const response = await fetch(`${API_BASE}${path}`, {
      ...options,
      signal: controller.signal,
      credentials: "omit",
      headers: {
        Accept: "application/json",
        ...(options.body ? { "Content-Type": "application/json" } : {}),
        ...options.headers,
      },
    });
    if (!response.ok) {
      // Do not render arbitrary server errors: credential validation can echo secrets.
      const message =
        response.status === 422
          ? "Some details were not accepted. Check your entries and try again."
          : response.status === 404
            ? "This item is not available yet."
            : response.status === 409
              ? "This action conflicts with an existing item. Refresh and try again."
              : `The request could not be completed (${response.status}). Please try again.`;
      throw new ApiError(message, response.status);
    }
    if (response.status === 204) return undefined as T;
    const body = await response.text();
    return body ? (JSON.parse(body) as T) : (undefined as T);
  } catch (error) {
    if (error instanceof ApiError) throw error;
    if (options.signal?.aborted)
      throw new DOMException("Aborted", "AbortError");
    if (controller.signal.aborted)
      throw new Error("The API took too long to respond. Please try again.");
    throw new Error(
      "Cannot reach the API. Check that your MeroGuru API container is running.",
    );
  } finally {
    clearTimeout(timer);
    options.signal?.removeEventListener("abort", abort);
  }
}
export const post = <T>(path: string, data?: unknown) =>
  request<T>(path, {
    method: "POST",
    ...(data === undefined ? {} : { body: JSON.stringify(data) }),
  });
export async function optional<T>(
  path: string,
  signal?: AbortSignal,
): Promise<T | null> {
  try {
    return (await request<T>(path, { signal })) ?? null;
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}
export const idPath = (id: string) => encodeURIComponent(id);
