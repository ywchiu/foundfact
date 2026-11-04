// Screen each post once, including while a request is in flight. Failed batches wait before retrying.
export function isVisiblePost(el) {
  if (document.visibilityState === "hidden") return false;
  const r = el.getBoundingClientRect();
  return r.width > 0 && r.height > 0 && r.bottom > 0 && r.top < innerHeight && r.right > 0 && r.left < innerWidth;
}
export function createScanner(adapter, screenFn, render, {
  batchMs = 400, maxBatch = 20, retryBaseMs = 5000, retryMaxMs = 300000, now = Date.now, isVisible = isVisiblePost,
} = {}) {
  const results = new Map();
  const pending = new Map();
  const inFlight = new Set();
  let timer = null, debounce = null, observer = null;
  let flushing = Promise.resolve(), active = false, stopped = false;
  let retryAt = 0, failures = 0;

  function apply(el, id) {
    const r = results.get(id);
    if (!r) return;
    if (r.label === "none") render.unmount(el);
    else render.mount(el, r);
  }

  function schedule() {
    if (stopped || active || timer !== null || !pending.size) return;
    timer = setTimeout(() => { timer = null; flush(); }, Math.max(batchMs, retryAt - now()));
  }

  function flush() {
    if (stopped || active || now() < retryAt) { schedule(); return flushing; }
    active = true;
    flushing = (async () => {
      while (!stopped && pending.size && now() >= retryAt) {
        const visible = new Set(adapter.findPosts(document).filter(isVisible).map(el => el.dataset.vfId));
        for (const id of pending.keys()) if (!visible.has(id)) pending.delete(id);
        const batch = [...pending.values()].filter(p => !results.has(p.id) && !inFlight.has(p.id)).slice(0, maxBatch);
        // A response may have completed after an earlier scan queued this ID.
        for (const id of pending.keys()) if (results.has(id)) pending.delete(id);
        if (!batch.length) break;
        for (const p of batch) { pending.delete(p.id); inFlight.add(p.id); }
        try {
          const out = (await screenFn(batch)) || [];
          const ids = new Set(batch.map(p => p.id));
          for (const r of out) if (ids.has(r.post_id)) results.set(r.post_id, r);
          if (batch.some(p => !results.has(p.id))) throw new Error("Incomplete screening response");
          failures = 0; retryAt = 0;
          if (!stopped) for (const el of adapter.findPosts(document)) apply(el, el.dataset.vfId);
        } catch (error) {
          for (const p of batch) if (!results.has(p.id)) pending.set(p.id, p);
          const delay = Math.min(retryMaxMs, retryBaseMs * 2 ** Math.min(failures++, 16));
          retryAt = now() + Math.max(delay, Number(error.retryAfterMs) || 0);
          break;
        } finally {
          for (const p of batch) inFlight.delete(p.id);
        }
      }
    })().finally(() => { active = false; schedule(); });
    return flushing;
  }

  function scan() {
    if (stopped) return flushing;
    for (const el of adapter.findPosts(document)) {
      if (!isVisible(el)) continue;
      const post = adapter.extractPost(el);
      if (!post) continue;
      if (el.dataset.vfId !== post.id) {
        render.unmount(el);
        el.dataset.vfId = post.id;
      }
      if (results.has(post.id)) apply(el, post.id);
      else if (!inFlight.has(post.id)) pending.set(post.id, post);
    }
    if (batchMs <= 0) return flush();
    schedule();
    return flushing;
  }

  function onScroll() { clearTimeout(debounce); debounce = setTimeout(scan, 200); }
  return {
    scan,
    start() {
      stopped = false; retryAt = 0; failures = 0;
      window.addEventListener("scroll", onScroll, true);
      window.addEventListener("resize", onScroll);
      document.addEventListener("visibilitychange", onScroll);
      scan();
      observer?.disconnect();
      observer = new MutationObserver(() => {
        clearTimeout(debounce);
        debounce = setTimeout(scan, 300);
      });
      observer.observe(document.body, { childList: true, subtree: true });
    },
    stop() {
      stopped = true;
      window.removeEventListener("scroll", onScroll, true);
      window.removeEventListener("resize", onScroll);
      document.removeEventListener("visibilitychange", onScroll);
      observer?.disconnect(); clearTimeout(timer); clearTimeout(debounce); timer = null;
    },
    results,
  };
}
