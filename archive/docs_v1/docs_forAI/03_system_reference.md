# System Reference

## Purpose

This file is the AI-oriented system reference for the project.

It is designed to be:

- more structured than `00_project_context.md`
- more implementation-aware than the original slide summaries
- more cautious than the user-provided AI draft when evidence is incomplete

## Evidence Legend

- `code-backed`: confirmed in the provided source repository
- `doc-backed`: clearly present in slides / diagrams / strategy memo
- `design-level`: appears as a current design choice, but should not be treated as fully verified implementation
- `pending re-check`: tied to the assignment/spec PDF or another source that still lacks clean machine-readable verification

## 1. Core Architecture Overview

The project is best understood as a multi-agent blood-glucose-management system for an intelligent customer-service setting.

Stable high-level themes:

- multi-agent collaboration
- three-layer memory management
- evaluation-driven self-evolution
- dual optimization focus: prompt + memory

Current best state summary:

`The system has moved beyond pure concept slides into prototype/integration territory, but it should still not be described as a fully verified end-to-end autonomous closed loop.`

## 2. Agent Map

### Business roles

| Agent | Status | Notes |
| --- | --- | --- |
| `Primary / Foreman` | `code-backed` + `doc-backed` | Final synthesis role and patient-facing output owner in the current workflow. |
| `Pharmacist` | `code-backed` + `doc-backed` | Medication-focused specialist. |
| `Nutritionist` | `code-backed` + `doc-backed` | Diet-focused specialist. |
| `Doctor` | `code-backed` + `doc-backed` | Metabolic / complication reasoning specialist. |
| `Memory Agent` | `code-backed` + `doc-backed` | Context governance, memory read/write, profile updates. |

### Extension roles

| Agent | Status | Notes |
| --- | --- | --- |
| `Educator / 科普老师` | `doc-backed` | Stable slide-level extension role; not present as a first-class runtime specialist in the current source repo. |
| `Counselor / 心理咨询师` | `doc-backed` | Stable slide-level extension role; not present as a first-class runtime specialist in the current source repo. |

### Evolution roles

| Agent | Status | Notes |
| --- | --- | --- |
| `Evaluator` | `code-backed` + `doc-backed` | Scores response quality and memory quality. |
| `Analyzer` | `code-backed` + `doc-backed` | Performs root-cause classification. |
| `Prompt Optimizer` | `code-backed` + `doc-backed` | Produces prompt diffs / prompt updates. |
| `Memory Optimizer` | `code-backed` + `doc-backed` | Produces memory add/update/delete operations. |

## 3. Role Boundaries

These boundaries are the safest synthesis of docs + code:

1. `Primary` is the final patient-facing output owner.
   - `code-backed`: the workflow collects expert outputs and then generates one `primary_response`.

2. Expert agents are advisory, not direct user-facing output channels.
   - `code-backed` in the current workflow implementation.

3. `Memory Agent` is responsible for context governance and memory IO, not business decisions.
   - `code-backed` in structure and usage.

4. Evolution agents operate on evaluation / analysis / optimization, not user dialogue output.
   - `code-backed` and also reinforced by routing config.

5. Extension roles such as `Educator` and `Counselor` should currently be treated as document-level roles unless new runtime code appears.

## 4. Memory Architecture

### Stable structure

The memory system is consistently modeled as three tiers:

- short-term memory
- medium-term memory
- long-term memory

This is:

- `doc-backed` across slides and diagrams
- `code-backed` conceptually in `MemoryAgent.retrieve_patient_context`, which returns `short_term`, `mid_term`, and `long_term`

### More specific design details

The following details appear in diagrams / slides and should be treated as `design-level`, not as fully implementation-verified facts:

- short-term TTL: `1 hour`
- medium-term TTL: `30 hours`
- long-term retention: persistent / long-lived
- storage idea: `SQLite + sqlite-vec`

These are useful as architecture hints for future AI work, but not as proof that the current runtime already enforces those exact policies.

### Current memory responsibilities in code

The provided source repo confirms that the memory module already supports:

- patient context retrieval
- agent-context construction
- fact extraction from interaction
- memory storage / write-back
- patient profile update
- memory search

## 5. Business Workflow

The standard consultation path can be summarized as:

1. receive user query
2. read patient context via `Memory Agent`
3. run expert analysis in parallel
4. synthesize specialist outputs into one final response
5. return patient-facing answer
6. extract key facts from the interaction
7. write memory and optionally trigger evaluation later

Status:

- `code-backed` as workflow structure
- `doc-backed` as the intended state-machine explanation

Important implementation note:

- the current workflow implementation is the strongest evidence that `Primary` depends on `Memory Agent` for context, rather than querying storage directly

## 6. Self-Evolution Dual-Loop

### Stable pipeline

The following pipeline is strongly supported:

1. evaluate response + memory quality
2. analyze root cause
3. route to prompt or memory optimization
4. re-run / re-evaluate

Status:

- `code-backed` for the main loop structure
- `doc-backed` for how the loop should be presented conceptually

### Trigger conditions

The following trigger logic is present in design/config materials:

- every `5` dialogue rounds
- or when score `< 35/50`

Status:

- `doc-backed` in `archive/round1_baseline/流程架构.pptx`
- `code/config-backed` in `config/evaluation_trigger.json` and routing config

### Root-cause classes

The current best synthesis is:

- `Prompt_Issue`
- `Memory_Issue`
- `Coordination_Issue` / workflow issue

These are:

- `doc-backed`
- `code-backed` in analyzer/problem typing and routing behavior

## 7. Current Implementation State

### Strongly supported as already present

- multi-agent workflow code exists
- memory-management code exists
- evaluator / analyzer / optimizer modules exist
- self-evolution loop code exists
- local API layer exists
- integration/demo test scaffolding exists

### Present but not fully validated

- fully reliable patient-data-backed demo flow
- fully stable memory-write / memory-quality pipeline
- fully verified end-to-end self-evolution improvement loop
- final production-grade runtime behavior

### Known concrete caveats from repo inspection

1. The checkout is better described as a local integration / prototype repo than as a finished production system.
2. The structured patient-data directory is missing in the current checkout, which causes some demo-alignment tests to fail.
3. Some acceptance/integration tests are still TODO/mock-oriented.
4. Some phase-1 memory tests currently mismatch the implementation data shape.

## 8. Guidance For Future AI Agents

When generating future logic, docs, or code against this project:

1. Treat `Primary` as the only patient-facing final response owner.
2. Treat `Memory Agent` as the gateway for context retrieval and memory updates.
3. Treat expert agents as specialist contributors, not direct user channels.
4. Treat `Evaluator -> Analyzer -> Optimizer` as the intended optimization backbone.
5. Treat TTL / sqlite-vec / trigger thresholds as current design anchors, not automatically as production-verified runtime guarantees.
6. Treat extension roles (`Educator`, `Counselor`) as valid architectural concepts, but not yet code-backed runtime roles unless new source files appear.

## 9. Best Current One-Line Summary

`This is a multi-agent blood-glucose-management prototype that already has workflow, memory, evaluation, and optimization code skeletons, while still relying on document-level design choices for some memory-policy and closed-loop details.`
