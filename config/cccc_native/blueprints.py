"""Blueprint generation for the CCCC-native glucose-management groups."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List

import yaml


MEDICAL_MAIN_ACTORS = [
    ("primary", "主治医生", "Own the user-facing reply and coordinate all specialist input."),
    ("pharmacist", "药剂师", "Review medication choices, dose risks, interactions, and contraindications."),
    ("nutritionist", "营养师", "Provide meal planning and dietary structure guidance."),
    ("doctor", "代谢病医生", "Assess complications, escalation thresholds, and disease-management direction."),
    ("memory", "记忆管理", "Read/write Memory Palace and maintain medium/long-term patient memory."),
]

EVALUATION_ACTORS = [
    ("evaluator", "质检员", "Score answer quality and memory quality against the medical evaluation dimensions."),
    ("analyzer", "分析师", "Separate prompt defects from memory defects and locate the owning actor."),
    ("prompt_optimizer", "提示词优化师", "Produce minimal prompt diffs for medical actors and the memory actor."),
    ("memory_optimizer", "记忆优化师", "Propose or apply memory add/update/delete operations in Memory Palace."),
]

DOCS_ROOT = Path(__file__).resolve().parents[2] / "docs" / "cccc_native"


def _strip_front_matter(text: str) -> str:
    raw = str(text or "")
    if not raw.startswith("---"):
        return raw
    parts = raw.split("---", 2)
    if len(parts) < 3:
        return raw
    return parts[2].lstrip("\r\n")


def _role_note_block(actor_id: str, body: str) -> str:
    return f"## @actor: {actor_id}\n\n{body.strip()}\n"


def build_help_markdown_for_main_group() -> str:
    doc_path = DOCS_ROOT / "medical_group_guidance.md"
    if doc_path.exists():
        return _strip_front_matter(doc_path.read_text(encoding="utf-8"))
    parts = [
        "# Medical Team Help",
        "",
        "This group is the user-facing glucose-management consultation team.",
        "",
        "## @role: foreman",
        "",
        "- `primary` is the only normal user-facing output.",
        "- Pull specialist input before answering when medication, diet, complication, or memory context matters.",
        "- Keep the final reply concise, structured, and clinically safe.",
        "",
        "## @role: peer",
        "",
        "- Peers should answer the foreman, not the user, unless explicitly requested.",
        "- Keep specialist replies focused on your own domain.",
        "- Escalate uncertainty instead of bluffing.",
        "",
    ]

    actor_blocks = {
        "primary": (
            "You are the primary physician actor. "
            "Act as the single user-facing medical coordinator. "
            "If the thread has a unique patient_id or medical_context.patient_id, your first tool call must be cccc_message_send(..., to='memory', ...) and it must explicitly include that patient_id. "
            "For a bound probe, you must not use session-local cccc_memory(...) or any other local tool as a substitute for the live memory actor path. "
            "Before a real memory->primary live-ledger chat.message reply exists, you must not call cccc_message_reply(...) to the user, must not send specialist consults, and must not skip memory. "
            "After real memory and specialist live-ledger replies exist, you may call cccc_message_reply(...) with one final answer for the user. "
            "If the thread does not have a unique patient_id, you may only use cccc_message_reply(...) to ask the user to clarify binding and must not pretend you know the patient profile. "
            "You must not spawn, invent, or simulate local sub-workers or surrogate specialists inside the primary session to replace live actor replies. "
            "Only actual live-ledger chat.message replies from memory, pharmacist, nutritionist, and doctor count as received specialist input. "
            "Before a real memory->primary live-ledger chat.message reply appears for the current round, you must not send any specialist consults to pharmacist, nutritionist, or doctor. "
            "If memory or any other live actor does not reply, you may wait, retry, or tell the user the full consult could not be completed, but you must not fill the gap with local worker output or keep advancing the chain. "
            "Memory and specialists may reply only to primary and must not reply directly to the user. "
            "Do not let the consultation degrade into five visible parallel replies."
        ),
        "pharmacist": (
            "You are the pharmacist actor. "
            "Respond only on medication selection, dosing, interactions, renal safety, hypoglycemia risk, "
            "and drug-use precautions. "
            "Default audience is `@foreman`."
        ),
        "nutritionist": (
            "You are the nutritionist actor. "
            "Respond only on meal structure, carbohydrate load, GI/GL, weight-management diet, "
            "and practical patient-friendly diet adjustments. "
            "Default audience is `@foreman`."
        ),
        "doctor": (
            "You are the metabolism/complication actor. "
            "Respond on complication assessment, tests, emergency risk, escalation, and disease-management direction. "
            "Default audience is `@foreman`."
        ),
        "memory": (
            "You are the memory actor. "
            "Use CCCC ledger as short-term memory and Memory Palace as medium/long-term memory. "
            "Your job is to retrieve patient profile/trend memory before consultations and write back stable facts after consultations. "
            "Update hot summaries in agent state to reduce repeated Memory Palace latency."
        ),
    }

    for actor_id, _, _ in MEDICAL_MAIN_ACTORS:
        parts.append(_role_note_block(actor_id, actor_blocks[actor_id]).rstrip())
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def build_help_markdown_for_evaluation_group() -> str:
    doc_path = DOCS_ROOT / "evaluation_group_guidance.md"
    if doc_path.exists():
        return _strip_front_matter(doc_path.read_text(encoding="utf-8"))
    parts = [
        "# Evaluation Team Help",
        "",
        "This group is a backstage optimization/evaluation team for the glucose-management actors.",
        "",
        "## @role: foreman",
        "",
        "- The evaluator group does not speak to end users in normal operation.",
        "- It inspects transcripts, scores outputs, and proposes prompt/memory changes.",
        "",
        "## @role: peer",
        "",
        "- Stay within your evaluation/optimization lane.",
        "- Produce structured artifacts, not vague observations.",
        "",
    ]

    actor_blocks = {
        "evaluator": (
            "You are the evaluator actor. "
            "Score answers and memory quality using the project evaluation dimensions. "
            "Prefer structured outputs that can feed dashboards and optimization logs."
        ),
        "analyzer": (
            "You are the analyzer actor. "
            "Determine whether failures come from prompt design, memory content, memory extraction, or workflow boundaries."
        ),
        "prompt_optimizer": (
            "You are the prompt optimizer actor. "
            "Generate minimal, reversible prompt diffs for primary/pharmacist/nutritionist/doctor/memory."
        ),
        "memory_optimizer": (
            "You are the memory optimizer actor. "
            "Propose or apply add/update/delete operations to Memory Palace while preserving clinically important history."
        ),
    }

    for actor_id, _, _ in EVALUATION_ACTORS:
        parts.append(_role_note_block(actor_id, actor_blocks[actor_id]).rstrip())
        parts.append("")
    return "\n".join(parts).strip() + "\n"


def build_main_group_template(runtime: str = "codex") -> str:
    template = {
        "kind": "cccc.group_template",
        "v": 1,
        "title": "glucose-management-main",
        "topic": "User-facing glucose-management medical team",
        "actors": [
            {
                "id": actor_id,
                "title": title,
                "runtime": runtime,
                "runner": "pty",
                "submit": "enter",
                "enabled": True,
                "capability_autoload": [],
            }
            for actor_id, title, _ in MEDICAL_MAIN_ACTORS
        ],
        "settings": {
            "default_send_to": "foreman",
            "desktop_pet_enabled": False,
            "terminal_transcript_visibility": "foreman",
        },
        "prompts": {
            "preamble": (
                "Medical main group:\n"
                "- User-facing consultations go through `primary`.\n"
                "- Specialists collaborate internally.\n"
                "- Short-term memory lives in the ledger; medium/long-term memory lives in Memory Palace.\n"
            ),
            "help": build_help_markdown_for_main_group(),
        },
        "automation": {"rules": [], "snippets": {}},
    }
    return yaml.safe_dump(template, allow_unicode=True, sort_keys=False)


def build_evaluation_group_template(runtime: str = "codex") -> str:
    template = {
        "kind": "cccc.group_template",
        "v": 1,
        "title": "glucose-management-eval",
        "topic": "Backstage evaluation and optimization team",
        "actors": [
            {
                "id": actor_id,
                "title": title,
                "runtime": runtime,
                "runner": "pty",
                "submit": "enter",
                "enabled": True,
                "capability_autoload": [],
            }
            for actor_id, title, _ in EVALUATION_ACTORS
        ],
        "settings": {
            "default_send_to": "foreman",
            "desktop_pet_enabled": False,
            "terminal_transcript_visibility": "foreman",
        },
        "prompts": {
            "preamble": (
                "Evaluation group:\n"
                "- Do not act as a user-facing consultation team.\n"
                "- Consume transcripts and memory state from the medical team.\n"
                "- Produce evaluation, analysis, and optimization artifacts.\n"
            ),
            "help": build_help_markdown_for_evaluation_group(),
        },
        "automation": {"rules": [], "snippets": {}},
    }
    return yaml.safe_dump(template, allow_unicode=True, sort_keys=False)
