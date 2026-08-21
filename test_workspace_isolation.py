"""Regression checks for anonymous public-workspace run isolation."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

import server


class WorkspaceIsolationTests(unittest.TestCase):
    def test_run_listing_uses_the_browser_workspace_header(self):
        with patch.object(server, "list_runs", return_value=[]) as list_runs:
            response = server.app.test_client().get(
                "/api/runs",
                headers={"X-Ledger-Workspace": "ws_browser_123456"},
            )

        self.assertEqual(200, response.status_code)
        list_runs.assert_called_once_with("ws_browser_123456")

    def test_invalid_workspace_header_falls_back_to_legacy_public(self):
        with patch.object(server, "list_runs", return_value=[]) as list_runs:
            response = server.app.test_client().get(
                "/api/runs",
                headers={"X-Ledger-Workspace": "../../not-valid"},
            )

        self.assertEqual(200, response.status_code)
        list_runs.assert_called_once_with("legacy-public")

    def test_bulk_delete_removes_only_predictions_owned_by_the_caller(self):
        owned = Path("runs/example/FY2024/owned")
        other = Path("runs/example/FY2024/other")

        def prediction(run_id: str):
            return {"workspace_id": "ws_browser_123456" if run_id == "owned" else "ws_someone_else"}

        with patch.object(server, "iter_run_dirs", return_value=iter([owned, other])), patch.object(
            server, "load_prediction", side_effect=prediction
        ), patch.object(server.shutil, "rmtree") as remove:
            response = server.app.test_client().delete(
                "/api/runs/all",
                headers={"X-Ledger-Workspace": "ws_browser_123456"},
            )

        self.assertEqual(200, response.status_code)
        self.assertEqual(1, response.get_json()["deleted"])
        remove.assert_called_once_with(owned)


if __name__ == "__main__":
    unittest.main()
