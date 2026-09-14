import { afterEach, describe, expect, it, vi } from "vitest";
import { optional, post, request } from "./client";
afterEach(() => vi.unstubAllGlobals());
describe("API client", () => {
  it("sends JSON with no authentication or cookies", async () => {
    const fetcher = vi
      .fn()
      .mockResolvedValue(new Response('{"id":"goal"}', { status: 200 }));
    vi.stubGlobal("fetch", fetcher);
    await post("/goals", { title: "Learn" });
    expect(fetcher.mock.calls[0][0]).toContain("/api/v1/goals");
    expect(fetcher.mock.calls[0][1].credentials).toBe("omit");
    expect(fetcher.mock.calls[0][1].headers.Authorization).toBeUndefined();
    expect(JSON.parse(fetcher.mock.calls[0][1].body)).toEqual({
      title: "Learn",
    });
  });
  it("does not display a provider secret echoed in an error", async () => {
    vi.stubGlobal(
      "fetch",
      vi
        .fn()
        .mockResolvedValue(
          new Response('{"detail":"secret-key-1234"}', { status: 422 }),
        ),
    );
    await expect(post("/credentials")).rejects.not.toThrow("secret-key");
  });
  it("treats absent optional content as empty", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 404 })),
    );
    await expect(optional("/lessons/1/assessment")).resolves.toBeNull();
  });
  it("accepts an empty success response", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue(new Response(null, { status: 204 })),
    );
    await expect(
      request("/credentials/1", { method: "DELETE" }),
    ).resolves.toBeUndefined();
  });
});
