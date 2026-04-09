# Root Archive Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Move root-level historical first-report files into explicit archive folders without breaking the current human/AI entry docs.

**Architecture:** Migrate in small batches. For each batch, first update every affected document path, then move the files, then run a targeted reference check. This keeps the repository navigable at every checkpoint.

**Tech Stack:** Markdown docs, shell file operations, ripgrep verification

---

### Task 1: Batch 1 path rewrites

**Files:**
- Create: `docs/superpowers/plans/2026-03-30-root-archive-migration.md`
- Modify: `docs_forAI/00_project_context.md`
- Modify: `docs_forAI/01_source_index.md`
- Modify: `docs_forAI/02_extraction_status.md`
- Modify: `docs_forHuman/根目录资料落位说明.md`
- Modify: `docs_forHuman/资料分类与阅读顺序.md`
- Modify: `docs_forHuman/项目梳理与理解.md`

- [ ] Step 1: Rewrite all batch-1 references to `archive/round1_history/`
- [ ] Step 2: Keep sidecar paths unchanged in `tmp/extracted_text/`
- [ ] Step 3: Note in human-facing docs that batch 1 is now archived, not root-level

### Task 2: Batch 1 file moves

**Files:**
- Move: `3-22-Sr.pdf` -> `archive/round1_history/3-22-Sr.pdf`
- Move: `3-24-Sr.pdf` -> `archive/round1_history/3-24-Sr.pdf`
- Move: `3.26-Sr.pdf` -> `archive/round1_history/3.26-Sr.pdf`
- Move: `3.26-Sr.pptx` -> `archive/round1_history/3.26-Sr.pptx`

- [ ] Step 1: Move the four files into `archive/round1_history/`
- [ ] Step 2: Confirm the archive directory contains all four files

### Task 3: Batch 1 verification

**Files:**
- Verify: `docs_forAI/00_project_context.md`
- Verify: `docs_forAI/01_source_index.md`
- Verify: `docs_forAI/02_extraction_status.md`
- Verify: `docs_forHuman/根目录资料落位说明.md`
- Verify: `docs_forHuman/资料分类与阅读顺序.md`
- Verify: `docs_forHuman/项目梳理与理解.md`

- [ ] Step 1: Run targeted `rg` for the old root-level batch-1 paths
- [ ] Step 2: Confirm no stale references remain in tracked docs
- [ ] Step 3: Report batch-1 completion before touching batch 2
