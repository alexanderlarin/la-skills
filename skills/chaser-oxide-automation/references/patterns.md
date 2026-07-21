# chaser-oxide patterns — full code reference

## Waiting strategies

The base API has no `waitForSelector`. Poll with a deadline:

```rust
use std::time::Duration;
use tokio::time::sleep;

async fn wait_for_selector(
    chaser: &ChaserPage,
    selector: &str,
    timeout: Duration,
) -> anyhow::Result<chaser_oxide::Element> {
    let deadline = tokio::time::Instant::now() + timeout;
    loop {
        if let Ok(el) = chaser.raw_page().find_element(selector).await {
            return Ok(el);
        }
        if tokio::time::Instant::now() >= deadline {
            anyhow::bail!("timeout waiting for {selector}");
        }
        sleep(Duration::from_millis(150)).await;
    }
}

async fn wait_for_fn(chaser: &ChaserPage, expr: &str, timeout: Duration) -> anyhow::Result<()> {
    let deadline = tokio::time::Instant::now() + timeout;
    loop {
        let v = chaser.evaluate(expr).await?;
        if matches!(v, Some(serde_json::Value::Bool(true))) {
            return Ok(());
        }
        if tokio::time::Instant::now() >= deadline {
            anyhow::bail!("timeout waiting for condition: {expr}");
        }
        sleep(Duration::from_millis(150)).await;
    }
}
```

Add small jitter to poll intervals so timing isn't metronomically robotic.

---

## Request interception

Arm at config time, listen for `EventRequestPaused`, then fulfill or continue each request.

```rust
use chaser_oxide::browser::{Browser, BrowserConfig};
use chaser_oxide::cdp::browser_protocol::fetch::{
    ContinueRequestParams, EventRequestPaused, FulfillRequestParams,
};
use base64::Engine;
use futures::StreamExt;

let (browser, mut handler) = Browser::launch(
    BrowserConfig::builder()
        .enable_request_intercept()   // REQUIRED — must be set at config time
        .disable_cache()
        .build().map_err(|e| anyhow::anyhow!(e))?,
).await?;
tokio::spawn(async move {
    while let Some(ev) = handler.next().await {
        if let Err(_) = ev { break; }
    }
});

let page = browser.new_page("about:blank").await?;
let mut paused = page.event_listener::<EventRequestPaused>().await?;
let page2 = page.clone();
tokio::spawn(async move {
    while let Some(ev) = paused.next().await {
        if ev.request.url.ends_with("/target") {
            let body = base64::engine::general_purpose::STANDARD.encode("<html>ok</html>");
            let _ = page2.execute(FulfillRequestParams::builder()
                .request_id(ev.request_id.clone())
                .response_code(200)
                .body(body)
                .build().unwrap()).await;
        } else {
            let _ = page2.execute(ContinueRequestParams::new(ev.request_id.clone())).await;
        }
    }
});
```

`ResourceType` is at `chaser_oxide::cdp::browser_protocol::network::ResourceType` and
re-exported at the crate root as `chaser_oxide::ResourceType`.

> `ChaserPage` has convenience wrappers (`enable_request_interception`, `fulfill_request_html`,
> `continue_request`) but they're not exercised by upstream examples — verify signatures before
> relying on them; the event-based form above is the proven path.

Don't over-block on hostile pages: a real browser fetches images/CSS, so a zero-asset
request pattern is itself anomalous.

---

## Screenshots

```rust
use chaser_oxide::page::ScreenshotParams;
use chaser_oxide::cdp::browser_protocol::page::CaptureScreenshotFormat;

// Full page → file
chaser.raw_page()
    .save_screenshot(
        ScreenshotParams::builder()
            .format(CaptureScreenshotFormat::Png)
            .full_page(true)
            .omit_background(true)
            .build(),
        "shot.png",
    )
    .await?;

// Single element → file
let el = chaser.raw_page().find_element("table.itemlist tr").await?;
el.save_screenshot(CaptureScreenshotFormat::Png, "row.png").await?;

// Raw bytes in memory
let bytes: Vec<u8> = chaser.raw_page()
    .screenshot(ScreenshotParams::builder().format(CaptureScreenshotFormat::Png).build())
    .await?;
```

---

## Cookies

Cookies live on `Browser`, not `Page`. Prefer a persistent `user_data_dir` over manual
shuttling for session reuse.

```rust
use chaser_oxide::cdp::browser_protocol::network::CookieParam;

let cookies = browser.get_cookies().await?;
browser.set_cookies(vec![
    CookieParam::builder()
        .domain(".example.com").name("x").value("y").path("/")
        .build()?,
]).await?;
browser.clear_cookies().await?;
```

---

## Error handling & retries

```rust
async fn scrape_with_retry(url: &str, max: u32) -> anyhow::Result<String> {
    let mut last = None;
    for attempt in 1..=max {
        match scrape_once(url).await {
            Ok(v)  => return Ok(v),
            Err(e) => {
                log::warn!("attempt {attempt} failed: {e}");
                last = Some(e);
                tokio::time::sleep(std::time::Duration::from_millis(800 * attempt as u64)).await;
            }
        }
    }
    Err(last.unwrap())
}
```

Cold first loads in a fresh profile are often flaky (redirects, late hydration); a warm
retry usually succeeds. Always wrap the whole operation in `tokio::time::timeout` so a
hung page can't block forever.
