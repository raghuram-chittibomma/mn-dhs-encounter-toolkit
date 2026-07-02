# TC-UAT-005 — Trainer uses Scenario lab

> **Bootstrap — review required.** See `qa-uat/PROVENANCE.md`.

| Field | Value |
|-------|-------|
| **Review status** | `approved` |
| **Persona** | MCO trainer / business analyst |
| **Priority** | P2 |
| **Workflow** | Demo data generation |

## Objective

Non-developer builds sample encounters from named scenarios.

## Steps

1. **Scenario lab** — select `epsdt_teen_checkup` or `atypical_provider`
2. Set seed `99`
3. Generate and download 837
4. Validate in **Validate 837** page
5. Save artifacts under `qa-uat/test-data/inputs/uat_scenario_lab_seed99.x12`

## Expected results

| Check | Expected |
|-------|----------|
| Generation | File downloads without CLI |
| Validation | Outcome matches scenario intent (clean for epsdt; atypical provider rules per guide) |

## Pass / fail

- **Pass:** End-to-end UI-only path works.
- **Fail:** Cannot generate or validate from Scenario lab.
