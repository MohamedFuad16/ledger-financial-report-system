import json
import os
import unittest
from unittest.mock import patch

import traffic
import server


class TrafficTests(unittest.TestCase):
    def test_record_visit_deduplicates_and_never_serializes_credentials(self):
        payload = {
            "session_id": "test-session-0123456789",
            "path": "/#strategy2",
            "referrer": "https://example.com/",
            "locale": "ja-JP",
            "timezone": "Asia/Tokyo",
            "viewport": "1440x900",
            "user_agent": "Test Browser",
        }
        with patch.dict(os.environ, {
            "UPSTASH_REDIS_REST_URL": "https://redis.example",
            "UPSTASH_REDIS_REST_TOKEN": "secret-token",
            "TRAFFIC_NOTIFY_EMAIL": "owner@example.com",
        }, clear=False), patch.object(traffic, "_upstash_command", return_value="OK"), patch.object(
            traffic, "_upstash_pipeline", return_value=[1, "OK", 1, 1]
        ) as pipeline, patch.object(traffic, "_notify_async") as notify:
            result = traffic.record_visit(payload, remote_ip="203.0.113.9")

        self.assertEqual(result, {"recorded": True, "duplicate": False, "email_queued": True})
        stored_event = json.loads(pipeline.call_args.args[0][0][2])
        self.assertEqual(stored_event["path"], "/#strategy2")
        self.assertEqual(stored_event["ip"], "203.0.113.9")
        self.assertNotIn("secret-token", json.dumps(stored_event))
        notify.assert_called_once()

    def test_record_visit_ignores_repeat_session(self):
        with patch.object(traffic, "_upstash_command", return_value=None), patch.object(
            traffic, "_upstash_pipeline"
        ) as pipeline:
            result = traffic.record_visit({"session_id": "repeat-session-012345"}, remote_ip="198.51.100.7")

        self.assertEqual(result, {"recorded": False, "duplicate": True, "email_queued": False})
        pipeline.assert_not_called()

    def test_traffic_route_accepts_the_public_application_without_admin_token(self):
        with patch.dict(os.environ, {
            "CORS_ALLOWED_ORIGINS": "https://assignment.mohamedfuad.com",
            "LEDGER_ADMIN_TOKEN": "private-admin-token",
        }, clear=False), patch.object(server, "record_visit", return_value={
            "recorded": True,
            "duplicate": False,
            "email_queued": True,
        }) as recorder:
            response = server.app.test_client().post(
                "/api/traffic",
                headers={"Origin": "https://assignment.mohamedfuad.com"},
                json={"session_id": "browser-session-012345"},
            )

        self.assertEqual(response.status_code, 202)
        self.assertTrue(response.get_json()["recorded"])
        recorder.assert_called_once()

    def test_traffic_route_rejects_an_unapproved_origin(self):
        with patch.dict(os.environ, {
            "CORS_ALLOWED_ORIGINS": "https://assignment.mohamedfuad.com",
        }, clear=False), patch.object(server, "record_visit") as recorder:
            response = server.app.test_client().post(
                "/api/traffic",
                headers={"Origin": "https://untrusted.example"},
                json={"session_id": "browser-session-012345"},
            )

        self.assertEqual(response.status_code, 403)
        recorder.assert_not_called()


if __name__ == "__main__":
    unittest.main()
