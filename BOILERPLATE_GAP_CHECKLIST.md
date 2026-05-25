# Boilerplate Gap Checklist

This checklist tracks boilerplate/features present in `../sphinx-github-changelog` that you may want to adopt here.

How to use:
- Default: items are considered adopted unless excluded.
- Exclude item: check `[x]` in the `Exclude` column and optionally add a reason.

## CI and GitHub automation

| Exclude | Item | Notes / Reason |
|---|---|---|
| [ ] | Add a dedicated coverage-comment workflow triggered from CI completion | |
| [ ] | In CI tests, upload one coverage artifact per Python version | |
| [ ] | Add a coverage merge + PR comment step/job | |
| [ ] | Add a separate autofix workflow on pull requests | |
| [ ] | Use explicit workflow/job permissions (least privilege) | |
| [ ] | Set `persist-credentials: false` on checkout except where write is needed | |
| [ ] | Add a release environment gate on publish job | |

## Packaging and metadata

| Exclude | Item | Notes / Reason |
|---|---|---|
| [ ] | Enrich project metadata (project URLs, keywords, expanded classifiers) | |
| [ ] | Add explicit `license-files` metadata | |
| [ ] | Add UV defaults (`tool.uv.default-groups`, `tool.uv.exclude-newer`) | |
| [ ] | Split dependency groups into `dev` / `docs` / `types` as needed | |

## Linting and static analysis

| Exclude | Item | Notes / Reason |
|---|---|---|
| [ ] | Expand pre-commit hooks (check-json, check-toml, check-yaml, shebang checks) (only those that have an effect in the repo) | |
| [ ] | Enable BasedPyright pre-commit hook (currently commented out) | |
| [ ] | Add Zizmor pre-commit hook for GitHub Actions linting | |
| [ ] | Align Ruff hook naming (`ruff` vs `ruff-check`) for consistency | |

## Testing habits

| Exclude | Item | Notes / Reason |
|---|---|---|
| [ ] | Add coverage flags to pytest default options | |
| [ ] | Add `tool.coverage.run` and `tool.coverage.report` settings | |
| [x] | Consider splitting tests into `tests/unit` and `tests/acceptance` | |
| [ ] | Add or expand `tests/conftest.py` fixtures strategy | Not sure what this is about. |

## Release/changelog process

| Exclude | Item | Notes / Reason |
|---|---|---|
| [ ] | Add `.github/release.yml` bot-author exclusions for generated changelogs | |

## Documentation and contributor workflow

| Exclude | Item | Notes / Reason |
|---|---|---|
| [ ] | Expand `CONTRIBUTING.md` with concrete commands for lint/test/release | |
| [x] | Add scripts docs (or helper scripts) for recurring project tasks | |
| [x] | Add docs build workflow/docs helper if docs become a priority | |

## Potentially not applicable (confirm intent)

| Exclude | Item | Notes / Reason |
|---|---|---|
| [x] | Add docs-specific dependencies/workflows (if no docs site is planned) | |
| [x] | Raise minimum Python to 3.11+ to match sphinx-github-changelog | |

## Exclusions log

Use this area if you want a short rationale list for decisions.

- [ ] Exclude:
- [ ] Exclude:
- [ ] Exclude:
