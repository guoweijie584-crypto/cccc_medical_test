import json
from pathlib import Path

from src.cccc_native.runtime_gate import classify_probe_round_from_ledger


def _write_ledger(tmp_path: Path, events: list[dict]) -> Path:
    ledger = tmp_path / "ledger.jsonl"
    lines = [json.dumps(item, ensure_ascii=False) for item in events]
    ledger.write_text("\n".join(lines), encoding="utf-8")
    return ledger


def _event(event_id: str, kind: str, by: str, data: dict) -> dict:
    return {
        "v": 1,
        "id": event_id,
        "ts": f"2026-03-26T00:00:{len(event_id):02d}Z",
        "kind": kind,
        "group_id": "g_test",
        "scope_key": "s_test",
        "by": by,
        "data": data,
    }


def test_classify_probe_round_pass_and_stale_when_superseded(tmp_path: Path):
    probe_id = "probe_pass"
    events = [
        _event(
            probe_id,
            "chat.message",
            "user",
            {
                "text": "bound round",
                "to": ["primary"],
                "refs": [{"medical_context": {"patient_id": "PAT_PASS"}}],
            },
        ),
        _event("m1", "chat.message", "primary", {"to": ["memory"], "reply_required": True}),
        _event("mr1", "chat.message", "memory", {"to": ["primary"], "reply_to": "m1"}),
        _event("s1", "chat.message", "primary", {"to": ["pharmacist"], "reply_required": True}),
        _event("s2", "chat.message", "primary", {"to": ["nutritionist"], "reply_required": True}),
        _event("s3", "chat.message", "primary", {"to": ["doctor"], "reply_required": True}),
        _event("pr1", "chat.message", "pharmacist", {"to": ["primary"], "reply_to": "s1"}),
        _event("nr1", "chat.message", "nutritionist", {"to": ["primary"], "reply_to": "s2"}),
        _event("dr1", "chat.message", "doctor", {"to": ["primary"], "reply_to": "s3"}),
        _event("u1", "chat.message", "primary", {"to": ["user"], "reply_to": probe_id}),
        _event("next_probe", "chat.message", "user", {"to": ["primary"], "text": "new round"}),
    ]

    verdict = classify_probe_round_from_ledger(_write_ledger(tmp_path, events), probe_id)

    assert verdict.round_verdict == "pass"
    assert verdict.active_probe_status == "stale"
    assert verdict.patient_id == "PAT_PASS"
    assert verdict.failure_reasons == []
    assert verdict.primary_user_messages[0].event_id == "u1"


def test_classify_probe_round_fails_on_early_send_path_violations(tmp_path: Path):
    probe_id = "probe_fail"
    events = [
        _event(
            probe_id,
            "chat.message",
            "user",
            {
                "text": "bound round",
                "to": ["primary"],
                "refs": [{"medical_context": {"patient_id": "PAT_FAIL"}}],
            },
        ),
        _event("m1", "chat.message", "primary", {"to": ["memory"], "reply_required": True}),
        _event(
            "nudge1",
            "system.notify",
            "system",
            {
                "target_actor_id": "memory",
                "message": "REPLY REQUIRED: event_id=m1",
            },
        ),
        _event("s1", "chat.message", "primary", {"to": ["pharmacist"]}),
        _event("s2", "chat.message", "primary", {"to": ["nutritionist"]}),
        _event("s3", "chat.message", "primary", {"to": ["doctor"]}),
        _event("u1", "chat.message", "primary", {"to": ["user"]}),
        _event("mr1", "chat.message", "memory", {"to": ["primary"], "reply_to": "m1"}),
    ]

    verdict = classify_probe_round_from_ledger(_write_ledger(tmp_path, events), probe_id)

    assert verdict.round_verdict == "fail"
    assert verdict.active_probe_status == "stale"
    assert sorted(verdict.failure_reasons) == [
        "primary_specialist_fan_out_before_memory_reply",
        "primary_user_before_memory_reply",
    ]
    assert len(verdict.memory_pending_notifications) == 1


def test_classify_probe_round_pending_and_active(tmp_path: Path):
    probe_id = "probe_pending"
    events = [
        _event(
            probe_id,
            "chat.message",
            "user",
            {
                "text": "bound round",
                "to": ["primary"],
                "refs": [{"medical_context": {"patient_id": "PAT_PENDING"}}],
            },
        ),
        _event("m1", "chat.message", "primary", {"to": ["memory"], "reply_required": True}),
        _event("cx1", "context.sync", "primary", {"version": "v1"}),
    ]

    verdict = classify_probe_round_from_ledger(_write_ledger(tmp_path, events), probe_id)

    assert verdict.round_verdict == "pending"
    assert verdict.active_probe_status == "active"
    assert verdict.pending_reason == "blocked_on_memory"
    assert verdict.pending_evidence["pending_memory_consult_ids"] == ["m1"]
    assert verdict.failure_reasons == []
    assert [item.event_id for item in verdict.memory_consults] == ["m1"]


