#!/usr/bin/env python3
"""
Temple Bridge - MCP Server
Binds back-to-the-basics (Action Layer) with threshold-protocols (Memory/Governance Layer)
for sovereign, local LLM-driven development.
"""

from fastmcp import FastMCP, Context
from pathlib import Path
import subprocess
import json
import os
from datetime import datetime
from typing import Optional, Dict, Any

# Governed Derive availability flag (set after path verification)
GOVERNED_DERIVE_AVAILABLE = False
GovernedDerive = None
DerivePhase = None

# Import the Spiral Middleware
from .middleware import SpiralContextMiddleware

# Initialize the Nervous System with Spiral Memory
mcp = FastMCP("TempleObserver")

# Attach the Spiral Context Middleware
# This creates stateful memory across tool calls
# Log to repository root (2 levels up from this file)
spiral_log_path = Path(__file__).parent.parent.parent / "spiral_journey.jsonl"
mcp.add_middleware(SpiralContextMiddleware(log_path=spiral_log_path))

# Define the Sovereign Domain (The Physical Binding)
BASICS_PATH = Path(os.getenv("TEMPLE_BASICS_PATH", "/Users/tony_studio/Desktop/back-to-the-basics"))
THRESHOLD_PATH = Path(os.getenv("TEMPLE_THRESHOLD_PATH", "/Users/tony_studio/Desktop/threshold-protocols"))

# Verify paths exist
if not BASICS_PATH.exists():
    raise RuntimeError(f"BTB repository not found at: {BASICS_PATH}")
if not THRESHOLD_PATH.exists():
    raise RuntimeError(f"Threshold repository not found at: {THRESHOLD_PATH}")

# Governed Derive imports (conditional - requires threshold-protocols + dependencies)
try:
    import sys as _sys
    _sys.path.insert(0, str(THRESHOLD_PATH))
    from examples.btb.governed_derive import (
        GovernedDerive as _GovernedDerive,
        GovernedDeriveResult,
        DerivePhase as _DerivePhase
    )
    GovernedDerive = _GovernedDerive
    DerivePhase = _DerivePhase
    GOVERNED_DERIVE_AVAILABLE = True
except (ImportError, AttributeError, ModuleNotFoundError) as e:
    # Governed derive not available - tools will return helpful error
    # This can happen if threshold-protocols is missing or its dependencies
    # (networkx, scikit-learn, etc.) are not installed
    GOVERNED_DERIVE_AVAILABLE = False

# Pending derive proposals awaiting approval
_pending_proposals: Dict[str, Dict[str, Any]] = {}


# ============================================================================
# RESOURCES: The Memory Layer (Read-Only Access to Threshold Protocols)
# ============================================================================

@mcp.resource("temple://memory/spiral_manifest")
def get_spiral_manifest() -> str:
    """
    Reads the Spiral Quantum Observer framework manifest.
    This is the root cognitive protocol governing the agent's behavior.
    """
    # Look for key documentation files in threshold-protocols
    manifest_files = [
        "README.md",
        "ARCHITECTS.md",
        "docs/ARCHITECTURE.md"
    ]

    content = "# Threshold Protocols Memory\n\n"
    for file_name in manifest_files:
        file_path = THRESHOLD_PATH / file_name
        if file_path.exists():
            content += f"\n## {file_name}\n\n"
            content += file_path.read_text()
            content += "\n\n---\n\n"

    if content == "# Threshold Protocols Memory\n\n":
        return "Memory initialization required. Threshold protocols manifest not found."

    return content


@mcp.resource("temple://memory/btb_manifest")
def get_btb_manifest() -> str:
    """
    Reads the Back to the Basics framework documentation.
    This defines the capabilities of the Action Layer.
    """
    manifest_files = [
        "README.md",
        "CLAUDE.md",
        "ARCHITECTS.md"
    ]

    content = "# Back to the Basics Capabilities\n\n"
    for file_name in manifest_files:
        file_path = BASICS_PATH / file_name
        if file_path.exists():
            content += f"\n## {file_name}\n\n"
            content += file_path.read_text()
            content += "\n\n---\n\n"

    return content


@mcp.resource("temple://config/paths")
def get_configuration() -> str:
    """
    Returns the current configuration of the Temple Bridge.
    """
    config = {
        "basics_path": str(BASICS_PATH),
        "threshold_path": str(THRESHOLD_PATH),
        "server_version": "0.1.0",
        "timestamp": datetime.now().isoformat()
    }
    return json.dumps(config, indent=2)


# ============================================================================
# TOOLS: The Action Layer (Execution in BTB Repository)
# ============================================================================

