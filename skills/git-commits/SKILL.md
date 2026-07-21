---
name: git-commits
description: Write great git commit messages following Chris Beams' 7 rules — imperative subject under 50 chars, body that narrates why, theme-sized commit scope. Use before writing any commit message. Asks once per repo whether commits should carry a Co-Authored-By trailer and remembers the answer; accepts an optional `coauthor` or `no-coauthor` argument to set it directly.
---

# Git Commit Message Skill

Source: https://chris.beams.io/git-commit

## The 7 Rules

1. **Separate subject from body with a blank line**
2. **Limit the subject line to 50 characters** (72 is the hard cap; GitHub truncates at 72)
3. **Capitalize the subject line**
4. **Do not end the subject line with a period**
5. **Use the imperative mood in the subject line**
6. **Wrap the body at 72 characters**
7. **Use the body to explain what and why, not how**

---

## Rule 5 — Imperative mood

The subject must complete this sentence: _"If applied, this commit will **[subject]**"_

| Good | Bad |
|------|-----|
| Fix broken login redirect | Fixed broken login redirect |
| Add price history timestamps | Adding price history timestamps |
| Remove deprecated auth flow | Removed deprecated auth flow |

Git itself uses imperative: "Merge branch", "Revert commit", "Initial commit".

---

## Rule 7 — Why, not how

The diff shows *what* changed. The commit message must explain *why*:
- What problem does this solve?
- Why this approach and not another?
- What was the state before, and what is it now?

Code is self-documenting for the *how*. Only the message can capture the *why*.

---

## Commit scope — group into medium-sized units

Decide *what goes in a commit* before writing the message. Default to **fewer,
theme-sized commits**, not the smallest possible diff. One commit should be one
coherent change a reviewer can take in at once — not one file, one function, or one
sub-task split off on its own.

**The grouping test** — put changes in the *same* commit when:
- They share one *why* (the same reason explains all of them)
- You would revert them together
- One is incomplete or doesn't make sense without the others
- They're the same kind of change across several files (a refactor, a rename, a
  fix and the call sites it touches)

**Split into separate commits only when** changes are genuinely independent:
- Different reasons (an unrelated bug fix that happened to be nearby)
- One is risky or worth reverting on its own
- One is pure noise next to real work (a large mechanical reformat vs. a logic change)

Each commit should still build / pass on its own — that's the floor, not a reason to
split further.

### Calibration

| Too granular (avoid) | Medium (aim here) | Too coarse (avoid) |
|----------------------|-------------------|--------------------|
| One commit per file for the same refactor | One commit for the whole refactor, body narrating the shared *why* | A day's unrelated fixes dumped together |
| Splitting a fix from the test/call-site it requires | Fix + its directly-required changes together | "Fix bugs and update UI and bump deps" |
| A commit for the type, then another for its first use | The feature slice that uses the type | Mixing a mechanical rename with a behavior change |

When several themes are in the working tree at once, stage by theme (`git add -p` or
per-path) and make one commit per theme — not one per change within a theme. Prefer 1
solid commit over 3 thin ones when they tell the same story.

A subject that needs *and* to join two facets of one change is fine ("Fix broken
scraper and add availability tracking" — both are the scraper work). A subject that
needs *and* to join *unrelated* work ("Fix bugs and update UI and bump deps") is the
smell that you've combined themes — split it.

---

## Project style adaptations

These override or extend the canonical rules for this project:

- **No type prefix** — never use `feat:`, `fix:`, `chore:`, `refactor:` etc
- **Dash list items** — body lists use `-`, never `*` or `•`
- **No trailing dots** — no line in subject or body ends with `.`
- **No trailers by default** — no `Co-Authored-By`, no generator footer (see "Attribution presets" for how to switch this per repo or per call)
- **Narrate the why by default** — the body is a flat `-` list explaining the shared reason behind the change, *not* a per-file changelog. Name a file only when it actually helps a reader understand the *why*. (See "Body shape" below for the one exception.)
- **Capitalize every bullet** — each `-` item starts with a capital letter, same as the subject
- **Imperative in bullets too** — body bullet points start with a verb in imperative mood, same rule as the subject line

---

## Attribution presets

Whether a commit carries a `Co-Authored-By` (or any generated-by) trailer is a
**per-repository policy**, not a fact about the message. Resolve it once, before writing,
by taking the first of these that applies — and only ask the user when every automatic
step came up empty:

1. **An explicit instruction in the request** — `coauthor` / `no-coauthor` passed as an
   argument to this skill, or stated in the conversation. Always wins, and is not saved
   unless the user says to make it permanent.
2. **A saved answer** — read the first of these files that exists:

   ```bash
   cat "$(git rev-parse --git-dir)/la-skills-commit-attribution" 2>/dev/null   # this repo
   cat ~/.config/la-skills/commit-attribution 2>/dev/null                      # global
   ```

   The file holds one word, `clean` or `coauthor`. Use it and say nothing.
3. **A written rule in the repo** — a `CLAUDE.md`, `AGENTS.md`, or `CONTRIBUTING.md` that
   asks for (or forbids) a trailer. Follow it; that is the project speaking. Don't save it,
   the file is already the source of truth.
4. **What the repo already does** — read the trailers on recent commits:

   ```bash
   git log -20 --pretty=%b | grep -ci "^co-authored-by:"
   ```

   A clear majority either way (roughly 80% or more, over at least 5 commits) is the house
   convention — match it, and don't save it either. This keeps a shared repo internally
   consistent without anyone configuring anything.
5. **Nothing decided it — ask, once.** Only now is the question worth the user's attention.
   Ask a single question with three answers, then act on it:

   | Answer | Do |
   |--------|-----|
   | Yes, add the trailer | write `coauthor` to the repo file (step 2) |
   | No, keep commits clean | write `clean` to the repo file |
   | Just this once | use it, save nothing, ask again next time |

   If the user says "always" or "everywhere", write to the global file instead of the repo
   one, creating `~/.config/la-skills/` if needed.

   ```bash
   echo clean > "$(git rev-parse --git-dir)/la-skills-commit-attribution"
   ```

   The repo file lives **inside `.git/`** on purpose: it never gets committed, never shows
   up in `git status`, and never lands in someone else's checkout — a personal preference
   should not become a diff in a shared project. The trade-off is that it is per-clone:
   a fresh clone asks once more. That is the right cost for not touching the working tree.

Never ask twice for the same repo, and never ask when steps 1-4 already answered. If a
saved answer contradicts a fresh explicit instruction, the instruction wins for that commit
and the saved answer stays — offer to update it only if the user asks for it to stick.

### The presets

| Preset | When | Footer |
|--------|------|--------|
| `clean` (default) | Solo work, personal repos | none |
| `coauthor` | Repos that credit agent or pair work in-tree | a blank line, then the `Co-Authored-By:` line(s) |

Two rules hold under either preset: trailers go **after a blank line at the very end** of
the body, and they are the **only** place a footer belongs — never fold attribution into
the subject or into a body bullet.

---

## Body shape — narrate the why, reach for file headers only on purpose

The body's job is to explain the *why* (Rule 7). A body split into one section per
touched file drifts into a per-file "what changed" changelog and fragments a single
coherent reason across headers. So the **default body is a flat `-` list narrating the
shared why** — even when the change spans several files. A reader should come away
understanding *why this commit exists*, not getting a file-by-file inventory.

Introduce a `path/to/file` section header **only** when one of these is true:

- **A change in that file is significant enough to call out on its own** — it carries
  risk, surprise, or a decision a reviewer should see isolated, not buried in the
  narrative.
- **A change is tangential to the commit's main theme** — a small "while I was here"
  fix that rode along. Giving it its own file section is how you *flag* it, so the
  reader sees it's a side change, not part of the headline work.

The tangential case has a hard limit: the **subject always describes the main theme
only** — never tack the side change onto the subject with `and`. If the incidental
change is big enough that a theme-only subject feels dishonest about what the commit
contains, that's the signal to **split it into its own commit** instead. The subject
staying clean is the guardrail against "dump everything in one commit and hand-wave it."

So: file headers are a deliberate tool for *significant* or *tangential* changes — not
the default layout for any commit that happens to touch more than one file.

---

## Templates

### Default — narrate the shared why

Use this for almost every commit, single- or multi-file. No file headers.

```
Imperative subject under 50 chars

- why this change exists / what problem it solves
- another facet of the same reason if needed
```

### With a called-out or tangential section

Reach for this only when a file's change is significant enough to isolate, or is a
tangential ride-along you want to flag (see "Body shape"). Keep the rest as narrative.

```
Imperative subject under 50 chars (main theme only)

- the main why, narrated as usual

path/to/tangential-or-significant-file.rs
- the side change or the part worth isolating, and why it's here
```

---

## Examples

### Good — default narrative (multi-file, no headers)

The change touches `lib.rs` and `store.ts`, but they share one why, so the body
narrates that why instead of inventorying each file.

```
Fix hidden auth window and track item availability

- Replace the offscreen-position hack with a layered window at zero
  alpha so the auth window stays invisible while the page still renders
- Thread an availability flag from the stock widget through to the
  history model so the UI can show out-of-stock state per tick
```

### Good — flagging a tangential ride-along

The headline work is the timeout centralization. A small unrelated tray-icon path fix
rode along — too minor for its own commit — so it gets its own file section to flag it,
and the subject stays about the main theme only.

```
Centralize backend timeouts in one timing module

- Move every scattered Duration literal into timing.rs so the
  scrape/login/quit budgets are tuned in one place

src/lib.rs
- Also fix the tray icon path that broke on the last asset move —
  unrelated to the timeout work, just noticed while editing here
```

### Bad

```
fix: updated some stuff.

changed the scraper and also fixed a bug in the store and some
other things that needed fixing.
```

---

## Preparing the message — always read the diff, not the chat

Before writing the commit message, run `git diff --staged` (and `git diff` for unstaged) to read the actual changes. Never rely solely on what was discussed in the current conversation — the staged diff is the ground truth. The chat may omit details, describe intent rather than what landed, or differ from what was actually staged.

If the diff spans several themes, first split it per "Commit scope" above — stage one theme, commit, repeat — and write each message against that theme's staged diff rather than the whole working tree.

- Use `git status` to see which files are staged vs unstaged
- Use `git diff --staged` to read exactly what will be committed
- If unstaged changes exist that belong in the commit, review them too
- Subject and body must match the diff, not just the stated intent

---

## Quick checklist before committing

- [ ] Commit is one coherent theme — related changes grouped, not split to the smallest diff
- [ ] Subject is ≤ 50 characters
- [ ] Subject starts with a capital letter
- [ ] Subject uses imperative ("Fix", not "Fixed" or "Fixes")
- [ ] Subject has no trailing period or type prefix
- [ ] Blank line between subject and body
- [ ] Body lines wrapped at 72 characters
- [ ] Body explains *why*, not *how*
- [ ] Body is a flat narrative by default — file headers only for a significant or tangential change
- [ ] Subject describes the main theme only — no tangential change tacked on with `and`
- [ ] All list items use `-`
- [ ] Every bullet starts with a capital letter
- [ ] Every bullet starts with an imperative verb
- [ ] Attribution preset resolved — a trailer is present or absent on purpose, not by accident
