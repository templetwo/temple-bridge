#!/usr/bin/env python3
"""
Tests for btb_derive_governed MCP tools.

These tests verify the governed derive capability is properly
wired through the Temple Bridge MCP server.
"""

import sys
import json
import tempfile
import shutil
import pytest
from pathlib import Path

# Add the src directory to path for package imports
src_path = str(Path(__file__).parent.parent / "src")
if src_path not in sys.path:
    sys.path.insert(0, src_path)


class TestGovernedDeriveAvailability:
    """Tests for governed derive availability detection."""

    def test_import_server(self):
        """Server module can be imported."""
        from temple_bridge import server
        assert hasattr(server, 'GOVERNED_DERIVE_AVAILABLE')

    def test_pending_proposals_initialized(self):
        """Pending proposals dictionary exists."""
        from temple_bridge import server
        assert hasattr(server, '_pending_proposals')
        assert isinstance(server._pending_proposals, dict)

    def test_derive_tools_exist(self):
        """All three derive tools are defined."""
        from temple_bridge import server
        assert hasattr(server, 'btb_derive_governed')
        assert hasattr(server, 'btb_derive_approve')
        assert hasattr(server, 'btb_derive_status')


class TestDeriveStatus:
    """Tests for btb_derive_status tool."""

    def test_empty_status(self):
        """Returns empty when no pending proposals."""
        from temple_bridge import server
        server._pending_proposals.clear()

        # FastMCP wraps functions - access the underlying fn
        result = server.btb_derive_status.fn()
        data = json.loads(result)

        assert data["pending_count"] == 0
        assert "No pending" in data.get("message", "")

    def test_status_with_pending(self):
        """Returns pending proposals when they exist."""
        from temple_bridge import server
        server._pending_proposals.clear()

        # Add a mock pending proposal
        server._pending_proposals["test_hash_123"] = {
            "source_dir": "/test/source",
            "target_dir": "/test/target",
            "timestamp": "2026-01-15T12:00:00"
        }

        result = server.btb_derive_status.fn()
        data = json.loads(result)

        assert data["pending_count"] == 1
        assert len(data["proposals"]) == 1
        assert data["proposals"][0]["proposal_hash"] == "test_hash_123"

        # Cleanup
        server._pending_proposals.clear()


class TestGovernedDeriveWithoutThreshold:
    """Tests when threshold-protocols is not available."""

    def test_graceful_degradation(self):
        """Tool returns helpful error when governed derive unavailable."""
        from temple_bridge import server

        # Temporarily disable governed derive
        original_value = server.GOVERNED_DERIVE_AVAILABLE
        server.GOVERNED_DERIVE_AVAILABLE = False

        try:
            result = server.btb_derive_governed.fn(source_dir="/nonexistent")
            data = json.loads(result)

            assert "error" in data
            assert "not available" in data["error"].lower()
            assert "suggestion" in data
        finally:
            # Restore original value
            server.GOVERNED_DERIVE_AVAILABLE = original_value


class TestGovernedDeriveApprove:
    """Tests for btb_derive_approve tool."""

    def test_approve_nonexistent_hash(self):
        """Returns error for unknown proposal hash."""
        from temple_bridge import server

        if not server.GOVERNED_DERIVE_AVAILABLE:
            pytest.skip("Governed derive not available - skipping approval tests")

        server._pending_proposals.clear()

        result = server.btb_derive_approve.fn(proposal_hash="nonexistent_hash")
        data = json.loads(result)

        assert "error" in data
        assert "No pending proposal" in data["error"]

    def test_approve_lists_available_hashes(self):
        """Error includes available hashes for guidance."""
        from temple_bridge import server

        if not server.GOVERNED_DERIVE_AVAILABLE:
            pytest.skip("Governed derive not available - skipping approval tests")

        server._pending_proposals.clear()

        # Add some mock proposals
        server._pending_proposals["hash_aaa"] = {"source_dir": "/a"}
        server._pending_proposals["hash_bbb"] = {"source_dir": "/b"}

        result = server.btb_derive_approve.fn(proposal_hash="wrong_hash")
        data = json.loads(result)

        assert "available_hashes" in data
        assert "hash_aaa" in data["available_hashes"]

        # Cleanup
        server._pending_proposals.clear()


@pytest.mark.skipif(
    not Path("/Users/vaquez/threshold-protocols").exists(),
    reason="threshold-protocols not found at expected path"
)
class TestGovernedDeriveIntegration:
    """Integration tests requiring threshold-protocols."""

    @pytest.fixture
    def temp_chaos_dir(self):
        """Create temporary directory with test files."""
        temp_dir = tempfile.mkdtemp(prefix="derive_test_")
        for i in range(20):
            region = ["us-east", "us-west"][i % 2]
            sensor = ["lidar", "thermal"][i % 2]
            (Path(temp_dir) / f"data_{region}_{sensor}_{i}.txt").write_text(f"Data {i}")
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    def test_dry_run_returns_proposal(self, temp_chaos_dir):
        """Dry run returns proposal without moving files."""
        from temple_bridge import server

        if not server.GOVERNED_DERIVE_AVAILABLE:
            pytest.skip("Governed derive not available")

        result_json = server.btb_derive_governed(
            source_dir=temp_chaos_dir,
            dry_run=True,
            auto_approve=True
        )
        result = json.loads(result_json)

        # Should complete without error
        assert result.get("error") is None or result["error"] is None
        assert "proposal" in result or result["phase"] in ["completed", "blocked"]

    def test_nonexistent_source_returns_error(self):
        """Returns error for missing source directory."""
        from temple_bridge import server

        if not server.GOVERNED_DERIVE_AVAILABLE:
            pytest.skip("Governed derive not available")

        result = server.btb_derive_governed(
            source_dir="/absolutely/nonexistent/path/12345",
            dry_run=True
        )
        data = json.loads(result)

        assert "error" in data
        assert data["phase"] == "blocked"


class TestMiddlewarePhaseTracking:
    """Tests for middleware phase transitions with derive tools."""

    def test_derive_tools_in_transitions(self):
        """Derive tools are registered in phase transitions."""
        from temple_bridge.middleware import SpiralContextMiddleware

        middleware = SpiralContextMiddleware()

        # Verify derive tools trigger phase updates
        # btb_derive_governed should transition to Action Synthesis
        middleware._update_phase_based_on_tool("btb_derive_governed")
        assert middleware.current_phase == "Action Synthesis"

        # btb_derive_approve should transition to Execution
        middleware._update_phase_based_on_tool("btb_derive_approve")
        assert middleware.current_phase == "Execution"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
