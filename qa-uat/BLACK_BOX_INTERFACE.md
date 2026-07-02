# Black-box interface (CLI and web UI)

**Execution only.** Use these commands to run tests. Do **not** use this file to
plan expected validator behavior — derive expectations from `docs/SPEC.md` and
companion guide PDFs. See `PROVENANCE.md`.

Use these commands to execute tests. Do not inspect `src/` to learn behavior.

## Install

```bash
pip install -e .          # CLI: validate, generate, gen999, gen835e
pip install -e ".[ui]"    # adds mn-encounter-ui
```

## CLI commands

| Command | Purpose |
|---------|---------|
| `mn-encounter list-scenarios` | List scenario names for `generate` |
| `mn-encounter generate` | Build synthetic 837 `.x12` |
| `mn-encounter validate` | Run validation layers on `.x12` |
| `mn-encounter gen999` | Build 999 from 837 |
| `mn-encounter gen835e` | Build 835E from 837 |

### generate

```bash
mn-encounter generate \
  --scenario <name> \
  --seed <int> \
  --out qa-uat/test-data/inputs/<file>.x12
```

| Flag | Notes |
|------|-------|
| `--scenario` | Repeatable; names from `list-scenarios` or SPEC |
| `--seed` | Required; same scenario+seed → same file |
| `--count` | Instances per scenario (default 1) |
| `--allow-inconsistent` | Only when intentionally writing broken non-`err_*` data |

Exit: `0` success, `2` unknown scenario or consistency failure.

### validate

```bash
mn-encounter validate --in <file.x12>
mn-encounter validate --in <file.x12> --format json --out qa-uat/results/executions/<case>_validate.json
mn-encounter validate --in <file.x12> --layers 1,2,3,4
```

Exit: `0` no error-level findings, `1` errors present, `2` unreadable input.

### gen999 / gen835e

```bash
mn-encounter gen999 --in <837.x12> --out qa-uat/test-data/inputs/<999>.x12
mn-encounter gen999 --in <837.x12> --out <out> --mode simulation --seed 7

mn-encounter gen835e --in <837.x12> --out qa-uat/test-data/inputs/<835e>.x12
mn-encounter gen835e --in <837.x12> --out <out> --mode deterministic
```

### Validate generated 999 (envelope only)

```bash
mn-encounter validate --in <999.x12> --layers 1
```

## Web UI

```bash
mn-encounter-ui
# http://localhost:8501
```

| Page | Black-box use |
|------|----------------|
| Validate 837 | Upload manufactured `.x12`, review findings, export JSON/CSV |
| Validation layers | Browse rule catalog (reference only at execution) |
| Generate 999 | Upload 837 → download 999 |
| Generate 835E | Upload 837 → download 835E |
| Scenario lab | Build sample 837 from scenario name + seed |

Privacy caption: local processing; files in memory only.

## Manufacturing data without generate

When scenarios are insufficient:

1. Start from a `generate` output and edit segments per companion guide tables.
2. Save under `qa-uat/test-data/inputs/` with a manifest entry.
3. Document edits in the test case file.

Never use real member IDs, names, or production trading partner credentials.
