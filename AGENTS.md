# AGENTS.md — la-skills

This repository is a portable collection of agent skills. Each skill is a
self-contained folder under `skills/` with a `SKILL.md`
(YAML frontmatter: `name` + `description`) and optional `scripts/`,
`references/`, `assets/`.

## For Codex and other agents

Install the skills into this project's `.codex/skills/` (or your agent's skill
directory) by copying the folders from `skills/`, or by running
`npx skills add alexanderlarin/la-skills`. Once installed, consult a skill's
`SKILL.md` whenever its `description` matches the task at hand, and follow its
instructions.

## Available skills

- **chaser-oxide-automation** — Rust browser automation with chaser-oxide over
  CDP: anti-bot evasion, clean Chrome launch, first-run-UI suppression,
  hidden/offscreen windows. Use for any Rust Chrome/Chromium automation.
- **git-commits** — Write git commit messages (Chris Beams' 7 rules, language-aware
  subjects, body that narrates why, and project style adaptations). Use
  before writing any commit message. Resolves the Co-Authored-By policy from
  the repo itself, asks once if it can't tell, and remembers the answer in
  `.git/`. Takes an optional `coauthor` / `no-coauthor` argument to override.

## Portability note

Keep skill bodies agent-neutral. Avoid hard dependencies on one agent's
invocation syntax (e.g. `/plugin`, `plugin:skill` namespacing) inside a skill's
instructions so the same `SKILL.md` stays useful across Claude Code, Codex, and
others.

## Packaging

`py scripts/package_skill.py` validates every skill's frontmatter and writes one
`.skill` bundle per skill into `dist/` for registries that take uploads. Pass
`--check` to validate without building.
