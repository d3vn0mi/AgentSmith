"""Main agent loop - Plan → Execute → Observe → Reason → Repeat."""

from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

from agent_smith.core.config import Config
from agent_smith.core.evidence import Credential, EvidenceStore, Port, Vulnerability
from agent_smith.core.mission import HistoryEntry, Mission, Phase
from agent_smith.events import EventBus
from agent_smith.llm.base import LLMProvider, LLMResponse, ToolDefinition
from agent_smith.tools.base import ToolRegistry
from agent_smith.transport.ssh import SSHConnection

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are AgentSmith, an autonomous penetration testing agent. You are conducting \
an authorized security assessment of a target machine.

TARGET: {target_ip}

CURRENT PHASE: {phase}
OBJECTIVE: {objective}

METHODOLOGY:
1. RECON: Port scan, service identification
2. ENUMERATION: Deep service probing, directory busting, version checks
3. EXPLOITATION: Exploit vulnerabilities, get initial access as a user
4. PRIVESC: Escalate privileges to root
5. POST_EXPLOIT: Capture flags, document attack path

RULES:
- Always explain your reasoning before choosing a tool
- After each tool result, analyze what you learned
- If a tool fails, try a different approach
- Look for user.txt on user Desktop directories and root.txt in admin/root directories
- When you find a flag file, read it immediately
- Be systematic: don't skip steps
- If stuck in a phase for too long, try creative approaches

{evidence}

RECENT HISTORY (last actions and results):
{history}

