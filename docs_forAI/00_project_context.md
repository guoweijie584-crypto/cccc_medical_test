# Project Context

## What This Directory Contains

This directory started as a document set for a course/research project. It is still document-first, but there is now an implementation repository available under:

- `tmp/source_repo/cccc_medical_test`

Observed source files:

- `archive/requirements_and_constraints/3.九安医疗-课程选题信息.pdf`
- `archive/requirements_and_constraints/Multi Agent框架-0326.pdf`
- `archive/round1_history/3-22-Sr.pdf`
- `archive/round1_history/3-24-Sr.pdf`
- `archive/round1_history/3.26-Sr.pdf`
- `archive/round1_baseline/3.26-SR-14.11.pdf`
- `archive/round1_history/3.26-Sr.pptx`
- `archive/round1_baseline/3.26-SR-14.11.pptx`
- `archive/round1_baseline/流程架构.pptx`
- `archive/reference_materials/一些框图源文件.pptx`
- `archive/reference_materials/面向智能客服的AI Agent 血糖管理自进化系统 - technology.pptx`

## Best Current Understanding

Project name:

`面向智能客服的AI Agent 血糖管理自进化系统`

Most likely project definition:

A multi-agent blood glucose management system for an intelligent customer-service setting. The core research/implementation theme is:

- multi-agent collaboration for diabetes support
- three-layer memory management
- self-evolution through prompt optimization plus memory optimization

This interpretation is strongly supported by the later slides and the strategy memo. The assignment/spec PDF is still the highest-priority source to re-check, but its saved text extraction currently failed and has not yet been re-verified line by line.

## Stable Core Design Across Files

These ideas appear consistently across the document set:

1. Scenario choice
   The team chose blood glucose management because it naturally requires long-term context, role collaboration, and historical information retrieval.

2. Multi-agent medical roles
   Repeated roles include:
   - primary/foreman/主治医生
   - pharmacist/药剂师
   - nutritionist/营养师
   - metabolic doctor/代谢病医生
   - science educator/科普老师
   - counselor/心理咨询师
   - memory agent/记忆管理

3. Memory as the main innovation line
   The strongest recurring design theme is `三层记忆管理`:
   - short-term memory
   - mid-term memory
   - long-term memory

4. Self-evolution as the second main line
   Repeated loop:
   - evaluate
   - analyze root cause
   - optimize prompt and/or memory
   - re-evaluate

5. CCCC-style orchestration language
   Several files use runtime terms such as:
   - Foreman
   - Actor
   - Ledger
   - Inbox
   - Automation
   - MCP tools
   - Daemon / Control Plane

## Strongest Source of Truth

If future work needs a primary source order, use this priority:

1. `archive/requirements_and_constraints/3.九安医疗-课程选题信息.pdf`
   Formal assignment/specification. Best source to re-check goals, stages, deliverables, and evaluation criteria once a clean extraction is available.

2. `archive/round1_baseline/3.26-SR-14.11.pptx` and `archive/round1_baseline/3.26-SR-14.11.pdf`
   Most mature presentation draft. Best source for current public-facing architecture, roles, governance, and automation examples.

3. `archive/round1_baseline/流程架构.pptx`
   Best source for clean business flow, memory flow, and self-evolution loop diagrams.

4. `archive/requirements_and_constraints/Multi Agent框架-0326.pdf`
   Best source for presentation strategy and boundary-setting about what is or is not already implemented.

5. `tmp/source_repo/cccc_medical_test`
   Best source for checking what has code-level prototype evidence versus what still exists only as architecture/design language.

## Current State vs Future State

Evidence-backed current state:

- the team has defined a multi-agent architecture
- role decomposition is relatively clear
- three-layer memory has been defined conceptually
- self-evolution has been defined as a framework/roadmap
- report materials were iterated multiple times in late March 2026
- a source repo now confirms workflow, memory, evaluator/analyzer/optimizer, and local API prototype code

Evidence-backed not-fully-done areas:

- memory integration is not fully implemented yet
- the exact memory write/update/forgetting mechanism is still evolving
- evaluator/analyzer/optimizer details are not finalized
- some decks are more visionary than the verified current progress

Important narrative constraint:

`archive/requirements_and_constraints/Multi Agent框架-0326.pdf` explicitly argues that the team should not present unimplemented parts as already complete.

## Potential Internal Tension

Likely tension across files:

- `technology.pptx` contains stronger achievement language such as "successfully built" and expansive business/future-roadmap claims
- the strategy memo says the first-stage report should present the project as "architecture formed, key modules still in progress"

Recommendation for future AI use:

Treat the realistic project state as:

`architecture and direction are formed; memory mechanism and self-evolution mechanism are the next major implementation focus`

Do not assume the full system is already running end-to-end unless new evidence appears.

For a more structured AI-readable reference that merges document evidence with code evidence, use:

- `docs_forAI/03_system_reference.md`

## Likely Timeline

Based on filenames and slide content:

- `archive/round1_history/3-22-Sr.pdf`: early concept exploration
- `archive/round1_history/3-24-Sr.pdf`: report structure draft
- `archive/round1_history/3.26-Sr.*`: initial polished report draft
- `3.26-SR-14.11.*`: later and more complete March 26 revision
- report date shown in slides: March 27, 2026

## Assignment-Level Definition

The assignment/spec PDF is likely the file that defines the official target system. Based on earlier summaries plus repeated later-slide themes, the likely emphasis includes:

- blood glucose management as the chosen scenario
- multi-agent role collaboration
- prompt-oriented self-evolution
- memory-oriented self-evolution

Specific deliverables, evaluation criteria, and any demo requirement should be treated as pending direct re-check against the PDF itself.

## Open Questions

These are not answered reliably by the current directory alone:

- whether OpenClaw or CCCC is the final execution framework
- what has truly been implemented versus mocked in demo form
- who owns which submodule in the team
- whether the latest "official" deck is the `3.26-SR-14.11` version or a later file stored elsewhere

## Working DoD For This Folder

For future AI agents reading this directory, a reasonable document-level definition of done is:

- understand the project as a multi-agent blood glucose management course project
- anchor goals to the assignment/spec PDF after it is re-checked directly
- anchor presentation status to the `3.26-SR-14.11` materials
- treat memory management as the main innovation line
- treat self-evolution as an intended closed-loop roadmap that may not yet be fully implemented
