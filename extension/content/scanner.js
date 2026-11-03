// Finds posts via a site adapter, screens new ones in batches, and keeps banners attached to the
// right post even when the site recycles DOM nodes (virtualized feeds).
export function createScanner(adapter, screenFn, render, { batchMs = 400, maxBatch = 20 } = {}) {
  const results = new Map(); // post id -> ScreenResult
  const pending = new Map(); // post id -> post
  let timer = null;
  let observer = null;
  let flushing = Promise.resolve();

  function apply(el, id) {
    const r = results.get(id);
    if (!r) return;
    if (r.label === "none") render.unmount(el);
    else render.mount(el, r);
  }

  async function flush() {
    timer = null;
    const batch = [...pending.values()].slice(0, maxBatch);
    batch.forEach((p) => pending.delete(p.id));
    if (!batch.length) return;
    let out = [];
    try {
      out = (await screenFn(batch)) || [];
    } catch {
      return; // offline / backend down: leave posts unmarked
    }
    for (const r of out) results.set(r.post_id, r);
    for (const el of adapter.findPosts(document)) {
      if (el.dataset.vfId && results.has(el.dataset.vfId)) apply(el, el.dataset.vfId);
    }
    if (pending.size) await flush();
  }

  function scan() {
    for (const el of adapter.findPosts(document)) {
      const post = adapter.extractPost(el);
      if (!post) continue;
      if (el.dataset.vfId !== post.id) {
        render.unmount(el); // recycled node: drop the old post's banner first
        el.dataset.vfId = post.id;
      }
      if (results.has(post.id)) apply(el, post.id); // re-attach if the site re-render removed it
      else pending.set(post.id, post);
    }
    if (!pending.size) return flushing;
    if (batchMs <= 0) {
      flushing = flushing.then(flush);
      return flushing;
    }
    if (!timer) timer = setTimeout(() => { flushing = flushing.then(flush); }, batchMs);
    return flushing;
  }

  return {
    scan,
    start() {
      scan();
      let debounce = null;
      observer = new MutationObserver(() => {
        clearTimeout(debounce);
        debounce = setTimeout(scan, 300);
      });
      observer.observe(document.body, { childList: true, subtree: true });
    },
    stop() { observer?.disconnect(); clearTimeout(timer); },
    results,
  };
}