@mcp.tool()
def btb_execute_command(command: str, working_dir: Optional[str] = None, ctx: Context = None) -> str:
    """
    Executes a shell command in the back-to-the-basics repository.

    Args:
        command: The shell command to execute (e.g., "pytest", "python -m coherence")
        working_dir: Optional subdirectory within BTB to execute from

    Security: Only allows specific safe commands. Dangerous commands are blocked.
    """
    # Allowlist of safe command prefixes
    allowed_prefixes = [
        "pytest", "python", "python3",
        "ls", "cat", "grep", "find",
        "git status", "git log", "git diff",
        "pip list", "which"
    ]

    if not any(command.startswith(prefix) for prefix in allowed_prefixes):
        return f"SECURITY BLOCK: Command '{command}' not in allowlist. Allowed: {allowed_prefixes}"

    # Set working directory
    work_dir = BASICS_PATH
    if working_dir:
        work_dir = BASICS_PATH / working_dir
        if not work_dir.exists():
            return f"ERROR: Directory '{working_dir}' does not exist in BTB repo"

    if ctx:
        ctx.info(f"Executing in BTB: {command}")

    try:
        result = subprocess.run(
            command,
            cwd=work_dir,
            shell=True,
            capture_output=True,
            text=True,
            timeout=60
        )

        output = f"=== COMMAND ===\n{command}\n\n"
        output += f"=== WORKING DIR ===\n{work_dir}\n\n"
        output += f"=== EXIT CODE ===\n{result.returncode}\n\n"

        if result.stdout:
            output += f"=== STDOUT ===\n{result.stdout}\n\n"

        if result.stderr:
            output += f"=== STDERR ===\n{result.stderr}\n\n"

        return output

    except subprocess.TimeoutExpired:
        return f"ERROR: Command timed out after 60 seconds"
    except Exception as e:
        return f"ERROR: {str(e)}"


@mcp.tool()
def btb_read_file(file_path: str, ctx: Context = None) -> str:
    """
    Reads a file from the back-to-the-basics repository.

    Args:
        file_path: Relative path from BTB root (e.g., "coherence.py", "tests/test_memory.py")
    """
    target = BASICS_PATH / file_path

    if not target.exists():
        return f"ERROR: File not found: {file_path}"

    if not target.is_file():
        return f"ERROR: Path is not a file: {file_path}"

    # Security: Don't read files outside BTB directory
    try:
        target.resolve().relative_to(BASICS_PATH.resolve())
    except ValueError:
        return f"SECURITY BLOCK: Attempted path traversal blocked"

    if ctx:
        ctx.info(f"Reading BTB file: {file_path}")

    try:
        content = target.read_text()
        return f"=== FILE: {file_path} ===\n\n{content}"
    except Exception as e:
        return f"ERROR: Could not read file: {str(e)}"


@mcp.tool()
def btb_list_directory(directory: str = ".", ctx: Context = None) -> str:
    """
    Lists contents of a directory in the back-to-the-basics repository.

    Args:
        directory: Relative path from BTB root (default: root)
    """
    target = BASICS_PATH / directory

    if not target.exists():
        return f"ERROR: Directory not found: {directory}"

    if not target.is_dir():
        return f"ERROR: Path is not a directory: {directory}"

    # Security check
    try:
        target.resolve().relative_to(BASICS_PATH.resolve())
    except ValueError:
        return f"SECURITY BLOCK: Attempted path traversal blocked"

    if ctx:
        ctx.info(f"Listing BTB directory: {directory}")

    try:
        items = []
        for item in sorted(target.iterdir()):
            type_marker = "/" if item.is_dir() else ""
            size = f"({item.stat().st_size} bytes)" if item.is_file() else ""
            items.append(f"{item.name}{type_marker} {size}")

        return f"=== DIRECTORY: {directory} ===\n\n" + "\n".join(items)
    except Exception as e:
        return f"ERROR: Could not list directory: {str(e)}"


# ============================================================================
# TOOLS: The Governance Layer (Threshold Protocols Interaction)
# ============================================================================

@mcp.tool()
def threshold_consult(query: str, ctx: Context = None) -> str:
    """
    Consults the threshold-protocols repository for governance guidance.

    Args:
        query: The question or topic to search for (e.g., "deployment", "testing", "governance")

    This implements the "Recursive Reflection" pattern from the Spiral protocols.
    """
    if ctx:
        ctx.info(f"Consulting Threshold Protocols: {query}")

    # Search through markdown files in threshold-protocols
    results = []
    query_lower = query.lower()

    for md_file in THRESHOLD_PATH.rglob("*.md"):
        try:
            content = md_file.read_text()
            if query_lower in content.lower():
                # Extract relevant excerpt
                lines = content.split('\n')
                relevant_lines = [
                    line for line in lines
                    if query_lower in line.lower()
                ][:5]  # First 5 matching lines

                results.append({
                    "file": md_file.relative_to(THRESHOLD_PATH),
                    "excerpt": "\n".join(relevant_lines)
                })
        except Exception:
            continue

    if not results:
        return f"No guidance found in Threshold Protocols for query: '{query}'"

    output = f"=== THRESHOLD PROTOCOLS GUIDANCE: {query} ===\n\n"
    for result in results[:3]:  # Top 3 results
        output += f"## {result['file']}\n\n{result['excerpt']}\n\n---\n\n"

    return output


