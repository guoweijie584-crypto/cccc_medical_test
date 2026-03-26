"""Runtime ledger gate helpers for bound-round verification."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

SPECIALISTS = ("pharmacist", "nutritionist", "doctor")
SPECIALIST_SET = set(SPECIALISTS)

_PATIENT_BINDING_RE = re.compile(r"\[PATIENT_BINDING\s+patient_id=([^\s\]]+)")


@dataclass(frozen=True)
class EventRef:
    line: int
    event_id: str
    ts: str
    kind: str
    by: str
    to: List[str] = field(default_factory=list)
    reply_to: str = ""


@dataclass
class RoundGateVerdict:
    probe_event_id: str
    probe_line: int
    patient_id: str
    round_verdict: str
    active_probe_status: str
    pending_reason: str = ""
    pending_evidence: Dict[str, Any] = field(default_factory=dict)
    failure_reasons: List[str] = field(default_factory=list)
    probe_event: Optional[EventRef] = None
    memory_consults: List[EventRef] = field(default_factory=list)
    memory_replies: List[EventRef] = field(default_factory=list)
    specialist_consults: List[EventRef] = field(default_factory=list)
    specialist_replies: Dict[str, List[EventRef]] = field(default_factory=dict)
    primary_user_messages: List[EventRef] = field(default_factory=list)
    memory_pending_notifications: List[EventRef] = field(default_factory=list)
    superseding_event: Optional[EventRef] = None

    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data["specialist_replies"] = {
            actor: [asdict(item) for item in refs]
            for actor, refs in self.specialist_replies.items()
        }
        return data


@dataclass(frozen=True)
class _LedgerEvent:
    line: int
    payload: Dict[str, Any]


def load_ledger_events(ledger_path: str | Path) -> List[_LedgerEvent]:
    path = Path(ledger_path)
    events: List[_LedgerEvent] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = raw.strip()
        if not text:
            continue
        payload = json.loads(text)
        if isinstance(payload, dict):
            events.append(_LedgerEvent(line=line_no, payload=payload))
    return events


def find_latest_bound_user_round_id(ledger_path: str | Path) -> str:
    latest = ""
    for item in load_ledger_events(ledger_path):
        payload = item.payload
        if str(payload.get("kind") or "") != "chat.message":
            continue
        if str(payload.get("by") or "").strip() != "user":
            continue
        if _extract_bound_patient_id(payload):
            latest = str(payload.get("id") or "").strip()
    return latest


def classify_probe_round_from_ledger(ledger_path: str | Path, probe_event_id: str) -> RoundGateVerdict:
    return classify_probe_round(load_ledger_events(ledger_path), probe_event_id)


def classify_probe_round(events: Iterable[_LedgerEvent], probe_event_id: str) -> RoundGateVerdict:
    probe_id = str(probe_event_id or "").strip()
    if not probe_id:
        raise ValueError("probe_event_id is required")

    event_list = list(events)
    probe_index = -1
    for index, item in enumerate(event_list):
        if str(item.payload.get("id") or "").strip() == probe_id:
            probe_index = index
            break
    if probe_index < 0:
        raise ValueError(f"probe event not found: {probe_id}")

    probe_payload = event_list[probe_index].payload
    verdict = RoundGateVerdict(
        probe_event_id=probe_id,
        probe_line=event_list[probe_index].line,
        patient_id=_extract_bound_patient_id(probe_payload),
        round_verdict="pending",
        active_probe_status="active",
        specialist_replies={actor: [] for actor in SPECIALISTS},
        probe_event=_event_ref(event_list[probe_index]),
    )

    memory_consult_ids: set[str] = set()
    specialist_consult_ids: Dict[str, set[str]] = {actor: set() for actor in SPECIALISTS}
    first_memory_reply_line: Optional[int] = None

    for item in event_list[probe_index + 1 :]:
        payload = item.payload
        kind = str(payload.get("kind") or "").strip()
        by = str(payload.get("by") or "").strip()
        data = payload.get("data") if isinstance(payload.get("data"), dict) else {}

        if kind == "chat.message" and by == "user":
            verdict.superseding_event = _event_ref(item)
            break
        if kind == "actor.restart":
            verdict.superseding_event = _event_ref(item)
            break

        if kind == "system.notify" and str(data.get("target_actor_id") or "").strip() == "memory":
            message = str(data.get("message") or "")
            if any(event_id and event_id in message for event_id in memory_consult_ids):
                verdict.memory_pending_notifications.append(_event_ref(item))
            continue

        if kind != "chat.message":
            continue

        to_tokens = _normalize_to_tokens(data)
        event_ref = _event_ref(item)
        event_id = event_ref.event_id
        reply_to = event_ref.reply_to

        if by == "primary":
            if "memory" in to_tokens:
                if event_id:
                    memory_consult_ids.add(event_id)
                    verdict.memory_consults.append(event_ref)
                continue

            specialist_targets = sorted(SPECIALIST_SET.intersection(to_tokens))
            if specialist_targets:
                verdict.specialist_consults.append(event_ref)
                for actor in specialist_targets:
                    if event_id:
                        specialist_consult_ids[actor].add(event_id)
                if first_memory_reply_line is None:
                    _append_failure(verdict, "primary_specialist_fan_out_before_memory_reply")
                continue

            if "user" in to_tokens:
                verdict.primary_user_messages.append(event_ref)
                if not memory_consult_ids:
                    _append_failure(verdict, "primary_user_without_memory_consult")
                elif first_memory_reply_line is None:
                    _append_failure(verdict, "primary_user_before_memory_reply")
                elif not all(verdict.specialist_replies[actor] for actor in SPECIALISTS):
                    _append_failure(verdict, "primary_user_before_all_specialist_replies")
                continue

        if by == "memory" and reply_to in memory_consult_ids:
            verdict.memory_replies.append(event_ref)
            if first_memory_reply_line is None:
                first_memory_reply_line = item.line
            continue

        if by in SPECIALIST_SET and reply_to in specialist_consult_ids.get(by, set()):
            verdict.specialist_replies[by].append(event_ref)

    if verdict.failure_reasons:
        verdict.round_verdict = "fail"
        verdict.active_probe_status = "stale"
        return verdict

    if (
        verdict.primary_user_messages
        and verdict.memory_replies
        and all(verdict.specialist_replies[actor] for actor in SPECIALISTS)
    ):
        verdict.round_verdict = "pass"
        verdict.active_probe_status = "stale"
        return verdict

    verdict.round_verdict = "pending"
    verdict.active_probe_status = "stale" if verdict.superseding_event is not None else "active"
    verdict.pending_reason, verdict.pending_evidence = _pending_state(verdict)
    return verdict


def _normalize_to_tokens(data: Dict[str, Any]) -> set[str]:
    raw = data.get("to")
    tokens: List[str] = []
    if isinstance(raw, list):
        tokens = [str(item).strip() for item in raw if str(item).strip()]
    elif isinstance(raw, str):
        token = raw.strip()
        if token:
            tokens = [token]
    normalized = {"user" if token == "@user" else token for token in tokens}
    return normalized


def _event_ref(item: _LedgerEvent) -> EventRef:
    payload = item.payload
    data = payload.get("data") if isinstance(payload.get("data"), dict) else {}
    return EventRef(
        line=item.line,
        event_id=str(payload.get("id") or "").strip(),
        ts=str(payload.get("ts") or "").strip(),
        kind=str(payload.get("kind") or "").strip(),
        by=str(payload.get("by") or "").strip(),
        to=sorted(_normalize_to_tokens(data)),
        reply_to=str(data.get("reply_to") or "").strip(),
    )


def _extract_bound_patient_id(event: Dict[str, Any]) -> str:
    data = event.get("data") if isinstance(event.get("data"), dict) else {}
    refs = data.get("refs")
    if isinstance(refs, list):
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            medical_context = ref.get("medical_context")
            if isinstance(medical_context, dict):
                patient_id = str(medical_context.get("patient_id") or "").strip()
                if patient_id:
                    return patient_id
    text = str(data.get("text") or "")
    match = _PATIENT_BINDING_RE.search(text)
    return match.group(1).strip() if match else ""


def _append_failure(verdict: RoundGateVerdict, reason: str) -> None:
    if reason not in verdict.failure_reasons:
        verdict.failure_reasons.append(reason)


def _pending_state(verdict: RoundGateVerdict) -> tuple[str, Dict[str, Any]]:
    if verdict.memory_consults and not verdict.memory_replies:
        return (
            "blocked_on_memory",
            {
                "pending_memory_consult_ids": [item.event_id for item in verdict.memory_consults],
                "memory_pending_notification_ids": [item.event_id for item in verdict.memory_pending_notifications],
            },
        )

    if verdict.memory_replies and verdict.specialist_consults:
        missing_specialists = [
            actor for actor in SPECIALISTS if not verdict.specialist_replies.get(actor)
        ]
        if missing_specialists:
            return (
                "blocked_on_specialist_replies",
                {
                    "missing_specialist_replies": missing_specialists,
                    "specialist_consult_ids": [item.event_id for item in verdict.specialist_consults],
                },
            )

    if verdict.memory_replies and all(verdict.specialist_replies.get(actor) for actor in SPECIALISTS):
        return (
            "blocked_on_primary_closeout",
            {
                "memory_reply_ids": [item.event_id for item in verdict.memory_replies],
                "specialist_reply_ids": {
                    actor: [item.event_id for item in verdict.specialist_replies.get(actor, [])]
                    for actor in SPECIALISTS
                },
            },
        )

    if verdict.probe_event and not verdict.memory_consults and not verdict.specialist_consults and not verdict.primary_user_messages:
        return (
            "blocked_on_primary_progress",
            {
                "probe_event_id": verdict.probe_event.event_id,
            },
        )

    return ("indeterminate_pending", {})
