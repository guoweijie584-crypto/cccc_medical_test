import os
import tempfile
import unittest
from unittest.mock import patch


class TestDeliveryStateBehavior(unittest.TestCase):
    def test_should_deliver_message_respects_idle_and_paused_semantics(self) -> None:
        from cccc.daemon.messaging.delivery import should_deliver_message
        from cccc.kernel.group import create_group, set_group_state
        from cccc.kernel.registry import load_registry

        old_home = os.environ.get("CCCC_HOME")
        try:
            with tempfile.TemporaryDirectory() as td:
                os.environ["CCCC_HOME"] = td
                reg = load_registry()
                group = create_group(reg, title="delivery-state")

                # active: allow chat + notify
                self.assertTrue(should_deliver_message(group, "chat.message"))
                self.assertTrue(should_deliver_message(group, "system.notify"))

                # idle: allow chat + notify; block other kinds
                group = set_group_state(group, state="idle")
                self.assertTrue(should_deliver_message(group, "chat.message"))
                self.assertTrue(should_deliver_message(group, "system.notify"))
                self.assertFalse(should_deliver_message(group, "chat.ack"))

                # paused: block all PTY delivery
                group = set_group_state(group, state="paused")
                self.assertFalse(should_deliver_message(group, "chat.message"))
                self.assertFalse(should_deliver_message(group, "system.notify"))
        finally:
            if old_home is None:
                os.environ.pop("CCCC_HOME", None)
            else:
                os.environ["CCCC_HOME"] = old_home

    def test_flush_pending_messages_schedules_fast_retry_when_pty_submit_fails(self) -> None:
        from cccc.daemon.messaging import delivery as mod

        class _Group:
            group_id = "g1"
            doc = {"state": "active", "delivery": {}}

        group = _Group()
        msg = mod.PendingMessage(
            event_id="e1",
            by="primary",
            to=["memory"],
            text="memory consult",
            ts="2026-03-26T00:00:00Z",
            kind="chat.message",
        )

        with (
            patch.object(mod.THROTTLE, "should_deliver", return_value=True),
            patch.object(mod.THROTTLE, "take_pending", return_value=[msg]),
            patch.object(mod.THROTTLE, "requeue_front") as requeue_mock,
            patch.object(mod, "find_actor", return_value={"id": "memory", "runner": "pty"}),
            patch.object(mod, "should_deliver_message", return_value=True),
            patch.object(mod, "is_preamble_sent", return_value=True),
            patch.object(mod, "render_batched_messages", return_value="rendered"),
            patch.object(mod, "pty_submit_text", return_value=False),
            patch.object(mod, "_schedule_retry_flush") as retry_mock,
        ):
            delivered = mod.flush_pending_messages(group, actor_id="memory")

        self.assertFalse(delivered)
        requeue_mock.assert_called_once()
        retry_mock.assert_called_once_with(group, actor_id="memory")


if __name__ == "__main__":
    unittest.main()