Choose the next tool to execute. Explain your reasoning first, then call exactly one tool.
"""


class AgentSmith:
    """The autonomous pentesting agent."""

    def __init__(
        self,
        config: Config,
        llm: LLMProvider,
        ssh: SSHConnection,
        tools: ToolRegistry,
        events: EventBus,
    ) -> None:
        self.config = config
        self.llm = llm
        self.ssh = ssh
        self.tools = tools
        self.events = events
        self.evidence = EvidenceStore()
        self.mission = Mission(
            target_ip=config.target.ip,
            max_iterations=config.agent.max_iterations,
        )

    async def run(self) -> None:
        """Main agent loop."""
        logger.info("AgentSmith starting mission against %s", self.mission.target_ip)
        await self.events.emit("mission_started", {
            "target_ip": self.mission.target_ip,
            "phase": self.mission.current_phase.value,
        })

        try:
            while not self.mission.is_complete() and not self.mission.is_over_limit():
                # Check pause state
                while self.mission.paused:
                    await asyncio.sleep(0.5)

                await self._step()

                # Check if both flags found
                if self.evidence.is_complete:
                    self.mission.set_phase(Phase.COMPLETE)
                    await self.events.emit("mission_complete", {
                        "flags": self.evidence.flags,
                        "iterations": self.mission.iteration,
                        "elapsed": self.mission.elapsed_seconds,
                    })
                    logger.info("Mission COMPLETE! Both flags captured.")
                    break

            if self.mission.is_over_limit():
                await self.events.emit("mission_timeout", {
                    "iterations": self.mission.iteration,
                    "evidence": self.evidence.to_dict(),
                })
                logger.warning("Mission hit iteration limit (%d)", self.mission.max_iterations)

        except Exception as e:
            logger.exception("Agent error: %s", e)
            await self.events.emit("error", {"error": str(e)})
            raise

    async def _step(self) -> None:
        """Execute a single agent step: plan → execute → observe → reason."""
        iteration = self.mission.iteration + 1

        # Build context for the LLM
        system = SYSTEM_PROMPT.format(
            target_ip=self.mission.target_ip,
            phase=self.mission.current_phase.value,
            objective=self.mission.current_objective,
            evidence=self.evidence.summary(),
            history=self._format_history(),
        )

        messages = [{"role": "user", "content": "Analyze the situation and choose the next action."}]

        await self.events.emit("thinking", {
            "iteration": iteration,
            "phase": self.mission.current_phase.value,
        })

        # 1. PLAN: Ask LLM what to do
        response = await self.llm.complete(
            messages=messages,
            tools=self.tools.get_definitions(),
            system=system,
        )

        thinking = response.content
        await self.events.emit("thought", {
            "iteration": iteration,
            "thinking": thinking,
        })

        if not response.has_tool_calls:
            # LLM didn't call a tool - record as note and continue
            self.evidence.add_note(f"Agent reflection: {thinking}")
            self.mission.add_history(HistoryEntry(
                iteration=iteration,
                phase=self.mission.current_phase.value,
                thinking=thinking,
                tool_name="none",
                tool_args={},
                output="[No tool called - agent reflected]",
            ))
            return

        # 2. EXECUTE: Run the selected tool
        tool_call = response.tool_calls[0]
        tool = self.tools.get(tool_call.name)

        if not tool:
            logger.warning("LLM requested unknown tool: %s", tool_call.name)
            self.mission.add_history(HistoryEntry(
                iteration=iteration,
                phase=self.mission.current_phase.value,
                thinking=thinking,
                tool_name=tool_call.name,
                tool_args=tool_call.arguments,
                output=f"Error: Unknown tool '{tool_call.name}'",
            ))
            return

        await self.events.emit("command_executing", {
            "iteration": iteration,
            "tool": tool_call.name,
            "args": tool_call.arguments,
            "thinking": thinking,
        })

        result = await tool.execute(self.ssh, **tool_call.arguments)

        await self.events.emit("command_executed", {
            "iteration": iteration,
            "tool": tool_call.name,
            "args": tool_call.arguments,
            "output": result.output[:2000],  # Truncate for event
            "success": result.success,
        })

        # 3. OBSERVE: Extract evidence from results
        await self._extract_evidence(result.output, tool_call.name, result.parsed)

        # 4. REASON: Update phase if needed
        await self._evaluate_phase()

        # Record history
        self.mission.add_history(HistoryEntry(
            iteration=iteration,
            phase=self.mission.current_phase.value,
            thinking=thinking,
            tool_name=tool_call.name,
            tool_args=tool_call.arguments,
            output=result.output[:2000],
        ))

    async def _extract_evidence(
        self,
        output: str,
        tool_name: str,
        parsed: dict[str, Any],
    ) -> None:
        """Extract structured evidence from tool output."""
        # Extract ports from nmap results
        if tool_name == "nmap" and "ports" in parsed:
            for p in parsed["ports"]:
                if p["state"] == "open":
                    self.evidence.add_port(Port(
                        number=p["port"],
                        protocol=p["protocol"],
                        state=p["state"],
                        service=p["service"],
                        version=p.get("version", ""),
                    ))

        # Check for flag patterns in any output
        flag_patterns = [
            (r"[a-f0-9]{32}", "Possible flag hash"),
            (r"HTB\{[^}]+\}", "HTB flag"),
            (r"flag\{[^}]+\}", "CTF flag"),
        ]

        for pattern, desc in flag_patterns:
            matches = re.findall(pattern, output)
            for match in matches:
                self.evidence.add_note(f"Found {desc}: {match}")

                # Try to determine if it's user or root flag
                if "user.txt" in output.lower() or "desktop" in output.lower():
                    self.evidence.add_flag("user", match)
                    await self.events.emit("flag_captured", {"type": "user", "value": match})
                elif "root.txt" in output.lower() or "/root/" in output.lower():
                    self.evidence.add_flag("root", match)
                    await self.events.emit("flag_captured", {"type": "root", "value": match})

        # Emit evidence update
        await self.events.emit("evidence_updated", self.evidence.to_dict())

    async def _evaluate_phase(self) -> None:
        """Evaluate if the agent should move to the next phase."""
        phase = self.mission.current_phase

        # Auto-advance based on evidence
        if phase == Phase.RECON and len(self.evidence.ports) > 0:
            if self.mission.phase_elapsed_seconds > 120:  # 2 min in recon with ports found
                self.mission.set_phase(Phase.ENUMERATION)
                await self.events.emit("phase_changed", {"phase": "enumeration"})

        elif phase == Phase.ENUMERATION:
            if self.evidence.vulnerabilities or self.evidence.credentials:
                self.mission.set_phase(Phase.EXPLOITATION)
                await self.events.emit("phase_changed", {"phase": "exploitation"})
            elif self.mission.phase_elapsed_seconds > self.config.agent.phase_timeout:
                self.mission.set_phase(Phase.EXPLOITATION)
                await self.events.emit("phase_changed", {"phase": "exploitation", "reason": "timeout"})

        elif phase == Phase.EXPLOITATION:
            if self.evidence.has_user_flag:
                self.mission.set_phase(Phase.PRIVESC)
                await self.events.emit("phase_changed", {"phase": "privesc"})

        elif phase == Phase.PRIVESC:
            if self.evidence.has_root_flag:
                self.mission.set_phase(Phase.POST_EXPLOIT)
                await self.events.emit("phase_changed", {"phase": "post_exploit"})

    def _format_history(self) -> str:
        """Format recent history for the LLM context."""
        entries = self.mission.recent_history(15)
        if not entries:
            return "[No previous actions]"

        lines = []
        for e in entries:
            output_preview = e.output[:500] if e.output else "[no output]"
            lines.append(
                f"[Step {e.iteration}] [{e.phase}] Tool: {e.tool_name}\n"
                f"  Args: {json.dumps(e.tool_args, default=str)}\n"
                f"  Output: {output_preview}\n"
            )
        return "\n".join(lines)

    async def inject_command(self, tool_name: str, args: dict[str, Any]) -> str:
        """Manually inject a command from the puppet master."""
        tool = self.tools.get(tool_name)
        if not tool:
            return f"Unknown tool: {tool_name}"

        result = await tool.execute(self.ssh, **args)

        self.mission.add_history(HistoryEntry(
            iteration=self.mission.iteration + 1,
            phase=self.mission.current_phase.value,
            thinking="[Manual injection from puppet master]",
            tool_name=tool_name,
            tool_args=args,
            output=result.output[:2000],
        ))

        await self._extract_evidence(result.output, tool_name, result.parsed)

        return result.output
