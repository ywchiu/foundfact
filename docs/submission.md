# Meta Global AI Developer Hackathon — submission checklist

Deadline: **Wed 2026-11-04 21:00 ET = Thu 2026-11-05 10:00 Taiwan.** Aim to submit by 2026-11-05 08:00 TW.

**Before the deadline (✋ = needs David's OK first):**

- [x] Test split eval run → `eval/results/meta.md`. This waits on the `data/eval/REVIEW.md` sign-off. After
  the run, copy the numbers into the README and the video's closing card.
- [x] ✋ Deployed to https://foundfact.infominer.io (a small VM, `deploy/vm.md`).
  - [x] Smoke test: /screen, /verify SSE through Cloudflare (22 s), 429 and 503 guards, /privacy.
- [x] Fill in the live URL in `README.md`. Build `dist/foundfact.zip` with `extension/build.sh --release <URL>`.
- [ ] Record the video from `docs/video-script.md`. Upload it as **public**, and check the link plays in a
  logged-out browser.
- [ ] Fill in the video link in `README.md`.
- [ ] ✋ Make the GitHub repo **public**. Check these first:
  - `git ls-files | grep -E '\.env$|posts.jsonl|teacher/.*jsonl|hunch.db'` returns nothing;
  - `git log -p | grep -iE 'sk-|muse_api=|openrouter_key='` returns nothing;
  - the README "Built during the hackathon vs. pre-existing" section is accurate.
- [ ] Submission form (fields as on the CV submit page, checked 2026-11-03; * = required):
  - [ ] Team Name* and Team Members (list everyone who worked on it)
  - [ ] Track*: **Startups Track**
  - [ ] Problem statement*: **Build for Your World**
  - [ ] Project Description*. There is no live-site field, so put https://foundfact.infominer.io and the
    extension install steps here, plus what was built during the hackathon.
  - [ ] Public GitHub Repository*
  - [ ] 3-Minute Demo Video*
  - [ ] Describe your use of Meta products to build the submitted project*
  - [ ] Why are Meta's models important to your solution?*
  - [ ] Optional: X post link (Most Viral), partner feedback
  - [ ] Survey*: how likely to build with Meta Model API; overall opinion of Meta Model API
  - [ ] Optional survey: recommend Meta Model API / Muse Code (0-5), biggest obstacle, comparison with other
    models, what matters most, switching cost, what would stop production use
  - [ ] Media consent checkbox (Meta and CV may publish the submitted materials)
- [ ] Post on X with the video and repo link, tagging the hackathon (Most Viral prize). ✋ David posts from
  his own account.
- [ ] Optional: Chrome Web Store submission (`docs/store-listing.md`). ✋ Needs David's developer account. Review
  takes days, so the hackathon submission does not depend on it.

**Content rules (Meta):**

- [ ] No political, election or war content in the repo demo data, the video, screenshots or the live site
  examples.
- [ ] The web app examples are scam-only: SMS, investment invite, fake customer service.
- [ ] Not "basic RAG": the agent does live web search plus claim-level verdicts that require evidence.
