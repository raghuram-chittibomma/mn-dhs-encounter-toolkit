# QA and UAT agents — how to run

## Isolation (required)

These agents plan and execute tests **without implementation knowledge**.

Read **`qa-uat/PROVENANCE.md`** first — bootstrap test cases were authored in the
implementation window and require guide-based review before sign-off.

| Allowed | Forbidden |
|---------|-----------|
| `docs/SPEC.md` | `src/**` |
| `docs/QA_VS_DHS_TEST.md` | `tests/**` (pytest) |
| `docs/reference/*.pdf` | `examples/**` (unless you manufactured a copy into `qa-uat/test-data/`) |
| `qa-uat/**` | `docs/VALIDATION_LAYERS.md`, `docs/RULE_SOURCE_TRACE.md` |
| `qa-uat/BLACK_BOX_INTERFACE.md` | Reading or inferring behavior from code, scenarios registry, or generator internals |

At execution time, **observed** validator output (rule IDs, messages) may be
recorded as **actual results** — but must not be used to **pre-write** expected
results before running the test.

## Start a QA session

New chat. Paste:

```
Use the mn-dhs-qa-agent skill.

Read qa-uat/PROVENANCE.md first. Re-derive bootstrap test case expectations
from SPEC + companion guide only. Then execute in qa-uat/.
Do not read src/ or tests/.
```

Follow-up examples:

- “Execute TC-QA-001 through TC-QA-005 and record results.”
- “Add test cases for 837I statement dates per the companion guide.”
- “Manufacture a void encounter missing ICN and validate.”

## Start a UAT session

New chat. Paste:

```
Use the mn-dhs-uat-agent skill.

Run UAT scenarios for an MCO encounter submission analyst.
Work only in qa-uat/. Use the web UI and CLI as a user would.
Do not read src/ or tests/.
```

Follow-up examples:

- “Walk through UAT-003 in the browser at localhost:8501.”
- “Sign off UAT for pre-submission validation workflow.”

## Prerequisites (test executor machine)

```bash
cd mn-dhs-encounter-toolkit
python -m venv .venv
.venv\Scripts\Activate.ps1   # Windows
pip install -e ".[ui]"
```

CLI-only QA: `pip install -e .` is sufficient.
