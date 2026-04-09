# Source Index

## Purpose

This file maps each document in the folder to its likely role, maturity, and trust level.

Trust levels used here:

- `high`: explicit requirements or repeated stable facts
- `medium`: likely current design, but presentation-oriented
- `low`: exploratory, inspirational, or clearly aspirational

## File Map

### `archive/requirements_and_constraints/3.九安医疗-课程选题信息.pdf`

- Type: formal task/specification
- Trust: `high` as source priority, `pending re-check` for detailed claims
- Role:
  likely defines the course topic, target architecture, implementation stages, deliverables, and evaluation criteria, but the saved extraction for this file failed
- Key points:
  - later materials strongly suggest the target is a blood glucose management multi-agent system
  - later materials strongly suggest prompt optimization and memory optimization are part of the intended roadmap
  - detailed role lists, stage plans, and grading criteria should be re-checked directly against the PDF

### `archive/requirements_and_constraints/Multi Agent框架-0326.pdf`

- Type: presentation strategy memo / AI prompt for deck generation
- Trust: `high` for presentation boundary, `medium` for implementation status
- Role:
  tells the team how to present the first-stage report without overstating progress
- Key points:
  - emphasize why the topic is valid
  - explain what is already designed
  - frame memory integration and self-evolution completion as next-step work
  - explicitly warns against pretending all modules are already implemented

### `archive/round1_history/3-22-Sr.pdf`

- Type: early concept research / internal brainstorming
- Trust: `low` to `medium`
- Role:
  captures inspiration around memory, forgetting, reconstruction, and self-evolution
- Key points:
  - memory-butler / glial-cell analogy
  - memory palace and human-brain analogies
  - evaluator-based iteration
  - rough role weighting ideas

### `archive/round1_history/3-24-Sr.pdf`

- Type: mid-stage report outline
- Trust: `medium`
- Role:
  early class-report skeleton
- Key points:
  - project title and team placeholders
  - architecture slide
  - authority/governance slide
  - innovation and progress slide

### `archive/round1_history/3.26-Sr.pdf`

- Type: polished short report deck
- Trust: `medium`
- Role:
  condensed presentation draft
- Key points:
  - project motivation
  - architecture overview
  - progress summary

### `archive/round1_baseline/3.26-SR-14.11.pdf`

- Type: later report deck
- Trust: `medium` to `high`
- Role:
  more complete presentation draft, likely close to the active report version
- Key points:
  - governance model with `Foreman`
  - expert role boundaries
  - automation rules with concrete triggers

### `archive/round1_history/3.26-Sr.pptx`

- Type: editable slide source for the short March 26 deck
- Trust: broadly aligned with `archive/round1_history/3.26-Sr.pdf`, but not assumed identical slide for slide
- Role:
  editable source for presentation revision

### `archive/round1_baseline/3.26-SR-14.11.pptx`

- Type: editable slide source for the later March 26 deck
- Trust: broadly aligned with `archive/round1_baseline/3.26-SR-14.11.pdf`, but not assumed identical slide for slide
- Role:
  best editable representation of the mature report draft

### `archive/round1_candidates/3.27-SR-0.06.pptx`

- Type: later same-line editable deck
- Trust: `medium`
- Role:
  expanded working variant of the `3.26-SR-14.11.*` main-deck line
- Key points:
  - keeps the same title, project intro, architecture backbone, role-governance frame, and self-evolution storyline
  - adds dedicated slides for memory architecture, business flow, evaluation loop, and optimizer routing
  - extracted sidecar now exists at `tmp/extracted_text/3.27-SR-0.06.pptx.txt`
- Caution:
  still contains unfinished section-divider placeholders after `THANKS`, so it should stay in the candidate pool rather than replacing the March 26 baseline automatically

### `archive/round1_candidates/汇报0327.pptx`

- Type: same-line editable classroom-report variant
- Trust: `medium`
- Role:
  working draft that reorganizes the mainline into `项目介绍 / 模块详情 / 进度介绍 / 团队介绍`
- Key points:
  - reuses the same core architecture, governance, memory, and self-evolution narrative as `3.26-SR-14.11.*`
  - adds named team members and a team-introduction page
  - extracted sidecar now exists at `tmp/extracted_text/汇报0327.pptx.txt`
- Caution:
  this is a presentation-organization variant, not a new evidence source; its wording and labels differ slightly from the baseline and should not by themselves change canonical status claims

### `archive/reference_materials/面向智能客服的_AI_Agent_血糖管理自进化系统.pptx`

- Type: concise generated stage-report deck
- Trust: `medium` for structure, `low` to `medium` for canonical status
- Role:
  compact re-authored showcase/summary deck rather than the main editable deck line
- Key points:
  - compresses the story into 9 slides: background, roles, flow, memory/self-evolution, progress, and team
  - metadata shows `PptxGenJS`, which suggests a regenerated presentation rather than a direct incremental save of the March 26 baseline file
  - extracted sidecar now exists at `tmp/extracted_text/面向智能客服的_AI_Agent_血糖管理自进化系统.pptx.txt`
- Caution:
  useful as a condensed presentation variant, but not enough evidence to replace `3.26-SR-14.11.*` as the canonical main deck

### `archive/round1_baseline/流程架构.pptx`

- Type: architecture/process diagrams
- Trust: `high` for conceptual flow
- Role:
  best file for understanding runtime process design
- Key points:
  - user -> primary -> memory -> experts -> synthesis -> memory writeback
  - memory palace + sqlite/sqlite-vec idea
  - evaluation-driven optimization loop
  - trigger example: every 5 rounds or score below 35/50

### `archive/reference_materials/一些框图源文件.pptx`

- Type: rough source diagrams
- Trust: `low` to `medium`
- Role:
  raw diagram source material that likely fed later polished decks

### `archive/reference_materials/面向智能客服的AI Agent 血糖管理自进化系统 - technology.pptx`

- Type: polished technology/value narrative deck
- Trust: `medium` for vision, `low` for exact implementation status
- Role:
  showcase-oriented deck with broader technical and business framing
- Key points:
  - layered architecture
  - knowledge graph / RAG / personalization / monitoring
  - business models and future roadmap
- Caution:
  some claims appear more ambitious than the conservative status framing in `archive/requirements_and_constraints/Multi Agent框架-0326.pdf`

## Best Reading Order For Future AI

1. `archive/requirements_and_constraints/3.九安医疗-课程选题信息.pdf`
2. `archive/requirements_and_constraints/Multi Agent框架-0326.pdf`
3. `archive/round1_baseline/3.26-SR-14.11.pptx`
4. `archive/round1_baseline/流程架构.pptx`
5. `archive/round1_candidates/3.27-SR-0.06.pptx` and `archive/round1_candidates/汇报0327.pptx` only when checking later same-line variants
6. remaining drafts and showcase decks as historical/supporting context

Note: item 1 is still the conceptual top priority, but it currently has an extraction gap. Until that is fixed, items 2-4 are the most directly usable machine-readable sources in this folder.
