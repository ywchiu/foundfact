import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";
import { beforeEach, describe, expect, it } from "vitest";
import * as threads from "../content/threads.js";

const FIXTURE = readFileSync(join(dirname(fileURLToPath(import.meta.url)), "fixtures/threads_feed.html"), "utf8");
beforeEach(() => { document.body.innerHTML = FIXTURE; });

describe("threads adapter", () => {
  it("finds one root per post and skips containers without a post link", () => {
    expect(threads.findPosts(document).length).toBe(2);
  });

  it("extracts body text without username, time, counts or translate button", () => {
    const p = threads.extractPost(threads.findPosts(document)[0]);
    expect(p.platform).toBe("threads");
    expect(p.author).toBe("stockvip888");
    expect(p.text).toContain("保證月獲利30%");
    expect(p.text).toContain("私訊領飆股名單");
    expect(p.text).not.toMatch(/stockvip888|3小時|翻譯|1,203|\b117\b/);
    expect(p.id).toBe("th-DfAAA111");
  });

  it("unwraps l.threads.com links and keeps post images but not avatars", () => {
    const p = threads.extractPost(threads.findPosts(document)[0]);
    expect(p.link_domains).toEqual(["lin.ee"]);
    expect(p.links).toEqual(["https://lin.ee/abc"]);
    expect(p.image_urls).toEqual(["https://instagram.ftpe8-4.fna.fbcdn.net/v/t15/chart.jpg"]);
  });

  it("drops counts like 2萬 from text", () => {
    const p = threads.extractPost(threads.findPosts(document)[1]);
    expect(p.text).toBe("今天爬合歡山，天氣超好");
  });
});
