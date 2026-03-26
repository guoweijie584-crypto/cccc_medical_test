import os
import sys
from pathlib import Path

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from src.cccc_native import runtime_manager as rm


def test_load_actor_llm_config_defaults(tmp_path, monkeypatch):
    cfg_file = tmp_path / "actor_llm_config.json"
    monkeypatch.setattr(rm, "NATIVE_LLM_CONFIG_FILE", cfg_file)
    data = rm.load_actor_llm_config()
    assert data["default"]["api_base"] == "https://api.deepseek.com/v1"
    assert data["actors"] == {}


def test_save_actor_llm_config_merges(tmp_path, monkeypatch):
    cfg_file = tmp_path / "actor_llm_config.json"
    monkeypatch.setattr(rm, "NATIVE_LLM_CONFIG_FILE", cfg_file)
    saved = rm.save_actor_llm_config(
        {
            "default": {"api_base": "https://example.com/v1", "model": "demo-model"},
            "actors": {"primary": {"api_key": "sk-demo"}},
        }
    )
    assert saved["default"]["api_base"] == "https://example.com/v1"
    assert saved["actors"]["primary"]["api_key"] == "sk-demo"
    loaded = rm.load_actor_llm_config()
    assert loaded == saved


def test_native_cccc_home_prefers_native_env_over_bootstrap_state(tmp_path, monkeypatch):
    state_file = tmp_path / "bootstrap_state.json"
    stale_home = tmp_path / "stale-home"
    wanted_home = tmp_path / "wanted-home"
    state_file.write_text(
        '{"cccc_home": "%s"}' % str(stale_home).replace("\\", "\\\\"),
        encoding="utf-8",
    )
    monkeypatch.setattr(rm, "BOOTSTRAP_STATE_FILE", state_file)
    monkeypatch.setattr(rm, "DEFAULT_NATIVE_CCCC_HOME", tmp_path / "default-home")
    monkeypatch.setenv("CCCC_NATIVE_HOME", str(wanted_home))
    monkeypatch.delenv("CCCC_HOME", raising=False)

    assert rm.native_cccc_home() == wanted_home.resolve()


def test_native_cccc_home_prefers_cccc_home_env_when_native_home_missing(tmp_path, monkeypatch):
    state_file = tmp_path / "bootstrap_state.json"
    stale_home = tmp_path / "stale-home"
    wanted_home = tmp_path / "wanted-home"
    state_file.write_text(
        '{"cccc_home": "%s"}' % str(stale_home).replace("\\", "\\\\"),
        encoding="utf-8",
    )
    monkeypatch.setattr(rm, "BOOTSTRAP_STATE_FILE", state_file)
    monkeypatch.setattr(rm, "DEFAULT_NATIVE_CCCC_HOME", tmp_path / "default-home")
    monkeypatch.delenv("CCCC_NATIVE_HOME", raising=False)
    monkeypatch.setenv("CCCC_HOME", str(wanted_home))

    assert rm.native_cccc_home() == wanted_home.resolve()


def test_send_group_message_uses_daemon_send_op(monkeypatch):
    captured = {}

    monkeypatch.setattr(rm, "ensure_native_daemon_running", lambda: None)

    def fake_call(op, args=None):
        captured["op"] = op
        captured["args"] = dict(args or {})
        return {"event": {"id": "evt_test"}}

    monkeypatch.setattr(rm, "_call_native_daemon", fake_call)

    result = rm.send_group_message(
        "g_main",
        by="primary",
        text="retrieve patient context",
        to=["memory"],
        priority="attention",
        reply_required=True,
        client_id="client-123",
    )

    assert result == {"event": {"id": "evt_test"}}
    assert captured["op"] == "send"
    assert captured["args"] == {
        "group_id": "g_main",
        "text": "retrieve patient context",
        "by": "primary",
        "to": ["memory"],
        "path": "",
        "priority": "attention",
        "reply_required": True,
        "client_id": "client-123",
        "src_group_id": "",
        "src_event_id": "",
    }
