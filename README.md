# la-skills

Personal collection of agent skills by **A. O. Larin**, usable from
**Claude Code** (plugin marketplace), **OpenAI Codex** (`.codex/skills/`), and any
registry that indexes plain skill folders.

The source of truth for every skill is a `SKILL.md` folder under [`skills/`](skills/).
Everything else — the Claude Code plugin manifests, the packaging script — is a thin
layer on top of those folders.

## Skills

| Skill | What it does |
|-------|--------------|
| [`chaser-oxide-automation`](skills/chaser-oxide-automation/) | Rust browser automation with chaser-oxide over CDP — anti-bot evasion, clean Chrome launch, first-run-UI suppression, hidden/offscreen windows. |
| [`git-commits`](skills/git-commits/) | Write git commit messages following Chris Beams' 7 rules with personal style adaptations. |

## Install — Claude Code

The repo root is both the marketplace and the plugin, so one add covers all skills:

```shell
/plugin marketplace add alexanderlarin/la-skills   # or a local path: /plugin marketplace add ./la-skills
/plugin install la-skills@la-skills
```

Skills are then namespaced as `la-skills:git-commits`, `la-skills:chaser-oxide-automation`.

Update after pushing changes:

```shell
/plugin marketplace update la-skills
```

## Install — skills.sh CLI

The root-level `skills/` layout is what the cross-agent CLI scans, so it installs into
whichever agent you are running (Claude Code, Codex, Cursor, OpenCode):

```bash
npx skills add alexanderlarin/la-skills
```

## Install — OpenAI Codex

Codex reads skills from `.codex/skills/`. Copy the folders in:

```bash
mkdir -p .codex/skills
cp -r skills/* .codex/skills/
```

## Packaging — Skills Manager and other registries

Registries that take an uploaded bundle want a `.skill` file: a zip whose single
top-level entry is the skill folder. Build them with the repo's own script — it
validates frontmatter first (`name` present, matching the folder, lowercase-with-hyphens;
`description` present and within 1024 characters):

```bash
py scripts/package_skill.py                 # validate + package every skill into dist/
py scripts/package_skill.py git-commits     # just one
py scripts/package_skill.py --check         # validate only, build nothing
```

`dist/` is gitignored — attach the bundles to a GitHub release rather than committing them.

## Where this can be published

| Target | How it ingests | What it needs from this repo |
|--------|----------------|------------------------------|
| Claude Code plugin marketplace | git repo + ref | `.claude-plugin/` manifests (done) |
| skills.sh | open listing, installs via CLI | root `skills/` folder (done) |
| SkillsMP | automated GitHub crawling | nothing — it finds skill-shaped repos |
| localskills.sh | publisher account, manual upload | a `.skill` bundle per skill |
| Awesome-lists / cursor.directory | PR or manual submission | a public repo URL |

Multiple skills in one repo is the normal case for all of these: the Claude Code plugin
exposes them as one install, and the skills.sh CLI walks the `skills/` container and lists
every skill it finds.

## Repo layout

```
la-skills/
├── .claude-plugin/
│   ├── marketplace.json          # marketplace catalog (plugin source: "./")
│   └── plugin.json               # plugin manifest
├── skills/                       # ← source of truth (portable SKILL.md folders)
│   ├── chaser-oxide-automation/
│   └── git-commits/
├── scripts/package_skill.py      # validate + build .skill bundles
├── AGENTS.md                     # Codex / cross-agent entry point
├── LICENSE                       # MIT
└── README.md
```

## License

MIT — see [LICENSE](LICENSE).
