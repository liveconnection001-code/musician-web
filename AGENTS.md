# MUSICIAN website project instructions

Before changing design, copy, imagery, SEO, or page structure, read
`MUSICIAN_DESIGN_GUIDELINES.md` in this directory and treat it as the project's
living design brief.

- Preserve the visual and structural relationship with the existing site.
- Check both desktop and mobile layouts before publishing.
- Give the user a short estimated working time when starting a substantial task.
- Add newly confirmed user preferences to `MUSICIAN_DESIGN_GUIDELINES.md`.
- Do not remove existing artist/unit categories or content unless the user clearly asks.
- Publish only after verifying that referenced assets exist on the server and that no broken images or links remain.

## Remote CI and deployment discipline

- Do not push trial-and-error or known-failing commits merely to run GitHub Actions. Complete equivalent local tests, syntax checks, and deployment preflight first; push only a coherent, success-ready checkpoint.
- When a secrets-, runner-, or production-only check is unavoidable, run one diagnostic execution, wait for its completion, and analyze its logs and artifacts before making local corrections. Do not trigger concurrent or repeated push-based retries to inspect results.
- Before a production deploy, verify the approved input, manifest, target files, and HTTP timeout/preflight locally. If a remote deploy fails, determine the cause before any subsequent deployment attempt.
- Keep GitHub notifications enabled: never suppress, reject, or block GitHub mail as a substitute for preventing avoidable failures.
