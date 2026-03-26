"""Chat send/reply operation handlers for daemon."""

from __future__ import annotations

import logging
import re
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, Optional

from ...contracts.v1 import ChatMessageData, ChatStreamData, DaemonError, DaemonResponse, Reference, SystemNotifyData
from ...kernel.actors import find_actor, list_actors, resolve_recipient_tokens
from ...kernel.group import get_group_state, load_group, set_group_state
from ...kernel.inbox import find_event, get_quote_text, has_chat_ack, is_message_for_actor, iter_events
from ...kernel.ledger import append_event
from ...kernel.messaging import (
    default_reply_recipients,
    enabled_recipient_actor_ids,
    get_default_send_to,
    targets_any_agent,
)
from ...kernel.registry import load_registry
from ...kernel.scope import detect_scope
from ...util.time import utc_now_iso
from .delivery import emit_system_notify, flush_pending_messages, get_headless_targets_for_message, queue_chat_message

logger = logging.getLogger("cccc.daemon.server")
_PATIENT_BINDING_RE = re.compile(r"\[PATIENT_BINDING[^\]]*patient_id=([^\s\]]+)")
_SPECIALIST_ACTOR_IDS = frozenset({"pharmacist", "nutritionist", "doctor"})


def _error(code: str, message: str, *, details: Optional[Dict[str, Any]] = None) -> DaemonResponse:
    return DaemonResponse(ok=False, error=DaemonError(code=code, message=message, details=(details or {})))


def _wake_group_on_human_message(
    group: Any,
    *,
    by: str,
    automation_on_resume: Callable[[Any], None],
    clear_pending_system_notifies: Callable[[str, set[str]], None],
) -> Any:
    # Keep idle stable against agent chatter / throttled deliveries.
    try:
        if get_group_state(group) != "idle":
            return group
        is_actor_sender = isinstance(find_actor(group, by), dict)
        if not by or by == "system" or is_actor_sender:
            return group
        group = set_group_state(group, state="active")
        try:
            automation_on_resume(group)
        except Exception:
            pass
        try:
            clear_pending_system_notifies(
                group.group_id,
                {"nudge", "keepalive", "help_nudge", "actor_idle", "silence_check", "auto_idle", "automation"},
            )
        except Exception:
            pass
        return group
    except Exception:
        return group


def _build_delivery_text(
    *,
    text: str,
    priority: str,
    reply_required: bool,
    event_id: str,
    refs: list[dict[str, Any]],
    attachments: list[dict[str, Any]],
    src_group_id: str = "",
    src_event_id: str = "",
) -> str:
    delivery_text = text
    hidden_blocks = _render_hidden_context_refs(refs)
    if hidden_blocks:
        delivery_text = "\n\n".join(hidden_blocks + ([delivery_text] if delivery_text else [])).strip()
    prefix_lines: list[str] = []
    if priority == "attention" and event_id:
        prefix_lines.append(f"[cccc] IMPORTANT (event_id={event_id}):")
    if reply_required and event_id:
        prefix_lines.append(f"[cccc] REPLY REQUIRED (event_id={event_id}): reply via cccc_message_reply.")
    if src_group_id and src_event_id:
        prefix_lines.append(f"[cccc] RELAYED FROM (group_id={src_group_id}, event_id={src_event_id}):")
    if prefix_lines:
        delivery_text = "\n".join(prefix_lines) + "\n" + delivery_text
    if attachments:
        lines = ["[cccc] Attachments:"]
        for attachment in attachments[:8]:
            title = str(attachment.get("title") or attachment.get("path") or "file").strip()
            size_bytes = int(attachment.get("bytes") or 0)
            rel_path = str(attachment.get("path") or "").strip()
            lines.append(f"- {title} ({size_bytes} bytes) [{rel_path}]")
        if len(attachments) > 8:
            lines.append(f"- … ({len(attachments) - 8} more)")
        delivery_text = (delivery_text.rstrip("\n") + "\n\n" + "\n".join(lines)).strip()
    return delivery_text


