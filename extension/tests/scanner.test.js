import { readFileSync } from "node:fs";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import * as fb from "../content/fb.js";
import { createScanner } from "../content/scanner.js";
import { mountBanner, unmountBanner, hasBanner } from "../content/banner.js";

import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
const FIXTURE = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "fixtures/fb_feed.html"), "utf8");

beforeEach(() => { document.body.innerHTML = FIXTURE; });
afterEach(() => { vi.useRealTimers(); });

describe("fb adapter", () => {
  it("finds one root per post and ignores comment articles", () => {
    const posts = fb.findPosts(document);
    expect(posts.length).toBe(2);
  });

  it("extracts text, author, link domains and images", () => {
    const p = fb.extractPost(fb.findPosts(document)[0]);
    expect(p.platform).toBe("facebook");
    expect(p.text).toContain("保證月報酬30%");
    expect(p.author).toBe("財經老師 陳大明");
    expect(p.link_domains).toEqual(expect.arrayContaining(["lin.ee", "stock-vip.cc"]));
    expect(p.links).toContain("https://lin.ee/abc123"); // unwrapped full URL, for short-link resolution
    expect(p.image_urls[0]).toContain("scontent");
    expect(p.id).toMatch(/^fb-/);
  });

  it("ids are stable for the same content and differ across posts", () => {
    const [a, b] = fb.findPosts(document);
    expect(fb.extractPost(a).id).toBe(fb.extractPost(a).id);
    expect(fb.extractPost(a).id).not.toBe(fb.extractPost(b).id);
  });
});

const HIGH = (id) => ({ post_id: id, label: "high", scam_type: "investment", p_scam: 0.99, p_claim: 0.9, pressure: 2, similar: [], answered_by: "muse", provider: "muse", latency_ms: 10 });
const NONE = (id) => ({ ...HIGH(id), label: "none", scam_type: null });

function makeScanner(screenFn) {
  return createScanner(fb, screenFn, {
    mount: (el, r) => mountBanner(el, r, "zh", () => {}),
    unmount: unmountBanner,
  }, { batchMs: 0, isVisible: () => true });
}

describe("scanner", () => {
  it("banners only flagged posts", async () => {
    const screenFn = vi.fn(async (posts) => posts.map((p) => (p.text.includes("飆股") ? HIGH(p.id) : NONE(p.id))));
    const s = makeScanner(screenFn);
    await s.scan();
    const [a, b] = fb.findPosts(document);
    expect(hasBanner(a)).toBe(true);
    expect(hasBanner(b)).toBe(false);
    expect(screenFn).toHaveBeenCalledTimes(1);
  });

  it("does not duplicate banners or re-screen the same post", async () => {
    const screenFn = vi.fn(async (posts) => posts.map((p) => HIGH(p.id)));
    const s = makeScanner(screenFn);
    await s.scan();
    await s.scan();
    const a = fb.findPosts(document)[0];
    expect(a.querySelectorAll(".vf-host").length).toBe(1);
    expect(screenFn).toHaveBeenCalledTimes(1);
  });

  it("does not requeue posts while their response is pending", async () => {
    let release;
    const gate = new Promise(resolve => { release = resolve; });
    const screenFn = vi.fn(async posts => { await gate; return posts.map(p => HIGH(p.id)); });
    const s = makeScanner(screenFn);
    const first = s.scan();
    await Promise.resolve();
    const second = s.scan();
    release();
    await Promise.all([first, second]);
    expect(screenFn).toHaveBeenCalledTimes(1);
    s.stop();
  });

  it("waits through server cooldown despite repeated DOM-triggered scans", async () => {
    vi.useFakeTimers();
    const screenFn = vi.fn()
      .mockRejectedValueOnce(Object.assign(new Error("HTTP 429"), { retryAfterMs: 60000 }))
      .mockImplementation(async posts => posts.map(p => HIGH(p.id)));
    const s = makeScanner(screenFn);
    await s.scan();
    await s.scan(); await s.scan();
    expect(screenFn).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(59999);
    expect(screenFn).toHaveBeenCalledTimes(1);
    await vi.advanceTimersByTimeAsync(1);
    expect(screenFn).toHaveBeenCalledTimes(2);
    expect(hasBanner(fb.findPosts(document)[0])).toBe(true);
    s.stop();
  });

  it("stops an already scheduled retry when disabled", async () => {
    vi.useFakeTimers();
    const screenFn = vi.fn(async () => { throw new Error("offline"); });
    const s = makeScanner(screenFn);
    await s.scan();
    s.stop();
    await vi.advanceTimersByTimeAsync(300000);
    await s.scan();
    expect(screenFn).toHaveBeenCalledTimes(1);
  });

  it("re-banners a recycled node with new content", async () => {
    const screenFn = vi.fn(async (posts) => posts.map((p) => (p.text.includes("飆股") ? HIGH(p.id) : NONE(p.id))));
    const s = makeScanner(screenFn);
    await s.scan();
    const a = fb.findPosts(document)[0];
    expect(hasBanner(a)).toBe(true);
    a.querySelector('[data-ad-rendering-role="story_message"]').textContent = "週末市集好熱鬧";
    a.querySelector('[data-ad-rendering-role="meta"]').textContent = "";
    a.querySelector('[data-ad-rendering-role="title"]').textContent = "";
    await s.scan();
    expect(hasBanner(a)).toBe(false);
    const lastBatch = screenFn.mock.calls.at(-1)[0];
    expect(lastBatch.map((p) => p.text)).toEqual(["週末市集好熱鬧"]);
  });

  it("remounts a banner that the site re-render removed", async () => {
    const s = makeScanner(async (posts) => posts.map((p) => HIGH(p.id)));
    await s.scan();
    const a = fb.findPosts(document)[0];
    a.querySelector(".vf-host").remove();
    await s.scan();
    expect(hasBanner(a)).toBe(true);
  });

  it("survives a failing screen call", async () => {
    const s = makeScanner(async () => { throw new Error("offline"); });
    await expect(s.scan()).resolves.not.toThrow();
    s.stop();
  });
});

