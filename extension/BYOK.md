# Standalone extension (0.2.0)

The extension does not use the FoundFact backend. The public website remains a separate, server-backed service with its original limits.

1. Load this folder unpacked, or unzip `dist/foundfact.zip` and load the extracted folder.
2. Open the extension's Settings page. Choose OpenRouter or TypeSafe and enter that service's Jev key. Enter a separate Meta Model API key for Muse.
3. Save, then reload an existing Facebook or Threads tab.

Keys are stored in this browser's extension-local storage, restricted to trusted extension contexts. They are not synced or sent to the social site or FoundFact server. This is not encryption at rest; someone with access to the browser profile can access its extension data. Do not include real keys in screenshots or recordings.

Visible posts are screened serially using Jev. The extension checks the bundled Taiwan police domain list before making a model request. It never follows suspect links or resolves short links. It does not inspect images during feed screening. Missing keys, invalid credentials, provider errors and rate limits pause screening; there is no Muse or backend fallback. Provider limits still apply to BYOK.

Clicking Why opens the native side panel and starts a direct Muse investigation. Muse reads the first supported social-CDN image if one exists, extracts claims, compares relevant bundled cases, searches the web, judges evidence and writes the report. Case candidates are selected locally using text overlap and reviewed by Muse; this is a different matcher from the website. Source-less verdicts and empty search hits cannot support a claim. Cached complete reports and feed results last 24 hours in extension session storage, and disappear when the browser session ends.

Optional hourly limits are local to this browser and credential. `0` means no local cap. Jev counts new post requests, Muse counts full investigations (each investigation can make multiple provider requests). Failed/aborted requests count because the provider may already have charged them. Identical cached content does not count. Cache, deduplication, one full check at a time, and provider Retry-After pauses prevent runaway retries. A fresh browser session resets local counters; these are spending conveniences, not an enforceable account budget. Set a provider-side spending cap for a hard account limit.

Required network permissions: Facebook/Threads; OpenRouter/TypeSafe for Jev; Meta for Muse; Facebook/Instagram image CDNs for image reading. No localhost, run.app or FoundFact API permission is included.

Validation: automated tests use mocked provider responses; no paid model call is made by the tests. A live check on an English Threads post confirmed Jev screening and a completed direct Muse investigation in the native side panel (2026-11-05 Taiwan time). It returned high risk with all three claims insufficient; this is a risk warning, not proof of fraud. Prior server-backed evaluation and timing figures do not establish performance of this new client-side path.
