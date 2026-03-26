import json
from pathlib import Path

from src.cccc_native.runtime_diagnostics import diagnose_memory_delivery


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


def _write_group_runtime(
    tmp_path: Path,
    *,
    ledger_events: list[dict],
    cursor_event_id: str,
    automation_nudge_keys: list[str],
    runner_pid: int = 4480,
) -> Path:
    group_dir = tmp_path / "g_test"
    (group_dir / "state" / "runners" / "pty").mkdir(parents=True, exist_ok=True)
    ledger_path = group_dir / "ledger.jsonl"
    ledger_path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in ledger_events),
        encoding="utf-8",
    )
    (group_dir / "state" / "read_cursors.json").write_text(
        json.dumps(
            {
                "memory": {
                    "event_id": cursor_event_id,
                    "ts": "2026-03-26T00:00:01Z",
                    "updated_at": "2026-03-26T00:00:02Z",
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (group_dir / "state" / "automation.json").write_text(
        json.dumps(
            {
                "actors": {
                    "memory": {
                        "nudge_items": {key: {"count": 1} for key in automation_nudge_keys},
                    }
                }
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    (group_dir / "state" / "runners" / "pty" / "memory.json").write_text(
        json.dumps(
            {
                "v": 1,
                "kind": "pty",
                "group_id": "g_test",
                "actor_id": "memory",
                "pid": runner_pid,
                "started_at": "2026-03-26T00:00:00Z",
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return group_dir


def test_diagnose_memory_delivery_stalled_when_runner_alive_nudged_and_cursor_stale(tmp_path: Path):
    probe_id = "probe_stall"
    events = [
        _event("old_cursor", "chat.message", "memory", {"to": ["primary"]}),
        _event(
            probe_id,
            "chat.message",
            "user",
            {"to": ["primary"], "refs": [{"medical_context": {"patient_id": "PAT_STALL"}}]},
        ),
        _event("m1", "chat.message", "primary", {"to": ["memory"], "reply_required": True}),
        _event("m2", "chat.message", "primary", {"to": ["memory"], "reply_required": True}),
        _event(
            "n1",
            "system.notify",
            "system",
            {"target_actor_id": "memory", "message": "REPLY REQUIRED: event_id=m1"},
        ),
        _event(
            "n2",
            "system.notify",
            "system",
            {"target_actor_id": "memory", "message": "Unread backlog: oldest from consult"},
        ),
    ]
    group_dir = _write_group_runtime(
        tmp_path,
        ledger_events=events,
        cursor_event_id="old_cursor",
        automation_nudge_keys=["reply_required:m1", "unread_backlog"],
    )

    diagnostics = diagnose_memory_delivery(group_dir, probe_id, pid_alive_fn=lambda pid: pid == 4480)

    assert diagnostics.status == "stalled"
    assert [item.event_id for item in diagnostics.memory_consults] == ["m1", "m2"]
    assert diagnostics.cursor_event_id == "old_cursor"
    assert diagnostics.cursor_stale is True
    assert diagnostics.runner_alive is True
    assert diagnostics.memory_reads == []
    assert diagnostics.memory_acks == []
    assert diagnostics.memory_replies == []
    assert diagnostics.automation_nudge_keys == ["reply_required:m1", "unread_backlog"]
    assert diagnostics.reasons == [
        "memory_consults_pending",
        "memory_nudged",
        "memory_automation_backlog",
        "no_memory_activity",
        "memory_cursor_stale",
        "memory_runner_alive",
    ]


def test_diagnose_memory_delivery_reports_replied_when_memory_reply_exists(tmp_path: Path):
    probe_id = "probe_reply"
    events = [
        _event("old_cursor", "chat.message", "memory", {"to": ["primary"]}),
        _event(
            probe_id,
            "chat.message",
            "user",
            {"to": ["primary"], "refs": [{"medical_context": {"patient_id": "PAT_REPLY"}}]},
        ),
        _event("m1", "chat.message", "primary", {"to": ["memory"], "reply_required": True}),
        _event(
            "n1",
            "system.notify",
            "system",
            {"target_actor_id": "memory", "message": "REPLY REQUIRED: event_id=m1"},
        ),
        _event("mr1", "chat.message", "memory", {"to": ["primary"], "reply_to": "m1"}),
    ]
    group_dir = _write_group_runtime(
        tmp_path,
        ledger_events=events,
        cursor_event_id="old_cursor",
        automation_nudge_keys=["reply_required:m1"],
    )

    diagnostics = diagnose_memory_delivery(group_dir, probe_id, pid_alive_fn=lambda _pid: True)

    assert diagnostics.status == "replied"
    assert [item.event_id for item in diagnostics.memory_replies] == ["mr1"]
    assert "no_memory_activity" not in diagnostics.reasons


def test_diagnose_memory_delivery_reports_consumed_when_memory_reads_consult(tmp_path: Path):
    probe_id = "probe_read"
    events = [
        _event("old_cursor", "chat.message", "memory", {"to": ["primary"]}),
        _event(
            probe_id,
            "chat.message",
            "user",
            {"to": ["primary"], "refs": [{"medical_context": {"patient_id": "PAT_READ"}}]},
        ),
        _event("m1", "chat.message", "primary", {"to": ["memory"], "reply_required": True}),
        _event(
            "n1",
            "system.notify",
            "system",
            {"target_actor_id": "memory", "message": "REPLY REQUIRED: event_id=m1"},
        ),
        _event("read1", "chat.read", "memory", {"actor_id": "memory", "event_id": "m1"}),
        _event("ack1", "chat.ack", "memory", {"actor_id": "memory", "event_id": "m1"}),
    ]
    group_dir = _write_group_runtime(
        tmp_path,
        ledger_events=events,
        cursor_event_id="m1",
        automation_nudge_keys=["unread_backlog"],
    )

    diagnostics = diagnose_memory_delivery(group_dir, probe_id, pid_alive_fn=lambda _pid: True)

    assert diagnostics.status == "consumed"
    assert [item.event_id for item in diagnostics.memory_reads] == ["read1"]
    assert [item.event_id for item in diagnostics.memory_acks] == ["ack1"]
    assert diagnostics.cursor_stale is False
    assert "no_memory_activity" not in diagnostics.reasons
