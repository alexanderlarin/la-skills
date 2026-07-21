---
name: chaser-oxide-automation
description: Expert guidance for browser automation in Rust with chaser-oxide (a hardened chromiumoxide fork) driving a real Chrome over CDP. Use whenever you scrape or automate Chrome/Chromium from Rust — anti-bot evasion, CDP, ChaserPage, fingerprint/native profiles, human-like interaction, request interception — or when porting Puppeteer/Node automation to Rust. ALSO use for launching Chrome cleanly from Rust: suppressing first-run UI (What's New tab, "Sign in to Chrome" promo, "unsupported command-line flag" infobar), Chrome launch flags, Local State / profile priming, Browser::launch vs Browser::connect, and headed / offscreen / hidden-desktop windows — even when the user doesn't name chaser-oxide. Triggers on chaser-oxide, chaser_oxide, ChaserPage, chromiumoxide, CDP, apply_native_profile, and Rust Chrome launch / profile / first-run-UI questions.
---

# chaser-oxide Browser Automation (Rust)

You are an expert in `chaser-oxide` — a Rust fork of `chromiumoxide` that hardens the
Chrome DevTools Protocol (CDP) client against bot detection **at the transport/protocol
layer**, not via JavaScript wrappers. You drive a **real, separately-installed Chrome /
Chromium binary** over CDP, so the fingerprint matches a genuine browser the way
Puppeteer's does — but with stealth, native-profile, and client-hints handling built in.

This is the recommended backend for stealth scraping in Rust when:
- The target blocks WebView2 / synthetic clients but lets real Chrome through.
- You need JS-injection-free evasion (JS wrappers like a `window.addEventListener`
  override break the target page's own scripts).
- You want a single Rust binary with no Node.js runtime to ship.

> ## ⚠️ Maintaining this skill — keep it PROJECT-AGNOSTIC
>
> This is a reusable skill, not a project log. When you learn something while working on a
> specific app, **distill the transferable automation lesson and strip every app-specific
> detail before adding it here**:
> - ❌ No app/company/site names, target URLs, real domains, file names, IPC/event names,
>   CSS selectors, locale-specific strings, or framework-state types.
> - ✅ Generic placeholders only: `example.com`, `window.__extract`, `user_data_dir`,
>   "the account id", "the target".
> - Keep the *mechanism* (the CDP/chaser API behavior, the failure mode, the fix pattern)
>   — that's the value. Drop the *instance*.
> - Project-specific facts (which selector, which widget, which target needs which config)
>   belong in that project's own docs/memory, with a link back to the general lesson here.
>
> A good test: if a reader on a totally different site couldn't apply the point as written,
> it's too specific — generalize it or move it out.

## References (load when needed)

- `references/patterns.md` — full code for: waiting strategies, request interception, screenshots, cookies, error handling/retries
- `references/puppeteer-mapping.md` — Puppeteer → chaser-oxide API mapping table
- `references/windows-hidden-desktop.md` — `CreateDesktopW` hidden desktop implementation (lesson #14)

---

## Web scraping heuristics — quality-ranking framework (read FIRST when designing extraction)

When you design how to extract a field, pick the **highest-ranked tier that is feasible**, and
**state the tier choice before writing the extractor**. Robustness drops sharply each tier down;
a lower tier is a deliberate, documented exception, not a default.

**Tier 1 — Structured & semantic data (always try first).** Purpose-built for consumption,
survives layout/CSS changes, often schema-validated:
- JSON-LD: `script[type="application/ld+json"]` (schema.org `Product`/`Offer`/`Article`…).
- Open Graph / meta tags (`og:*`, `product:price:amount`, `itemprop=...`).
- The page's own JSON: SPA hydration/state blobs (inline `data-state`/`__NEXT_DATA__`-style
  JSON) and the **XHR/fetch endpoints** the page itself calls — reverse-engineer and call them
  directly (often returns far more than the rendered DOM; see lessons #11–#13).
- RSS/Atom feeds, sitemaps.
With chaser-oxide: read these by `evaluate`-ing a tiny parser in the page (`JSON.parse` the
LD/state blob), or `fetch` the API from the page's main world (cookies via `credentials:
'include'`). Deserialize straight into a Rust struct.

**Tier 2 — Semantic DOM selectors (when no structured data exists).** Identify elements by what
they REPRESENT, not how they look:
- Stable `data-*`/`role`/`aria`/`id`/`data-testid` attributes; never presentational/obfuscated
  classes (build-hashed classes like `.p2y_17`/`.css-1ab2c3` rotate every deploy → silent null).
- Text/label anchoring (XPath `//label[contains(.,'Price')]/following-sibling::*`, or find a
  container by a stable attribute then read its children).
With chaser-oxide: `raw_page().find_element("[data-widget=...]")` / `find_elements`, then
`inner_text()`/`attribute()`.

**Tier 3 — ML-assisted parsing (when the DOM is genuinely inconsistent/dynamic).** Embedding- or
vision-language-model extraction over a screenshot (`raw_page().save_screenshot(...)`) + layout.
Robust to class renames / A/B variants, at higher runtime + dev cost. Use only when Tier 1–2 fail
*consistently* due to layout instability — not for a one-off selector you could anchor semantically.

**Tier 4 — Regex (last resort).** HTML is not a regular language; regex over raw markup breaks on
whitespace/attribute-order/nesting (5–20%/month breakage, silent wrong data). Acceptable ONLY for:
a tiny, monitored scope; or extracting from **already-isolated plain text** (an API/JSON string, a
single element's `textContent`, a log line). If you must: constrain to a small substring, use
negated classes (`[^>]*`) over `.`, and **validate the output shape — fail loudly on mismatch**.

### Decision flow
`structured data? → Tier 1` · else `stable semantic attribute / text anchor? → Tier 2` · else
`layout chronically unstable & budget allows? → Tier 3` · else `tiny scope + plain text + validated? → Tier 4`.

### Two rules that override "always pick the highest tier"
1. **A higher tier can carry a DIFFERENT SEMANTIC VALUE than the one you actually want.**
   Validate that the higher-tier field is semantically identical to your target before adopting it.
   It's legitimate to take availability from Tier-1 JSON-LD while taking a price from a Tier-2
   widget when those are the *right* values. Document why you descended.
2. **Provide ordered fallbacks, but only across tiers that mean the same thing.** A fallback that
   silently substitutes a different-semantic value is worse than returning null.

When a poll-friendly extractor "isn't ready", return `null` (not 0/empty) so the caller keeps
polling; reserve a concrete value for a genuine reading (incl. a real zero/out-of-stock).

---

## Core mental model

- `chaser-oxide` is a **self-contained fork** — it vendors the chromiumoxide tree
  (`chromiumoxide_cdp` / `chromiumoxide_types` 0.9) inside the one crate; there is **no
  separate `chromiumoxide` dependency**. The base `Browser`, `BrowserConfig`, `Page`,
  `Element`, `Handler`, `BrowserFetcher`, and `Result` are all exported from the
  `chaser_oxide` crate root.
- Two stealth surfaces, both added by the fork:
  - `ChaserPage` — wraps a `Page` (`ChaserPage::new(page)`) and adds: `apply_profile` /
    `apply_native_profile`, `evaluate`, `evaluate_stealth`, human mouse/keyboard, scrolling.
    **`apply_native_profile()` is the recommended entry point** — upstream's own quickstart
    leads with it. It reads the live Chrome version over CDP and detects host OS and RAM, so
    the fingerprint is consistent by construction rather than hand-assembled.
  - `page.enable_stealth_mode()` — method on the **base `Page`**. The lighter option:
    basic automation-signal removal (protocol-level evasion + init scripts for all future
    document loads), with no fingerprint work. Use it when you want minimal interference
    rather than a full profile.
  - Either way, call it on the blank page **before** the first `goto`.
- Reach the base `Page` from a `ChaserPage` via `chaser.raw_page()` for base-API methods
  (`find_element`, `save_screenshot`, `evaluate_on_new_document`, `wait_for_navigation`, …).
- **Cookies live on `Browser`, not `Page`**: `browser.get_cookies()`, `set_cookies()`, `clear_cookies()`.
- Every `Browser::launch` returns a `Handler` that **must be polled** on its own task or
  nothing happens. Forgetting this is the #1 beginner bug.
- CDP types live under `chaser_oxide::cdp::...`; `ResourceType` is also re-exported at the
  crate root as `chaser_oxide::ResourceType`.

## Dependencies

```toml
[dependencies]
chaser-oxide = "0.2"
tokio = { version = "1", features = ["rt-multi-thread", "macros", "time", "sync"] }
futures = "0.3"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
anyhow = "1"
```

## Basic structure — launch, poll, drive, drop

```rust
use chaser_oxide::{Browser, BrowserConfig, ChaserPage};
use futures::StreamExt;
use std::time::Duration;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    let (mut browser, mut handler) = Browser::launch(
        BrowserConfig::builder()
            .viewport(None)   // real-window viewport — best for fingerprint
            .build()
            .map_err(|e| anyhow::anyhow!(e))?,
    ).await?;

    // Poll the handler — REQUIRED. Break on error so is_finished() fires on disconnect.
    let handler_task = tokio::spawn(async move {
        while let Some(ev) = handler.next().await {
            if let Err(e) = ev { log::debug!("handler error: {e:?}"); break; }
        }
    });

    let page = browser.new_page("about:blank").await?;
    let chaser = ChaserPage::new(page);
    chaser.apply_native_profile().await?;       // BEFORE navigation
    tokio::time::sleep(Duration::from_millis(100)).await;

    chaser.goto("https://example.com").await?;
    let title = chaser.evaluate("document.title").await?; // Option<serde_json::Value>

    browser.close().await?;
    browser.wait().await?;
    handler_task.abort();
    Ok(())
}
```

**Stealth before navigation:** `apply_native_profile()` / `apply_profile()` (and
`enable_stealth_mode()`) must run on the blank page **before** `goto()` so the very first request already carries the
hardened identity. The 100 ms sleep ensures registration lands.

## Launch / BrowserConfig

```rust
BrowserConfig::builder()
    .viewport(None)                       // real-window viewport (best fingerprint)
    // .new_headless_mode()               // new headless; .with_head() for visible window
    // .enable_request_intercept()        // Fetch-domain interception (see references/patterns.md)
    // .disable_cache()                   // pair with interception
    // .chrome_executable("/path/chrome")
    // .user_data_dir("/path/profile")    // persistent cookies/session
    // .arg("--window-size=1280,800")
    // .arg("--lang=ru-RU")
    .disable_default_args()               // drop chromiumoxide's ~19 automation-fingerprint flags
    .build()?
```

- `.viewport(None)` — lets the real OS window drive the viewport; fingerprints better than a forced size.
- `.with_head()` — for flows a human must complete (login, CAPTCHA).
- `.disable_default_args()` + add back only essentials — see lesson #2.

## Stealth profiles (the heart of chaser-oxide)

```rust
// Recommended — native profile (auto-detects OS, Chrome version, RAM):
let page = browser.new_page("about:blank").await?;
let chaser = ChaserPage::new(page);   // wrap about:blank
chaser.apply_native_profile().await?; // BEFORE goto
chaser.goto("https://target").await?;

// Lighter — enable_stealth_mode on the base Page, no fingerprint work:
let page = browser.new_page("about:blank").await?;
page.enable_stealth_mode().await?;
page.goto("https://target").await?;
let chaser = ChaserPage::new(page);

// Explicit fingerprint:
use chaser_oxide::profiles::{ChaserProfile, Gpu};
let profile = ChaserProfile::windows()
    .chrome_version(131).gpu(Gpu::NvidiaRTX3080).memory_gb(16)
    .locale("ru-RU").timezone("Europe/Moscow").screen(1920, 1080)
    .build();
chaser.apply_profile(&profile).await?;
```

Keep fingerprints internally consistent — don't mix macOS OS with Windows UA.
`native()` is consistent by construction; prefer it for the scraping path.

## Navigation, element selection, JS evaluation

```rust
// Navigate
chaser.goto("https://example.com").await?;
let html = chaser.content().await?;
let cur  = chaser.url().await?;                    // Option<String>
chaser.raw_page().wait_for_navigation().await?;    // after a click that navigates

// Elements (base API via raw_page())
let el    = chaser.raw_page().find_element("button#submit").await?;
let items = chaser.raw_page().find_elements(".card").await?;
let text  = el.inner_text().await?;                // Option<String>
let href  = el.attribute("href").await?;           // Option<String>
// Element also: click(), type_str(), press_key(), scroll_into_view(), find_element() (scoped)
```

**Two `evaluate` surfaces — don't mix them up:**
- `chaser.evaluate(script)` → `Result<Option<Value>>`. Isolated world (clean, page JS can't see your code).
- `chaser.evaluate_stealth(script)` → main world (sees real page globals, spoofed values, injected `window.__extract`).
- `raw_page().evaluate(script)` → base chromiumoxide, returns `EvaluationResult`; convert with `.into_value::<T>()`.

```rust
// Main-world define-and-call in one eval (the core/harness pattern):
let v = raw_page.evaluate(format!("{EXTRACTOR_JS}\n;window.__extract()")).await?
    .into_value::<MyStruct>()?;
```

**CAVEAT:** `evaluate_on_new_document` lands in the MAIN world; a fresh `evaluate_stealth` call
runs in a FRESH isolated world and can't see it → silent `null`. Inject AND read in the same world,
or define-and-call in one `raw_page().evaluate()` call.

Note: `evaluate(&str)` routes via `is_likely_js_function` — a leading `function`/arrow goes to
`callFunctionOn`. Keep extractor sources starting with a `/* comment */` so they take the
plain-expression path.

## Waiting strategies

There is **no `waitForSelector`**. Poll with a deadline — see `references/patterns.md` for
the full `wait_for_selector` / `wait_for_fn` helpers. Key principle: prefer condition-based
waits over fixed sleeps; add small jitter to poll intervals.

## Human-like interaction (anti-detection)

```rust
chaser.move_mouse_human(640.0, 360.0).await?;       // Bezier-curve mouse path
chaser.click_human(640.0, 360.0).await?;            // human move + click at coords
chaser.type_text("query").await?;                    // realistic per-key timing
chaser.type_text_with_delay("query", 60, 180).await?;
chaser.type_text_with_typos("username").await?;      // injects + corrects typos
chaser.press_enter().await?;  // also press_tab(), press_key("Enter")
chaser.scroll_human(800).await?;                     // human-paced wheel scroll
```

Use `*_human` methods on hostile/behavior-analyzed pages instead of `Element::click()` /
`type_str()`. `scroll_human` matters for lazy-loaded content that only fires on a real scroll.

## Request interception, screenshots, cookies, error handling

See `references/patterns.md` for full verified code. Quick reference:
- **Interception**: arm with `.enable_request_intercept()` at config time; listen for `EventRequestPaused`.
- **Screenshots**: `raw_page().save_screenshot(ScreenshotParams…, path)` (file) or `.screenshot(params)` (bytes).
- **Cookies**: on `Browser` — `get_cookies()`, `set_cookies(vec![CookieParam…])`, `clear_cookies()`.
- **Retries**: exponential backoff; cold first loads are often flaky, a warm retry usually succeeds.

## Integrating into a desktop app (e.g. Tauri)

- **Per-operation launch, shared profile.** Launch Chrome per op (login / scrape / fetch); point every launch at one `user_data_dir` so sessions are shared. Per-op cost is negligible when ops are seconds/hours apart.
- **Return values directly.** `evaluate()` returns Rust values — no URL-scheme round-trips needed.
- **Core/harness reuse.** Shared JS core injected as init script; harness collapses to Rust polling + `evaluate`.
- **Headed login, poll for an authoritative identity field** (account id, not display name), then persist.
- **JoinHandle type gotcha.** `tauri::async_runtime::spawn` returns a different `JoinHandle` type than `tokio::spawn`. If you store it typed `tokio::task::JoinHandle<T>`, spawn with `tokio::spawn`.
- **Cancellation**: own `Browser` in a task; aborting drops it → CDP close. Also abort the handler task.
- **Logout = delete the `user_data_dir`.**

---

## Anti-detection & robustness lessons

Hard-won, reusable across targets. Project-specific tuning belongs in that project's own docs.

1. **Stealth is not a silver bullet — measure plain vs. stealth.** Protocol-level stealth
   (`enable_stealth_mode` / `apply_*_profile`) injects main-world scripts and CDP emulation overrides
   that create *detectable inconsistencies* on some strict targets. A **least-modified real Chrome
   (base `Page`, no emulation)** can pass where stealth fails. Make stealth toggleable and compare.

2. **Match a real browser's launch: minimal args via `.disable_default_args()`.** chromiumoxide's
   `DEFAULT_ARGS` add ~19 flags that real users never have and anti-bots fingerprint. Drop them;
   add back only essentials (`--no-first-run`, `--no-default-browser-check`, window size, `--lang`).
   `launch()` still adds `--remote-debugging-port`/`--user-data-dir`/`--disable-extensions`.
   `navigator.webdriver` stays false either way. NOTE: `.disable_default_args()` does NOT
   strip chaser-oxide's separately-injected `--disable-blink-features=AutomationControlled`
   (see #18) — to be rid of it you must spawn Chrome yourself and `Browser::connect`.

3. **Open `about:blank` first, navigate second.** `browser.new_page("https://slow-target")` BLOCKS
   until load. Always `new_page("about:blank")` (instant), then navigate as a separate step.

4. **MAIN world vs isolated world — the null-extract trap.** See the "JS evaluation" section above.

5. **Detect anti-bot structurally — NOT by page text, and NOT by HTTP status alone.** Some anti-bots
   serve the block as HTTP 200 (redirect to a challenge URL with an empty app shell). The robust
   signal: `blocked = status∈{403,429} OR (challenge-marker URL AND zero app-framework elements)`.
   Never match localized body text — fragile and locale-dependent.

6. **One diagnostic probe per poll.** Return the extraction result AND a structural snapshot
   (`{ url, title, authForm, widgetCount, bodyLen }`) and log it (throttled). This turns "it just
   fails" into: logged-in / login-form / blocked / mid-load. Gate success on an authoritative field
   (e.g. an account id), not a display string.

7. **Anti-bot flags are stateful.** Repeated hits can flag IP/profile. When evaluating a config:
   reset `user_data_dir`, idle for a cool-down, then do one clean run. Don't judge while hot.

8. **Teardown — close AND wait, or you get the "Restore pages?" bubble.** `Browser::Drop` uses
   `kill_on_drop`: a bare `browser.close().await` without `browser.wait()` can SIGKILL Chrome
   before it exits cleanly, which Chrome records as a crash. Fix: `close().await` THEN
   `tokio::time::timeout(_, browser.wait())`. For paths that drop `Browser` without `close()`
   (task `abort()`): launch with `--disable-session-crashed-bubble` + `--hide-crash-restore-bubble`,
   AND before each launch rewrite `Default/Preferences` (`exit_type:"Crashed"→"Normal"`,
   `exited_cleanly:false→true`) so Chrome has nothing to restore.

   **Windows: call CDP `Browser.close` before `TerminateProcess`** — otherwise Chrome logs
   `Failed to unregister class Chrome_WidgetWin_0. Error = 1412`. Wait for natural exit via
   `WaitForSingleObject` (3–5 s); only then `TerminateProcess` as a fallback.
   Use `tokio::sync::Notify::notify_waiters()` to broadcast quit to ALL active browser tasks.

9. **Serialize Chrome per `user_data_dir`.** Two Chrome processes on the same profile collide on
   `SingletonLock`. Guard every launch with one async `Mutex<()>`: foreground ops `lock().await`;
   background/periodic ops `try_lock()` and skip if busy.

10. **Tab-close ≠ process-exit.** Closing the last tab/window doesn't necessarily end the Chrome
    process. Use both signals: handler-finished = whole browser exited; target-missing = that tab
    closed (`browser.pages()` — target vanishes on close, not on navigation).

    **Critical: the handler loop must `break` on error, not just log.** `while let Some(ev)`
    matches `Some(Err(...))` — a WebSocket disconnect produces errors, not `None`, so the loop
    spins forever and `JoinHandle::is_finished()` never becomes true. Fix:

    ```rust
    while let Some(ev) = handler.next().await {
        if let Err(e) = ev {
            log::debug!("cdp handler event error: {e:?}");
            break; // transport error is terminal — exit so is_finished() fires promptly
        }
    }
    ```

    Handler stream errors are transport-level (WebSocket close/reset). CDP method errors surface
    on the individual method call, not the stream — so breaking on any stream error is safe.

11. **Don't DOM-scrape a virtualized/paginated list — drive its API.** SPAs server-render only the
    FIRST SCREEN as inline state blobs; lazy-loaded items are rendered without new blobs. "Scroll to
    bottom + read DOM" silently caps at the first page. Call the list's own pagination endpoint via
    `evaluate` of an `await fetch(...)` IIFE; dedup across pages. Union the first-screen DOM snapshot
    in LAST — never pre-seed it into the dedup set or page 0 makes the bulk look "all seen."

12. **A per-client failure is not universal — re-probe under real Chrome first.** An API returning
    403 to a bare fetch or WebView may answer 200 under a real CDP-driven Chrome (full cookie jar,
    `Origin`/`Referer`, client-hints, TLS fingerprint). Before building elaborate header-capture
    machinery, run one probe: `evaluate` of `await fetch(url, {credentials:'include'})`. The fix
    is often "just call it."

13. **Session revalidation: optimistic + background re-scrape, fail-safe.** Emit the cached identity
    immediately (fast UI), then in the background open the account URL and re-scrape ONCE (no retries;
    early-exit on a definitive signal). 3-way outcome: `LoggedIn` → refresh; definitive `LoggedOut` →
    clear; `Inconclusive` (anti-bot / didn't render) → **keep cached session**. Never log a user out
    on an inconclusive check.

14. **"New headless" is still fingerprintable — use offscreen-headed for invisible ops.**
    `new_headless_mode()` can be detected by strict targets. For invisible background ops, launch a
    normal **headed** window and park it far offscreen (`--window-position=-32000,-32000`). Same
    fingerprint that passes interactively, no window the user sees.

    **Windows: offscreen windows can still briefly flash.** Use `CreateDesktopW` for truly invisible
    sessions — an isolated WinAPI desktop that is never rendered but runs Chrome fully (layout,
    IntersectionObserver, rAF all work). See `references/windows-hidden-desktop.md` for the full
    implementation. Connect via `Browser::connect(format!("http://127.0.0.1:{port}"))` once Chrome's
    CDP port is open.

15. **Race long CDP operations against session death with an `until_dead` helper.** Navigation
    futures (`http_future` / `goto`) have no tie to handler liveness — when Chrome exits the
    WebSocket drops but the future keeps waiting for an event that never arrives (~30 s timeout).
    Add a helper that resolves as soon as the handler task finishes (requires lesson #10's `break`):

    ```rust
    pub async fn until_dead(&self) {
        loop {
            if !self.is_alive() { return; }
            tokio::time::sleep(std::time::Duration::from_millis(200)).await;
        }
    }

    // Race a navigation against Chrome being closed mid-load:
    let result = tokio::select! {
        r = session.open_page(url, focused) => Some(r),
        _ = session.until_dead()            => None,
    };
    ```

    Without lesson #10's `break`, `is_alive()` stays true forever and `until_dead()` never
    resolves. The two fixes are a pair.

16. **Suppress Chrome's first-run UI via the RIGHT `Local State` key — and only patch a
    COMPLETE file.** Modern Chrome gates the "What's New" tab on
    `browser.last_whats_new_version` in the profile-root `Local State` (an integer
    milestone); the legacy `browser.whats_new_ui.last_version` is **ignored** on current
    builds. Patching only the legacy key fails *intermittently* — it appears to work on
    repeat launches (Chrome records the milestone itself after showing What's New once) but
    re-fires on fresh/cleared profiles and after a Chrome upgrade. Set
    `last_whats_new_version` above any real milestone (e.g. `9999`) on **every** launch
    (Chrome rewrites the real value each start). The "Sign in to Chrome" promo is suppressed
    by a `First Run` sentinel file in the profile root. **CRITICAL:** a hand-written *sparse*
    `Local State` is discarded by Chrome at boot (it regenerates a complete one and re-arms
    the UI), so you may only patch a `Local State` that Chrome itself wrote — detect
    completeness by a top-level `os_crypt` key (+ non-trivial size), NOT mere file existence
    (a stub appears within milliseconds of launch).

17. **Windowless profile prime — initialize a fresh profile with zero visible UI.** To
    bootstrap that complete `Local State` on a brand-new/cleared profile without any window
    or flash, launch Chrome with `--no-startup-window` (kept alive by `--remote-debugging-port`):
    it fully initializes the profile (writes a complete `Local State` incl. `os_crypt`) while
    opening **no windows or tabs** — first-run UI is never rendered, on any platform. Poll
    until the file is *complete* (lesson #16), then kill the process (the file is already
    flushed). Superior to priming with a hidden/offscreen window, which still renders
    first-run UI invisibly and can briefly flash. Patch lesson #16's keys before the real
    launch.

18. **chaser-oxide's launcher force-injects `--disable-blink-features=AutomationControlled`,
    and the builder can't disable it.** Its `BrowserConfig` `hidden` field defaults on with
    no public setter to turn off, and `.disable_default_args()` does NOT strip this flag (it's
    added separately from `DEFAULT_ARGS`). The flag trips Chrome's yellow "You are using an
    unsupported command-line flag" infobar AND is itself an automation tell. For a truly
    least-modified, infobar-free Chrome, **spawn the binary yourself** (`tokio::process::Command`
    with your exact flags + `--remote-debugging-port`) and attach with
    `Browser::connect("http://127.0.0.1:{port}")` — the same connect pattern as the hidden
    desktop (#14). Verify against your installed chaser-oxide version; this is fork behavior.

19. **Reuse the existing tab — never create-then-close (it flashes).** Chrome opens one tab
    at launch. `new_page(...)` followed by closing the original swaps tabs → a visible
    flicker ("winking tab"). Instead reuse the first tab from `browser.pages()` and navigate
    it, and/or start Chrome at `about:blank` so there is exactly one clean tab to drive.

20. **`goto`/`http_future` hangs ~30 s on non-network schemes.** `about:`, `chrome:`, and
    `data:` URLs produce no HTTP response, so a navigation that waits on the response future
    blocks until an internal fallback (~30 s). Detect these schemes and navigate WITHOUT
    awaiting a response (return "no status"). Only http(s) navigations carry the anti-bot
    status signal (#5) anyway.

21. **Skip the orphan-kill process scan on the hot path — launch optimistically.** Scanning
    the process table to kill an orphaned Chrome on the same `user_data_dir` (WMI / PowerShell
    `Get-CimInstance`, or equivalent) costs ~2–3 s *per launch* and dominates interactive
    (login) latency. Launch first; only if Chrome fails to expose its CDP port (the
    SingletonLock-conflict symptom, lesson #9) run the kill + clear-lock + retry once.
    Background/periodic ops can keep the upfront kill — their latency is non-critical.

22. **Don't ship Chrome's simulation/test switches** (e.g. `--simulate-outdated-no-au`). They
    drive Chrome's update-state UI and can surface unexpected cards ("Chrome was updated" /
    "outdated") — a normal install never passes them. Least-modified principle: if a real
    user's Chrome wouldn't have a flag, drop it.

---

## Best practices

1. Spawn the handler-polling task immediately after `launch`; abort it on teardown. **Break on error** (see lesson #10).
2. Apply stealth **before** the first real `goto` — `chaser.apply_native_profile()` for the scraping path, `page.enable_stealth_mode()` when you only want the light touch; add ~100 ms settle.
3. Prefer the native fingerprint for scraping; keep any spoofed profile internally consistent.
4. Use condition-based waits (poll `find_element` / `evaluate`) with jitter, not fixed sleeps.
5. Use `*_human` methods and `scroll_human` on hostile/behavior-analyzed pages.
6. Wrap every operation in `tokio::time::timeout`; race long CDP futures against `until_dead()`.
7. Use `evaluate_stealth` for main-world calls (injected globals); `evaluate` for isolated-world reads. Deserialize into typed structs; keep extraction logic in shared JS cores.
8. Share one `user_data_dir` for session reuse; delete it to log out. Cookies are on `Browser`.
9. Don't reintroduce JS-wrapper stealth — protocol-level is the point of this library.
10. Pin `chaser-oxide` (fast-moving 0.2.x). The base `Page`/`Element`/`Browser` API is chromiumoxide 0.9-equivalent, reachable via `raw_page()`.

## Caveats / verify-against-source

`chaser-oxide` is a fast-moving 0.2.x **self-contained fork** (current: 0.2.4; vendors
`chromiumoxide_cdp` / `chromiumoxide_types` 0.9). Some `ChaserPage` convenience methods
(e.g. request-interception wrappers) aren't covered by upstream examples — verify signatures
with `cargo doc --open` before relying on them. The base `Page`/`Element`/`Browser` API
(chromiumoxide 0.9) is always reachable via `raw_page()`.

**Porting from Puppeteer?** See `references/puppeteer-mapping.md`.