def _normalize_refs(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("refs must be a list")
    refs: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            raise ValueError("invalid ref (must be object)")
        refs.append(Reference.model_validate(item).model_dump())
    return refs


def _extract_bound_patient_id(event: dict[str, Any]) -> str:
    data = event.get("data")
    if not isinstance(data, dict):
        return ""

    refs = data.get("refs")
    if isinstance(refs, list):
        for ref in refs:
            if not isinstance(ref, dict):
                continue
            title = str(ref.get("title") or "").strip().lower()
            medical_context = ref.get("medical_context")
            if title == "medical_context" and isinstance(medical_context, dict):
                patient_id = str(medical_context.get("patient_id") or "").strip()
                if patient_id:
                    return patient_id

    text = str(data.get("text") or "")
    match = _PATIENT_BINDING_RE.search(text)
    if match:
        return str(match.group(1) or "").strip()
    return ""


def _current_round_has_memory_reply(
    group: Any,
    *,
    user_event_id: str,
    blocked_action: str = "user_reply",
) -> Optional[DaemonResponse]:
    if str(group.doc.get("title") or "").strip() != "glucose-management-main":
        return None

    original = find_event(group, user_event_id)
    if original is None:
        return None
    if str(original.get("kind") or "") != "chat.message":
        return None
    if str(original.get("by") or "").strip() != "user":
        return None
    if not _extract_bound_patient_id(original):
        return None

    started = False
    memory_consult_ids: list[str] = []
    specialist_consult_ids: Dict[str, list[str]] = {actor_id: [] for actor_id in _SPECIALIST_ACTOR_IDS}
    specialist_reply_counts: Dict[str, int] = {actor_id: 0 for actor_id in _SPECIALIST_ACTOR_IDS}
    memory_reply_seen = False
    for ev in iter_events(group.ledger_path):
        event_id = str(ev.get("id") or "").strip()
        if not started:
            if event_id == user_event_id:
                started = True
            continue
        if str(ev.get("kind") or "") != "chat.message":
            continue
        data = ev.get("data")
        if not isinstance(data, dict):
            continue
        sender = str(ev.get("by") or "").strip()
        if sender == "primary":
            to_tokens = data.get("to")
            normalized_to_tokens = (
                {str(item or "").strip() for item in to_tokens}
                if isinstance(to_tokens, list)
                else set()
            )
            if "memory" in normalized_to_tokens:
                if event_id:
                    memory_consult_ids.append(event_id)
                continue
            for actor_id in _SPECIALIST_ACTOR_IDS:
                if actor_id in normalized_to_tokens and event_id:
                    specialist_consult_ids[actor_id].append(event_id)
        elif sender == "memory":
            if str(data.get("reply_to") or "").strip() in memory_consult_ids:
                memory_reply_seen = True
                if blocked_action == "specialist_consult":
                    return None
                continue
        elif sender in _SPECIALIST_ACTOR_IDS:
            if str(data.get("reply_to") or "").strip() in specialist_consult_ids.get(sender, []):
                specialist_reply_counts[sender] += 1

    if memory_consult_ids:
        if not memory_reply_seen:
            if blocked_action == "specialist_consult":
                return _error(
                    "memory_reply_required",
                    "primary cannot consult specialists before a real memory->primary ledger reply exists for the current bound round",
                    details={
                        "reply_to": user_event_id,
                        "pending_memory_consults": memory_consult_ids,
                        "blocked_action": blocked_action,
                    },
                )
            return _error(
                "memory_reply_required",
                "primary cannot reply to user before a real memory->primary ledger reply exists for the current bound round",
                details={
                    "reply_to": user_event_id,
                    "pending_memory_consults": memory_consult_ids,
                    "blocked_action": blocked_action,
                },
            )
        if blocked_action == "specialist_consult":
            return None
        missing_specialists = [
            actor_id for actor_id in sorted(_SPECIALIST_ACTOR_IDS) if specialist_reply_counts.get(actor_id, 0) <= 0
        ]
        if missing_specialists:
            return _error(
                "specialist_replies_required",
                "primary cannot reply to user before required specialist replies exist for the current bound round",
                details={
                    "reply_to": user_event_id,
                    "blocked_action": blocked_action,
                    "missing_specialists": missing_specialists,
                    "specialist_consults": specialist_consult_ids,
                    "memory_reply_seen": memory_reply_seen,
                },
            )
        return None
    if blocked_action == "specialist_consult":
        return _error(
            "memory_consult_required",
            "primary cannot consult specialists on a bound round before sending a live consult to memory",
            details={"reply_to": user_event_id, "blocked_action": blocked_action},
        )
    return _error(
        "memory_consult_required",
        "primary cannot reply to user on a bound round before sending a live consult to memory",
        details={"reply_to": user_event_id, "blocked_action": blocked_action},
    )


def _latest_bound_round_gate(group: Any, *, blocked_action: str) -> Optional[DaemonResponse]:
    latest_bound_user_event_id = _latest_bound_user_event_id(group)
    if not latest_bound_user_event_id:
        return None
    return _current_round_has_memory_reply(
        group,
        user_event_id=latest_bound_user_event_id,
        blocked_action=blocked_action,
    )


def _latest_bound_user_event_id(group: Any) -> str:
    latest_bound_user_event_id = ""
    for ev in iter_events(group.ledger_path):
        if str(ev.get("kind") or "") != "chat.message":
            continue
        if str(ev.get("by") or "").strip() != "user":
            continue
        if not _extract_bound_patient_id(ev):
            continue
        latest_bound_user_event_id = str(ev.get("id") or "").strip()
    return latest_bound_user_event_id


def _render_legacy_medical_context(payload: dict[str, Any]) -> str:
    patient_id = str(payload.get("patient_id") or "").strip()
    patient_name = str(payload.get("patient_name") or "").strip() or "unknown"
    profile = payload.get("profile")
    profile_dict = profile if isinstance(profile, dict) else {}
    glucose_recent = profile_dict.get("glucose_recent")
    glucose_recent_items: list[str] = []
    if isinstance(glucose_recent, list):
        for item in glucose_recent:
            if not isinstance(item, dict):
                continue
            glucose_type = str(item.get("type") or "").strip()
            if not glucose_type:
                continue
            timestamp = str(item.get("timestamp") or "").strip()
            suffix = f"@{timestamp}" if timestamp else ""
            glucose_recent_items.append(f"{glucose_type}:{item.get('value')}{suffix}")

    lines = [
        f"[PATIENT_BINDING patient_id={patient_id} patient_name={patient_name}]",
        "[PATIENT_PROFILE]",
        f"name={str(profile_dict.get('name') or patient_name or 'unknown').strip() or 'unknown'}",
        f"age={profile_dict.get('age')}" if profile_dict.get("age") not in (None, "") else "",
        f"gender={str(profile_dict.get('gender') or '').strip()}" if str(profile_dict.get("gender") or "").strip() else "",
        f"diabetes_type={str(profile_dict.get('diabetes_type') or '').strip()}" if str(profile_dict.get("diabetes_type") or "").strip() else "",
        f"diagnosis_date={str(profile_dict.get('diagnosis_date') or '').strip()}" if str(profile_dict.get("diagnosis_date") or "").strip() else "",
        (
            "medications="
            + " | ".join(str(item).strip() for item in profile_dict.get("medications") or [] if str(item).strip())
        )
        if isinstance(profile_dict.get("medications"), list) and any(str(item).strip() for item in profile_dict.get("medications") or [])
        else "",
        (
            "complications="
            + " | ".join(str(item).strip() for item in profile_dict.get("complications") or [] if str(item).strip())
        )
        if isinstance(profile_dict.get("complications"), list) and any(str(item).strip() for item in profile_dict.get("complications") or [])
        else "",
        (
            "glucose_recent=" + " | ".join(glucose_recent_items)
        )
        if glucose_recent_items
        else "",
        "[/PATIENT_PROFILE]",
    ]
    return "\n".join(line for line in lines if line).strip()


def _render_hidden_context_refs(refs: list[dict[str, Any]]) -> list[str]:
    hidden_blocks: list[str] = []
    for ref in refs:
        if not isinstance(ref, dict):
            continue
        title = str(ref.get("title") or "").strip().lower()
        medical_context = ref.get("medical_context")
        if title != "medical_context" and not isinstance(medical_context, dict):
            continue
        text = str(ref.get("text") or "").strip()
        if text:
            hidden_blocks.append(text)
            continue
        if isinstance(medical_context, dict):
            rendered = _render_legacy_medical_context(medical_context)
            if rendered:
                hidden_blocks.append(rendered)
    return hidden_blocks


def _touch_registry_updated_at(group_id: str, ts: str) -> None:
    try:
        reg = load_registry()
        meta = reg.groups.get(group_id)
        if isinstance(meta, dict):
            meta["updated_at"] = str(ts or utc_now_iso())
            reg.save()
    except Exception:
        pass


def _notify_headless_targets(
    *,
    group: Any,
    by: str,
    event_id: str,
    priority: str,
    reply_required: bool,
    event: dict[str, Any],
) -> None:
    try:
        headless_targets = get_headless_targets_for_message(group, event=event, by=by)
        if reply_required:
            notify_title = "Need reply"
            notify_priority = "urgent" if priority == "attention" else "high"
        else:
            notify_title = "Needs acknowledgement" if priority == "attention" else "New message"
            notify_priority = "urgent" if priority == "attention" else "high"
        for actor_id in headless_targets:
            append_event(
                group.ledger_path,
                kind="system.notify",
                group_id=group.group_id,
                scope_key="",
                by="system",
                data={
                    "kind": "info",
                    "priority": notify_priority,
                    "title": notify_title,
                    "message": f"New message from {by}. Check your inbox.",
                    "target_actor_id": actor_id,
                    "requires_ack": False,
                    "context": {"event_id": event_id, "from": by},
                },
            )
    except Exception:
        pass


def handle_send(
    args: Dict[str, Any],
    *,
    coerce_bool: Callable[[Any], bool],
    normalize_attachments: Callable[[Any, Any], list[dict[str, Any]]],
    effective_runner_kind: Callable[[str], str],
    auto_wake_recipients: Callable[[Any, list[str], str], list[str]],
    automation_on_resume: Callable[[Any], None],
    automation_on_new_message: Callable[[Any], None],
    clear_pending_system_notifies: Callable[[str, set[str]], None],
) -> DaemonResponse:
    group_id = str(args.get("group_id") or "").strip()
    text = str(args.get("text") or "")
    by = str(args.get("by") or "user").strip()
    priority = str(args.get("priority") or "normal").strip() or "normal"
    reply_required = coerce_bool(args.get("reply_required"))
    src_group_id = str(args.get("src_group_id") or "").strip()
    src_event_id = str(args.get("src_event_id") or "").strip()
    dst_group_id = str(args.get("dst_group_id") or "").strip()
    client_id = str(args.get("client_id") or "").strip()
    source_platform = str(args.get("source_platform") or "").strip()
    source_user_name = str(args.get("source_user_name") or "").strip()
    source_user_id = str(args.get("source_user_id") or "").strip()
    mention_user_ids_raw = args.get("mention_user_ids")
    mention_user_ids = (
        [str(item).strip() for item in mention_user_ids_raw if str(item).strip()]
        if isinstance(mention_user_ids_raw, list)
        else []
    )
    dst_to_raw = args.get("dst_to")
    dst_to: list[str] = []
    if isinstance(dst_to_raw, list):
        dst_to = [str(x).strip() for x in dst_to_raw if isinstance(x, str) and str(x).strip()]
    if (src_group_id and not src_event_id) or (src_event_id and not src_group_id):
        src_group_id = ""
        src_event_id = ""
    to_raw = args.get("to")
    to_tokens: list[str] = []
    if isinstance(to_raw, list):
        to_tokens = [str(x).strip() for x in to_raw if isinstance(x, str) and str(x).strip()]
    elif isinstance(to_raw, str):
        token = to_raw.strip()
        if token:
            to_tokens = [token]
    to_explicitly_set = len(to_tokens) > 0

    if priority not in ("normal", "attention"):
        return _error("invalid_priority", "priority must be 'normal' or 'attention'")
    if not group_id:
        return _error("missing_group_id", "missing group_id")

    group = load_group(group_id)
    if group is None:
        return _error("group_not_found", f"group not found: {group_id}")

    group = _wake_group_on_human_message(
        group,
        by=by,
        automation_on_resume=automation_on_resume,
        clear_pending_system_notifies=clear_pending_system_notifies,
    )

    try:
        to = resolve_recipient_tokens(group, to_tokens)
    except Exception as e:
        return _error("invalid_recipient", str(e))

    if not to:
        mention_pattern = re.compile(r"@(\w[\w-]*)")
        mentions = mention_pattern.findall(text)
        if mentions:
            actors = list_actors(group)
            actor_ids = {str(actor.get("id") or "") for actor in actors if isinstance(actor, dict)}
            valid_mentions = [m for m in mentions if m in actor_ids or m in ("all", "peers", "foreman")]
            if valid_mentions:
                mention_tokens = [f"@{m}" if m in ("all", "peers", "foreman") else m for m in valid_mentions]
                try:
                    to = resolve_recipient_tokens(group, mention_tokens)
                except Exception:
                    pass

    if not to and not to_explicitly_set and get_default_send_to(group.doc) == "foreman":
        to = ["@foreman"]

    if str(by or "").strip() == "primary":
        latest_bound_user_event_id = _latest_bound_user_event_id(group)
        if latest_bound_user_event_id and "memory" in to:
            reply_required = True
        if "user" in to:
            gate_error = _latest_bound_round_gate(group, blocked_action="user_reply")
            if gate_error is not None:
                return gate_error
        prospective_event = {"kind": "chat.message", "data": {"to": list(to)}}
        if any(is_message_for_actor(group, actor_id=actor_id, event=prospective_event) for actor_id in _SPECIALIST_ACTOR_IDS):
            gate_error = _latest_bound_round_gate(group, blocked_action="specialist_consult")
            if gate_error is not None:
                return gate_error

    if targets_any_agent(to):
        matched_enabled = enabled_recipient_actor_ids(group, to)
        if by and by in matched_enabled:
            matched_enabled = [actor_id for actor_id in matched_enabled if actor_id != by]
        if not matched_enabled:
            woken = auto_wake_recipients(group, to, by)
            if not woken:
                wanted = " ".join(to) if to else "@all"
                return _error(
                    "no_enabled_recipients",
                    (
                        "No enabled recipients after excluding sender. "
                        "Please specify 'to' explicitly, e.g. to=['user'], to=['@all'], or to=['peer-reviewer']. "
                        f"Current resolved recipients: {wanted}"
                    ),
                    details={"to": list(to)},
                )

    path = str(args.get("path") or "").strip()
    if path:
        scope = detect_scope(Path(path))
        scope_key = scope.scope_key
        scopes = group.doc.get("scopes")
        attached = False
        if isinstance(scopes, list):
            attached = any(isinstance(item, dict) and item.get("scope_key") == scope_key for item in scopes)
        if not attached:
            return _error(
                "scope_not_attached",
                f"scope not attached: {scope_key}",
                details={"hint": "cccc attach <path> --group <id>"},
            )
    else:
        scope_key = str(group.doc.get("active_scope_key") or "").strip()
    if not scope_key:
        scope_key = ""

    try:
        refs = _normalize_refs(args.get("refs"))
    except Exception as e:
        return _error("invalid_refs", str(e))
    try:
        attachments = normalize_attachments(group, args.get("attachments"))
    except Exception as e:
        return _error("invalid_attachments", str(e))

    if not text.strip() and not attachments:
        return _error("empty_message", "message text cannot be empty")

    event = append_event(
        group.ledger_path,
        kind="chat.message",
        group_id=group.group_id,
        scope_key=scope_key,
        by=by,
        data=ChatMessageData(
            text=text,
            format="plain",
            priority=priority,
            reply_required=reply_required,
            to=to,
            refs=refs,
            attachments=attachments,
            source_platform=source_platform or None,
            source_user_name=source_user_name or None,
            source_user_id=source_user_id or None,
            mention_user_ids=mention_user_ids or None,
            src_group_id=src_group_id or None,
            src_event_id=src_event_id or None,
            dst_group_id=dst_group_id or None,
            dst_to=dst_to if dst_group_id else None,
            client_id=client_id or None,
        ).model_dump(),
    )
    _touch_registry_updated_at(group.group_id, str(event.get("ts") or utc_now_iso()))

    effective_to = to if to else ["@all"]
    event_id = str(event.get("id") or "").strip()
    event_ts = str(event.get("ts") or "").strip()
    delivery_text = _build_delivery_text(
        text=text,
        priority=priority,
        reply_required=reply_required,
        event_id=event_id,
        refs=refs,
        attachments=attachments,
        src_group_id=src_group_id,
        src_event_id=src_event_id,
    )
    actors = list_actors(group)
    logger.debug(f"[SEND] group={group_id} text={text[:30]!r} actors={[a.get('id') for a in actors]} effective_to={effective_to}")
    for actor in actors:
        if not isinstance(actor, dict):
            continue
        actor_id = str(actor.get("id") or "").strip()
        if not actor_id or actor_id == "user" or actor_id == by:
            logger.debug(f"[SEND] skip actor={actor_id} (user/by)")
            continue
        event_with_effective_to = dict(event)
        event_with_effective_to["data"] = dict(event.get("data") or {})
        event_with_effective_to["data"]["to"] = effective_to
        if not is_message_for_actor(group, actor_id=actor_id, event=event_with_effective_to):
            logger.debug(f"[SEND] skip actor={actor_id} (not for actor)")
            continue
        runner_kind = str(actor.get("runner") or "pty").strip()
        if effective_runner_kind(runner_kind) == "pty":
            queue_chat_message(
                group,
                actor_id=actor_id,
                event_id=event_id,
                by=by,
                to=effective_to,
                text=delivery_text,
                source_platform=source_platform or None,
                source_user_name=source_user_name or None,
                source_user_id=source_user_id or None,
                ts=event_ts,
            )
            flush_pending_messages(group, actor_id=actor_id)
            if reply_required:
                emit_system_notify(
                    group,
                    by="system",
                    notify=SystemNotifyData(
                        kind="nudge",
                        priority="normal",
                        title="Action items pending (reply_required=1)",
                        message=f"REPLY REQUIRED: event_id={event_id}. Reply via cccc_message_reply(event_id={event_id}, ...).",
                        target_actor_id=actor_id,
                        context={"event_id": event_id, "from": by},
                        requires_ack=False,
                        related_event_id=event_id,
                    ),
                )

    event_for_headless = dict(event)
    event_for_headless["data"] = dict(event.get("data") or {})
    event_for_headless["data"]["to"] = effective_to
    _notify_headless_targets(
        group=group,
        by=by,
        event_id=event_id,
        priority=priority,
        reply_required=reply_required,
        event=event_for_headless,
    )

    try:
        automation_on_new_message(group)
    except Exception:
        pass

    return DaemonResponse(ok=True, result={"event": event})


def handle_reply(
    args: Dict[str, Any],
    *,
    coerce_bool: Callable[[Any], bool],
    normalize_attachments: Callable[[Any, Any], list[dict[str, Any]]],
    effective_runner_kind: Callable[[str], str],
    auto_wake_recipients: Callable[[Any, list[str], str], list[str]],
    automation_on_resume: Callable[[Any], None],
    automation_on_new_message: Callable[[Any], None],
    clear_pending_system_notifies: Callable[[str, set[str]], None],
) -> DaemonResponse:
    group_id = str(args.get("group_id") or "").strip()
    text = str(args.get("text") or "")
    by = str(args.get("by") or "user").strip()
    reply_to = str(args.get("reply_to") or "").strip()
    priority = str(args.get("priority") or "normal").strip() or "normal"
    reply_required = coerce_bool(args.get("reply_required"))
    client_id = str(args.get("client_id") or "").strip()
    to_raw = args.get("to")
    to_tokens: list[str] = []
    if isinstance(to_raw, list):
        to_tokens = [str(x).strip() for x in to_raw if isinstance(x, str) and str(x).strip()]

    if priority not in ("normal", "attention"):
        return _error("invalid_priority", "priority must be 'normal' or 'attention'")
    if not group_id:
        return _error("missing_group_id", "missing group_id")
    if not reply_to:
        return _error("missing_reply_to", "missing reply_to event_id")

    group = load_group(group_id)
    if group is None:
        return _error("group_not_found", f"group not found: {group_id}")

    group = _wake_group_on_human_message(
        group,
        by=by,
        automation_on_resume=automation_on_resume,
        clear_pending_system_notifies=clear_pending_system_notifies,
    )

    original = find_event(group, reply_to)
    if original is None:
        return _error("event_not_found", f"event not found: {reply_to}")
    quote_text = get_quote_text(group, reply_to, max_len=100)
    original_data = original.get("data") if isinstance(original.get("data"), dict) else {}
    original_source_platform = str(original_data.get("source_platform") or "").strip()
    original_source_user_name = str(original_data.get("source_user_name") or "").strip()
    original_source_user_id = str(original_data.get("source_user_id") or "").strip()
    original_mention_user_ids_raw = original_data.get("mention_user_ids")
    original_mention_user_ids = (
        [str(item).strip() for item in original_mention_user_ids_raw if str(item).strip()]
        if isinstance(original_mention_user_ids_raw, list)
        else []
    )

    if not to_tokens:
        to_tokens = default_reply_recipients(group, by=by, original_event=original)
    try:
        to = resolve_recipient_tokens(group, to_tokens)
    except Exception as e:
        return _error("invalid_recipient", str(e))

    if str(by or "").strip() == "primary" and ("user" in to or "@user" in to):
        gate_error = _current_round_has_memory_reply(group, user_event_id=reply_to)
        if gate_error is not None:
            return gate_error

    if targets_any_agent(to):
        matched_enabled = enabled_recipient_actor_ids(group, to)
        if by and by in matched_enabled:
            matched_enabled = [actor_id for actor_id in matched_enabled if actor_id != by]
        if not matched_enabled:
            woken = auto_wake_recipients(group, to, by)
            if not woken:
                wanted = " ".join(to) if to else "@all"
                return _error(
                    "no_enabled_recipients",
                    (
                        "No enabled recipients after excluding sender. "
                        "Please specify 'to' explicitly, e.g. to=['user'], to=['@all'], or to=['peer-reviewer']. "
                        f"Current resolved recipients: {wanted}"
                    ),
                    details={"to": list(to)},
                )

    scope_key = str(group.doc.get("active_scope_key") or "").strip()
    try:
        refs = _normalize_refs(args.get("refs"))
    except Exception as e:
        return _error("invalid_refs", str(e))
    try:
        attachments = normalize_attachments(group, args.get("attachments"))
    except Exception as e:
        return _error("invalid_attachments", str(e))
    if not text.strip() and not attachments:
        return _error("empty_message", "message text cannot be empty")

    event = append_event(
        group.ledger_path,
        kind="chat.message",
        group_id=group.group_id,
        scope_key=scope_key,
        by=by,
        data=ChatMessageData(
            text=text,
            format="plain",
            priority=priority,
            reply_required=reply_required,
            to=to,
            reply_to=reply_to,
            quote_text=quote_text,
            refs=refs,
            attachments=attachments,
            source_platform=original_source_platform or None,
            source_user_name=original_source_user_name or None,
            source_user_id=original_source_user_id or None,
            mention_user_ids=original_mention_user_ids or None,
            client_id=client_id or None,
        ).model_dump(),
    )

    ack_event: Optional[dict[str, Any]] = None
    try:
        if str(original.get("kind") or "") == "chat.message":
            original_by = str(original.get("by") or "").strip()
            original_data = original.get("data") if isinstance(original.get("data"), dict) else {}
            original_priority = str(original_data.get("priority") or "normal").strip()
            if by and by != original_by and original_priority == "attention":
                if is_message_for_actor(group, actor_id=by, event=original):
                    target_event_id = str(original.get("id") or "").strip()
                    if target_event_id and not has_chat_ack(group, event_id=target_event_id, actor_id=by):
                        ack_event = append_event(
                            group.ledger_path,
                            kind="chat.ack",
                            group_id=group.group_id,
                            scope_key="",
                            by=by,
                            data={"actor_id": by, "event_id": target_event_id},
                        )
    except Exception:
        ack_event = None

    _touch_registry_updated_at(group.group_id, str(event.get("ts") or utc_now_iso()))

    effective_to = to if to else ["@all"]
    event_with_effective_to = dict(event)
    event_with_effective_to["data"] = dict(event.get("data") or {})
    event_with_effective_to["data"]["to"] = effective_to

    event_id = str(event.get("id") or "").strip()
    event_ts = str(event.get("ts") or "").strip()
    delivery_text = _build_delivery_text(
        text=text,
        priority=priority,
        reply_required=reply_required,
        event_id=event_id,
        refs=refs,
        attachments=attachments,
    )
    for actor in list_actors(group):
        if not isinstance(actor, dict):
            continue
        actor_id = str(actor.get("id") or "").strip()
        if not actor_id or actor_id == "user" or actor_id == by:
            continue
        if not is_message_for_actor(group, actor_id=actor_id, event=event_with_effective_to):
            continue
        runner_kind = str(actor.get("runner") or "pty").strip()
        if effective_runner_kind(runner_kind) == "pty":
            queue_chat_message(
                group,
                actor_id=actor_id,
                event_id=event_id,
                by=by,
                to=effective_to,
                text=delivery_text,
                reply_to=reply_to,
                quote_text=quote_text,
                ts=event_ts,
            )
            flush_pending_messages(group, actor_id=actor_id)
            if reply_required:
                emit_system_notify(
                    group,
                    by="system",
                    notify=SystemNotifyData(
                        kind="nudge",
                        priority="normal",
                        title="Action items pending (reply_required=1)",
                        message=f"REPLY REQUIRED: event_id={event_id}. Reply via cccc_message_reply(event_id={event_id}, ...).",
                        target_actor_id=actor_id,
                        context={"event_id": event_id, "from": by},
                        requires_ack=False,
                        related_event_id=event_id,
                    ),
                )

    _notify_headless_targets(
        group=group,
        by=by,
        event_id=event_id,
        priority=priority,
        reply_required=reply_required,
        event=event_with_effective_to,
    )

    try:
        automation_on_new_message(group)
    except Exception:
        pass

    return DaemonResponse(ok=True, result={"event": event, "ack_event": ack_event})


def handle_stream_emit(args: Dict[str, Any]) -> DaemonResponse:
    """Handle chat.stream events (start/update/end)."""
    group_id = str(args.get("group_id") or "").strip()
    by = str(args.get("by") or "").strip()
    op = str(args.get("op") or "").strip()

    if not group_id:
        return _error("missing_group_id", "missing group_id")
    if not by:
        return _error("missing_by", "missing by")
    if op not in ("start", "update", "end"):
        return _error("invalid_op", "op must be 'start', 'update', or 'end'")

    group = load_group(group_id)
    if group is None:
        return _error("group_not_found", f"group not found: {group_id}")

    stream_id = str(args.get("stream_id") or "").strip()
    if op == "start":
        stream_id = uuid.uuid4().hex
    elif not stream_id:
        return _error("missing_stream_id", "stream_id is required for update/end")

    text = str(args.get("text") or "")
    fmt = str(args.get("format") or "plain").strip() or "plain"
    seq = int(args.get("seq") or 0)
    to_raw = args.get("to")
    to: list[str] = []
    if isinstance(to_raw, list):
        to = [str(x).strip() for x in to_raw if isinstance(x, str) and str(x).strip()]
    reply_to = str(args.get("reply_to") or "").strip() or None
    client_id = str(args.get("client_id") or "").strip() or None

    data = ChatStreamData(
        stream_id=stream_id,
        op=op,
        text=text,
        format=fmt,
        seq=seq,
        to=to,
        reply_to=reply_to,
        client_id=client_id,
    )

    scope_key = str(group.doc.get("active_scope_key") or "").strip()
    event = append_event(
        group.ledger_path,
        kind="chat.stream",
        group_id=group.group_id,
        scope_key=scope_key,
        by=by,
        data=data.model_dump(),
    )

    return DaemonResponse(ok=True, result={"event": event, "stream_id": stream_id})


def try_handle_chat_op(
    op: str,
    args: Dict[str, Any],
    *,
    coerce_bool: Callable[[Any], bool],
    normalize_attachments: Callable[[Any, Any], list[dict[str, Any]]],
    effective_runner_kind: Callable[[str], str],
    auto_wake_recipients: Callable[[Any, list[str], str], list[str]],
    automation_on_resume: Callable[[Any], None],
    automation_on_new_message: Callable[[Any], None],
    clear_pending_system_notifies: Callable[[str, set[str]], None],
) -> Optional[DaemonResponse]:
    if op == "stream_emit":
        return handle_stream_emit(args)
    if op == "send":
        return handle_send(
            args,
            coerce_bool=coerce_bool,
            normalize_attachments=normalize_attachments,
            effective_runner_kind=effective_runner_kind,
            auto_wake_recipients=auto_wake_recipients,
            automation_on_resume=automation_on_resume,
            automation_on_new_message=automation_on_new_message,
            clear_pending_system_notifies=clear_pending_system_notifies,
        )
    if op == "reply":
        return handle_reply(
            args,
            coerce_bool=coerce_bool,
            normalize_attachments=normalize_attachments,
            effective_runner_kind=effective_runner_kind,
            auto_wake_recipients=auto_wake_recipients,
            automation_on_resume=automation_on_resume,
            automation_on_new_message=automation_on_new_message,
            clear_pending_system_notifies=clear_pending_system_notifies,
        )
    return None
