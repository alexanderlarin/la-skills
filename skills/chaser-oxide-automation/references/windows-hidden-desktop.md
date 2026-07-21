# Windows hidden desktop for invisible Chrome sessions

Use `CreateDesktopW` when offscreen positioning (`--window-position=-32000,-32000`) still
causes a brief taskbar flash or visible window during Chrome startup on Windows. An isolated
WinAPI desktop within `WinSta0` is never rendered — Chrome boots and runs fully
(IntersectionObserver, layout, rAF all work) without any pixel reaching the screen.

## Full implementation

```rust
// All Win32 calls in a synchronous block — convert non-Send handles to raw isize
// BEFORE any .await so the async future stays Send-compatible.
let (port, hdesktop_raw, hprocess_raw, hthread_raw) = {
    let hdesktop = unsafe {
        CreateDesktopW(
            PCWSTR(name_w.as_ptr()),
            PCWSTR::null(),
            None,
            DESKTOP_CONTROL_FLAGS(0),
            0x01FF_u32,
            None,
        )?
    };
    let si = STARTUPINFOW {
        cb: size_of::<STARTUPINFOW>() as u32,
        lpDesktop: PWSTR(desktop_path_w.as_mut_ptr()),  // "WinSta0\<name>"
        ..Default::default()
    };
    let mut pi = PROCESS_INFORMATION::default();
    CreateProcessW(
        PCWSTR::null(),
        Some(PWSTR(cmd_w.as_mut_ptr())),
        None, None, false,
        PROCESS_CREATION_FLAGS(0),
        None, PCWSTR::null(), &si, &mut pi,
    )?;
    // Extract as isize so the tuple is Send (HANDLE wraps *mut c_void)
    (port, hdesktop.0 as isize, pi.hProcess.0 as isize, pi.hThread.0 as isize)
};

// Poll until Chrome's CDP port is open, then connect (async; only Send types in scope).
let (browser, handler) = Browser::connect(format!("http://127.0.0.1:{port}")).await?;
```

`Browser::connect(url)` auto-fetches the WebSocket endpoint from `/json/version` — use it
whenever you manage the Chrome process yourself instead of via `Browser::launch`.

## Send-safety rule

Win32 `HANDLE` / `HDESK` wrap `*mut c_void` and are not `Send`. Any async fn called from
`tokio::spawn` must be `Send`. Perform ALL Win32 calls in a synchronous block before the
first `.await`, extract results as `isize` (`handle.0 as isize`), and reconstruct typed
handles only inside sync closures (`HANDLE(raw as *mut _)`) as needed.

## Cargo features (`windows` crate)

```toml
[dependencies.windows]
features = [
    "Win32_Foundation",
    "Win32_Graphics_Gdi",        # required by CreateDesktopW
    "Win32_Security",            # required by CreateDesktopW
    "Win32_UI_WindowsAndMessaging",
    "Win32_System_StationsAndDesktops",
    "Win32_System_Threading",
]
```

`CreateDesktopW` needs both `Win32_Graphics_Gdi` AND `Win32_Security`; missing either gives
a confusing "not found" error.

## Cleanup

Call `browser.close().await` first, wait for the process to exit naturally via
`WaitForSingleObject` (3–5 s), then `CloseHandle` + `CloseDesktop`. `TerminateProcess` as
a timeout fallback is safe — it's a no-op on an already-exited process.
