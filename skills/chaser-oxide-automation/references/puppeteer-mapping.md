# Puppeteer → chaser-oxide mapping

Quick reference when porting Node/Puppeteer code to Rust.

| Puppeteer (Node)                         | chaser-oxide (Rust)                                                          |
|------------------------------------------|-----------------------------------------------------------------------------|
| `puppeteer.launch({headless, args})`     | `Browser::launch(BrowserConfig::builder()…build()?)` + poll handler         |
| (implicit) browser event loop            | `tokio::spawn(async move { while let Some(ev) = handler.next().await { if let Err(_) = ev { break; } } })` |
| `browser.newPage()`                      | `browser.new_page("about:blank").await?` → `ChaserPage::new(page)`          |
| `puppeteer-extra-plugin-stealth`         | `page.enable_stealth_mode()` (+ `chaser.apply_native_profile()`)            |
| `page.goto(url, {waitUntil})`            | `chaser.goto(url).await?` (+ poll / `wait_for_navigation()`)                |
| `page.$('sel')` / `page.$$('sel')`      | `raw_page().find_element(sel)` / `find_elements(sel)`                       |
| `page.waitForSelector(sel)`              | poll `find_element` with a deadline (see patterns.md)                       |
| `page.waitForFunction(fn)`               | poll `evaluate(expr)` for `true` (see patterns.md)                         |
| `page.$eval(sel, el => …)`              | `find_element` → `el.inner_text()` / `el.attribute()`                      |
| `page.evaluate(() => …)`                | `chaser.evaluate("…")` (→ `Option<Value>`) or `raw_page().evaluate(..).into_value()` |
| `page.evaluateOnNewDocument(fn)`         | `raw_page().evaluate_on_new_document(js)`                                   |
| `page.click(sel)`                        | `find_element(sel)?.click()` or `chaser.click_human(x, y)`                 |
| `page.type(sel, txt, {delay})`           | `chaser.type_text_with_delay(txt, min, max)`                               |
| `page.keyboard.press('Enter')`           | `chaser.press_enter()` / `press_key("Enter")`                              |
| `page.mouse.move(x, y)`                 | `chaser.move_mouse_human(x, y)`                                             |
| `page.setRequestInterception(true)`      | `BrowserConfig…enable_request_intercept()` + `EventRequestPaused` listener  |
| `request.respond({...})`                | `page.execute(FulfillRequestParams…)`                                       |
| `request.continue()`                    | `page.execute(ContinueRequestParams::new(id))`                             |
| `page.screenshot({path})`               | `raw_page().save_screenshot(ScreenshotParams…, path)`                      |
| `page.cookies()` / `setCookie`          | `browser.get_cookies()` / `browser.set_cookies(vec![CookieParam])`         |
| `browser.close()`                       | `browser.close().await?; browser.wait().await?` + abort handler task        |