describe("banner", () => {
  it("renders brand + type text in shadow DOM and calls onWhy", () => {
    const el = fb.findPosts(document)[0];
    const onWhy = vi.fn();
    mountBanner(el, HIGH("x"), "zh", onWhy);
    const root = el.querySelector(".vf-host").shadowRoot;
    expect(root.textContent).toContain("這篇貼文可能是投資詐騙");
    expect(root.textContent).toContain("by 查證助手");
    root.querySelector("button").click();
    expect(onWhy).toHaveBeenCalled();
    mountBanner(el, HIGH("x"), "en", onWhy);
    expect(el.querySelector(".vf-host").shadowRoot.textContent).toContain("This post may be a investment scam".replace("a investment", "an investment"));
  });

  it("leaves an identical banner untouched so its own mutation cannot retrigger a scan", () => {
    const el = fb.findPosts(document)[0];
    mountBanner(el, HIGH("x"), "zh", () => {});
    const first = el.querySelector(".vf-host");
    mountBanner(el, HIGH("x"), "zh", () => {});
    expect(el.querySelector(".vf-host")).toBe(first);
    mountBanner(el, HIGH("x"), "en", () => {});
    expect(el.querySelector(".vf-host")).not.toBe(first);
  });

  it("says the link is on the police fraud-domain list for blocklist hits", () => {
    const el = fb.findPosts(document)[0];
    const hit = { ...HIGH("x"), answered_by: "blocklist", link_hit: { domain: "evil-invest.com" } };
    mountBanner(el, hit, "zh", () => {});
    expect(el.querySelector(".vf-host").shadowRoot.textContent).toContain("連結 evil-invest.com 在警政署涉詐網站名單上");
    mountBanner(el, hit, "en", () => {});
    expect(el.querySelector(".vf-host").shadowRoot.textContent).toContain("Link evil-invest.com is on Taiwan police's fraud-site list");
  });
});

it("screens a post only after it becomes visible while scrolling", async () => {
  vi.useFakeTimers();
  const posts = fb.findPosts(document); let visible = new Set([posts[0]]);
  const screenFn = vi.fn(async ps => ps.map(p => NONE(p.id)));
  const s = createScanner(fb, screenFn, { mount() {}, unmount() {} }, { batchMs: 0, isVisible: el => visible.has(el) });
  s.start(); await s.scan();
  expect(screenFn.mock.calls.flatMap(([ps]) => ps)).toHaveLength(1);
  visible = new Set([posts[1]]); window.dispatchEvent(new Event("scroll"));
  await vi.advanceTimersByTimeAsync(200);
  expect(screenFn.mock.calls.flatMap(([ps]) => ps)).toHaveLength(2);
  s.stop();
});
