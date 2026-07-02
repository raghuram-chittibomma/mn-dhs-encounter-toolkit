# QA / UAT workspace (black-box)

Independent test planning and execution for the MN DHS Encounter Toolkit. Test
design is driven by **requirements and companion guides only** — not application
source code.

**Important:** Initial test cases are **bootstrap scaffold** (developer-authored).
Read [PROVENANCE.md](PROVENANCE.md) before sign-off; re-derive expectations in a
fresh agent chat.

## Agents

| Agent | Skill | Purpose |
|-------|-------|---------|
| **QA** | `mn-dhs-qa-agent` | Functional black-box testing: CLI, validation layers, 999/835E, data manufacturing |
| **UAT** | `mn-dhs-uat-agent` | End-user workflows: MCO pre-submission, web UI, sign-off scenarios |

Start a **new Cursor chat** and invoke the skill by name (e.g. “use
`mn-dhs-qa-agent`”). Do not attach `src/` or prior implementation context.

**Bootstrap cases:** initial test cases were scaffolded with developer-window
context. See [`PROVENANCE.md`](PROVENANCE.md) — independent agents must
re-derive expected results from SPEC + companion PDFs before sign-off.

See [AGENTS.md](AGENTS.md) for invocation prompts and isolation rules.

## Layout

```
qa-uat/
  authoritative-context/   What agents may read (SPEC, PDFs, scope docs)
  BLACK_BOX_INTERFACE.md     CLI + UI commands (no implementation)
  test-plans/                Master QA and UAT plans
  test-cases/qa/             Individual QA test cases
  test-cases/uat/            Individual UAT test cases
  test-data/                 Manufactured inputs + manifest
  results/executions/        Per-run JSON logs (gitignored)
  reports/                   Execution reports and UAT sign-off
  scripts/                   Helpers to record runs
  registry/                  Test case index
```

## Typical workflow

1. **Plan** — Agent reads `authoritative-context/` and companion PDFs; extends
   `test-cases/` if gaps are found.
2. **Manufacture data** — Follow `test-data/manufacturing/DATA_GEN_RECIPES.md`
   or case-specific steps (CLI `generate`, hand-built X12, or edited fixtures).
3. **Execute** — You ask the agent to run a case; it uses only the black-box
   interface and records output under `results/executions/`.
4. **Report** — Agent fills `reports/` from the template and updates
   `registry/TEST_CASE_INDEX.md`.

## Recording a run

```bash
python qa-uat/scripts/record_execution.py \
  --case TC-QA-003 \
  --status pass \
  --notes "validate exit 0, 0 errors" \
  --artifact results/executions/TC-QA-003_20260702.json
```

## Boundaries

What this workspace **does not** replace: DHS MN–ITS integration test. See
`docs/QA_VS_DHS_TEST.md` (allowed for scope context only).
