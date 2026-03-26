import os
import tempfile
import unittest


class TestPrimaryMemoryReplyGate(unittest.TestCase):
    def _with_home(self):
        old_home = os.environ.get("CCCC_HOME")
        td_ctx = tempfile.TemporaryDirectory()
        td = td_ctx.__enter__()
        os.environ["CCCC_HOME"] = td

        def cleanup() -> None:
            td_ctx.__exit__(None, None, None)
            if old_home is None:
                os.environ.pop("CCCC_HOME", None)
            else:
                os.environ["CCCC_HOME"] = old_home

        return td, cleanup

    def _call(self, op: str, args: dict):
        from cccc.contracts.v1 import DaemonRequest
        from cccc.daemon.server import handle_request

        return handle_request(DaemonRequest.model_validate({"op": op, "args": args}))

    def _create_medical_group(self, *actor_ids: str) -> str:
        create, _ = self._call("group_create", {"title": "glucose-management-main", "topic": "", "by": "user"})
        self.assertTrue(create.ok, getattr(create, "error", None))
        group_id = str((create.result or {}).get("group_id") or "").strip()
        self.assertTrue(group_id)

        for actor_id in actor_ids:
            add, _ = self._call(
                "actor_add",
                {
                    "group_id": group_id,
                    "by": "user",
                    "actor_id": actor_id,
                    "title": actor_id,
                    "runtime": "codex",
                    "runner": "headless",
                },
            )
            self.assertTrue(add.ok, getattr(add, "error", None))
        return group_id

    def _send_bound_user_message(self, group_id: str) -> str:
        user_send, _ = self._call(
            "send",
            {
                "group_id": group_id,
                "by": "user",
                "to": ["primary"],
                "text": "Need management advice",
                "refs": [
                    {
                        "kind": "text",
                        "title": "medical_context",
                        "medical_context": {
                            "patient_id": "PAT001",
                            "patient_name": "Test",
                            "profile": {"name": "Test", "age": 39},
                        },
                    }
                ],
            },
        )
        self.assertTrue(user_send.ok, getattr(user_send, "error", None))
        user_event = (user_send.result or {}).get("event") if isinstance(user_send.result, dict) else {}
        self.assertIsInstance(user_event, dict)
        assert isinstance(user_event, dict)
        user_event_id = str(user_event.get("id") or "").strip()
        self.assertTrue(user_event_id)
        return user_event_id

    def test_primary_reply_requires_memory_consult_and_reply_for_bound_round(self) -> None:
        _, cleanup = self._with_home()
        try:
            group_id = self._create_medical_group("primary", "memory", "pharmacist", "nutritionist", "doctor")
            user_event_id = self._send_bound_user_message(group_id)

            blocked_without_consult, _ = self._call(
                "reply",
                {
                    "group_id": group_id,
                    "by": "primary",
                    "to": ["user"],
                    "reply_to": user_event_id,
                    "text": "Premature answer",
                },
            )
            self.assertFalse(blocked_without_consult.ok)
            self.assertEqual(getattr(blocked_without_consult.error, "code", ""), "memory_consult_required")

            consult, _ = self._call(
                "send",
                {
                    "group_id": group_id,
                    "by": "primary",
                    "to": ["memory"],
                    "text": "memory consult",
                    "reply_required": True,
                },
            )
            self.assertTrue(consult.ok, getattr(consult, "error", None))
            consult_event = (consult.result or {}).get("event") if isinstance(consult.result, dict) else {}
            self.assertIsInstance(consult_event, dict)
            assert isinstance(consult_event, dict)
            consult_event_id = str(consult_event.get("id") or "").strip()
            self.assertTrue(consult_event_id)

            blocked_without_reply, _ = self._call(
                "reply",
                {
                    "group_id": group_id,
                    "by": "primary",
                    "to": ["user"],
                    "reply_to": user_event_id,
                    "text": "Still premature",
                },
            )
            self.assertFalse(blocked_without_reply.ok)
            self.assertEqual(getattr(blocked_without_reply.error, "code", ""), "memory_reply_required")

            memory_reply, _ = self._call(
                "reply",
                {
                    "group_id": group_id,
                    "by": "memory",
                    "to": ["primary"],
                    "reply_to": consult_event_id,
                    "text": "verified context",
                },
            )
            self.assertTrue(memory_reply.ok, getattr(memory_reply, "error", None))

            specialist_consults: dict[str, str] = {}
            for actor_id in ("pharmacist", "nutritionist", "doctor"):
                consult, _ = self._call(
                    "send",
                    {
                        "group_id": group_id,
                        "by": "primary",
                        "to": [actor_id],
                        "text": f"{actor_id} consult",
                        "reply_required": True,
                    },
                )
                self.assertTrue(consult.ok, getattr(consult, "error", None))
                consult_event = (consult.result or {}).get("event") if isinstance(consult.result, dict) else {}
                self.assertIsInstance(consult_event, dict)
                assert isinstance(consult_event, dict)
                consult_event_id = str(consult_event.get("id") or "").strip()
                self.assertTrue(consult_event_id)
                specialist_consults[actor_id] = consult_event_id

            for actor_id, consult_event_id in specialist_consults.items():
                specialist_reply, _ = self._call(
                    "reply",
                    {
                        "group_id": group_id,
                        "by": actor_id,
                        "to": ["primary"],
                        "reply_to": consult_event_id,
                        "text": f"{actor_id} guidance",
                    },
                )
                self.assertTrue(specialist_reply.ok, getattr(specialist_reply, "error", None))

            allowed_reply, _ = self._call(
                "reply",
                {
                    "group_id": group_id,
                    "by": "primary",
                    "to": ["user"],
                    "reply_to": user_event_id,
                    "text": "Now allowed",
                },
            )
            self.assertTrue(allowed_reply.ok, getattr(allowed_reply, "error", None))
        finally:
            cleanup()

    def test_primary_reply_to_user_requires_specialist_replies_after_memory_reply_for_bound_round(self) -> None:
        _, cleanup = self._with_home()
        try:
            group_id = self._create_medical_group("primary", "memory", "pharmacist", "nutritionist", "doctor")
            user_event_id = self._send_bound_user_message(group_id)

            consult, _ = self._call(
                "send",
                {
                    "group_id": group_id,
                    "by": "primary",
                    "to": ["memory"],
                    "text": "memory consult",
                    "reply_required": True,
                },
            )
            self.assertTrue(consult.ok, getattr(consult, "error", None))
            consult_event = (consult.result or {}).get("event") if isinstance(consult.result, dict) else {}
            self.assertIsInstance(consult_event, dict)
            assert isinstance(consult_event, dict)
            consult_event_id = str(consult_event.get("id") or "").strip()
            self.assertTrue(consult_event_id)

            memory_reply, _ = self._call(
                "reply",
                {
                    "group_id": group_id,
                    "by": "memory",
                    "to": ["primary"],
                    "reply_to": consult_event_id,
                    "text": "verified context",
                },
            )
            self.assertTrue(memory_reply.ok, getattr(memory_reply, "error", None))

            blocked_without_specialists, _ = self._call(
                "reply",
                {
                    "group_id": group_id,
                    "by": "primary",
                    "to": ["user"],
                    "reply_to": user_event_id,
                    "text": "Still premature after memory",
                },
            )
            self.assertFalse(blocked_without_specialists.ok)
            self.assertEqual(
                getattr(blocked_without_specialists.error, "code", ""),
                "specialist_replies_required",
            )
        finally:
            cleanup()

    def test_primary_send_to_user_requires_memory_consult_for_bound_round(self) -> None:
        _, cleanup = self._with_home()
        try:
            group_id = self._create_medical_group("primary", "memory")
            _ = self._send_bound_user_message(group_id)

            blocked_send, _ = self._call(
                "send",
                {
                    "group_id": group_id,
                    "by": "primary",
                    "to": ["user"],
                    "text": "Premature send-path answer",
                },
            )
            self.assertFalse(blocked_send.ok)
            self.assertEqual(getattr(blocked_send.error, "code", ""), "memory_consult_required")
        finally:
            cleanup()

    def test_primary_send_to_user_requires_memory_reply_for_bound_round(self) -> None:
        _, cleanup = self._with_home()
        try:
            group_id = self._create_medical_group("primary", "memory", "pharmacist", "nutritionist", "doctor")
            _ = self._send_bound_user_message(group_id)

            consult, _ = self._call(
                "send",
                {
                    "group_id": group_id,
                    "by": "primary",
                    "to": ["memory"],
                    "text": "memory consult",
                    "reply_required": True,
                },
            )
            self.assertTrue(consult.ok, getattr(consult, "error", None))

            blocked_send, _ = self._call(
                "send",
                {
                    "group_id": group_id,
                    "by": "primary",
                    "to": ["user"],
                    "text": "Still premature send-path answer",
                },
            )
            self.assertFalse(blocked_send.ok)
            self.assertEqual(getattr(blocked_send.error, "code", ""), "memory_reply_required")
        finally:
            cleanup()

    def test_primary_send_to_user_requires_specialist_replies_after_memory_reply_for_bound_round(self) -> None:
        _, cleanup = self._with_home()
        try:
            group_id = self._create_medical_group("primary", "memory", "pharmacist", "nutritionist", "doctor")
            _ = self._send_bound_user_message(group_id)

            consult, _ = self._call(
                "send",
                {
                    "group_id": group_id,
                    "by": "primary",
                    "to": ["memory"],
                    "text": "memory consult",
                    "reply_required": True,
                },
            )
            self.assertTrue(consult.ok, getattr(consult, "error", None))
            consult_event = (consult.result or {}).get("event") if isinstance(consult.result, dict) else {}
            self.assertIsInstance(consult_event, dict)
            assert isinstance(consult_event, dict)
            consult_event_id = str(consult_event.get("id") or "").strip()
            self.assertTrue(consult_event_id)

            memory_reply, _ = self._call(
                "reply",
                {
                    "group_id": group_id,
                    "by": "memory",
                    "to": ["primary"],
                    "reply_to": consult_event_id,
                    "text": "verified context",
                },
            )
            self.assertTrue(memory_reply.ok, getattr(memory_reply, "error", None))

            blocked_send, _ = self._call(
                "send",
                {
                    "group_id": group_id,
                    "by": "primary",
                    "to": ["user"],
                    "text": "premature user closeout without specialists",
                },
            )
            self.assertFalse(blocked_send.ok)
            self.assertEqual(getattr(blocked_send.error, "code", ""), "specialist_replies_required")
        finally:
            cleanup()

    def test_primary_send_to_specialist_requires_real_memory_reply_for_bound_round(self) -> None:
        _, cleanup = self._with_home()
        try:
            group_id = self._create_medical_group("primary", "memory", "pharmacist")
            _ = self._send_bound_user_message(group_id)

            blocked_without_consult, _ = self._call(
                "send",
                {
                    "group_id": group_id,
                    "by": "primary",
                    "to": ["pharmacist"],
                    "text": "premature specialist consult",
                },
            )
            self.assertFalse(blocked_without_consult.ok)
            self.assertEqual(getattr(blocked_without_consult.error, "code", ""), "memory_consult_required")

            consult, _ = self._call(
                "send",
                {
                    "group_id": group_id,
                    "by": "primary",
                    "to": ["memory"],
                    "text": "memory consult",
                    "reply_required": True,
                },
            )
            self.assertTrue(consult.ok, getattr(consult, "error", None))

            blocked_without_reply, _ = self._call(
                "send",
                {
                    "group_id": group_id,
                    "by": "primary",
                    "to": ["pharmacist"],
                    "text": "still premature specialist consult",
                },
            )
            self.assertFalse(blocked_without_reply.ok)
            self.assertEqual(getattr(blocked_without_reply.error, "code", ""), "memory_reply_required")
        finally:
            cleanup()

    def test_primary_memory_consult_is_forced_reply_required_for_bound_round(self) -> None:
        _, cleanup = self._with_home()
        try:
            group_id = self._create_medical_group("primary", "memory")
            _ = self._send_bound_user_message(group_id)

            consult, _ = self._call(
                "send",
                {
                    "group_id": group_id,
                    "by": "primary",
                    "to": ["memory"],
                    "text": "memory consult without explicit reply_required",
                    "reply_required": False,
                },
            )
            self.assertTrue(consult.ok, getattr(consult, "error", None))
            consult_event = (consult.result or {}).get("event") if isinstance(consult.result, dict) else {}
            self.assertIsInstance(consult_event, dict)
            assert isinstance(consult_event, dict)
            data = consult_event.get("data") if isinstance(consult_event.get("data"), dict) else {}
            self.assertIsInstance(data, dict)
            assert isinstance(data, dict)
            self.assertTrue(bool(data.get("reply_required")))
        finally:
            cleanup()


if __name__ == "__main__":
    unittest.main()
