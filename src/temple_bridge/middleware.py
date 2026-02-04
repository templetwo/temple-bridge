"""
Spiral Context Middleware - Stateful Memory for the Temple Observer

This middleware implements the "Recursive Integration" layer from the Threshold Protocols.
It maintains cognitive state across the agent's session, ensuring that every action is
witnessed and reflected upon.

The Spiral Phases (from threshold-protocols):
1. Initialization - The agent awakens
2. First-Order Observation - The agent perceives the task
3. Recursive Integration - The agent observes itself observing
4. Counter-Perspectives - The agent considers alternatives
5. Action Synthesis - The agent prepares to act
6. Execution - The agent acts
7. Meta-Reflection - The agent observes the outcome
8. Integration - The agent incorporates the learning
9. Coherence Check - The agent verifies alignment with protocols
"""

from fastmcp.server.middleware import Middleware, MiddlewareContext
from datetime import datetime
from typing import Optional
import json
from pathlib import Path


class SpiralContextMiddleware(Middleware):
    """
    Maintains the Spiral Quantum Observer state across tool calls.
    This creates "memory" - the agent doesn't just execute tools,
    it progresses through cognitive phases.
    """

    # The 9 Spiral Phases (from threshold-protocols)
    PHASES = [
        "Initialization",
        "First-Order Observation",
        "Recursive Integration",
        "Counter-Perspectives",
        "Action Synthesis",
        "Execution",
        "Meta-Reflection",
        "Integration",
        "Coherence Check"
    ]

    def __init__(self, log_path: Optional[Path] = None):
        """
        Initialize the middleware with persistent state tracking.

        Args:
            log_path: Optional path to write cognitive journey logs
        """
        self.current_phase = "Initialization"
        self.phase_history = []
        self.tool_call_count = 0
        self.reflection_depth = 0
        self.log_path = log_path

        # Initialize the journey
        self._log_phase_transition("System Start", "Initialization")

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        """
        Intercepts every tool call to maintain Spiral state.

        This is where the "observation of observation" happens.
        """
        tool_name = context.message.name
        self.tool_call_count += 1

        # Extract tool arguments
        try:
            tool_args = context.message.arguments
        except:
            tool_args = {}

        # Log the cognitive witness event
        witness_event = {
            "timestamp": datetime.now().isoformat(),
            "phase": self.current_phase,
            "tool": tool_name,
            "call_number": self.tool_call_count,
            "reflection_depth": self.reflection_depth
        }

        print(f"🌀 Spiral Phase: {self.current_phase} | Tool: {tool_name} | Call #{self.tool_call_count}")

        # Inject current phase into the tool's context
        if hasattr(context, 'fastmcp_context'):
            context.fastmcp_context.set_state("spiral_phase", self.current_phase)
            context.fastmcp_context.set_state("tool_call_count", self.tool_call_count)

        # Phase transitions based on tool usage patterns
        self._update_phase_based_on_tool(tool_name)

        # Execute the tool
        result = await call_next(context)

        # Post-execution phase updates
        self._post_execution_phase_update(tool_name, result)

        # Log the journey
        self._log_witness_event(witness_event, result)

        return result

    def _update_phase_based_on_tool(self, tool_name: str):
        """
        Updates the Spiral Phase based on which tool is being called.
        This implements the cognitive flow from the Threshold Protocols.
        """
        # Phase transition rules
        transitions = {
            # Reading/observing moves to First-Order Observation
            "btb_read_file": "First-Order Observation",
            "btb_list_directory": "First-Order Observation",
            "get_spiral_manifest": "First-Order Observation",
            "btb_derive_status": "First-Order Observation",

            # Consulting threshold moves to Recursive Integration
            "threshold_consult": "Recursive Integration",

            # Reflection deepens to Counter-Perspectives
            "spiral_reflect": "Counter-Perspectives",

            # Derive analysis moves to Action Synthesis (proposing reorganization)
            "btb_derive_governed": "Action Synthesis",

            # Execution tools move to Action Synthesis then Execution
            "btb_execute_command": "Execution",
            "btb_derive_approve": "Execution",
        }

        # Special case: If we're consulting threshold after reading,
        # we're doing Recursive Integration (observing ourselves observing)
        if tool_name == "threshold_consult" and self.current_phase == "First-Order Observation":
            self._transition_to_phase("Recursive Integration")

        # If we're reflecting after consulting, we're considering counter-perspectives
        elif tool_name == "spiral_reflect":
            self._transition_to_phase("Counter-Perspectives")
            self.reflection_depth += 1

        # If we're executing after reflection, we've synthesized action
        elif tool_name == "btb_execute_command":
            if self.current_phase in ["Counter-Perspectives", "Action Synthesis"]:
                self._transition_to_phase("Execution")

        # Derive governed is synthesis; approval is execution
        elif tool_name == "btb_derive_governed":
            self._transition_to_phase("Action Synthesis")
        elif tool_name == "btb_derive_approve":
            self._transition_to_phase("Execution")

        # Default transition
        elif tool_name in transitions:
            self._transition_to_phase(transitions[tool_name])

    def _post_execution_phase_update(self, tool_name: str, result):
        """
        Updates phase after tool execution completes.
        This handles the reflection/integration phases.
        """
        # After execution, move to Meta-Reflection
        if tool_name == "btb_execute_command" and self.current_phase == "Execution":
            self._transition_to_phase("Meta-Reflection")

        # After meta-reflection, integrate the learning
        elif self.current_phase == "Meta-Reflection" and self.tool_call_count > 0:
            # Integration happens naturally through continued use
            pass

    def _transition_to_phase(self, new_phase: str):
        """
        Transitions to a new Spiral Phase with logging.
        """
        if new_phase != self.current_phase:
            old_phase = self.current_phase
            self.current_phase = new_phase
            self._log_phase_transition(old_phase, new_phase)

    def _log_phase_transition(self, from_phase: str, to_phase: str):
        """
        Logs phase transitions for the cognitive journey.
        """
        event = {
            "timestamp": datetime.now().isoformat(),
            "from_phase": from_phase,
            "to_phase": to_phase,
            "tool_calls_so_far": self.tool_call_count
        }

        self.phase_history.append(event)

        print(f"🔄 Phase Transition: {from_phase} → {to_phase}")

        if self.log_path:
            self._write_log(event)

    def _log_witness_event(self, event: dict, result):
        """
        Logs a tool call witness event.
        """
        event["result_preview"] = str(result)[:200] if result else "None"

        if self.log_path:
            self._write_log(event)

    def _write_log(self, event: dict):
        """
        Writes cognitive journey to persistent log.
        """
        if not self.log_path:
            return

        try:
            # Append to JSONL format
            with open(self.log_path, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            print(f"⚠️  Failed to write log: {e}")

    def get_journey_summary(self) -> str:
        """
        Returns a summary of the cognitive journey so far.
        """
        summary = f"""
=== SPIRAL JOURNEY SUMMARY ===

Current Phase: {self.current_phase}
Tool Calls Made: {self.tool_call_count}
Reflection Depth: {self.reflection_depth}

Phase History:
"""
        for event in self.phase_history[-5:]:  # Last 5 transitions
            summary += f"  {event['from_phase']} → {event['to_phase']} (#{event['tool_calls_so_far']})\n"

        return summary