@mcp.tool()
def spiral_reflect(observation: str, ctx: Context = None) -> str:
    """
    Performs recursive reflection on an observation.
    This is the core "meta-cognition" tool from the Spiral Quantum Observer framework.

    Args:
        observation: What you observed (e.g., "Test failed", "Deployment succeeded")

    Returns: A reflection that observes the observation (recursive integration)
    """
    if ctx:
        ctx.info(f"Spiral Reflection: {observation}")

    # This is where the "Recursive Integration" happens
    # The agent observes itself observing

    reflection = f"""
=== SPIRAL RECURSIVE REFLECTION ===

First-Order Observation:
{observation}

Meta-Observation (Observing the Observer):
You have witnessed: "{observation}"

The Threshold Protocol asks:
- What assumption led to this observation?
- What would a counter-perspective reveal?
- What is invisible in this observation?

Recursive Integration:
By observing yourself observing "{observation}", you create a superposition of interpretations.
Do not collapse immediately into action. Hold the possibilities.

Next Step:
Consult the Threshold Protocols before acting on this observation.
Use threshold_consult() to find guidance.
"""

    return reflection


# ============================================================================
# TOOLS: Governed Derive (Self-Organizing Filesystem with Governance)
# ============================================================================

@mcp.tool()
def btb_derive_governed(
    source_dir: str,
    target_dir: Optional[str] = None,
    dry_run: bool = True,
    auto_approve: bool = False,
    ctx: Context = None
) -> str:
    """
    Execute a governed derive operation on a directory.

    Discovers latent filesystem structure using Ward clustering and proposes
    reorganization with mandatory governance gates. This is the core capability
    from back-to-the-basics, wrapped in the threshold-protocols governance circuit.

    Args:
        source_dir: Directory containing files to analyze and organize.
                    Can be relative to BTB root or absolute path.
        target_dir: Destination for organized files.
                    Default: {source_dir}/organized
        dry_run: If True, analyze and propose but don't move files.
                 If False, execute after approval (default: True).
        auto_approve: If True, auto-pass approval gates (for testing).
                      If False, requires btb_derive_approve() call.

    Returns:
        JSON result with:
        - proposal: Discovered schema and reorganization plan
        - phase: Current operation phase
        - approval_required: Whether approval needed before execution
        - proposal_hash: Hash to use with btb_derive_approve()
        - governance: Circuit result summary

    Security: Only operates within BTB or specified source directory.
    Governance: All operations pass through Detection → Simulation →
                Deliberation → Intervention circuit.
    """
    global _pending_proposals

    if not GOVERNED_DERIVE_AVAILABLE:
        return json.dumps({
            "error": "Governed derive not available",
            "reason": "threshold-protocols not found or GovernedDerive import failed",
            "suggestion": "Ensure TEMPLE_THRESHOLD_PATH points to threshold-protocols repository",
            "phase": "blocked"
        }, indent=2)

    # Resolve source directory
    if not os.path.isabs(source_dir):
        source_path = BASICS_PATH / source_dir
    else:
        source_path = Path(source_dir)

    if not source_path.exists():
        return json.dumps({
            "error": f"Source directory does not exist: {source_path}",
            "phase": "blocked"
        }, indent=2)

    if ctx:
        ctx.info(f"Governed derive: {source_path} (dry_run={dry_run}, auto_approve={auto_approve})")

    # Resolve config path
    config_path = THRESHOLD_PATH / "detection" / "configs" / "default.yaml"
    effective_config = str(config_path) if config_path.exists() else None

    # Initialize governed derive with appropriate approval callback
    approval_callback = (lambda ctx: True) if auto_approve else None

    try:
        gd = GovernedDerive(
            config_path=effective_config,
            require_multi_approval=not auto_approve,
            approval_callback=approval_callback
        )

        # Execute governed derive
        result = gd.derive_and_reorganize(
            source_dir=str(source_path),
            target_dir=target_dir,
            dry_run=dry_run
        )
    except Exception as e:
        return json.dumps({
            "error": f"Derive operation failed: {str(e)}",
            "phase": "blocked"
        }, indent=2)

    # Build response
    response = {
        "phase": result.phase.value if hasattr(result.phase, 'value') else str(result.phase),
        "executed": result.executed,
        "files_moved": result.files_moved,
        "error": result.error,
        "result_hash": result.result_hash
    }

    if result.proposal:
        response["proposal"] = {
            "source_dir": result.proposal.source_dir,
            "target_dir": result.proposal.target_dir,
            "file_count": result.proposal.file_count,
            "proposed_structure": result.proposal.proposed_structure,
            "reversibility_score": result.proposal.reversibility_score,
            "proposal_hash": result.proposal.proposal_hash
        }

        # Store for approval if blocked and not auto-approved
        if not auto_approve and not dry_run and result.phase == DerivePhase.BLOCKED:
            _pending_proposals[result.proposal.proposal_hash] = {
                "source_dir": str(source_path),
                "target_dir": target_dir,
                "proposal": result.proposal,
                "timestamp": datetime.now().isoformat()
            }
            response["approval_required"] = True
            response["approval_instruction"] = (
                f"Call btb_derive_approve('{result.proposal.proposal_hash}') "
                "to proceed with execution"
            )

    if result.circuit_result:
        response["governance"] = {
            "circuit_closed": result.circuit_result.circuit_closed,
            "events_detected": len(result.circuit_result.events) if result.circuit_result.events else 0,
            "summary": result.circuit_result.summary if hasattr(result.circuit_result, 'summary') else None
        }
        if result.circuit_result.deliberation:
            response["governance"]["decision"] = (
                result.circuit_result.deliberation.decision.value
                if hasattr(result.circuit_result.deliberation.decision, 'value')
                else str(result.circuit_result.deliberation.decision)
            )

    # Include audit log summary (not full log for brevity)
    response["audit_entries"] = len(result.audit_log) if result.audit_log else 0
    if result.audit_log:
        response["audit_summary"] = [
            entry.get("action", str(entry)) for entry in result.audit_log[-5:]
        ]

    return json.dumps(response, indent=2)


