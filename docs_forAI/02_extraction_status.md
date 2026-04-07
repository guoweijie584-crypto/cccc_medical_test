# Extraction Status

## Purpose

This file records which source documents already have usable machine-readable text in `tmp/extracted_text/`, which ones are duplicated across formats, and which ones still need manual re-check.

## Current Status

### Successfully extracted and usable

- `archive/round1_history/3-22-Sr.pdf` -> `tmp/extracted_text/3-22-Sr.pdf.txt`
- `archive/round1_history/3-24-Sr.pdf` -> `tmp/extracted_text/3-24-Sr.pdf.txt`
- `archive/round1_history/3.26-Sr.pdf` -> `tmp/extracted_text/3.26-Sr.pdf.txt`
- `archive/round1_baseline/3.26-SR-14.11.pdf` -> `tmp/extracted_text/3.26-SR-14.11.pdf.txt`
- `archive/round1_history/3.26-Sr.pptx` -> `tmp/extracted_text/3.26-Sr.pptx.txt`
- `archive/round1_baseline/3.26-SR-14.11.pptx` -> `tmp/extracted_text/3.26-SR-14.11.pptx.txt`
- `archive/round1_candidates/3.27-SR-0.06.pptx` -> `tmp/extracted_text/3.27-SR-0.06.pptx.txt`
- `archive/round1_candidates/汇报0327.pptx` -> `tmp/extracted_text/汇报0327.pptx.txt`
- `archive/requirements_and_constraints/Multi Agent框架-0326.pdf` -> `tmp/extracted_text/Multi Agent框架-0326.pdf.txt`
- `archive/round1_baseline/流程架构.pptx` -> `tmp/extracted_text/流程架构.pptx.txt`
- `archive/reference_materials/一些框图源文件.pptx` -> `tmp/extracted_text/一些框图源文件.pptx.txt`
- `archive/reference_materials/面向智能客服的AI Agent 血糖管理自进化系统 - technology.pptx` -> `tmp/extracted_text/面向智能客服的AI Agent 血糖管理自进化系统 - technology.pptx.txt`
- `archive/reference_materials/面向智能客服的_AI_Agent_血糖管理自进化系统.pptx` -> `tmp/extracted_text/面向智能客服的_AI_Agent_血糖管理自进化系统.pptx.txt`

### Extraction failed or not yet usable

- `archive/requirements_and_constraints/3.九安医疗-课程选题信息.pdf` -> `tmp/extracted_text/3.九安医疗-课程选题信息.pdf.txt`
  - current content is only `EXTRACTION_ERROR: 'bbox'`
  - consequence: detailed claims attributed to the assignment/spec PDF should be treated as pending re-check

## Duplication Notes

- `archive/round1_history/3.26-Sr.pdf` and `archive/round1_history/3.26-Sr.pptx` are paired versions of the same deck
- `archive/round1_baseline/3.26-SR-14.11.pdf` and `archive/round1_baseline/3.26-SR-14.11.pptx` are paired versions of the same later deck
- `archive/round1_candidates/3.27-SR-0.06.pptx` and `archive/round1_candidates/汇报0327.pptx` are later same-line March 27 revisions of the `3.26-SR-14.11.*` deck family
- `archive/reference_materials/面向智能客服的_AI_Agent_血糖管理自进化系统.pptx` is a compact regenerated presentation variant; it overlaps topically with `archive/reference_materials/面向智能客服的AI Agent 血糖管理自进化系统 - technology.pptx`, but it is not the same file lineage
- for presentation reading order, the PDF version is closer to final slide flow; the PPTX version is better when individual text boxes matter
- the newly generated PPTX sidecars are slide-text oriented and good enough for archive comparison, but visual layout / animation differences still need manual deck review if final presentation use is in scope

## Recommended Working Order

1. Use `Multi Agent框架-0326.pdf.txt` for conservative status framing.
2. Use `3.26-SR-14.11.pdf.txt` and `3.26-SR-14.11.pptx.txt` for the mature report draft.
3. Use `流程架构.pptx.txt` for business flow, memory flow, and evaluation loop details.
4. Use `3.27-SR-0.06.pptx.txt` and `汇报0327.pptx.txt` only when checking whether later same-line variants should change archive identity.
5. Use `面向智能客服的_AI_Agent_血糖管理自进化系统.pptx.txt` and `面向智能客服的AI Agent 血糖管理自进化系统 - technology.pptx.txt` as showcase/reference material rather than baseline evidence.
6. Treat `archive/requirements_and_constraints/3.九安医疗-课程选题信息.pdf` as the highest-priority re-check target before making detailed claims about official requirements.