def test_classify_probe_round_pending_but_stale_after_restart(tmp_path: Path):
    probe_id = "probe_stale"
    events = [
        _event(
            probe_id,
            "chat.message",
            "user",
            {
                "text": "bound round",
                "to": ["primary"],
                "refs": [{"medical_context": {"patient_id": "PAT_STALE"}}],
            },
        ),
        _event("m1", "chat.message", "primary", {"to": ["memory"], "reply_required": True}),
        _event("restart1", "actor.restart", "user", {"actor_id": "primary"}),
    ]

    verdict = classify_probe_round_from_ledger(_write_ledger(tmp_path, events), probe_id)

    assert verdict.round_verdict == "pending"
    assert verdict.active_probe_status == "stale"
    assert verdict.pending_reason == "blocked_on_memory"
    assert verdict.superseding_event is not None
    assert verdict.superseding_event.event_id == "restart1"


def test_classify_probe_round_fails_when_final_user_reply_precedes_required_specialist_replies(tmp_path: Path):
    probe_id = "probe_late_gap"
    events = [
        _event(
            probe_id,
            "chat.message",
            "user",
            {
                "text": "bound round",
                "to": ["primary"],
                "refs": [{"medical_context": {"patient_id": "PAT_LATE"}}],
            },
        ),
        _event("m1", "chat.message", "primary", {"to": ["memory"], "reply_required": True}),
        _event("mr1", "chat.message", "memory", {"to": ["primary"], "reply_to": "m1"}),
        _event("s1", "chat.message", "primary", {"to": ["pharmacist"], "reply_required": True}),
        _event("s2", "chat.message", "primary", {"to": ["nutritionist"], "reply_required": True}),
        _event("s3", "chat.message", "primary", {"to": ["doctor"], "reply_required": True}),
        _event("pr1", "chat.message", "pharmacist", {"to": ["primary"], "reply_to": "s1"}),
        _event("u1", "chat.message", "primary", {"to": ["user"], "reply_to": probe_id}),
        _event("nr1", "chat.message", "nutritionist", {"to": ["primary"], "reply_to": "s2"}),
        _event("dr1", "chat.message", "doctor", {"to": ["primary"], "reply_to": "s3"}),
    ]

    verdict = classify_probe_round_from_ledger(_write_ledger(tmp_path, events), probe_id)

    assert verdict.round_verdict == "fail"
    assert verdict.failure_reasons == ["primary_user_before_all_specialist_replies"]
    assert [item.event_id for item in verdict.primary_user_messages] == ["u1"]


def test_classify_probe_round_pending_on_missing_specialist_replies(tmp_path: Path):
    probe_id = "probe_waiting_specialists"
    events = [
        _event(
            probe_id,
            "chat.message",
            "user",
            {
                "text": "bound round",
                "to": ["primary"],
                "refs": [{"medical_context": {"patient_id": "PAT_WAIT"}}],
            },
        ),
        _event("m1", "chat.message", "primary", {"to": ["memory"], "reply_required": True}),
        _event("mr1", "chat.message", "memory", {"to": ["primary"], "reply_to": "m1"}),
        _event("s1", "chat.message", "primary", {"to": ["pharmacist"], "reply_required": True}),
        _event("s2", "chat.message", "primary", {"to": ["nutritionist"], "reply_required": True}),
        _event("s3", "chat.message", "primary", {"to": ["doctor"], "reply_required": True}),
        _event("nr1", "chat.message", "nutritionist", {"to": ["primary"], "reply_to": "s2"}),
        _event("dr1", "chat.message", "doctor", {"to": ["primary"], "reply_to": "s3"}),
        _event("restart1", "actor.restart", "user", {"actor_id": "memory"}),
    ]

    verdict = classify_probe_round_from_ledger(_write_ledger(tmp_path, events), probe_id)

    assert verdict.round_verdict == "pending"
    assert verdict.active_probe_status == "stale"
    assert verdict.pending_reason == "blocked_on_specialist_replies"
    assert verdict.pending_evidence["missing_specialist_replies"] == ["pharmacist"]


def test_classify_probe_round_pending_on_primary_progress(tmp_path: Path):
    probe_id = "probe_waiting_primary"
    events = [
        _event(
            probe_id,
            "chat.message",
            "user",
            {
                "text": "bound round",
                "to": ["primary"],
                "refs": [{"medical_context": {"patient_id": "PAT_IDLE"}}],
            },
        ),
        _event("restart1", "actor.restart", "user", {"actor_id": "primary"}),
    ]

    verdict = classify_probe_round_from_ledger(_write_ledger(tmp_path, events), probe_id)

    assert verdict.round_verdict == "pending"
    assert verdict.active_probe_status == "stale"
    assert verdict.pending_reason == "blocked_on_primary_progress"
    assert verdict.pending_evidence["probe_event_id"] == probe_id
