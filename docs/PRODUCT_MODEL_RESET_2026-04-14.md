# PaperFit Product Model Reset

Date: 2026-04-14
Status: active
Scope: product definition, host-facing entry model, documentation contract

## Summary

PaperFit is now defined as a **cross-host academic-paper layout agent system**, not as a CLI-first tool bundle.

Supported host targets remain:

- `Claude Code`
- `Codex`
- `Cursor`

Across all hosts, the stable product contract is:

- the user describes the goal in natural language
- the PaperFit agent routes the request to the correct workflow
- internal runtime / CLI / scripts perform execution
- visual results are the primary acceptance signal

## Why This Reset Was Needed

The previous documentation and host assets drifted toward a CLI-first mental model:

- users could easily conclude they needed to run `paperfit run`, `paperfit runtime`, or `paperfit render` themselves
- `/paperfit` had drifted toward a portrait-only command instead of a unified entry
- host-specific assets were inconsistent about whether the user should speak naturally or operate the internal execution layer

That direction conflicts with the intended product shape: **agent-operated, vision-first, natural-language-first**.

## Product Model After Reset

### 1. User Layer

Users should be able to express requests like:

- `Use PaperFit to analyze this paper's layout`
- `Use PaperFit to repair the layout with minimal semantic change`
- `Use PaperFit to migrate this paper to CVPR`
- `Use PaperFit to reduce the paper to 8 pages`
- `Use PaperFit to inspect the visual layout only`

Slash commands remain valid in hosts that support them, but they are **shortcuts**, not the only supported mental model.

### 2. Agent Layer

The orchestrator is responsible for:

- intent routing
- project inspection
- state management
- visual inspection
- repair routing
- gatekeeper decisions
- user-facing progress and final summaries

### 3. Execution Layer

The following remain important, but they are internal:

- `paperfit runtime`
- `paperfit run`
- `paperfit render`
- bundled Python / shell scripts

These are execution primitives for the agent, plus tools for debugging, installation validation, and regression testing.

## Stable Task Types

The normalized PaperFit task model is:

- `analyze_layout`
- `full_vto`
- `visual_only`
- `repair_table`
- `adjust_length`
- `template_migration`
- `status_query`
- `undo_last_change`

This task model should stay consistent across hosts even if the host UI differs.

## Host Contract

### Claude Code

- `/paperfit` is the unified natural-language entry
- expert shortcuts such as `/fix-layout`, `/check-visual`, `/repair-table`, `/adjust-length`, `/migrate-template`, `/show-status`, `/paperfit-priority`, and `/paperfit-undo` remain available
- ordinary natural-language prompts should still map onto the same task types

### Codex

- there are no Claude-style slash commands
- the user should express intent directly in natural language
- `AGENTS.md` and installed skills carry the PaperFit contract

### Cursor

- project rules and installed skills should push the system toward the same natural-language-first behavior
- internal PaperFit commands remain execution details, not the primary UI

## Non-Negotiable Constraints

The reset does **not** weaken the core safety and quality boundaries:

- do not claim success without checking rendered page images
- visual results are the primary acceptance signal
- do not silently delete figures, tables, captions, labels, or key paper objects
- preserve academic meaning
- keep semantic edits controlled and auditable
- prefer width-aware table reconstruction over brute-force scaling

## Migration Notes

### What changed

- `README.md` now introduces PaperFit as a cross-host agent system
- `agents/orchestrator-agent.md` now treats natural-language intent as the primary input contract
- Claude command docs now explicitly support natural-language triggering and describe CLI as internal execution
- host assets for Codex and Cursor now align with the same product model
- installer and command tests now include regression checks for the new natural-language contract

### What did not change

- runtime architecture still exists
- scripts still exist
- state files and reports still exist
- expert commands still exist
- debugging through CLI remains supported

## Validation Status

Completed:

- documentation and host-asset smoke checks
- installer / doctor / command regression tests
- real-project runtime smoke on local paper projects

Known remaining gap:

- there is still no true end-to-end automated host conversation test that proves a live host session routes a natural-language PaperFit request exactly as intended

That means PaperFit now has a **documented and test-guarded entry contract**, but not yet a full UI-level host simulation test.

## Decision

Going forward, PaperFit should be described internally and externally as:

**A cross-host, natural-language, vision-in-the-loop academic typesetting agent system.**
