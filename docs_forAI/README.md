# docs_forAI Guide

## Purpose

This directory is the AI-facing context layer for the project.

It is meant to answer three different needs:

1. fast project orientation
2. source-priority and evidence-boundary checking
3. implementation-aware architectural reference

## Read This First

If an AI agent is dropped into this workspace and needs the shortest reliable entry path, read in this order:

1. `03_system_reference.md`
2. `00_project_context.md`
3. `01_source_index.md`
4. `02_extraction_status.md`
5. `../docs_shared/证据边界与事实口径.md`

## What Each File Is For

### `03_system_reference.md`

Best first file for most future AI agents.

Use it when the task is:

- understand the system architecture quickly
- distinguish code-backed facts from doc-backed design
- reason about roles, memory, workflow, and self-evolution

This is the most structured and implementation-aware AI summary currently available.

### `00_project_context.md`

Use it when the task is:

- understand the folder as a whole
- understand the project framing
- understand the overall current-state vs future-state narrative

This file is broader and more narrative than `03_system_reference.md`.

### `01_source_index.md`

Use it when the task is:

- decide which original file to trust for a specific question
- understand which deck is exploratory versus mature
- map a claim back to likely source material

### `02_extraction_status.md`

Use it when the task is:

- check whether a claim is grounded in machine-readable text
- understand duplication across PDF/PPTX pairs
- avoid over-trusting files whose extraction failed

### `../docs_shared/证据边界与事实口径.md`

Use it when the task is:

- align AI-side wording with the human-side wording
- understand what should be called code-backed, doc-backed, design-level, or pending re-check
- avoid evidence-boundary drift across directories

## Recommended Usage Patterns

### For architecture or implementation questions

Read:

1. `03_system_reference.md`
2. source repo under `tmp/source_repo/cccc_medical_test`

### For presentation-status or wording questions

Read:

1. `00_project_context.md`
2. `01_source_index.md`
3. `archive/requirements_and_constraints/Multi Agent框架-0326.pdf` and `3.26-SR-14.11.*`

### For requirement-level questions

Read:

1. `01_source_index.md`
2. `02_extraction_status.md`
3. then re-check `archive/requirements_and_constraints/3.九安医疗-课程选题信息.pdf` directly if detailed claims matter

## Important Boundary

Do not treat all details in this directory as equally verified.

Current best rule:

- use `code-backed` facts when speaking about implementation
- use `doc-backed` facts when speaking about architecture and presentation
- use `design-level` details as current design intent, not guaranteed runtime truth
- use `pending re-check` details cautiously until the assignment/spec PDF is re-verified

## One-Line Summary

`If you only read one file, read 03_system_reference.md; if you need to justify a claim, then check 01_source_index.md and 02_extraction_status.md.`