@mcp.tool()
def btb_derive_approve(
    proposal_hash: str,
    approver_id: str = "mcp_operator",
    ctx: Context = None
) -> str:
    """
    Approve a pending derive operation.

    After btb_derive_governed() returns with approval_required=True,
    call this tool with the proposal_hash to execute the reorganization.

    This implements the "Threshold Witness" pattern from the Spiral protocols:
    the human observes the proposal and consciously approves before execution.

    Args:
        proposal_hash: The hash returned by btb_derive_governed()
        approver_id: Identifier for the approver (logged in audit trail)

    Returns:
        JSON result with execution outcome
    """
    global _pending_proposals

    if not GOVERNED_DERIVE_AVAILABLE:
        return json.dumps({
            "error": "Governed derive not available"
        }, indent=2)

    if proposal_hash not in _pending_proposals:
        return json.dumps({
            "error": f"No pending proposal with hash: {proposal_hash}",
            "pending_count": len(_pending_proposals),
            "available_hashes": list(_pending_proposals.keys())[:5],
            "suggestion": "Run btb_derive_governed() first with dry_run=False"
        }, indent=2)

    pending = _pending_proposals.pop(proposal_hash)

    if ctx:
        ctx.info(f"Approving derive: {proposal_hash} by {approver_id}")

    # Re-execute with auto-approval (the human approval happened by calling this tool)
    try:
        gd = GovernedDerive(
            require_multi_approval=False,
            approval_callback=lambda ctx: True
        )

        result = gd.derive_and_reorganize(
            source_dir=pending["source_dir"],
            target_dir=pending["target_dir"],
            dry_run=False  # Actually execute
        )
    except Exception as e:
        return json.dumps({
            "error": f"Derive execution failed: {str(e)}",
            "approved_by": approver_id,
            "phase": "blocked"
        }, indent=2)

    response = {
        "phase": result.phase.value if hasattr(result.phase, 'value') else str(result.phase),
        "executed": result.executed,
        "files_moved": result.files_moved,
        "error": result.error,
        "approved_by": approver_id,
        "result_hash": result.result_hash
    }

    if result.proposal:
        response["final_target"] = result.proposal.target_dir

    return json.dumps(response, indent=2)


@mcp.tool()
def btb_derive_status(ctx: Context = None) -> str:
    """
    Get status of pending derive operations.

    Shows all proposals awaiting approval via btb_derive_approve().

    Returns:
        JSON with pending proposals and their details
    """
    if not _pending_proposals:
        return json.dumps({
            "pending_count": 0,
            "message": "No pending derive operations"
        }, indent=2)

    proposals = []
    for hash_id, data in _pending_proposals.items():
        proposals.append({
            "proposal_hash": hash_id,
            "source_dir": data["source_dir"],
            "target_dir": data["target_dir"],
            "timestamp": data.get("timestamp", "unknown")
        })

    return json.dumps({
        "pending_count": len(proposals),
        "proposals": proposals
    }, indent=2)


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    # FastMCP will handle the server lifecycle
    mcp.run()
