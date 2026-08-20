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

    def test_mutating_routes_do_not_require_a_backend_access_token(self):
        response = server.app.test_client().post(
            "/api/corpus/stage",
            headers={"Origin": "https://assignment.mohamedfuad.com"},
            json={"document_ids": []},
        )

        self.assertNotEqual(response.status_code, 401)
        self.assertNotIn("backend access token", response.get_data(as_text=True).lower())

    def test_visit_email_contains_a_readable_html_table(self):
        event = {
            "event_id": "event-123",
            "accessed_at": "2026-08-20T16:00:00+00:00",
            "path": "/#strategy2",
            "referrer": "https://example.com/?a=<unsafe>",
            "ip": "203.0.113.9",
            "locale": "ja-JP",
            "timezone": "Asia/Tokyo",
            "viewport": "390x844",
            "user_agent": "Test Browser",
        }
        with patch.dict(os.environ, {
            "TRAFFIC_NOTIFY_EMAIL": "owner@example.com",
            "TRAFFIC_FROM_EMAIL": "owner@example.com",
            "AWS_REGION": "ap-northeast-1",
        }, clear=False), patch.object(traffic, "_ses_client") as ses_client:
            self.assertTrue(traffic._email_visit(event))

        content = ses_client.return_value.send_email.call_args.kwargs["Content"]["Simple"]
        html_body = content["Body"]["Html"]["Data"]
        self.assertIn("<table", html_body)
        self.assertIn("Access time", html_body)
        self.assertIn("ledger-icon.png", html_body)
        self.assertNotIn("<unsafe>", html_body)
        self.assertIn("&lt;unsafe&gt;", html_body)

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
